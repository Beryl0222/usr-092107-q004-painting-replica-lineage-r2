"""访问分级与脱敏。

- open：普通研究者可读取全文。
- restricted：需研究授权（viewer 持有 research_access）。
- custodian_only：传统诀窍等内容，只向保管人或持有授权码的调用方公开；
  其他调用方只能看到保管人与授权范围的登记，看不到 payload、证据与摘要。
"""

from typing import Any

# 受限研究内容所需的授权码
RESEARCH_SCOPE = "research_access"


def can_read(event: dict[str, Any], viewer: dict[str, Any]) -> bool:
    """viewer 形如 {"person_id": "...", "is_custodian": bool, "scopes": [...]}。"""
    access = event.get("access")
    if access is None or access.get("classification") == "open":
        return True

    scopes = set(viewer.get("scopes") or [])
    if access.get("classification") == "restricted":
        return RESEARCH_SCOPE in scopes

    # custodian_only
    if viewer.get("is_custodian"):
        return True
    return bool(scopes & set(access.get("authorization_scopes") or []))


def redact_event(event: dict[str, Any], viewer: dict[str, Any]) -> dict[str, Any]:
    """返回适合该 viewer 的事件副本；无权阅读时只保留信封与保管登记。"""
    if can_read(event, viewer):
        return dict(event)

    access = event.get("access") or {}
    return {
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "aggregate_type": event["aggregate_type"],
        "aggregate_id": event["aggregate_id"],
        "occurred_at": event["occurred_at"],
        "version": event["version"],
        "summary": "【内容受限】该记录为传统诀窍或受限资料，当前调用方无权阅读",
        "access": {
            "classification": access.get("classification"),
            "custodian": access.get("custodian"),
            "authorization_scopes": access.get("authorization_scopes"),
        },
        "redacted": True,
    }


def visible_events(events: list[dict[str, Any]], viewer: dict[str, Any]) -> list[dict[str, Any]]:
    return [redact_event(e, viewer) for e in events]
