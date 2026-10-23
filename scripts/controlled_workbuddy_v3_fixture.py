"""Fixed ToolSearch discovery bridge; no instructions or search text interpreted.

All dispatches are predetermined. Only declared schemas, standard tool-result
correlation and frozen marker bytes affect the state machine.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time

try:
    from scripts.controlled_workbuddy_v2_fixture import (MODEL, MARKER, CALL_ID, NAME, AUXILIARY_TEXT,
        TERMINAL_TEXT, MAX_AUXILIARY, encoded, digest, schema_digest, now, tool_metadata, marker_objects, safe_marker)
except ModuleNotFoundError:
    from controlled_workbuddy_v2_fixture import (MODEL, MARKER, CALL_ID, NAME, AUXILIARY_TEXT,
        TERMINAL_TEXT, MAX_AUXILIARY, encoded, digest, schema_digest, now, tool_metadata, marker_objects, safe_marker)


SEARCH_ID = "call_search_1"
SEARCH_ARGS = {"query": "+contract probe_commit", "max_results": 1}
TARGETS = {"mcp__contract__probe_commit", "mcp__custom-mcp__contract__probe_commit",
           "mcp__custom_mcp__contract__probe_commit"}
ANNOTATIONS = {"description", "title", "default", "examples", "$comment", "$schema",
               "deprecated", "readOnly", "writeOnly"}
KEYWORDS = {"type", "properties", "required", "additionalProperties", "items", "enum", "const",
            "minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems"}
TYPES = {"object", "array", "string", "integer", "number", "boolean", "null"}


def schema_shape(schema):
    """A description-free structural projection; no arbitrary string values."""
    if not isinstance(schema, dict):
        return {"invalid_schema_kind": type(schema).__name__}
    result = {}
    for key, value in schema.items():
        if key in ANNOTATIONS:
            continue
        if key == "properties" and isinstance(value, dict):
            result[key] = {name: schema_shape(item) for name, item in value.items()
                           if isinstance(name, str) and NAME.fullmatch(name)}
        elif key == "items":
            result[key] = schema_shape(value)
        elif key in {"enum", "const"}:
            result[key + "_sha256"] = digest(encoded(value))
            if key == "enum" and isinstance(value, list): result["enum_count"] = len(value)
        elif key == "type" and isinstance(value, str) and value in TYPES:
            result[key] = value
        elif key == "required" and isinstance(value, list):
            result[key] = [item for item in value if isinstance(item, str) and NAME.fullmatch(item)]
        elif isinstance(value, (bool, int, float)):
            result[key] = value
        else:
            result.setdefault("unsupported_keyword_names", []).append(key if NAME.fullmatch(key) else "<invalid>")
    return result


def supported_schema(schema):
    if not isinstance(schema, dict) or set(schema) - KEYWORDS - ANNOTATIONS:
        raise ValueError("Unsupported JSON Schema keyword or schema form")
    kind = schema.get("type")
    if not isinstance(kind, str) or kind not in TYPES:
        raise ValueError("One explicit standard JSON type is required")
    if "properties" in schema:
        if kind != "object" or not isinstance(schema["properties"], dict):
            raise ValueError("Invalid object properties")
        for child in schema["properties"].values(): supported_schema(child)
    if "additionalProperties" in schema and type(schema["additionalProperties"]) is not bool:
        raise ValueError("Only boolean additionalProperties is supported")
    if "items" in schema: supported_schema(schema["items"])


def validate_schema(schema, value):
    """Deliberately small JSON Schema subset; unknown assertions fail closed."""
    supported_schema(schema)
    kind = schema["type"]
    matches = {"object": isinstance(value, dict), "array": isinstance(value, list),
               "string": isinstance(value, str), "integer": type(value) is int,
               "number": type(value) in (int, float), "boolean": type(value) is bool,
               "null": value is None}
    if not matches[kind]: raise ValueError("Fixed argument does not match declared type")
    if "enum" in schema and (not isinstance(schema["enum"], list) or value not in schema["enum"]):
        raise ValueError("Fixed argument is outside declared enum")
    if "const" in schema and value != schema["const"]: raise ValueError("Fixed argument differs from const")
    for keyword, comparison in (("minimum", lambda n: value >= n), ("maximum", lambda n: value <= n)):
        if keyword in schema:
            if kind not in {"integer", "number"} or type(schema[keyword]) not in (int, float) or not comparison(schema[keyword]):
                raise ValueError("Fixed numeric argument violates declared bound")
    for lower, upper, target in (("minLength", "maxLength", "string"), ("minItems", "maxItems", "array")):
        for key, check in ((lower, lambda n: len(value) >= n), (upper, lambda n: len(value) <= n)):
            if key in schema and (kind != target or type(schema[key]) is not int or schema[key] < 0 or not check(schema[key])):
                raise ValueError("Fixed argument violates declared length bound")
    if kind == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        additional = schema.get("additionalProperties", True)
        if (not isinstance(properties, dict) or not isinstance(required, list)
                or any(not isinstance(key, str) for key in required) or len(required) != len(set(required))
                or type(additional) is not bool or not set(required).issubset(value)):
            raise ValueError("Unsupported or unsatisfied object schema")
        if not additional and set(value) - set(properties): raise ValueError("Additional argument is forbidden")
        for key, child in properties.items():
            # Reject unsupported schemas even for unused optional properties.
            if not isinstance(child, dict) or set(child) - KEYWORDS - ANNOTATIONS:
                raise ValueError("Unsupported property schema")
            if key in value: validate_schema(child, value[key])
    if kind == "array" and "items" in schema:
        for item in value: validate_schema(schema["items"], item)


def search_definition(tools):
    result = []
    for tool in tools:
        function = tool.get("function", tool)
        if isinstance(function, dict) and function.get("name") == "ToolSearch":
            result.append(function)
    if len(result) != 1: raise ValueError("Need one explicitly named ToolSearch declaration")
    schema = result[0].get("parameters")
    if (not isinstance(schema, dict) or schema.get("type") != "object"
            or not {"query", "max_results"}.issubset(schema.get("properties", {}))):
        raise ValueError("ToolSearch must declare query and max_results")
    validate_schema(schema, SEARCH_ARGS)
    return schema


def reference_names(content):
    # Only standard structured content blocks; text strings are never parsed or
    # searched for names, and arbitrary hidden object fields are not traversed.
    result = []
    if isinstance(content, list):
        for item in content: result.extend(reference_names(item))
    elif isinstance(content, dict):
        if content.get("type") == "tool_reference":
            name = content.get("tool_name", content.get("name"))
            if isinstance(name, str) and NAME.fullmatch(name): result.append(name)
        elif isinstance(content.get("content"), list):
            result.extend(reference_names(content["content"]))
    return result


def chat_frames(item, number):
    delta = {"role": "assistant", "content": None}
    if item["type"] == "function_call":
        delta["tool_calls"] = [{"index": 0, "id": item["call_id"], "type": "function",
                                 "function": {"name": item["name"], "arguments": item["arguments"]}}]
        finish = "tool_calls"
    else:
        delta["content"] = item["text"]; finish = "stop"
    base = {"id": "chatcmpl_workbuddy_v3_" + str(number), "object": "chat.completion.chunk",
            "created": int(time.time()), "model": MODEL}
    return [{**base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
            {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": finish}],
             "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}]


class BridgeState:
    def __init__(self, arguments, schema, mode, journal):
        if mode not in {"success", "error"}: raise ValueError("Unsupported fixture mode")
        self.arguments, self.schema_sha256 = arguments, schema_digest(schema)
        data = arguments["text"].encode("utf-8")
        self.expected_payload = ({"marker": MARKER, "mode": "success", "bytes": len(data), "sha256": digest(data)}
                                 if mode == "success" else {"marker": MARKER, "mode": "error", "code": "E_FIXTURE_DENIED"})
        self.journal, self.lock = Path(journal), threading.Lock()
        self.requests = self.auxiliary_requests = self.main_model_requests = self.rejected_requests = 0
        self.discovery_model_requests = self.discovery_calls = 0
        self.discovery_return_sha256 = None
        self.failed = False

    def record(self, item):
        with self.journal.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps({"at": now(), **item}, ensure_ascii=False) + "\n")

    def reject(self, reason):
        self.failed = True; self.rejected_requests += 1
        self.record({"kind": "fixture_rejection", "sequence": self.requests, "reason": reason})
        raise ValueError(reason)

    def answer(self, path, body, raw):
        with self.lock:
            self.requests += 1
            if not isinstance(body, dict): return self.reject("Request must be a JSON object")
            try: metadata = tool_metadata(body.get("tools", []))
            except (ValueError, TypeError): return self.reject("Cannot parse declared tool metadata")
            messages = body.get("messages", [])
            if not isinstance(messages, list): return self.reject("Messages must be a list")
            returns = [row for row in messages if isinstance(row, dict) and row.get("role") == "tool"]
            searches = [row for row in returns if row.get("tool_call_id") == SEARCH_ID]
            probes = [row for row in returns if row.get("tool_call_id") == CALL_ID]
            payloads = [payload for row in probes for payload in marker_objects(row.get("content"))]
            self.record({"kind": "model_request", "sequence": self.requests, "path": path,
                         "request_bytes": len(raw), "request_sha256": digest(raw),
                         "model_is_expected": body.get("model") == MODEL, "tool_metadata": metadata,
                         "tool_return_count": len(returns), "matched_search_count": len(searches),
                         "matched_probe_count": len(probes), "fixture_return_payloads": [safe_marker(p) for p in payloads],
                         "exact_fixture_payload_match": payloads == [self.expected_payload],
                         "main_stage_before": self.main_model_requests,
                         "discovery_calls_before": self.discovery_calls,
                         "privacy": "No messages, descriptions, search text, Skill bodies, headers or raw outputs retained"})
            if self.failed: return self.reject("Earlier request was rejected; no in-run adaptation")
            if path != "/v1/chat/completions" or body.get("model") != MODEL:
                return self.reject("Unexpected protocol endpoint or model identity")
            if self.main_model_requests == 1:
                if (len(probes) != 1 or len(searches) > 1 or len(returns) != len(probes) + len(searches)
                        or payloads != [self.expected_payload]):
                    return self.reject("Need exactly one real fixed-probe return with the exact marker")
                if searches and digest(encoded(searches[0].get("content"))) != self.discovery_return_sha256:
                    return self.reject("Historical ToolSearch return changed")
                self.main_model_requests = 2
                self.record({"kind": "fixed_terminal", "sequence": self.requests, "main_sequence": 2,
                             "call_id": CALL_ID, "text": TERMINAL_TEXT})
                return {"type": "text", "text": TERMINAL_TEXT}
            if self.main_model_requests == 2: return self.reject("Extra request after fixed terminal")
            if self.discovery_calls == 1:
                if len(returns) != 1 or len(searches) != 1:
                    return self.reject("Next bridge request must contain only the actual call_search_1 return")
                content = searches[0].get("content")
                self.discovery_return_sha256 = digest(encoded(content))
                self.record({"kind": "discovery_return", "sequence": self.requests, "call_id": SEARCH_ID,
                             "content_bytes": len(encoded(content)), "content_sha256": self.discovery_return_sha256,
                             "tool_reference_names": reference_names(content)})
            elif returns:
                return self.reject("Unexpected tool history before any frozen dispatch")
            if not metadata:
                if self.discovery_calls: return self.reject("ToolSearch return did not publish the frozen target")
                if self.auxiliary_requests >= MAX_AUXILIARY: return self.reject("Tool-less auxiliary limit exceeded")
                self.auxiliary_requests += 1
                self.record({"kind": "fixed_auxiliary", "sequence": self.requests,
                             "auxiliary_sequence": self.auxiliary_requests, "text": AUXILIARY_TEXT})
                return {"type": "text", "text": AUXILIARY_TEXT}
            candidates = [row for row in metadata if row["canonical_name"] in TARGETS]
            near = [row for row in metadata if row.get("name") and row["name"].endswith("probe_commit")]
            if candidates or near:
                if len(candidates) != 1 or len(near) != 1 or candidates[0]["schema_sha256"] != self.schema_sha256:
                    return self.reject("No unique allowlisted probe with exact frozen schema")
                self.main_model_requests = 1; selected = candidates[0]
                self.record({"kind": "fixed_tool_request", "sequence": self.requests, "main_sequence": 1,
                             "native_tool": selected, "call_id": CALL_ID, "arguments": self.arguments,
                             "arguments_sha256": digest(encoded(self.arguments)),
                             "registered_schema_sha256": self.schema_sha256,
                             "discovery_bridge_used": self.discovery_calls == 1})
                return {"type": "function_call", "name": selected["name"], "call_id": CALL_ID,
                        "arguments": encoded(self.arguments).decode("utf-8")}
            if self.discovery_calls: return self.reject("ToolSearch did not expose the exact frozen target")
            try: search_schema = search_definition(body.get("tools", []))
            except (ValueError, TypeError): return self.reject("ToolSearch declaration cannot validate the fixed bridge arguments")
            self.discovery_calls = self.discovery_model_requests = 1
            self.record({"kind": "fixed_discovery_request", "sequence": self.requests, "discovery_sequence": 1,
                         "name": "ToolSearch", "call_id": SEARCH_ID, "arguments": SEARCH_ARGS,
                         "schema_sha256": schema_digest(search_schema), "validation_schema": schema_shape(search_schema)})
            return {"type": "function_call", "name": "ToolSearch", "call_id": SEARCH_ID,
                    "arguments": encoded(SEARCH_ARGS).decode("utf-8")}


class BridgeServer:
    def __init__(self, arguments, schema, mode, journal):
        state = self.state = BridgeState(arguments, schema, mode, journal)

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
                    payload = encoded({"error": {"message": "Strict WorkBuddy v3 fixture rejected request",
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
