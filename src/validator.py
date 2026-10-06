"""校验领域事件信封与各事件类型的基础约束。

仅依赖标准库；完整跨系统契约见 contracts/domain.schema.json。
"""

from typing import Any

REQUIRED = (
    "event_id",
    "event_type",
    "aggregate_type",
    "aggregate_id",
    "occurred_at",
    "version",
    "summary",
)

EVENT_TYPES = {
    "REFERENCE_FROZEN",
    "EXAMINATION_RECORDED",
    "FINDING_RECORDED",
    "PROJECT_OPENED",
    "ASSIGNMENT_RECORDED",
    "MATERIAL_LOT_RECORDED",
    "MATERIAL_TESTED",
    "TRIAL_RECORDED",
    "STAGE_ATTESTED",
    "DETAIL_RECORDED",
    "GENERATION_LINKED",
    "OBJECT_REGISTERED",
    "IDENTITY_RECLASSIFIED",
    "MOUNTING_RECORDED",
    "CONSERVATION_PERFORMED",
    "EXPERT_OPINION_RECORDED",
    "DESCRIPTION_REVIEW_FLAGGED",
    "OBJECT_ACCESSIONED",
    "LABEL_REVISED",
    "LOAN_LABEL_ISSUED",
}

# 事件类型允许归属的聚合类型
EVENT_AGGREGATE = {
    "REFERENCE_FROZEN": "reference_work",
    "EXAMINATION_RECORDED": "examination",
    "FINDING_RECORDED": "examination",
    "PROJECT_OPENED": "replica_project",
    "ASSIGNMENT_RECORDED": "replica_project",
    "TRIAL_RECORDED": "replica_project",
    "STAGE_ATTESTED": "replica_project",
    "DETAIL_RECORDED": "replica_project",
    "GENERATION_LINKED": "replica_project",
    "MATERIAL_LOT_RECORDED": "material_lot",
    "MATERIAL_TESTED": "material_lot",
    "OBJECT_REGISTERED": "replica_object",
    "IDENTITY_RECLASSIFIED": "replica_object",
    "MOUNTING_RECORDED": "replica_object",
    "CONSERVATION_PERFORMED": "replica_object",
    "EXPERT_OPINION_RECORDED": "replica_object",
    "DESCRIPTION_REVIEW_FLAGGED": "replica_object",
    "OBJECT_ACCESSIONED": "collection_decision",
    "LABEL_REVISED": "loan_label",
    "LOAN_LABEL_ISSUED": "loan_label",
}

# 各事件 payload 必填字段
PAYLOAD_REQUIRED = {
    "REFERENCE_FROZEN": ("title", "basis_version"),
    "EXAMINATION_RECORDED": ("target", "methods"),
    "FINDING_RECORDED": ("examination_id", "conclusions"),
    "PROJECT_OPENED": ("title", "goal"),
    "ASSIGNMENT_RECORDED": ("assignments",),
    "MATERIAL_LOT_RECORDED": ("material_kind", "batch_no"),
    "MATERIAL_TESTED": ("test", "suitable"),
    "TRIAL_RECORDED": ("attempt_id", "outcome"),
    "STAGE_ATTESTED": ("stage",),
    "DETAIL_RECORDED": ("detail_code", "generation", "technique"),
    "GENERATION_LINKED": ("parent", "relation"),
    "OBJECT_REGISTERED": ("title", "object_kind", "status"),
    "IDENTITY_RECLASSIFIED": ("from_status", "to_status", "reason"),
    "MOUNTING_RECORDED": ("format", "mounter"),
    "CONSERVATION_PERFORMED": ("treatments", "conservator"),
    "EXPERT_OPINION_RECORDED": ("expert_id", "opinion"),
    "DESCRIPTION_REVIEW_FLAGGED": ("source_finding_event_id", "claims_to_review"),
    "OBJECT_ACCESSIONED": ("object_id", "decision", "custody_level", "license_id", "basis"),
    "LABEL_REVISED": ("object_id", "revision_reason", "identity_snapshot"),
    "LOAN_LABEL_ISSUED": ("object_id", "loan_exhibition", "identity_snapshot"),
}

CLASSIFICATIONS = {"open", "restricted", "custodian_only"}


def validate_event(record: dict[str, Any]) -> list[str]:
    """返回错误信息列表；空列表表示通过基础校验。"""
    errors: list[str] = [f"缺少字段：{name}" for name in REQUIRED if name not in record]
    if errors:
        return errors

    event_type = record["event_type"]
    if event_type not in EVENT_TYPES:
        errors.append(f"未知 event_type：{event_type}")
    else:
        expected_aggregate = EVENT_AGGREGATE[event_type]
        if record.get("aggregate_type") != expected_aggregate:
            errors.append(
                f"{event_type} 必须归属聚合 {expected_aggregate}，实际为 {record.get('aggregate_type')}"
            )

        payload = record.get("payload")
        if not isinstance(payload, dict):
            errors.append("缺少字段：payload")
        else:
            for field in PAYLOAD_REQUIRED[event_type]:
                if field not in payload:
                    errors.append(f"{event_type} 的 payload 缺少字段：{field}")
            if event_type == "TRIAL_RECORDED" and payload.get("outcome") == "failed":
                if not payload.get("failure_reason"):
                    errors.append("失败试验（outcome=failed）必须填写 failure_reason")
            if event_type == "OBJECT_ACCESSIONED" and payload.get("decision") == "accepted":
                if not payload.get("basis"):
                    errors.append("同意入藏必须给出 basis（作者/材料/工艺等价值依据）")

    if not isinstance(record["version"], int) or record["version"] < 1:
        errors.append("version 必须是正整数")
    if not isinstance(record["event_id"], str) or not record["event_id"]:
        errors.append("event_id 必须是非空字符串")
    if not isinstance(record["summary"], str) or not record["summary"]:
        errors.append("summary 必须是非空字符串")

    access = record.get("access")
    if access is not None:
        errors.extend(_validate_access(access))
    return errors


def _validate_access(access: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    classification = access.get("classification")
    if classification not in CLASSIFICATIONS:
        errors.append(f"access.classification 非法：{classification}")
    if classification == "custodian_only":
        if not access.get("custodian"):
            errors.append("custodian_only 事件必须登记 custodian（保管人）")
        if not access.get("authorization_scopes"):
            errors.append("custodian_only 事件必须登记 authorization_scopes（授权范围）")
    return errors
