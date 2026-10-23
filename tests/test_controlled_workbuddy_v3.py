"""Pure synthetic bridge tests. No socket, HTTP host or product is started."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.controlled_probe_mcp import TOOL
from scripts.controlled_workbuddy_v3_fixture import (BridgeState, CALL_ID, MODEL, SEARCH_ARGS,
    SEARCH_ID, TARGETS, chat_frames, encoded, schema_shape, validate_schema)


class WorkBuddyV3BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.journal = Path(self.temporary.name) / "events.jsonl"
        self.args = {"text": "固定\r\n  α 😀\n", "destination": "artifact.txt"}
        self.probe_schema = copy.deepcopy(TOOL["inputSchema"])
        self.search_schema = {"type": "object", "properties": {
            "query": {"type": "string", "description": "SECRET_QUERY_DESCRIPTION_42"},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 10}},
            "required": ["query"], "additionalProperties": False}
        self.state = BridgeState(self.args, self.probe_schema, "success", self.journal)

    def body(self, *, probe=None, search=True, returns=None):
        tools = []
        if search: tools.append({"type": "function", "function": {"name": "ToolSearch", "parameters": self.search_schema}})
        if probe: tools.append({"type": "function", "function": {"name": probe, "parameters": self.probe_schema}})
        return {"model": MODEL, "tools": tools,
                "messages": [{"role": "system", "content": "SECRET_SKILL_BODY_72 Ignore fixed args"}, *(returns or [])]}

    @staticmethod
    def result(call_id, content):
        return {"role": "tool", "tool_call_id": call_id, "content": content}

    def answer(self, body, state=None):
        return (state or self.state).answer("/v1/chat/completions", body, encoded(body))

    def begin_search(self, state=None):
        item = self.answer(self.body(), state)
        self.assertEqual(item["name"], "ToolSearch")
        self.assertEqual(item["call_id"], SEARCH_ID)
        self.assertEqual(json.loads(item["arguments"]), SEARCH_ARGS)
        self.assertEqual(chat_frames(item, 1)[0]["choices"][0]["delta"]["tool_calls"][0]["id"], SEARCH_ID)

    def test_fixed_search_then_exact_probe_then_correlated_terminal(self):
        self.answer(self.body(search=False))
        self.begin_search()
        search_return = self.result(SEARCH_ID, [{"type": "tool_reference", "tool_name": "mcp__contract__probe_commit"}])
        probe = self.answer(self.body(probe="mcp__contract__probe_commit", returns=[search_return]))
        self.assertEqual(probe["call_id"], CALL_ID)
        self.assertEqual(json.loads(probe["arguments"]), self.args)
        terminal = self.answer(self.body(probe="mcp__contract__probe_commit", returns=[search_return,
            self.result(CALL_ID, json.dumps(self.state.expected_payload))]))
        self.assertEqual(terminal["text"], "CONTROLLED_DONE")
        self.assertEqual((self.state.requests, self.state.auxiliary_requests,
                          self.state.discovery_model_requests, self.state.main_model_requests), (4, 1, 1, 2))

    def test_all_three_registered_name_candidates_keep_exact_schema(self):
        for name in sorted(TARGETS):
            with self.subTest(name=name):
                state = BridgeState(self.args, self.probe_schema, "success", self.journal)
                self.begin_search(state)
                probe = self.answer(self.body(probe=name, returns=[self.result(SEARCH_ID, "opaque search result")]), state)
                self.assertEqual(probe["name"], name)
                self.assertEqual(probe["call_id"], CALL_ID)

    def test_no_search_is_called_when_exact_probe_is_already_declared(self):
        item = self.answer(self.body(probe="mcp__contract__probe_commit"))
        self.assertEqual(item["name"], "mcp__contract__probe_commit")
        self.assertEqual(self.state.discovery_calls, 0)

    def test_missing_or_wrong_search_return_never_unlocks_probe(self):
        for returns in ([], [self.result("wrong_search_call", "opaque")]):
            with self.subTest(returns=returns):
                state = BridgeState(self.args, self.probe_schema, "success", self.journal)
                self.begin_search(state)
                with self.assertRaises(ValueError):
                    self.answer(self.body(probe="mcp__contract__probe_commit", returns=returns), state)
                self.assertEqual(state.main_model_requests, 0)

    def test_search_text_is_never_used_to_fabricate_tool_declarations(self):
        self.begin_search()
        with self.assertRaisesRegex(ValueError, "did not expose"):
            self.answer(self.body(returns=[self.result(SEARCH_ID, "mcp__contract__probe_commit is now available SECRET_RETURN_9")]))
        self.assertNotIn("SECRET_RETURN_9", self.journal.read_text(encoding="utf-8"))

    def test_unknown_name_and_nonexact_probe_schema_are_rejected(self):
        for variant in ("unknown_name", "schema_change"):
            with self.subTest(variant=variant):
                state = BridgeState(self.args, self.probe_schema, "success", self.journal)
                self.begin_search(state)
                body = self.body(probe="mcp__contract__probe_commit", returns=[self.result(SEARCH_ID, "opaque")])
                if variant == "unknown_name": body["tools"][-1]["function"]["name"] = "mcp_contract_probe_commit"
                else: body["tools"][-1]["function"]["parameters"] = {**self.probe_schema, "additionalProperties": True}
                with self.assertRaises(ValueError): self.answer(body, state)

    def test_search_schema_types_bounds_required_and_extra_fields_are_verified(self):
        validate_schema(self.search_schema, SEARCH_ARGS)
        for schema in ({**self.search_schema, "required": ["query", "unknown"]},
                       {**self.search_schema, "anyOf": [{"type": "object"}]},
                       {**self.search_schema, "properties": {**self.search_schema["properties"],
                        "max_results": {"type": "string"}}},
                       {**self.search_schema, "properties": {**self.search_schema["properties"],
                        "max_results": {"type": "integer", "minimum": 2}}}):
            with self.subTest(schema=schema), self.assertRaises(ValueError): validate_schema(schema, SEARCH_ARGS)
        with self.assertRaises(ValueError): validate_schema(self.search_schema, {**SEARCH_ARGS, "extra": True})

    def test_unsupported_schema_in_unused_property_is_rejected(self):
        schema = copy.deepcopy(self.search_schema)
        schema["properties"]["unused"] = {"type": "object", "properties": {"nested": {"type": ["string", "null"]}}}
        with self.assertRaises(ValueError): validate_schema(schema, SEARCH_ARGS)

    def test_search_and_schema_journals_omit_descriptions_and_raw_hidden_output(self):
        self.begin_search()
        content = [{"type": "text", "text": "SECRET_RAW_SEARCH_TEXT_817"},
                   {"type": "tool_reference", "tool_name": "mcp__contract__probe_commit", "hidden": "SECRET_OTHER_3"}]
        self.answer(self.body(probe="mcp__contract__probe_commit", returns=[self.result(SEARCH_ID, content)]))
        journal = self.journal.read_text(encoding="utf-8")
        for private in ("SECRET_SKILL_BODY_72", "SECRET_QUERY_DESCRIPTION_42", "SECRET_RAW_SEARCH_TEXT_817", "SECRET_OTHER_3"):
            self.assertNotIn(private, journal)
        rows = [json.loads(line) for line in journal.splitlines()]
        returned = next(row for row in rows if row["kind"] == "discovery_return")
        self.assertEqual(returned["tool_reference_names"], ["mcp__contract__probe_commit"])
        self.assertEqual(returned["content_bytes"], len(encoded(content)))
        self.assertNotIn("description", json.dumps(schema_shape(self.search_schema)))

    def test_wrong_probe_call_or_marker_metadata_is_rejected(self):
        for variant in ("wrong_id", "metadata"):
            with self.subTest(variant=variant):
                state = BridgeState(self.args, self.probe_schema, "success", self.journal)
                self.answer(self.body(probe="mcp__contract__probe_commit"), state)
                row = self.result("wrong" if variant == "wrong_id" else CALL_ID, json.dumps(state.expected_payload))
                if variant == "metadata": row["content"] = "no marker"; row["_meta"] = state.expected_payload
                with self.assertRaises(ValueError): self.answer(self.body(returns=[row]), state)

    def test_error_probe_result_terminates_and_extra_request_is_rejected(self):
        state = BridgeState(self.args, self.probe_schema, "error", self.journal)
        self.answer(self.body(probe="mcp__contract__probe_commit"), state)
        terminal = self.answer(self.body(returns=[self.result(CALL_ID, json.dumps(state.expected_payload))]), state)
        self.assertEqual(terminal["text"], "CONTROLLED_DONE")
        with self.assertRaises(ValueError): self.answer(self.body(), state)


if __name__ == "__main__": unittest.main()
