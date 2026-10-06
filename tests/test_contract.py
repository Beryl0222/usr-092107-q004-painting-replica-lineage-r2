import json
import unittest
from pathlib import Path

from src.validator import validate_event

ROOT = Path(__file__).parents[1]


def load(name: str):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def base_event(**overrides) -> dict:
    event = {
        "event_id": "evt-test-001",
        "event_type": "REFERENCE_FROZEN",
        "aggregate_type": "reference_work",
        "aggregate_id": "RW-TEST",
        "occurred_at": "2026-10-01T09:00:00+08:00",
        "version": 1,
        "summary": "测试事件",
    }
    event.update(overrides)
    return event


class ContractTest(unittest.TestCase):
    def test_sample_matches_envelope(self) -> None:
        self.assertEqual(validate_event(load("sample.json")), [])


class LineageExampleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.events = load("lineage_example.json")

    def test_each_event_valid(self) -> None:
        for event in self.events:
            self.assertEqual(validate_event(event), [], event["event_id"])

    def test_event_ids_unique(self) -> None:
        ids = [event["event_id"] for event in self.events]
        self.assertEqual(len(ids), len(set(ids)))

    def test_versions_increase_per_aggregate(self) -> None:
        seen: dict[tuple[str, str], int] = {}
        for event in self.events:
            key = (event["aggregate_type"], event["aggregate_id"])
            previous = seen.get(key, 0)
            self.assertGreater(event["version"], previous, event["event_id"])
            seen[key] = event["version"]

    def test_failed_trials_kept(self) -> None:
        outcomes = [e.get("outcome") for e in self.events if e["event_type"] == "TRIAL_SAMPLE_RECORDED"]
        self.assertIn("failure", outcomes)


class EnvelopeRuleTest(unittest.TestCase):
    def test_unknown_event_type_rejected(self) -> None:
        errors = validate_event(base_event(event_type="PAINTED"))
        self.assertIn("事件类型未登记：PAINTED", errors)

    def test_event_on_wrong_aggregate_rejected(self) -> None:
        errors = validate_event(base_event(event_type="SECRET_REGISTERED", aggregate_type="replica_project"))
        self.assertTrue(any("不应挂在聚合" in e for e in errors))

    def test_bad_occurred_at_rejected(self) -> None:
        errors = validate_event(base_event(occurred_at="昨天上午"))
        self.assertIn("occurred_at 不是有效的日期时间", errors)

    def test_secret_must_not_carry_content(self) -> None:
        event = base_event(
            event_type="SECRET_REGISTERED",
            aggregate_type="secret",
            custodian="王砚农",
            authorization_scope="项目组内演示",
            content="水温四十度",
        )
        errors = validate_event(event)
        self.assertIn("诀窍事件不得包含诀窍内容字段：content", errors)

    def test_secret_requires_custodian_and_scope(self) -> None:
        errors = validate_event(base_event(event_type="SECRET_REGISTERED", aggregate_type="secret"))
        self.assertIn("缺少字段：custodian", errors)
        self.assertIn("缺少字段：authorization_scope", errors)

    def test_review_flag_requires_targets(self) -> None:
        event = base_event(event_type="REVIEW_FLAGGED", aggregate_type="detection", targets=[])
        errors = validate_event(event)
        self.assertIn("复核标记必须给出非空 targets", errors)

    def test_label_identity_restricted(self) -> None:
        event = base_event(
            event_type="LABEL_ISSUED",
            aggregate_type="collection_decision",
            identity="poster",
            custody_level="一般藏品",
            permission="限馆内",
        )
        errors = validate_event(event)
        self.assertIn("identity 取值须为 original/replica/teaching_sample", errors)

    def test_trial_outcome_restricted(self) -> None:
        event = base_event(event_type="TRIAL_SAMPLE_RECORDED", aggregate_type="trial_sample", outcome="unknown")
        errors = validate_event(event)
        self.assertIn("outcome 取值须为 success/failure/partial", errors)


if __name__ == "__main__":
    unittest.main()
