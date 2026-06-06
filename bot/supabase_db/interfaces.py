import datetime
import functools
import logging
from typing import Any, Callable

import httpx
import supabase

import settings

logger = logging.getLogger("discord").getChild("supabase")


def _db_error_handler(default: Any = None, not_found: Any = None) -> Callable:
    """HTTP エラーと予期しない例外を捕捉してデフォルト値を返すデコレータ。"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                result = await func(*args, **kwargs)
                if result is None and not_found is not None:
                    return not_found
                return result
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error in {func.__name__}: {e}")
                return default
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}")
                return default
        return wrapper
    return decorator


class SupabaseDB:
    """Supabase 非同期クライアントのラッパー。生テーブル操作のみを担当する。"""

    async def get_client(self) -> None:
        """Supabase 非同期クライアントを初期化する。"""
        self.client: supabase.AsyncClient = await supabase.acreate_client(
            settings.SUPABASE_API_URL,
            settings.SUPABASE_API_KEY,
        )

    # --- Event notify channel ---

    @_db_error_handler(default=None)
    async def add_event_notify_channel(self, server_id: int, channel_id: int) -> None:
        """通知チャンネルレコードを追加する。"""
        await self.client.table("event_notify_channel").insert(
            {"server_id": server_id, "channel_id": channel_id}).execute()

    @_db_error_handler(default=None)
    async def get_event_notify_channel(self, server_id: int) -> dict | None:
        """サーバーの通知チャンネルレコードを取得する。"""
        result = await self.client.table("event_notify_channel").select("*").eq(
            "server_id", server_id).execute()
        if not result.data:
            logger.info(f"Notify channel not found: server_id={server_id}")
            return None
        return result.data[0]

    @_db_error_handler(default=None)
    async def update_event_notify_channel(self, server_id: int, channel_id: int) -> None:
        """サーバーの通知チャンネルを更新する。"""
        await self.client.table("event_notify_channel").update(
            {"channel_id": channel_id}).eq("server_id", server_id).execute()

    # --- Events ---

    @_db_error_handler(default=None)
    async def add_event(
        self,
        msg_id: int,
        event_id: int,
        server_id: int,
        author_id: int,
        name: str,
        description: str | None,
        start_time: datetime.datetime,
        view_name: str,
        was_ended: bool = False,
    ) -> None:
        """イベントレコードを追加する。"""
        await self.client.table("event_notify").insert({
            "msg_id": msg_id,
            "event_id": event_id,
            "server_id": server_id,
            "author_id": author_id,
            "name": name,
            "description": description,
            "start_time": start_time.isoformat(),
            "was_ended": was_ended,
            "view_name": view_name,
        }).execute()

    @_db_error_handler(default=None)
    async def get_event(self, msg_id: int) -> dict | None:
        """msg_id でイベントレコードを取得する。"""
        result = await self.client.table("event_notify").select("*").eq(
            "msg_id", msg_id).execute()
        if not result.data:
            logger.info(f"Event not found: msg_id={msg_id}")
            return None
        return result.data[0]

    @_db_error_handler(default=None)
    async def get_event_by_event_id(self, event_id: int) -> dict | None:
        """Discord event_id でイベントレコードを取得する。"""
        result = await self.client.table("event_notify").select("*").eq(
            "event_id", event_id).execute()
        if not result.data:
            logger.info(f"Event not found: event_id={event_id}")
            return None
        return result.data[0]

    @_db_error_handler(default=None)
    async def update_event_status(self, msg_id: int, was_ended: bool) -> None:
        """イベントの終了フラグを更新する。"""
        await self.client.table("event_notify").update(
            {"was_ended": was_ended}).eq("msg_id", msg_id).execute()

    @_db_error_handler(default=None)
    async def update_event(
        self,
        msg_id: int,
        name: str,
        description: str | None,
        start_time: datetime.datetime,
    ) -> None:
        """イベントの名前・説明・開始時刻を更新する。"""
        await self.client.table("event_notify").update({
            "name": name,
            "description": description,
            "start_time": start_time.isoformat(),
        }).eq("msg_id", msg_id).execute()

    @_db_error_handler(default=None)
    async def delete_event(self, msg_id: int) -> None:
        """イベントレコードを削除する。"""
        await self.client.table("event_notify").delete().eq("msg_id", msg_id).execute()

    @_db_error_handler(default=[], not_found=[])
    async def get_all_events_held_on_server(self, server_id: int) -> list[dict]:
        """サーバーで開催済みの全イベントを取得する。"""
        result = await self.client.table("event_notify").select("*").eq(
            "server_id", server_id).eq("was_ended", True).execute()
        if not result.data:
            logger.info(f"No ended events found: server_id={server_id}")
            return []
        return result.data

    @_db_error_handler(default=[], not_found=[])
    async def get_overdue_events(self, current_time: datetime.datetime) -> list[dict]:
        """開始時刻を過ぎているのに未終了のイベントを取得する。"""
        result = await self.client.table("event_notify").select("*").lt(
            "start_time", current_time.isoformat()).eq("was_ended", False).execute()
        if not result.data:
            logger.info(f"No overdue events before: {current_time}")
            return []
        return result.data

    @_db_error_handler(default=[], not_found=[])
    async def get_active_event_sessions(self, current_time: datetime.datetime) -> list[dict]:
        """開始時刻がまだ未来の未終了イベントを取得する（ビュー再登録用）。"""
        result = await self.client.table("event_notify").select("*").gt(
            "start_time", current_time.isoformat()).eq("was_ended", False).execute()
        if not result.data:
            logger.info(f"No active sessions after: {current_time}")
            return []
        return result.data

    # --- Participants ---

    @_db_error_handler(default=None)
    async def add_joined_user(self, event_id: int, user_id: int) -> None:
        """イベントの参加ユーザーを追加する。"""
        await self.client.table("event_joined_user").insert(
            {"event_id": event_id, "user_id": user_id}).execute()

    @_db_error_handler(default=None)
    async def delete_joined_user(self, event_id: int, user_id: int) -> None:
        """イベントの参加ユーザーを削除する。"""
        await self.client.table("event_joined_user").delete().eq(
            "event_id", event_id).eq("user_id", user_id).execute()

    @_db_error_handler(default=None)
    async def delete_all_joined_users(self, event_id: int) -> None:
        """イベントの全参加ユーザーを削除する。"""
        await self.client.table("event_joined_user").delete().eq(
            "event_id", event_id).execute()

    @_db_error_handler(default=[], not_found=[])
    async def get_joined_user_ids(self, event_id: int) -> list[int]:
        """イベントの参加ユーザーIDリストを取得する。"""
        result = await self.client.table("event_joined_user").select("*").eq(
            "event_id", event_id).execute()
        if not result.data:
            logger.info(f"No joined users found: event_id={event_id}")
            return []
        return [row["user_id"] for row in result.data]

    # --- Points ---

    @_db_error_handler(default=None)
    async def init_point(self, server_id: int, user_id: int) -> None:
        """ユーザーのポイントレコードをデフォルト値で作成する。"""
        await self.client.table("point_earned").insert(
            {"server_id": server_id, "user_id": user_id}).execute()

    @_db_error_handler(default=None)
    async def update_point(self, server_id: int, user_id: int, point: int) -> None:
        """ユーザーのポイントを指定値に更新する。"""
        await self.client.table("point_earned").update(
            {"point": point}).eq("server_id", server_id).eq("user_id", user_id).execute()

    @_db_error_handler(default=None)
    async def remove_point(self, server_id: int, user_id: int) -> None:
        """ユーザーのポイントレコードを削除する。"""
        await self.client.table("point_earned").delete().eq(
            "server_id", server_id).eq("user_id", user_id).execute()

    @_db_error_handler(default=0)
    async def get_point(self, server_id: int, user_id: int) -> int:
        """ユーザーの現在ポイントを取得する。未登録なら0で初期化して返す。"""
        result = await self.client.table("point_earned").select("*").eq(
            "server_id", server_id).eq("user_id", user_id).execute()
        if not result.data:
            await self.init_point(server_id, user_id)
            return 0
        return result.data[0]["point"]

    @_db_error_handler(default=[])
    async def get_user_points_on_server(self, server_id: int, limit: int = 10) -> list[dict]:
        """サーバーのポイントランキングを降順で取得する。"""
        result = await self.client.table("point_earned").select("*").eq(
            "server_id", server_id).order("point", desc=True).limit(limit).execute()
        if not result.data:
            logger.info(f"No points found: server_id={server_id}")
            return []
        return result.data
