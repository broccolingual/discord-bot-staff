from sqlalchemy.future import select

from db.conn import get_session
from models.event import EventNotifyChannel, EventNotify, EventJoinedUser
from models.point import PointEarned
    
class DB():
    @staticmethod
    async def addEventNotifyChannel(server_id, channel_id):
        async with get_session() as session:
            session.add(EventNotifyChannel(server_id=server_id, channel_id=channel_id))
    
    @staticmethod
    async def getEventNotifyChannel(server_id):
        async with get_session() as session:
            result = await session.execute(select(EventNotifyChannel).filter(EventNotifyChannel.server_id == server_id))
            return result.scalars().first()
    
    @staticmethod
    async def updateEventNotifyChannel(server_id, channel_id):
        async with get_session() as session:
            result = await session.execute(select(EventNotifyChannel).filter(EventNotifyChannel.server_id == server_id))
            item = result.scalars().first()
            item.channel_id = channel_id
            session.add(item)
    
    @staticmethod
    async def addEvent(msg_id, event_id, author_id):
        async with get_session() as session:
            session.add(EventNotify(msg_id=msg_id, event_id=event_id, author_id=author_id))
    
    @staticmethod
    async def getEvent(msg_id):
        async with get_session() as session:
            result = await session.execute(select(EventNotify).filter(EventNotify.msg_id == msg_id))
            return await result.scalars().first()
    
    @staticmethod
    async def getMessage(event_id):
        async with get_session() as session:
            result = await session.execute(select(EventNotify).filter(EventNotify.event_id == event_id))
            return result.scalars().first()
    
    @staticmethod
    async def updateEvent(msg_id, event_id, author_id):
        async with get_session() as session:
            result = await session.execute(select(EventNotify).filter(EventNotify.msg_id == msg_id))
            item = result.scalars().first()
            item.event_id = event_id
            item.author_id = author_id
            session.add(item)
    
    @staticmethod
    async def addJoinedUser(event_id, user_id):
        async with get_session() as session:
            session.add(EventJoinedUser(event_id=event_id, user_id=user_id))
    
    @staticmethod
    async def deleteJoinedUser(event_id, user_id):
        async with get_session() as session:
            result = await session.execute(select(EventJoinedUser).filter(EventJoinedUser.event_id == event_id).filter(EventJoinedUser.user_id == user_id))
            item = result.scalars().first()
            await session.delete(item)
    
    @staticmethod
    async def getJoinedUsers(event_id):
        async with get_session() as session:
            result = await session.execute(select(EventJoinedUser).filter(EventJoinedUser.event_id == event_id).order_by(EventJoinedUser.created_at))
            return result.scalars().all()
    
    @staticmethod
    async def initPoint(server_id, user_id):
        async with get_session() as session:
            session.add(PointEarned(server_id=server_id, user_id=user_id, point=0))
    
    @staticmethod
    async def updatePoint(server_id, user_id, point):
        async with get_session() as session:
            result = await session.execute(select(PointEarned).filter(PointEarned.server_id == server_id).filter(PointEarned.user_id == user_id))
            item = result.scalars().first()
            item.point += point
            session.add(item)
    
    @staticmethod
    async def removePoint(server_id, user_id, point):
        async with get_session() as session:
            result = await session.execute(select(PointEarned).filter(PointEarned.server_id == server_id).filter(PointEarned.user_id == user_id))
            item = result.scalars().first()
            item.point -= point
            session.add(item)
    
    @staticmethod
    async def getPoint(server_id, user_id):
        async with get_session() as session:
            result = await session.execute(select(PointEarned).filter(PointEarned.server_id == server_id).filter(PointEarned.user_id == user_id))
            return result.scalars().first()
    
    @staticmethod
    async def getUserPointsOnServer(server_id, limit=10):
        async with get_session() as session:
            result = await session.execute(select(PointEarned).filter(PointEarned.server_id == server_id).order_by(PointEarned.point.desc()).limit(limit))
            return result.scalars().all()
