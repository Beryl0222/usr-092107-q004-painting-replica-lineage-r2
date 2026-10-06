"""谱系投影：从不可变事件流折叠出读取模型。

供三类使用场景：
1. 研究者：按细节编码比较同一细节在不同代际的处理；查看试验（含失败）与责任范围。
2. 藏品管理员：准确区分原作（reference_work）、摹本（facsimile）与教学样张
   （teaching_sample），并取得对象当前身份、保管级别与许可。
3. 巡展：签发或核对标签时，标签上的身份快照必须与投影出的当前状态一致。

被后继事件更正（links.supersedes_event_id 指向）的事件不参与投影；
复核标记（DESCRIPTION_REVIEW_FLAGGED）只提示说明待核，从不倒改任何历史记录。
"""

from collections import defaultdict
from typing import Any

IDENTITY_FIELDS = ("object_kind", "status", "custody_level", "license_id")


class LineageProjection:
    def __init__(self, events: list[dict[str, Any]] | None = None) -> None:
        self._events: list[dict[str, Any]] = []
        self._superseded: set[str] = set()
        if events:
            for event in events:
                self.apply(event)

    def apply(self, event: dict[str, Any]) -> None:
        self._events.append(event)
        supersedes = (event.get("links") or {}).get("supersedes_event_id")
        if supersedes:
            self._superseded.add(supersedes)

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def _effective(self, aggregate_id: str | None = None) -> list[dict[str, Any]]:
        result = [
            e
            for e in self._events
            if e["event_id"] not in self._superseded and not e.get("redacted")
        ]
        if aggregate_id is not None:
            result = [e for e in result if e["aggregate_id"] == aggregate_id]
        return sorted(result, key=lambda e: e["version"])

    # ---- 藏品管理：当前身份 -------------------------------------------------

    def object_state(self, object_id: str) -> dict[str, Any]:
        """折叠出对象当前身份。原作（reference_work）不在此列，另有专门区分。"""
        state: dict[str, Any] = {
            "object_id": object_id,
            "object_kind": None,
            "status": None,
            "title": None,
            "project_id": None,
            "custody_level": None,
            "license_id": None,
            "accession_no": None,
            "accession_basis": [],
            "pending_review_flags": [],
        }

        for event in self._effective(object_id):
            payload = event.get("payload", {})
            kind = event["event_type"]
            if kind == "OBJECT_REGISTERED":
                state["title"] = payload.get("title", state["title"])
                state["project_id"] = payload.get("project_id", state["project_id"])
                state["object_kind"] = payload["object_kind"]
                state["status"] = payload["status"]
            elif kind == "IDENTITY_RECLASSIFIED":
                if payload.get("to_kind"):
                    state["object_kind"] = payload["to_kind"]
                state["status"] = payload["to_status"]
            elif kind == "DESCRIPTION_REVIEW_FLAGGED":
                for claim in payload.get("claims_to_review", []):
                    state["pending_review_flags"].append(
                        {
                            "source_finding_event_id": payload["source_finding_event_id"],
                            "event_id": claim["event_id"],
                            "claim": claim["claim"],
                        }
                    )

        # 入藏决定属于 collection_decision 聚合，按 payload.object_id 关联
        for event in self._effective():
            if event["event_type"] != "OBJECT_ACCESSIONED":
                continue
            payload = event["payload"]
            if payload.get("object_id") != object_id or payload.get("decision") != "accepted":
                continue
            state["custody_level"] = payload["custody_level"]
            state["license_id"] = payload["license_id"]
            state["accession_no"] = payload.get("accession_no")
            state["accession_basis"] = payload.get("basis", [])
        return state

    def classify(self, object_id: str) -> str:
        """返回 original / facsimile / teaching_sample / unknown。"""
        if any(
            e["aggregate_type"] == "reference_work" and e["aggregate_id"] == object_id
            for e in self._effective()
        ):
            return "original"
        kind = self.object_state(object_id)["object_kind"]
        return kind if kind in ("facsimile", "teaching_sample") else "unknown"

    # ---- 研究者：代际细节比较、责任与试验 -----------------------------------

    def detail_generations(self, detail_code: str) -> list[dict[str, Any]]:
        """同一细节在不同代际/尝试中的处理，按代际与发生时间排列。"""
        rows: list[dict[str, Any]] = []
        for event in self._effective():
            if event["event_type"] != "DETAIL_RECORDED":
                continue
            payload = event["payload"]
            if payload.get("detail_code") != detail_code:
                continue
            rows.append(
                {
                    "project_id": event["aggregate_id"],
                    "event_id": event["event_id"],
                    "occurred_at": event["occurred_at"],
                    "generation": payload["generation"],
                    "attempt_id": payload.get("attempt_id"),
                    "technique": payload["technique"],
                    "material_lot_ids": payload.get("material_lot_ids", []),
                    "note": payload.get("note"),
                }
            )
        return sorted(rows, key=lambda r: (r["generation"], r["occurred_at"]))

    def attempt_trials(self, project_id: str) -> dict[str, list[dict[str, Any]]]:
        """按尝试分支归集试验；失败与放弃的试验同样保留。"""
        trials: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in self._effective(project_id):
            if event["event_type"] != "TRIAL_RECORDED":
                continue
            payload = event["payload"]
            trials[payload["attempt_id"]].append(
                {
                    "trial_no": payload.get("trial_no"),
                    "outcome": payload["outcome"],
                    "material_lot_ids": payload.get("material_lot_ids", []),
                    "method": payload.get("method"),
                    "failure_reason": payload.get("failure_reason"),
                    "event_id": event["event_id"],
                }
            )
        return dict(trials)

    def responsibilities(self, project_id: str) -> list[dict[str, Any]]:
        """多人接续/并行时每人的责任范围与指导关系（取最新一次登记为准）。"""
        latest: dict[str, dict[str, Any]] = {}
        for event in self._effective(project_id):
            if event["event_type"] != "ASSIGNMENT_RECORDED":
                continue
            for item in event["payload"]["assignments"]:
                latest[item["person_id"]] = item
        return list(latest.values())

    # ---- 巡展：标签一致性 ---------------------------------------------------

    def label_mismatches(self, label_event: dict[str, Any]) -> list[str]:
        """核对标签事件中的身份快照是否与对象当前身份、保管级别和许可一致。"""
        payload = label_event["payload"]
        current = self.object_state(payload["object_id"])
        snapshot = payload["identity_snapshot"]
        mismatches: list[str] = []
        for field in IDENTITY_FIELDS:
            if snapshot.get(field) != current.get(field):
                mismatches.append(
                    f"标签 {field}={snapshot.get(field)!r} 与当前状态 {current.get(field)!r} 不一致"
                )
        return mismatches

    def issue_label_snapshot(self, object_id: str) -> dict[str, Any]:
        """按当前状态生成标签应使用的身份快照。"""
        state = self.object_state(object_id)
        return {field: state[field] for field in IDENTITY_FIELDS}
