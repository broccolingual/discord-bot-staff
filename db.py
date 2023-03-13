import asyncio
import datetime

import asyncpg

import settings

def startEventLoop(func):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(func)

async def getConn():
    return await asyncpg.connect(settings.DSN)

async def run():
    conn = await getConn()
    values = await conn.fetch("select version()")
    print(values)
    await conn.close()

if __name__ == "__main__":
    startEventLoop(run())