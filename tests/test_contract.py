import json
import unittest
from pathlib import Path

from src.validator import validate_event


class ContractTest(unittest.TestCase):
    def test_sample_matches_envelope(self) -> None:
        sample = json.loads((Path(__file__).parents[1] / "data" / "sample.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_event(sample), [])

    def test_lineage_sample_events_valid(self) -> None:
        lineage = json.loads(
            (Path(__file__).parents[1] / "data" / "lineage_sample.json").read_text(encoding="utf-8")
        )
        errors = {e["event_id"]: validate_event(e) for e in lineage}
        bad = {k: v for k, v in errors.items() if v}
        self.assertEqual(bad, {})

    def test_failed_trial_requires_reason(self) -> None:
        event = {
            "event_id": "x",
            "event_type": "TRIAL_RECORDED",
            "aggregate_type": "replica_project",
            "aggregate_id": "p",
            "occurred_at": "1985-04-06T16:00:00+08:00",
            "version": 1,
            "summary": "失败但未填原因",
            "payload": {"attempt_id": "a", "outcome": "failed"},
        }
        self.assertTrue(any("failure_reason" in m for m in validate_event(event)))

    def test_custodian_only_requires_registration(self) -> None:
        event = {
            "event_id": "x",
            "event_type": "MATERIAL_LOT_RECORDED",
            "aggregate_type": "material_lot",
            "aggregate_id": "m",
            "occurred_at": "1985-04-15T10:00:00+08:00",
            "version": 1,
            "summary": "诀窍未登记保管人与授权范围",
            "payload": {"material_kind": "pigment", "batch_no": "b1"},
            "access": {"classification": "custodian_only"},
        }
        messages = validate_event(event)
        self.assertTrue(any("custodian" in m for m in messages))
        self.assertTrue(any("authorization_scopes" in m for m in messages))

    def test_event_aggregate_mismatch_rejected(self) -> None:
        event = {
            "event_id": "x",
            "event_type": "REFERENCE_FROZEN",
            "aggregate_type": "replica_object",
            "aggregate_id": "o",
            "occurred_at": "1985-03-02T09:00:00+08:00",
            "version": 1,
            "summary": "聚合归属错误",
            "payload": {"title": "t", "basis_version": "v"},
        }
        self.assertTrue(any("必须归属聚合" in m for m in validate_event(event)))


if __name__ == "__main__":
    unittest.main()
