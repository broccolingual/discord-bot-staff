from models.event import EventNotifyChannel, EventNotify, EventJoinedUser
from db.db import DB

class CRUDBase:
    @staticmethod
    async def execute(query, *args, **kwargs):
        async with DB() as db:
            result = await db.execute(query, *args, **kwargs)
        return result
    
class Event(CRUDBase):
    def __init__(self):
        self.eventNotify = EventNotify()
    
    async def addEventNotifyChannel(server_id, channel_id):
        pass
    
    async def getEventNotifyChannel(server_id):
        pass
    
    async def updateEventNotifyChannel(server_id, channel_id):
        pass
    
    async def addEvent(msg_id, event_id, author_id):
        pass
    
    async def getEvent(msg_id):
        pass
    
    async def updateEvent(msg_id, event_id, author_id):
        pass
    
    async def addJoinedUser(event_id, user_id):
        pass
    
    async def deleteJoinedUser(event_id, user_id):
        pass
    
    async def getJoinedUsers(event_id):
        pass
