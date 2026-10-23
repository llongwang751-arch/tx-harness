"""Strict WorkBuddy transport diagnostics with metadata-only request logging.

This is a deterministic fixture, not an agent. Tool-less auxiliary traffic is
bounded separately from the single frozen tool call and its correlated return.
No request messages, tool descriptions, Skill bodies, headers or raw outputs
are written to the journal. Unknown tool spelling or schema fails calibration.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading
import time


MODEL = "fixed-tool-v1"
MARKER = "CONTROLLED_TOOL_V1"
CALL_ID = "call_controlled_1"
TARGET = "mcp__contract__probe_commit"
AUXILIARY_TEXT = "CONTROLLED_AUXILIARY"
TERMINAL_TEXT = "CONTROLLED_DONE"
MAX_AUXILIARY = 3
NAME = re.compile(r"[A-Za-z0-9_.:-]{1,256}")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def schema_digest(schema):
    return digest(json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8"))


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def tool_metadata(tools, namespace=None):
    result = []
    if not isinstance(tools, list):
        raise ValueError("Tool declarations must be a list")
    for tool in tools:
        if not isinstance(tool, dict):
            raise ValueError("Tool declaration must be an object")
        if tool.get("type") == "namespace":
            name = tool.get("name")
            if not isinstance(name, str) or not NAME.fullmatch(name):
                raise ValueError("Invalid namespace spelling")
            result.extend(tool_metadata(tool.get("tools", []), name))
            continue
        function = tool.get("function", tool)
        if not isinstance(function, dict):
            raise ValueError("Function declaration must be an object")
        name = function.get("name")
        valid_name = isinstance(name, str) and NAME.fullmatch(name) is not None
        schema = function.get("parameters", function.get("inputSchema"))
        result.append({"name": name if valid_name else None,
                       "invalid_name_sha256": None if valid_name else digest(encoded(name)),
                       "namespace": namespace,
                       "canonical_name": (namespace + "__" if namespace else "") + name if valid_name else None,
                       "schema_sha256": schema_digest(schema), "schema_present": schema is not None})
    return result


def marker_objects(value):
    if isinstance(value, dict):
        if value.get("marker") == MARKER:
            return [value]
        return [result for child in value.values() for result in marker_objects(child)]
    if isinstance(value, list):
        return [result for child in value for result in marker_objects(child)]
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except ValueError:
            decoded = None
        if isinstance(decoded, (dict, list)):
            return marker_objects(decoded)
        found = []
        for match in re.finditer(r'\{\s*"marker"\s*:', value):
            try:
                decoded, _ = json.JSONDecoder().raw_decode(value[match.start():])
            except ValueError:
                continue
            if isinstance(decoded, dict) and decoded.get("marker") == MARKER:
                found.append(decoded)
        return found
    return []


def safe_marker(payload):
    """Record only fixed fixture fields; arbitrary marked content is not echoed."""
    result = {"marker": MARKER}
    if isinstance(payload.get("mode"), str) and payload["mode"] in {"success", "error"}:
        result["mode"] = payload["mode"]
    if type(payload.get("bytes")) is int:
        result["bytes"] = payload["bytes"]
    if isinstance(payload.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", payload["sha256"]):
        result["sha256"] = payload["sha256"]
    if payload.get("code") == "E_FIXTURE_DENIED":
        result["code"] = payload["code"]
    return result


def chat_frames(item, number):
    delta = {"role": "assistant", "content": None}
    if item["type"] == "function_call":
        delta["tool_calls"] = [{"index": 0, "id": CALL_ID, "type": "function",
                                 "function": {"name": item["name"], "arguments": item["arguments"]}}]
        finish = "tool_calls"
    else:
        delta["content"] = item["text"]
        finish = "stop"
    base = {"id": "chatcmpl_workbuddy_v2_" + str(number), "object": "chat.completion.chunk",
            "created": int(time.time()), "model": MODEL}
    return [{**base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
            {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": finish}],
             "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}]


class DiagnosticState:
    def __init__(self, arguments, schema, mode, journal):
        if mode not in {"success", "error"}:
            raise ValueError("Unsupported fixture mode")
        self.arguments = arguments
        self.schema_sha256 = schema_digest(schema)
        data = arguments["text"].encode("utf-8")
        self.expected_payload = ({"marker": MARKER, "mode": "success", "bytes": len(data), "sha256": digest(data)}
                                 if mode == "success" else
                                 {"marker": MARKER, "mode": "error", "code": "E_FIXTURE_DENIED"})
        self.journal = Path(journal)
        self.lock = threading.Lock()
        self.requests = self.auxiliary_requests = self.main_model_requests = self.rejected_requests = 0
        self.failed = False

    def record(self, item):
        with self.journal.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps({"at": now(), **item}, ensure_ascii=False) + "\n")

    def reject(self, reason):
        self.failed = True
        self.rejected_requests += 1
        self.record({"kind": "fixture_rejection", "sequence": self.requests, "reason": reason})
        raise ValueError(reason)

    def answer(self, path, body, raw):
        with self.lock:
            self.requests += 1
            if not isinstance(body, dict):
                self.record({"kind": "model_request", "sequence": self.requests, "path": path,
                             "request_bytes": len(raw), "request_sha256": digest(raw),
                             "metadata_parse_failed": True, "tool_metadata": []})
                return self.reject("Request must be a JSON object")
            tools = body.get("tools", [])
            try:
                metadata = tool_metadata(tools)
            except (ValueError, TypeError):
                self.record({"kind": "model_request", "sequence": self.requests, "path": path,
                             "request_bytes": len(raw), "request_sha256": digest(raw),
                             "metadata_parse_failed": True, "tool_metadata": []})
                return self.reject("Cannot parse standard tool metadata")
            messages = body.get("messages", [])
            if not isinstance(messages, list):
                self.record({"kind": "model_request", "sequence": self.requests, "path": path,
                             "request_bytes": len(raw), "request_sha256": digest(raw),
                             "metadata_parse_failed": True, "tool_metadata": metadata})
                return self.reject("Messages must be a list")
            returns = [row for row in messages if isinstance(row, dict) and row.get("role") == "tool"]
            matched = [row for row in returns if row.get("tool_call_id") == CALL_ID]
            payloads = [payload for row in matched for payload in marker_objects(row.get("content"))]
            self.record({"kind": "model_request", "sequence": self.requests, "path": path,
                         "request_bytes": len(raw), "request_sha256": digest(raw),
                         "model_is_expected": body.get("model") == MODEL,
                         "tool_metadata": metadata, "tool_return_count": len(returns),
                         "matched_fixed_call_count": len(matched),
                         "fixed_call_id_present": len(matched) == 1,
                         "fixture_return_payloads": [safe_marker(payload) for payload in payloads],
                         "exact_fixture_payload_match": payloads == [self.expected_payload],
                         "main_stage_before": self.main_model_requests,
                         "privacy": "No raw messages, descriptions, Skill text, headers or tool outputs recorded"})
            if self.failed:
                return self.reject("Fixture already rejected an earlier request; no recovery within this calibration")
            if path != "/v1/chat/completions" or body.get("model") != MODEL:
                return self.reject("Unexpected protocol endpoint or model identity")
            if returns:
                if self.main_model_requests != 1 or len(returns) != 1 or len(matched) != 1 or payloads != [self.expected_payload]:
                    return self.reject("Need one exact fixed-call tool result after the single frozen dispatch")
                self.main_model_requests = 2
                self.record({"kind": "fixed_terminal", "sequence": self.requests, "main_sequence": 2,
                             "call_id": CALL_ID, "text": TERMINAL_TEXT})
                return {"type": "text", "text": TERMINAL_TEXT}
            if not metadata:
                if self.auxiliary_requests >= MAX_AUXILIARY:
                    return self.reject("Tool-less auxiliary request limit exceeded")
                self.auxiliary_requests += 1
                self.record({"kind": "fixed_auxiliary", "sequence": self.requests,
                             "auxiliary_sequence": self.auxiliary_requests, "text": AUXILIARY_TEXT,
                             "classification": "tool-less and no tool return; purpose not inferred from hidden context"})
                return {"type": "text", "text": AUXILIARY_TEXT}
            # Other built-in declarations may be present. Only one exact,
            # explicitly recognized contract target can ever be dispatched.
            candidates = [row for row in metadata if row["canonical_name"] == TARGET]
            near = [row for row in metadata if row.get("name") and row["name"].endswith("probe_commit")]
            if (self.main_model_requests != 0 or len(candidates) != 1 or len(near) != 1
                    or candidates[0]["schema_sha256"] != self.schema_sha256):
                return self.reject("No unique allowlisted target with the exact registered input schema")
            self.main_model_requests = 1
            selected = candidates[0]
            self.record({"kind": "fixed_tool_request", "sequence": self.requests, "main_sequence": 1,
                         "native_tool": selected, "call_id": CALL_ID, "arguments": self.arguments,
                         "arguments_sha256": digest(encoded(self.arguments)),
                         "registered_schema_sha256": self.schema_sha256})
            return {"type": "function_call", "name": selected["name"], "call_id": CALL_ID,
                    "arguments": encoded(self.arguments).decode("utf-8")}


class DiagnosticServer:
    def __init__(self, arguments, schema, mode, journal):
        state = self.state = DiagnosticState(arguments, schema, mode, journal)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                payload = encoded({"object": "list", "data": [{"id": MODEL, "object": "model", "owned_by": "local-fixture"}]})
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)

            def do_POST(self):
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= 16 * 1024 * 1024:
                        raise ValueError("Unexpected request size")
                    raw = self.rfile.read(size)
                    body = json.loads(raw)
                    item = state.answer(self.path, body, raw)
                    self.send_response(200); self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Connection", "close"); self.send_header("Cache-Control", "no-cache"); self.end_headers()
                    for frame in chat_frames(item, state.requests):
                        self.wfile.write(b"data: " + encoded(frame) + b"\n\n")
                    self.wfile.write(b"data: [DONE]\n\n"); self.wfile.flush(); self.close_connection = True
                except Exception as error:
                    # Exception text can contain malformed request data. Only its
                    # class is retained; rejection reasons above are fixed strings.
                    state.record({"kind": "fixture_transport_error", "error_type": type(error).__name__})
                    payload = encoded({"error": {"message": "Strict WorkBuddy v2 fixture rejected request",
                                                  "type": "fixture_protocol_error"}})
                    self.send_response(400); self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)

        self.http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.http.server_port}/v1"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.http.shutdown(); self.http.server_close(); self.thread.join(timeout=5)
