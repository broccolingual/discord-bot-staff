from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class EventNotifyChannel:
    """通知チャンネルの登録情報を保持するモデル。"""

    server_id: int
    channel_id: int

    @classmethod
    def from_db_record(cls, record: dict) -> "EventNotifyChannel":
        """DB レコードから EventNotifyChannel を生成する。"""
        return cls(server_id=record["server_id"], channel_id=record["channel_id"])


@dataclass
class EventInfo:
    """イベントの全情報と参加者リストを一元管理するモデル。"""

    event_id: int
    server_id: int
    msg_id: int
    author_id: int
    name: str
    description: Optional[str]
    start_time: datetime
    was_ended: bool
    view_name: str
    participant_ids: list[int] = field(default_factory=list)

    @classmethod
    def from_db_record(
        cls,
        record: dict,
        participant_ids: list[int] | None = None,
    ) -> "EventInfo":
        """DB レコードと参加者リストから EventInfo を生成する。"""
        return cls(
            event_id=record["event_id"],
            server_id=record["server_id"],
            msg_id=record["msg_id"],
            author_id=record["author_id"],
            name=record["name"],
            description=record.get("description"),
            start_time=datetime.fromisoformat(record["start_time"]),
            was_ended=record["was_ended"],
            view_name=record.get("view_name", ""),
            participant_ids=participant_ids or [],
        )
