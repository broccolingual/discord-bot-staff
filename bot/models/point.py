from dataclasses import dataclass


@dataclass
class PointInfo:
    """ユーザーのポイント情報を保持するモデル。"""

    server_id: int
    user_id: int
    point: int

    @classmethod
    def from_db_record(cls, record: dict) -> "PointInfo":
        """DB レコードから PointInfo を生成する。"""
        return cls(
            server_id=record["server_id"],
            user_id=record["user_id"],
            point=record["point"],
        )
