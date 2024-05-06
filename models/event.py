from sqlalchemy import Column, BigInteger, DateTime, text
from sqlalchemy.sql import func

from db.base_class import Base

class EventNotifyChannel(Base):
    __tablename__ = "event_notify_channel"
    __table_args__ = {'mysql_engine':'InnoDB', 'mysql_charset':'utf8mb4','mysql_collate':'utf8mb4_bin'}
    
    server_id = Column(BigInteger(), nullable=False, primary_key=True, unique=True)
    channel_id = Column(BigInteger(), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

class EventNotify(Base):
    __tablename__ = "event_notify"
    __table_args__ = {'mysql_engine':'InnoDB', 'mysql_charset':'utf8mb4','mysql_collate':'utf8mb4_bin'}

    msg_id = Column(BigInteger(), nullable=False, primary_key=True, unique=True)
    event_id = Column(BigInteger(), nullable=False)
    author_id = Column(BigInteger())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
    
class EventJoinedUser(Base):
    __tablename__ = "event_joined_user"
    __table_args__ = {'mysql_engine':'InnoDB', 'mysql_charset':'utf8mb4','mysql_collate':'utf8mb4_bin'}
    
    event_id = Column(BigInteger(), nullable=False, primary_key=True)
    user_id = Column(BigInteger(), nullable=False, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
