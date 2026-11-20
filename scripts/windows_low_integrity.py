"""Set mandatory labels on disposable test objects and launch one low-integrity child."""
from contextlib import ExitStack
import ctypes as c
from ctypes import wintypes as w
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys


class SidAndAttributes(c.Structure):
    _fields_ = [('sid', c.c_void_p), ('attributes', w.DWORD)]


class StartupInfo(c.Structure):
    _fields_ = [
        ('size', w.DWORD), ('reserved', w.LPWSTR), ('desktop', w.LPWSTR), ('title', w.LPWSTR),
        ('x', w.DWORD), ('y', w.DWORD), ('xsize', w.DWORD), ('ysize', w.DWORD),
        ('xchars', w.DWORD), ('ychars', w.DWORD), ('fill', w.DWORD), ('flags', w.DWORD),
        ('show', w.WORD), ('reserved_size', w.WORD), ('reserved_bytes', c.c_void_p),
        ('stdin', w.HANDLE), ('stdout', w.HANDLE), ('stderr', w.HANDLE),
    ]


class ProcessInfo(c.Structure):
    _fields_ = [('process', w.HANDLE), ('thread', w.HANDLE), ('pid', w.DWORD), ('tid', w.DWORD)]


def winapi(dll, name, result, *types):
    api = getattr(c.WinDLL(dll, use_last_error=True), name)
    api.argtypes = types
    api.restype = result
    return api


BOOL, DWORD, HANDLE, PTR = w.BOOL, w.DWORD, w.HANDLE, c.c_void_p
if os.name == 'nt':
    local_free = winapi('kernel32', 'LocalFree', PTR, PTR)
    close = winapi('kernel32', 'CloseHandle', BOOL, HANDLE)
    current_process = winapi('kernel32', 'GetCurrentProcess', HANDLE)
    get_std_handle = winapi('kernel32', 'GetStdHandle', HANDLE, DWORD)
    set_handle_flags = winapi('kernel32', 'SetHandleInformation', BOOL, HANDLE, DWORD, DWORD)
    wait = winapi('kernel32', 'WaitForSingleObject', DWORD, HANDLE, DWORD)
    get_exit_code = winapi('kernel32', 'GetExitCodeProcess', BOOL, HANDLE, c.POINTER(DWORD))
    terminate = winapi('kernel32', 'TerminateProcess', BOOL, HANDLE, DWORD)
    open_file = winapi('kernel32', 'CreateFileW', HANDLE, w.LPCWSTR, DWORD, DWORD, PTR, DWORD, DWORD, HANDLE)
    to_descriptor = winapi('advapi32', 'ConvertStringSecurityDescriptorToSecurityDescriptorW', BOOL,
                           w.LPCWSTR, DWORD, c.POINTER(PTR), c.POINTER(DWORD))
    get_sacl = winapi('advapi32', 'GetSecurityDescriptorSacl', BOOL, PTR, c.POINTER(BOOL), c.POINTER(PTR), c.POINTER(BOOL))
    set_file_security = winapi('advapi32', 'SetNamedSecurityInfoW', DWORD, w.LPWSTR, DWORD, DWORD, PTR, PTR, PTR, PTR)
    open_token = winapi('advapi32', 'OpenProcessToken', BOOL, HANDLE, DWORD, c.POINTER(HANDLE))
    restrict_token = winapi('advapi32', 'CreateRestrictedToken', BOOL, HANDLE, DWORD, DWORD, PTR,
                            DWORD, PTR, DWORD, PTR, c.POINTER(HANDLE))
    convert_sid = winapi('advapi32', 'ConvertStringSidToSidW', BOOL, w.LPCWSTR, c.POINTER(PTR))
    sid_length = winapi('advapi32', 'GetLengthSid', DWORD, PTR)
    sid_count = winapi('advapi32', 'GetSidSubAuthorityCount', c.POINTER(c.c_ubyte), PTR)
    sid_authority = winapi('advapi32', 'GetSidSubAuthority', c.POINTER(DWORD), PTR, DWORD)
    set_token = winapi('advapi32', 'SetTokenInformation', BOOL, HANDLE, DWORD, PTR, DWORD)
    get_token = winapi('advapi32', 'GetTokenInformation', BOOL, HANDLE, DWORD, PTR, DWORD, c.POINTER(DWORD))
    spawn = winapi('advapi32', 'CreateProcessAsUserW', BOOL, HANDLE, w.LPCWSTR, w.LPWSTR, PTR, PTR,
                   BOOL, DWORD, PTR, w.LPCWSTR, c.POINTER(StartupInfo), c.POINTER(ProcessInfo))


def check(ok):
    if not ok:
        raise c.WinError(c.get_last_error())


def set_mandatory_label(path: Path, sddl: str):
    descriptor, sacl = PTR(), PTR()
    present, defaulted = BOOL(), BOOL()
    check(to_descriptor(sddl, 1, c.byref(descriptor), None))
    try:
        check(get_sacl(descriptor, c.byref(present), c.byref(sacl), c.byref(defaulted)))
        if not present.value or not sacl:
            raise ValueError('Descriptor lacks a mandatory SACL.')
        error = set_file_security(str(path), 1, 0x10, None, None, None, sacl)
        if error:
            raise c.WinError(error)
    finally:
        local_free(descriptor)


def integrity_rid(process):
    handle = HANDLE()
    check(open_token(process, 0x0008, c.byref(handle)))  # TOKEN_QUERY
    try:
        size = DWORD()
        get_token(handle, 25, None, 0, c.byref(size))  # TokenIntegrityLevel
        buffer = c.create_string_buffer(size.value)
        check(get_token(handle, 25, buffer, size, c.byref(size)))
        sid = c.cast(buffer, c.POINTER(SidAndAttributes)).contents.sid
        return sid_authority(sid, sid_count(sid)[0] - 1)[0]
    finally:
        close(handle)


def launch(argv):
    with ExitStack() as stack:
        source, token, sid = HANDLE(), HANDLE(), PTR()
        check(open_token(current_process(), 0x008B, c.byref(source)))  # ASSIGN_PRIMARY, DUPLICATE, QUERY, ADJUST_DEFAULT
        stack.callback(close, source)
        check(restrict_token(source, 0x01, 0, None, 0, None, 0, None, c.byref(token)))  # DISABLE_MAX_PRIVILEGE
        stack.callback(close, token)
        check(convert_sid('S-1-16-4096', c.byref(sid)))
        stack.callback(local_free, sid)
        label = SidAndAttributes(sid, 0x20)  # SE_GROUP_INTEGRITY
        check(set_token(token, 25, c.byref(label), c.sizeof(label) + sid_length(sid)))

        startup = StartupInfo()
        startup.size = c.sizeof(startup)
        startup.flags = 0x100  # STARTF_USESTDHANDLES
        startup.stdin, startup.stdout, startup.stderr = [get_std_handle(DWORD(-i)) for i in (10, 11, 12)]
        for handle in (startup.stdin, startup.stdout, startup.stderr):
            check(set_handle_flags(handle, 1, 1))
        child = ProcessInfo()
        arguments = c.create_unicode_buffer(subprocess.list2cmdline(argv))
        # Start suspended to verify the actual child token before it can execute.
        flags = 0x08000000 | 0x00000004  # CREATE_NO_WINDOW, CREATE_SUSPENDED
        check(spawn(token, argv[0], arguments, None, None, True, flags, None, os.getcwd(),
                    c.byref(startup), c.byref(child)))
        stack.callback(close, child.process)
        stack.callback(close, child.thread)
        try:
            rid = integrity_rid(child.process)
            if rid != 4096:
                raise RuntimeError(f'Child token integrity is {rid}, expected low (4096).')
            print(json.dumps({'child_integrity_rid': rid}), file=sys.stderr, flush=True)
            resume = winapi('kernel32', 'ResumeThread', DWORD, HANDLE)
            if resume(child.thread) == 0xFFFFFFFF:
                raise c.WinError(c.get_last_error())
            if wait(child.process, 0xFFFFFFFF) != 0:
                raise c.WinError(c.get_last_error())
            status = DWORD()
            check(get_exit_code(child.process, c.byref(status)))
            return status.value
        except BaseException:
            terminate(child.process, 1)
            raise


def inspect_paths(allowed, protected):
    digest = sha256(allowed.read_bytes()).hexdigest()
    handle = open_file(str(protected), 0x80000000, 7, None, 3, 0x80, None)  # GENERIC_READ, OPEN_EXISTING
    error = c.get_last_error() if handle == PTR(-1).value else 0
    if handle != PTR(-1).value:
        close(handle)
    print(json.dumps({'integrity_rid': integrity_rid(current_process()), 'input_sha256': digest,
                      'protected_open_win32': error}))


if __name__ == '__main__':
    if os.name != 'nt' or len(sys.argv) < 2:
        raise SystemExit('Usage on Windows: windows_low_integrity.py <executable> <args>')
    if len(sys.argv) == 4 and sys.argv[1] == '--probe':
        inspect_paths(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        raise SystemExit(launch(sys.argv[1:]))
