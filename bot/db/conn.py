from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

import settings
                
engine_async = create_async_engine(settings.DB_DSN, echo=True)

@asynccontextmanager    
async def get_session():
    session_async = sessionmaker(
        bind=engine_async,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_async() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
        
