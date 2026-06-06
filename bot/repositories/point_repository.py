import logging

from models.point import PointInfo
from supabase_db.interfaces import SupabaseDB

logger = logging.getLogger("discord").getChild("point_repository")


class PointRepository:
    """PointInfo を通じた Supabase ポイントデータの抽象化層。"""

    def __init__(self, db: SupabaseDB) -> None:
        """SupabaseDB ラッパーを受け取り内部に保持する。"""
        self._db = db

    async def get_point(self, server_id: int, user_id: int) -> int:
        """ユーザーの現在ポイントを返す。未登録なら 0 で初期化する。"""
        return await self._db.get_point(server_id, user_id)

    async def increment_point(self, server_id: int, user_id: int, amount: int) -> None:
        """ポイントを加算する。初回ユーザー（ポイント 0）も正しく反映される。"""
        current = await self._db.get_point(server_id, user_id)
        await self._db.update_point(server_id, user_id, current + amount)

    async def decrement_point(self, server_id: int, user_id: int, amount: int) -> None:
        """ポイントを減算する（0 未満にはならない）。"""
        current = await self._db.get_point(server_id, user_id)
        await self._db.update_point(server_id, user_id, max(0, current - amount))

    async def remove_point(self, server_id: int, user_id: int) -> None:
        """ユーザーのポイントレコードを削除する。"""
        await self._db.remove_point(server_id, user_id)

    async def get_leaderboard(self, server_id: int, limit: int = 10) -> list[PointInfo]:
        """サーバーのポイントランキングを PointInfo リストで返す。"""
        records = await self._db.get_user_points_on_server(server_id, limit)
        return [PointInfo.from_db_record(r) for r in records]
