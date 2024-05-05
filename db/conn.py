from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import settings

DB_DSN = settings.DSN

engine = create_engine(DB_DSN)
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)

def getDB():
    return SessionLocal()
