"""校验领域事件信封的基础字段与领域规则。"""

from datetime import datetime

REQUIRED = ("event_id", "event_type", "aggregate_type", "aggregate_id", "occurred_at", "version", "summary")

EVENT_TYPES = (
    "REFERENCE_FROZEN",
    "SURVEY_RECORDED",
    "MATERIAL_LOT_REGISTERED",
    "MATERIAL_TESTED",
    "TRIAL_SAMPLE_RECORDED",
    "STAGE_ATTESTED",
    "RESPONSIBILITY_ASSIGNED",
    "MENTORSHIP_RECORDED",
    "MOUNTING_RECORDED",
    "EXPERT_OPINION_RECORDED",
    "SECRET_REGISTERED",
    "DETECTION_RECORDED",
    "REVIEW_FLAGGED",
    "OBJECT_ACCESSIONED",
    "IDENTITY_RECLASSIFIED",
    "LABEL_ISSUED",
    "LABEL_REVISED",
)

AGGREGATE_TYPES = (
    "reference_work",
    "replica_project",
    "material_lot",
    "trial_sample",
    "secret",
    "detection",
    "collection_decision",
)

# 每种事件允许挂靠的聚合
EVENT_AGGREGATES = {
    "REFERENCE_FROZEN": ("reference_work",),
    "SURVEY_RECORDED": ("reference_work",),
    "MATERIAL_LOT_REGISTERED": ("material_lot",),
    "MATERIAL_TESTED": ("material_lot",),
    "TRIAL_SAMPLE_RECORDED": ("trial_sample",),
    "STAGE_ATTESTED": ("replica_project",),
    "RESPONSIBILITY_ASSIGNED": ("replica_project",),
    "MENTORSHIP_RECORDED": ("replica_project",),
    "MOUNTING_RECORDED": ("reference_work", "replica_project"),
    "EXPERT_OPINION_RECORDED": ("replica_project", "collection_decision"),
    "SECRET_REGISTERED": ("secret",),
    "DETECTION_RECORDED": ("detection",),
    "REVIEW_FLAGGED": ("detection",),
    "OBJECT_ACCESSIONED": ("collection_decision",),
    "IDENTITY_RECLASSIFIED": ("collection_decision",),
    "LABEL_ISSUED": ("collection_decision",),
    "LABEL_REVISED": ("collection_decision",),
}

# 特定事件必须携带的额外字段
EVENT_REQUIRED_FIELDS = {
    "TRIAL_SAMPLE_RECORDED": ("outcome",),
    "RESPONSIBILITY_ASSIGNED": ("assignee", "scope"),
    "SECRET_REGISTERED": ("custodian", "authorization_scope"),
    "REVIEW_FLAGGED": ("targets",),
    "IDENTITY_RECLASSIFIED": ("from_identity", "to_identity"),
    "LABEL_ISSUED": ("identity", "custody_level", "permission"),
}

# 诀窍只登记保管人与授权范围，诀窍内容本身不落库
SECRET_FORBIDDEN_FIELDS = ("content", "technique_detail")

OBJECT_IDENTITIES = ("original", "replica", "teaching_sample")

TRIAL_OUTCOMES = ("success", "failure", "partial")


def validate_event(record: dict) -> list[str]:
    errors = [f"缺少字段：{name}" for name in REQUIRED if name not in record]
    if "version" in record and (not isinstance(record["version"], int) or record["version"] < 1):
        errors.append("version 必须是正整数")

    event_type = record.get("event_type")
    aggregate_type = record.get("aggregate_type")
    if event_type is not None and event_type not in EVENT_TYPES:
        errors.append(f"事件类型未登记：{event_type}")
    if aggregate_type is not None and aggregate_type not in AGGREGATE_TYPES:
        errors.append(f"聚合类型未登记：{aggregate_type}")
    if event_type in EVENT_AGGREGATES and aggregate_type in AGGREGATE_TYPES:
        if aggregate_type not in EVENT_AGGREGATES[event_type]:
            errors.append(f"事件 {event_type} 不应挂在聚合 {aggregate_type}")

    occurred_at = record.get("occurred_at")
    if isinstance(occurred_at, str):
        try:
            datetime.fromisoformat(occurred_at)
        except ValueError:
            errors.append("occurred_at 不是有效的日期时间")

    for name in EVENT_REQUIRED_FIELDS.get(event_type, ()):
        if name not in record:
            errors.append(f"缺少字段：{name}")

    if event_type == "SECRET_REGISTERED":
        for name in SECRET_FORBIDDEN_FIELDS:
            if name in record:
                errors.append(f"诀窍事件不得包含诀窍内容字段：{name}")

    if event_type == "TRIAL_SAMPLE_RECORDED" and record.get("outcome") not in (None, *TRIAL_OUTCOMES):
        errors.append(f"outcome 取值须为 {'/'.join(TRIAL_OUTCOMES)}")

    if event_type == "REVIEW_FLAGGED":
        targets = record.get("targets")
        if targets is not None and (not isinstance(targets, list) or not targets):
            errors.append("复核标记必须给出非空 targets")

    if event_type == "IDENTITY_RECLASSIFIED" and record.get("to_identity") not in (None, *OBJECT_IDENTITIES):
        errors.append(f"to_identity 取值须为 {'/'.join(OBJECT_IDENTITIES)}")

    if event_type == "LABEL_ISSUED" and record.get("identity") not in (None, *OBJECT_IDENTITIES):
        errors.append(f"identity 取值须为 {'/'.join(OBJECT_IDENTITIES)}")

    return errors
