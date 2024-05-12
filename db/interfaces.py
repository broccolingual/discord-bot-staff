from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.event import EventNotifyChannel, EventNotify, EventJoinedUser
from models.point import PointEarned
import settings
    
class DB():
    def __init__(self):
        self.engine = create_engine(settings.DSN)
        self.sessionmaker = sessionmaker(autocommit=False, autoflush=True, bind=self.engine)
        self.session = self.sessionmaker()
    
    def addEventNotifyChannel(self, server_id, channel_id):
        self.session.add(EventNotifyChannel(server_id=server_id, channel_id=channel_id))
        self.session.commit()
        return self
    
    def getEventNotifyChannel(self, server_id):
        result = self.session.query(EventNotifyChannel).filter(EventNotifyChannel.server_id == server_id).first()
        return result
    
    def updateEventNotifyChannel(self, server_id, channel_id):
        self.session.query(EventNotifyChannel).filter(EventNotifyChannel.server_id == server_id).update({EventNotifyChannel.channel_id: channel_id})
        self.session.commit()
        return self
    
    def addEvent(self, msg_id, event_id, author_id):
        self.session.add(EventNotify(msg_id=msg_id, event_id=event_id, author_id=author_id))
        self.session.commit()
        return self
    
    def getEvent(self, msg_id):
        result = self.session.query(EventNotify).filter(EventNotify.msg_id == msg_id).first()
        return result
    
    def getMessage(self, event_id):
        result = self.session.query(EventNotify).filter(EventNotify.event_id == event_id).first()
        return result
    
    def updateEvent(self, msg_id, event_id, author_id):
        self.session.query(EventNotify).filter(EventNotify.msg_id == msg_id).update({EventNotify.event_id: event_id, EventNotify.author_id: author_id})
        self.session.commit()
        return self
    
    def addJoinedUser(self, event_id, user_id):
        self.session.add(EventJoinedUser(event_id=event_id, user_id=user_id))
        self.session.commit()
        return self
    
    def deleteJoinedUser(self, event_id, user_id):
        self.session.query(EventJoinedUser).filter(EventJoinedUser.event_id == event_id).filter(EventJoinedUser.user_id == user_id).delete()
        self.session.commit()
        return self
    
    def getJoinedUsers(self, event_id):
        result = self.session.query(EventJoinedUser.user_id).filter(EventJoinedUser.event_id == event_id).order_by(EventJoinedUser.created_at).all()
        return result
    
    def initPoint(self, server_id, user_id):
        self.session.add(PointEarned(server_id=server_id, user_id=user_id, point=0))
        self.session.commit()
        return self
    
    def updatePoint(self, server_id, user_id, point):
        self.session.query(PointEarned).filter(PointEarned.server_id == server_id).filter(PointEarned.user_id == user_id).update({PointEarned.point: PointEarned.point + point})
        self.session.commit()
        return self
    
    def removePoint(self, server_id, user_id, point):
        self.session.query(PointEarned).filter(PointEarned.server_id == server_id).filter(PointEarned.user_id == user_id).update({PointEarned.point: PointEarned.point - point})
        self.session.commit()
        return self
    
    def getPoint(self, server_id, user_id):
        result = self.session.query(PointEarned).filter(PointEarned.server_id == server_id).filter(PointEarned.user_id == user_id).first()
        return result
    
    def getUserPointsOnServer(self, server_id, limit=10):
        result = self.session.query(PointEarned).filter(PointEarned.server_id == server_id).order_by(PointEarned.point.desc()).limit(limit)
        return result
