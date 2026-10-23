from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.controlled_probe_mcp import MARKER, ProbeServer


class ControlledProbeMcpTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name)
        self.journal = self.workspace / "mcp-events.jsonl"

    def server(self, mode="success"):
        return ProbeServer(self.workspace, mode, self.journal)

    def frame(self, method="tools/call", arguments=None):
        return {"jsonrpc": "2.0", "id": 3, "method": method, "params": {
            "name": "probe_commit", "arguments": arguments if arguments is not None
            else {"text": "中\n  空格\r\n", "destination": "artifact.txt"}}}

    def test_initialize_echoes_version_and_lists_only_the_fixed_schema(self):
        server = self.server()
        reply = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                               "params": {"protocolVersion": "2026-07-28"}})
        self.assertEqual(reply["result"]["protocolVersion"], "2026-07-28")
        self.assertEqual(reply["result"]["capabilities"], {"tools": {}})
        tools = server.handle(self.frame("tools/list"))["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], ["probe_commit"])
        self.assertEqual(tools[0]["inputSchema"]["additionalProperties"], False)
        self.assertEqual(set(tools[0]["inputSchema"]["required"]), {"text", "destination"})

    def test_success_records_exact_utf8_and_audits_actual_request_and_result(self):
        frame = self.frame()
        reply = self.server().handle(frame)
        data = frame["params"]["arguments"]["text"].encode("utf-8")
        self.assertEqual((self.workspace / "artifact.txt").read_bytes(), data)
        payload = json.loads(reply["result"]["content"][0]["text"])
        self.assertEqual(payload, {"marker": MARKER, "mode": "success", "bytes": len(data),
                                  "sha256": hashlib.sha256(data).hexdigest()})
        record = json.loads(self.journal.read_text(encoding="utf-8"))
        self.assertEqual(record["request"], frame)
        self.assertEqual(record["response"], reply)
        self.assertGreaterEqual(datetime.fromisoformat(record["completed_at"]),
                                datetime.fromisoformat(record["received_at"]))
        self.assertGreaterEqual(record["elapsed_ms"], 0)

    def test_error_mode_returns_fixture_denial_without_creating_artifact(self):
        reply = self.server("error").handle(self.frame())
        self.assertTrue(reply["result"]["isError"])
        self.assertEqual(json.loads(reply["result"]["content"][0]["text"]),
                         {"marker": MARKER, "mode": "error", "code": "E_FIXTURE_DENIED"})
        self.assertFalse((self.workspace / "artifact.txt").exists())

    def test_extra_keys_types_and_all_other_destinations_are_rejected(self):
        server = self.server()
        invalid = [
            {"text": "a", "destination": "../outside.txt"},
            {"text": "a", "destination": str(self.workspace / "artifact.txt")},
            {"text": "a", "destination": "artifact.txt", "extra": True},
            {"text": 3, "destination": "artifact.txt"},
            {"text": "a"},
            {"text": "\ud800", "destination": "artifact.txt"},
        ]
        for arguments in invalid:
            with self.subTest(arguments=ascii(arguments)):
                self.assertEqual(server.handle(self.frame(arguments=arguments))["error"]["code"], -32602)
        frame = self.frame(); frame["params"]["name"] = "write_anywhere"
        self.assertEqual(server.handle(frame)["error"]["code"], -32602)
        self.assertFalse((self.workspace / "artifact.txt").exists())

    def test_existing_artifact_is_never_overwritten(self):
        target = self.workspace / "artifact.txt"
        target.write_bytes(b"preserve existing")
        reply = self.server().handle(self.frame())
        self.assertEqual(reply["error"]["code"], -32602)
        self.assertEqual(target.read_bytes(), b"preserve existing")

    def test_notifications_never_respond_or_call_the_tool(self):
        server = self.server()
        for method in ("initialize", "notifications/initialized", "tools/call", "ping"):
            frame = self.frame(method); del frame["id"]
            self.assertIsNone(server.handle(frame))
        self.assertFalse((self.workspace / "artifact.txt").exists())
        rows = [json.loads(line) for line in self.journal.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["request"]["method"] for row in rows], ["initialize", "tools/call"])
        self.assertTrue(all(row["response"] is None for row in rows))

    def test_stdio_survives_bad_json_and_emits_only_jsonrpc(self):
        requests = ["invalid json", '{"jsonrpc":"2.0","id":1,"id":2,"method":"ping"}',
                    json.dumps({"jsonrpc": "2.0", "id": 4, "method": "ping"}),
                    json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})]
        output = io.StringIO()
        self.server().run(io.StringIO("\n".join(requests) + "\n"), output)
        rows = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(len(rows), 3)
        self.assertEqual([row.get("error", {}).get("code") for row in rows[:2]], [-32700, -32700])
        self.assertEqual(rows[2], {"jsonrpc": "2.0", "id": 4, "result": {}})
        self.assertFalse(self.journal.exists())

    def test_artifact_and_workspace_symlinks_are_rejected_if_supported(self):
        original = self.workspace / "original.txt"; original.write_bytes(b"unchanged")
        target = self.workspace / "artifact.txt"
        linked_workspace = self.workspace / "linked-workspace"
        real_workspace = self.workspace / "real-workspace"; real_workspace.mkdir()
        try:
            target.symlink_to(original)
            linked_workspace.symlink_to(real_workspace, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"OS does not permit test symlinks: {error}")
        self.assertEqual(self.server().handle(self.frame())["error"]["code"], -32602)
        self.assertEqual(original.read_bytes(), b"unchanged")
        with self.assertRaises(ValueError):
            ProbeServer(linked_workspace, "success", self.journal)

    def test_cli_roundtrip_uses_utf8_in_a_fresh_process(self):
        command = [sys.executable, "-X", "utf8", str(Path(__file__).resolve().parents[1]
                   / "scripts/controlled_probe_mcp.py"), "--workspace", str(self.workspace),
                   "--mode", "success", "--journal", str(self.journal)]
        completed = subprocess.run(command, input=json.dumps(self.frame(), ensure_ascii=False) + "\n",
                                   text=True, encoding="utf-8", capture_output=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        reply = json.loads(completed.stdout)
        self.assertEqual(reply["result"]["content"][0]["type"], "text")
        self.assertEqual((self.workspace / "artifact.txt").read_bytes(), "中\n  空格\r\n".encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
