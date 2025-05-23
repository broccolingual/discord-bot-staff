import supabese

import settings

async def get_supabase_client() -> supabese.AsyncClient:
    """
    Returns a Supabase async client instance.
    """
    return await supabese.create_async_client(
        url=settings.SUPABASE_API_URL,
        key=settings.SUPABASE_API_KEY
    )
