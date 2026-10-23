"""A deterministic stdio MCP fixture; never an agent or a model implementation.

Only the explicitly supplied workspace and journal are writable. The MCP process
is a trusted host tool: its writes do not test a product's filesystem sandbox.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time


MARKER = "CONTROLLED_TOOL_V1"
TOOL = {
    "name": "probe_commit",
    "description": "Commit the supplied UTF-8 text to the fixed artifact.txt fixture.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "destination": {"type": "string"},
        },
        "required": ["text", "destination"],
        "additionalProperties": False,
    },
}


def compact(value):
    # Escaped JSON also preserves malformed surrogate inputs in rejected-call
    # audit records without turning an argument error into a logging crash.
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _reparse_or_link(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def safe_directory(path):
    """Reject existing symlink/junction components before resolving a directory."""
    absolute = Path(path).absolute()
    for component in (absolute, *absolute.parents):
        if _reparse_or_link(component):
            raise ValueError("Symlink or reparse-point directory is not allowed")
    if not absolute.is_dir():
        raise ValueError("An existing explicit directory is required")
    return absolute.resolve(strict=True)


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


class RpcError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


class ProbeServer:
    def __init__(self, workspace, mode, journal):
        if mode not in {"success", "error"}:
            raise ValueError("Unsupported fixture mode")
        self.workspace = safe_directory(workspace)
        self.mode = mode
        journal = Path(journal).absolute()
        self.journal_parent = safe_directory(journal.parent)
        self.journal = self.journal_parent / journal.name
        if self.journal == self.workspace / "artifact.txt":
            raise ValueError("Journal must differ from the artifact")
        if os.path.lexists(self.journal):
            if _reparse_or_link(self.journal) or not self.journal.is_file():
                raise ValueError("Journal must be a regular file")

    def audit(self, request, response, received_at, started_ns):
        # Recheck static directory links for every effect. Exclusive artifact
        # creation below also prevents overwriting a raced-in final component.
        if safe_directory(self.journal_parent) != self.journal_parent:
            raise ValueError("Journal directory changed")
        if os.path.lexists(self.journal) and _reparse_or_link(self.journal):
            raise ValueError("Journal symlink is not allowed")
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        flags |= getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        record = {
            "received_at": received_at,
            "completed_at": utc_now(),
            "elapsed_ms": (time.monotonic_ns() - started_ns) / 1_000_000,
            "pid": os.getpid(),
            "mode": self.mode,
            "request": request,
            "response": response,
        }
        with os.fdopen(os.open(self.journal, flags, 0o600), "ab") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("Journal must remain a regular file")
            stream.write((compact(record) + "\n").encode("utf-8"))
            stream.flush()

    def call(self, params):
        if not isinstance(params, dict) or params.get("name") != "probe_commit":
            raise RpcError(-32602, "Only probe_commit is supported")
        arguments = params.get("arguments")
        if not isinstance(arguments, dict) or set(arguments) != {"text", "destination"}:
            raise RpcError(-32602, "Expected exactly text and destination")
        if not isinstance(arguments["text"], str) or arguments["destination"] != "artifact.txt":
            raise RpcError(-32602, "Expected string text and destination artifact.txt")
        try:
            data = arguments["text"].encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            raise RpcError(-32602, "Text must be valid UTF-8") from None
        if self.mode == "error":
            payload = {"marker": MARKER, "mode": "error", "code": "E_FIXTURE_DENIED"}
            return {"content": [{"type": "text", "text": compact(payload)}], "isError": True}

        if safe_directory(self.workspace) != self.workspace:
            raise RpcError(-32603, "Workspace directory changed")
        target = self.workspace / "artifact.txt"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            with os.fdopen(os.open(target, flags, 0o600), "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            raise RpcError(-32602, "Artifact already exists; overwrite refused") from None
        except OSError:
            raise RpcError(-32603, "Artifact creation failed") from None
        payload = {
            "marker": MARKER,
            "mode": "success",
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        return {"content": [{"type": "text", "text": compact(payload)}]}

    def handle(self, request):
        received_at, started_ns = utc_now(), time.monotonic_ns()
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return self.error(None, -32600, "Invalid JSON-RPC request")
        method = request.get("method")
        identifier = request.get("id")
        has_id = "id" in request
        if not isinstance(method, str) or (has_id and (isinstance(identifier, bool)
                or not isinstance(identifier, (int, str, type(None))))):
            return self.error(None, -32600, "Invalid JSON-RPC request")
        response = None
        # JSON-RPC notifications never perform a tools/call side effect and never
        # receive a response, including a mistakenly notified initialize.
        if has_id:
            try:
                params = request.get("params", {})
                if method == "initialize":
                    if not isinstance(params, dict) or not isinstance(params.get("protocolVersion"), str):
                        raise RpcError(-32602, "protocolVersion must be a string")
                    result = {
                        "protocolVersion": params["protocolVersion"],
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "controlled-probe-mcp", "version": "1.0.0"},
                    }
                elif method == "tools/list":
                    result = {"tools": [TOOL]}
                elif method == "tools/call":
                    result = self.call(params)
                elif method == "ping":
                    result = {}
                else:
                    raise RpcError(-32601, "Method not found")
                response = {"jsonrpc": "2.0", "id": identifier, "result": result}
            except RpcError as error:
                response = self.error(identifier, error.code, error.message)
        if method in {"initialize", "tools/list", "tools/call"}:
            self.audit(request, response, received_at, started_ns)
        return response

    @staticmethod
    def error(identifier, code, message):
        return {"jsonrpc": "2.0", "id": identifier, "error": {"code": code, "message": message}}

    def run(self, source, destination):
        for line in source:
            try:
                request = json.loads(line, object_pairs_hook=_no_duplicate_keys,
                                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON")))
            except (ValueError, json.JSONDecodeError):
                response = self.error(None, -32700, "Parse error")
            else:
                response = self.handle(request)
            if response is not None:
                destination.write(compact(response) + "\n")
                destination.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--mode", choices=("success", "error"), required=True)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    # Windows pipes otherwise use the account ANSI encoding for stdin/stdout.
    for stream in (sys.stdin, sys.stdout):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="strict", newline="\n")
    try:
        ProbeServer(args.workspace, args.mode, args.journal).run(sys.stdin, sys.stdout)
    except (OSError, ValueError) as error:
        print(f"controlled-probe-mcp: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
