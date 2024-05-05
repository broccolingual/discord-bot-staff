import os
import asyncio

from aiomysql.sa import create_engine

import settings

DB_DSN = settings.DSN

class DB:
    async def __aenter__(self, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        engine = await create_engine(DB_DSN)
        self._conn = await engine.acquire()
        return self
    
    async def __aexit__(self, *args, **kwargs):
        await self._conn.close()
        
    async def execute(self, query, *args, **kwargs):
        return await self._conn.execute(query, *args, **kwargs)
