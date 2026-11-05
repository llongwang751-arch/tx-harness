"""行为协议 v1 的回归测试：冻结字段、变体契约与双闸门必须始终成立。"""
import unittest

from scripts import audit_behavior_protocol


class BehaviorProtocolFreeze(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = audit_behavior_protocol.json.loads(
            audit_behavior_protocol.PROTOCOL.read_text(encoding="utf-8"))

    def test_protocol_is_frozen_preregistration(self):
        self.assertEqual(self.protocol["status"], "preregistered_frozen_not_yet_run")
        self.assertEqual(self.protocol["run_budget"]["slots"], [],
                         "冻结时实验位必须为空：运行与否是决策门之后的事")
        for key in ("no_total_score", "no_ranking", "no_task_count_claim",
                    "no_harness_attribution"):
            self.assertTrue(self.protocol[key])

    def test_full_audit_passes(self):
        problems = audit_behavior_protocol.verify(self.protocol)
        self.assertEqual(problems, [])

    def test_gates_recomputed_match_frozen_file(self):
        gates = audit_behavior_protocol.build_gates(self.protocol)
        self.assertTrue(gates["passed"])
        frozen = audit_behavior_protocol.json.loads(
            audit_behavior_protocol.GATES.read_text(encoding="utf-8"))
        self.assertEqual(
            audit_behavior_protocol.json.dumps(frozen, sort_keys=True,
                                               ensure_ascii=False),
            audit_behavior_protocol.json.dumps(gates, sort_keys=True,
                                               ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
