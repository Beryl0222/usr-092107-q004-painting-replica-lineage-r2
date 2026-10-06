"""事件流：把节点接成不可覆盖的谱系。

不变量：
1. 事件只能追加；event_id 一经存在，同 ID 再提交且内容不同即被拒绝。
2. 同一 aggregate_id 内 version 从 1 起连续递增，不允许跳号、重复或回退。
3. links.supersedes_event_id 只能指向同聚合已存在的另一事件；被更正事件原样保留。
"""

from typing import Any

from .validator import validate_event


class AppendOnlyStream:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._index: dict[str, dict[str, Any]] = {}
        self._aggregate_versions: dict[str, set[int]] = {}

    @property
    def events(self) -> list[dict[str, Any]]:
        """按接收顺序返回全部事件（浅拷贝引用，调用方不应原地修改）。"""
        return list(self._events)

    def append(self, event: dict[str, Any]) -> None:
        """校验并追加一条事件；任何不变量被破坏时抛 ValueError，流状态不变。"""
        errors = validate_event(event)
        if errors:
            raise ValueError("；".join(errors))

        event_id = event["event_id"]
        if event_id in self._index:
            if self._index[event_id] != event:
                raise ValueError(f"事件 {event_id} 已存在且内容不同：历史记录不可覆盖")
            raise ValueError(f"事件 {event_id} 已存在：禁止重复追加")

        aggregate_id = event["aggregate_id"]
        version = event["version"]
        seen = self._aggregate_versions.setdefault(aggregate_id, set())
        expected = len(seen) + 1
        if version != expected:
            raise ValueError(
                f"聚合 {aggregate_id} 的 version 必须为 {expected}（从 1 起连续递增），收到 {version}"
            )

        supersedes = (event.get("links") or {}).get("supersedes_event_id")
        if supersedes is not None:
            if supersedes == event_id:
                raise ValueError("事件不能更正自身")
            prior = self._index.get(supersedes)
            if prior is None:
                raise ValueError(f"被更正事件 {supersedes} 尚不存在，更正只能指向已接收记录")
            if prior["aggregate_id"] != aggregate_id:
                raise ValueError(
                    f"更正事件 {supersedes} 属于另一聚合 {prior['aggregate_id']}"
                )

        self._events.append(event)
        self._index[event_id] = event
        seen.add(version)

    def extend(self, events: list[dict[str, Any]]) -> None:
        for event in events:
            self.append(event)

    def get(self, event_id: str) -> dict[str, Any] | None:
        return self._index.get(event_id)

    def aggregate(self, aggregate_id: str) -> list[dict[str, Any]]:
        """按 version 顺序返回某聚合的全部事件。"""
        return sorted(
            (e for e in self._events if e["aggregate_id"] == aggregate_id),
            key=lambda e: e["version"],
        )
