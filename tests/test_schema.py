import json
import unittest
from pathlib import Path

try:
    import jsonschema
except ImportError:  # 正式校验为可选增强；核心校验零依赖
    jsonschema = None

ROOT = Path(__file__).parents[1]


@unittest.skipIf(jsonschema is None, "未安装 jsonschema，跳过正式契约校验")
class SchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads((ROOT / "contracts" / "domain.schema.json").read_text(encoding="utf-8"))
        cls.events = json.loads((ROOT / "data" / "lineage_sample.json").read_text(encoding="utf-8"))
        cls.sample = json.loads((ROOT / "data" / "sample.json").read_text(encoding="utf-8"))
        cls.validator = jsonschema.Draft202012Validator(cls.schema)

    def test_all_events_satisfy_schema(self) -> None:
        for event in self.events + [self.sample]:
            errors = list(self.validator.iter_errors(event))
            self.assertEqual(errors, [], msg=f"{event['event_id']}: {errors[0].message if errors else ''}")

    def test_failed_trial_without_reason_rejected(self) -> None:
        trial = next(e for e in self.events if e["event_id"] == "evt-proj-1985-03")
        bad = json.loads(json.dumps(trial))
        bad["event_id"] = "negative-case"
        bad["payload"].pop("failure_reason")
        self.assertTrue(any("failure_reason" in e.message for e in self.validator.iter_errors(bad)))

    def test_knowhow_without_custodian_rejected(self) -> None:
        knowhow = next(e for e in self.events if e["event_id"] == "evt-lot-knowhow-8503-01")
        bad = json.loads(json.dumps(knowhow))
        bad["event_id"] = "negative-case"
        bad["access"].pop("custodian")
        self.assertTrue(any("custodian" in e.message for e in self.validator.iter_errors(bad)))


if __name__ == "__main__":
    unittest.main()
