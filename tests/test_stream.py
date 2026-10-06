import copy
import json
import unittest
from pathlib import Path

from src.stream import AppendOnlyStream


def base_event(event_id="e1", version=1, aggregate_id="a1", **overrides):
    event = {
        "event_id": event_id,
        "event_type": "PROJECT_OPENED",
        "aggregate_type": "replica_project",
        "aggregate_id": aggregate_id,
        "occurred_at": "1985-03-10T09:00:00+08:00",
        "version": version,
        "summary": "立项",
        "payload": {"title": "临摹项目", "goal": "research_copy"},
    }
    event.update(overrides)
    return event


class StreamTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stream = AppendOnlyStream()

    def test_versions_must_be_consecutive(self) -> None:
        self.stream.append(base_event(version=1))
        with self.assertRaisesRegex(ValueError, "连续递增"):
            self.stream.append(base_event(event_id="e2", version=3))

    def test_duplicate_id_cannot_overwrite(self) -> None:
        event = base_event()
        self.stream.append(event)
        tampered = copy.deepcopy(event)
        tampered["summary"] = "被篡改的新说法"
        with self.assertRaisesRegex(ValueError, "不可覆盖"):
            self.stream.append(tampered)
        self.assertEqual(self.stream.get("e1")["summary"], "立项")

    def test_supersede_points_to_existing_same_aggregate(self) -> None:
        self.stream.append(base_event())
        with self.assertRaisesRegex(ValueError, "尚不存在"):
            self.stream.append(
                base_event(
                    event_id="e2",
                    version=2,
                    links={"supersedes_event_id": "missing"},
                )
            )
        other_aggregate = base_event(event_id="e9", aggregate_id="other")
        self.stream.append(other_aggregate)
        with self.assertRaisesRegex(ValueError, "另一聚合"):
            self.stream.append(
                base_event(
                    event_id="e2",
                    version=2,
                    links={"supersedes_event_id": "e9"},
                )
            )

    def test_supersede_appends_without_deleting_prior(self) -> None:
        self.stream.append(base_event(summary="旧表述"))
        self.stream.append(
            base_event(
                event_id="e2",
                version=2,
                summary="更正后的表述",
                links={"supersedes_event_id": "e1"},
            )
        )
        self.assertIsNotNone(self.stream.get("e1"))
        self.assertEqual(self.stream.get("e1")["summary"], "旧表述")

    def test_failed_append_leaves_stream_unchanged(self) -> None:
        self.stream.append(base_event())
        before = len(self.stream.events)
        with self.assertRaises(ValueError):
            self.stream.append(base_event(event_id="e2", version=99))
        self.assertEqual(len(self.stream.events), before)

    def test_full_sample_lineage_is_appendable(self) -> None:
        lineage = json.loads(
            (Path(__file__).parents[1] / "data" / "lineage_sample.json").read_text(encoding="utf-8")
        )
        stream = AppendOnlyStream()
        stream.extend(lineage)
        self.assertEqual(len(stream.events), len(lineage))
        obj_events = stream.aggregate("obj-fac-1985-01")
        self.assertEqual([e["version"] for e in obj_events], list(range(1, 9)))


if __name__ == "__main__":
    unittest.main()
