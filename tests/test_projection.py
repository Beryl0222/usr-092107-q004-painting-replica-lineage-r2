import copy
import json
import unittest
from pathlib import Path

from src.projection import LineageProjection

DATA = Path(__file__).parents[1] / "data" / "lineage_sample.json"
OBJECT_ID = "obj-fac-1985-01"
TEACHING_ID = "obj-teach-2004-09"


def load_events():
    return json.loads(DATA.read_text(encoding="utf-8"))


class ProjectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.events = load_events()
        cls.projection = LineageProjection(cls.events)
        cls.by_id = {e["event_id"]: e for e in cls.events}

    def test_distinguishes_original_facsimile_and_teaching_sample(self) -> None:
        self.assertEqual(self.projection.classify("ref-qiushan"), "original")
        self.assertEqual(self.projection.classify(OBJECT_ID), "facsimile")
        self.assertEqual(self.projection.classify(TEACHING_ID), "teaching_sample")
        self.assertEqual(self.projection.classify("nonexistent"), "unknown")

    def test_identity_tracks_research_output_to_collection_item(self) -> None:
        state = self.projection.object_state(OBJECT_ID)
        self.assertEqual(state["status"], "collection_item")
        self.assertEqual(state["object_kind"], "facsimile")
        self.assertEqual(state["accession_no"], "新-0021847")
        self.assertEqual(state["custody_level"], "L2")
        self.assertEqual(state["license_id"], "展览许可-2021-L2-限学术与巡展")
        self.assertIn("craft_value", state["accession_basis"])

    def test_new_finding_flags_review_without_rewriting_past(self) -> None:
        state = self.projection.object_state(OBJECT_ID)
        flagged = [f for f in state["pending_review_flags"] if f["event_id"] == "evt-obj-fac-1985-01-03"]
        self.assertEqual(len(flagged), 1)
        self.assertIn("evt-exam-2019-07-02", flagged[0]["source_finding_event_id"])
        # 1990 年意见原文保持不变
        old_opinion = self.by_id["evt-obj-fac-1985-01-03"]["payload"]["opinion"]
        self.assertIn("天然矿物石青", old_opinion)

    def test_detail_comparable_across_generations(self) -> None:
        rows = self.projection.detail_generations("peak.cun_texture")
        self.assertEqual([r["generation"] for r in rows], [1, 2])
        self.assertEqual(rows[0]["project_id"], "proj-1985-qiushan")
        self.assertEqual(rows[1]["project_id"], "proj-2003-teaching")
        self.assertIn("四层积染", rows[1]["technique"])

    def test_failed_trials_remain_under_attempt(self) -> None:
        trials = self.projection.attempt_trials("proj-1985-qiushan")
        branch_b = trials["attempt-B"]
        outcomes = {t["outcome"] for t in branch_b}
        self.assertEqual(outcomes, {"failed", "accepted"})
        failed = next(t for t in branch_b if t["outcome"] == "failed")
        self.assertIn("泛红", failed["failure_reason"])
        self.assertIn("lot-silk-8501", failed["material_lot_ids"])

    def test_responsibilities_record_scope_and_supervision(self) -> None:
        people = {p["person_id"]: p for p in self.projection.responsibilities("proj-2003-teaching")}
        self.assertIn("纸本教学再摹", people["p-wangyun"]["scope"])
        self.assertEqual(people["p-wangyun"]["attempt_id"], "attempt-C")
        self.assertEqual(people["p-wangyun"]["supervised_by_person_id"], "p-zhangheng")
        self.assertEqual(people["p-zhangheng"]["role"], "supervisor")
        self.assertIn("皴法", people["p-zhangheng"]["scope"])

    def test_loan_label_matches_current_identity(self) -> None:
        label = self.by_id["evt-label-2026-tour-01"]
        self.assertEqual(self.projection.label_mismatches(label), [])
        self.assertEqual(
            self.projection.issue_label_snapshot(OBJECT_ID),
            label["payload"]["identity_snapshot"],
        )

    def test_stale_label_is_rejected(self) -> None:
        stale = {
            "event_id": "evt-label-stale",
            "event_type": "LOAN_LABEL_ISSUED",
            "payload": {
                "object_id": OBJECT_ID,
                "loan_exhibition": "旧巡展",
                "identity_snapshot": {
                    "object_kind": "facsimile",
                    "status": "research_output",
                    "custody_level": "L3",
                    "license_id": "普通复制品-无外借许可",
                },
            },
        }
        mismatches = self.projection.label_mismatches(stale)
        self.assertTrue(any("status" in m for m in mismatches))
        self.assertTrue(any("custody_level" in m for m in mismatches))
        self.assertTrue(any("license_id" in m for m in mismatches))

    def test_superseded_event_does_not_participate_in_projection(self) -> None:
        events = [
            {
                "event_id": "reg-1",
                "event_type": "OBJECT_REGISTERED",
                "aggregate_type": "replica_object",
                "aggregate_id": "obj-x",
                "occurred_at": "1986-05-10T09:00:00+08:00",
                "version": 1,
                "summary": "初登记标题含误字",
                "payload": {
                    "title": "《秋山行旋图》摹本",
                    "object_kind": "facsimile",
                    "status": "research_output",
                },
            },
            {
                "event_id": "reg-2",
                "event_type": "OBJECT_REGISTERED",
                "aggregate_type": "replica_object",
                "aggregate_id": "obj-x",
                "occurred_at": "1986-05-11T09:00:00+08:00",
                "version": 2,
                "summary": "补正标题（旧记录保留）",
                "payload": {
                    "title": "《秋山行旅图》摹本",
                    "object_kind": "facsimile",
                    "status": "research_output",
                },
                "links": {"supersedes_event_id": "reg-1"},
            },
        ]
        projection = LineageProjection(events)
        self.assertEqual(projection.object_state("obj-x")["title"], "《秋山行旅图》摹本")
        # 被更正的原始事件仍在流中、未被删除
        self.assertIsNotNone(next(e for e in projection.events if e["event_id"] == "reg-1"))

    def test_projection_does_not_mutate_source_events(self) -> None:
        snapshot = copy.deepcopy(self.events)
        _ = LineageProjection(self.events).object_state(OBJECT_ID)
        self.assertEqual(self.events, snapshot)


if __name__ == "__main__":
    unittest.main()
