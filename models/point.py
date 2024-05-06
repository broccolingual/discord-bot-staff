from sqlalchemy import Column, BigInteger, DateTime, text
from sqlalchemy.sql import func

from db.base_class import Base

class PointEarned(Base):
    __tablename__ = "point_earned"
    __table_args__ = {'mysql_engine':'InnoDB', 'mysql_charset':'utf8mb4','mysql_collate':'utf8mb4_bin'}
    
    server_id = Column(BigInteger(), nullable=False, primary_key=True)
    user_id = Column(BigInteger(), nullable=False, primary_key=True)
    point = Column(BigInteger(), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
