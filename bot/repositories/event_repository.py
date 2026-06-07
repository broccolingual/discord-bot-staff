import datetime
import logging
from typing import Optional

from models.event import EventInfo, EventNotifyChannel
from supabase_db.interfaces import SupabaseDB

logger = logging.getLogger("discord").getChild("event_repository")


class EventRepository:
    """EventInfo / EventNotifyChannel を通じた Supabase イベントデータの抽象化層。"""

    def __init__(self, db: SupabaseDB) -> None:
        """SupabaseDB ラッパーを受け取り内部に保持する。"""
        self._db = db

    # --- Notify channel ---

    async def get_notify_channel(self, server_id: int) -> Optional[EventNotifyChannel]:
        """サーバーの通知チャンネルを取得する。未登録なら None を返す。"""
        record = await self._db.get_event_notify_channel(server_id)
        if record is None:
            return None
        return EventNotifyChannel.from_db_record(record)

    async def add_notify_channel(self, server_id: int, channel_id: int) -> None:
        """サーバーの通知チャンネルを新規登録する。"""
        await self._db.add_event_notify_channel(server_id, channel_id)

    async def update_notify_channel(self, server_id: int, channel_id: int) -> None:
        """サーバーの通知チャンネルを変更する。"""
        await self._db.update_event_notify_channel(server_id, channel_id)

    # --- Events ---

    async def save_event(self, event_info: EventInfo) -> None:
        """EventInfo をもとにイベントレコードを DB に保存する。"""
        await self._db.add_event(
            msg_id=event_info.msg_id,
            event_id=event_info.event_id,
            server_id=event_info.server_id,
            author_id=event_info.author_id,
            name=event_info.name,
            description=event_info.description,
            start_time=event_info.start_time,
            view_name=event_info.view_name,
            was_ended=event_info.was_ended,
        )

    async def get_event_by_event_id(self, event_id: int) -> Optional[EventInfo]:
        """Discord event_id でイベントと参加者リストを取得する。"""
        record = await self._db.get_event_by_event_id(event_id)
        if record is None:
            return None
        participant_ids = await self._db.get_joined_user_ids(event_id)
        return EventInfo.from_db_record(record, participant_ids)

    async def get_event_by_msg_id(self, msg_id: int) -> Optional[EventInfo]:
        """msg_id でイベントと参加者リストを取得する。"""
        record = await self._db.get_event(msg_id)
        if record is None:
            return None
        participant_ids = await self._db.get_joined_user_ids(record["event_id"])
        return EventInfo.from_db_record(record, participant_ids)

    async def update_event_status(self, msg_id: int, was_ended: bool) -> None:
        """イベントの終了フラグを更新する。"""
        await self._db.update_event_status(msg_id, was_ended)

    async def get_active_sessions(self, current_time: datetime.datetime) -> list[EventInfo]:
        """開始時刻が未来の未終了イベントを参加者込みで取得する（ビュー再登録用）。"""
        records = await self._db.get_active_event_sessions(current_time)
        if not records:
            return []
        result: list[EventInfo] = []
        for record in records:
            participant_ids = await self._db.get_joined_user_ids(record["event_id"])
            result.append(EventInfo.from_db_record(record, participant_ids))
        return result

    async def get_overdue_events(self, current_time: datetime.datetime) -> list[EventInfo]:
        """開始時刻を過ぎているのに未終了のイベントを取得する。"""
        records = await self._db.get_overdue_events(current_time)
        if not records:
            return []
        return [EventInfo.from_db_record(r) for r in records]

    async def get_all_events_held_on_server(self, server_id: int) -> list[EventInfo]:
        """サーバーで開催済みの全イベントを取得する。"""
        records = await self._db.get_all_events_held_on_server(server_id)
        if not records:
            return []
        return [EventInfo.from_db_record(r) for r in records]

    # --- Participants ---

    async def add_participant(self, event_id: int, user_id: int) -> None:
        """イベントに参加者を追加する。"""
        await self._db.add_joined_user(event_id, user_id)

    async def remove_participant(self, event_id: int, user_id: int) -> None:
        """イベントから参加者を削除する。"""
        await self._db.delete_joined_user(event_id, user_id)

    async def get_participant_ids(self, event_id: int) -> list[int]:
        """イベントの参加者 ID リストを取得する。"""
        return await self._db.get_joined_user_ids(event_id)
