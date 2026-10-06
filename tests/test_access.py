import unittest

from src.access import can_read, redact_event

KNOWHOW_EVENT = {
    "event_id": "evt-lot-knowhow-8503-01",
    "event_type": "MATERIAL_LOT_RECORDED",
    "aggregate_type": "material_lot",
    "aggregate_id": "lot-knowhow-8503",
    "occurred_at": "1985-04-15T10:00:00+08:00",
    "version": 1,
    "summary": "登记石青水漂炮制诀窍（内容受限）",
    "access": {
        "classification": "custodian_only",
        "custodian": "绘画修复临摹组（岗位：颜料保管）",
        "authorization_scopes": ["know_how:pigment_preparation"],
    },
    "payload": {"preparation": "【受限内容】水漂遍数与胶水比例……"},
    "evidence_refs": [{"kind": "know_how_note", "uri": "urn:sealed:knowhow/8503"}],
}

RESTRICTED_EVENT = {
    "event_id": "r1",
    "event_type": "EXAMINATION_RECORDED",
    "aggregate_type": "examination",
    "aggregate_id": "exam-x",
    "occurred_at": "2019-07-10T09:30:00+08:00",
    "version": 1,
    "summary": "受限检测档案",
    "access": {"classification": "restricted"},
    "payload": {"target": {"kind": "replica_object", "id": "o"}, "methods": ["xray"]},
}

RESEARCHER = {"person_id": "p-researcher", "scopes": []}
AUTHORIZED_RESEARCHER = {"person_id": "p-researcher2", "scopes": ["research_access"]}
CUSTODIAN = {"person_id": "p-keeper", "is_custodian": True, "scopes": []}
SCOPE_HOLDER = {"person_id": "p-mentor", "scopes": ["know_how:pigment_preparation"]}


class AccessTest(unittest.TestCase):
    def test_ordinary_researcher_cannot_read_know_how(self) -> None:
        self.assertFalse(can_read(KNOWHOW_EVENT, RESEARCHER))
        redacted = redact_event(KNOWHOW_EVENT, RESEARCHER)
        self.assertTrue(redacted["redacted"])
        self.assertNotIn("payload", redacted)
        self.assertNotIn("evidence_refs", redacted)
        # 仍能看到保管人与授权范围的登记
        self.assertEqual(redacted["access"]["custodian"], "绘画修复临摹组（岗位：颜料保管）")
        self.assertEqual(redacted["access"]["authorization_scopes"], ["know_how:pigment_preparation"])

    def test_custodian_and_scope_holder_can_read(self) -> None:
        self.assertTrue(can_read(KNOWHOW_EVENT, CUSTODIAN))
        self.assertTrue(can_read(KNOWHOW_EVENT, SCOPE_HOLDER))
        self.assertIn("payload", redact_event(KNOWHOW_EVENT, CUSTODIAN))

    def test_restricted_requires_research_access(self) -> None:
        self.assertFalse(can_read(RESTRICTED_EVENT, RESEARCHER))
        self.assertTrue(can_read(RESTRICTED_EVENT, AUTHORIZED_RESEARCHER))

    def test_open_event_readable_by_anyone(self) -> None:
        open_event = dict(KNOWHOW_EVENT, access={"classification": "open"})
        self.assertTrue(can_read(open_event, RESEARCHER))
        self.assertFalse(redact_event(open_event, RESEARCHER).get("redacted"))


if __name__ == "__main__":
    unittest.main()
