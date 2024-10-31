from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import settings

engine = create_engine(settings.DB_DSN)
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)

def getDB():
    return SessionLocal()
