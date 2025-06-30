import functools
import logging

import httpx
import supabase

import settings

logger = logging.getLogger("discord").getChild("supabase")


class SupabaseDB():
    async def get_client(self) -> supabase.AsyncClient:
        self.client = await supabase.acreate_client(
            settings.SUPABASE_API_URL,
            settings.SUPABASE_API_KEY)

    def supabase_error_handler(default_return=None, notfound_return=None):
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    result = await func(*args, **kwargs)
                    if result is None and notfound_return is not None:
                        return notfound_return
                    return result
                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error in {func.__name__}: {e}")
                    return default_return
                except Exception as e:
                    logger.error(f"Unexpected error in {func.__name__}: {e}")
                    return default_return
            return wrapper
        return decorator

    @supabase_error_handler(default_return=None)
    async def add_event_notify_channel(self, server_id, channel_id):
        await self.client.table("event_notify_channel").insert({"server_id": server_id, "channel_id": channel_id}).execute()

    @supabase_error_handler(default_return=None)
    async def get_event_notify_channel(self, server_id):
        result = await self.client.table("event_notify_channel").select("*").eq("server_id", server_id).execute()
        if not result.data or len(result.data) == 0:
            logger.info(
                f"No event notify channel found for server_id: {server_id}")
            return None
        return result.data[0]

    @supabase_error_handler(default_return=None)
    async def update_event_notify_channel(self, server_id, channel_id):
        await self.client.table("event_notify_channel").update({"channel_id": channel_id}).eq("server_id", server_id).execute()

    @supabase_error_handler(default_return=None)
    async def add_event(self, msg_id, event_id, server_id, author_id, name, description, start_time, view_name, was_ended=False):
        await self.client.table("event_notify").insert({
            "msg_id": msg_id,
            "event_id": event_id,
            "server_id": server_id,
            "author_id": author_id,
            "name": name,
            "description": description,
            "start_time": start_time.isoformat(),
            "was_ended": was_ended,
            "view_name": view_name
        }).execute()

    @supabase_error_handler(default_return=None)
    async def get_event(self, msg_id):
        result = await self.client.table("event_notify").select("*").eq("msg_id", msg_id).execute()
        if not result.data or len(result.data) == 0:
            logger.info(f"No event found for msg_id: {msg_id}")
            return None
        return result.data[0]

    @supabase_error_handler(default_return=None, notfound_return=[])
    async def get_all_events_held_on_server(self, server_id):
        result = await self.client.table("event_notify").select("*").eq("server_id", server_id).eq("was_ended", True).execute()
        if not result.data or len(result.data) == 0:
            logger.info(f"No events found for server_id: {server_id}")
            return []
        return result.data

    @supabase_error_handler(default_return=None, notfound_return=[])
    async def get_events_should_have_been_started(self, current_time):
        result = await self.client.table("event_notify").select("*").lt("start_time", current_time.isoformat()).eq("was_ended", False).execute()
        if not result.data or len(result.data) == 0:
            logger.info(
                f"No events should have been started before: {current_time}")
            return []
        return result.data

    @supabase_error_handler(default_return=None, notfound_return=[])
    async def get_active_event_sessions(self, current_time):
        result = await self.client.table("event_notify").select("*").gt("start_time", current_time.isoformat()).eq("was_ended", False).execute()
        if not result.data or len(result.data) == 0:
            logger.info(
                f"No active event sessions found after: {current_time}")
            return []
        return result.data

    @supabase_error_handler(default_return=None)
    async def update_event_status(self, msg_id, was_ended):
        await self.client.table("event_notify").update({"was_ended": was_ended}).eq("msg_id", msg_id).execute()

    @supabase_error_handler(default_return=None)
    async def get_message(self, event_id):
        result = await self.client.table("event_notify").select("*").eq("event_id", event_id).execute()
        if not result.data or len(result.data) == 0:
            logger.info(f"No message found for event_id: {event_id}")
            return None
        return result.data[0]

    @supabase_error_handler(default_return=None)
    async def update_event(self, msg_id, name, description, start_time):
        await self.client.table("event_notify").update({
            "name": name,
            "description": description,
            "start_time": start_time.isoformat()
        }).eq("msg_id", msg_id).execute()

    @supabase_error_handler(default_return=None)
    async def delete_event(self, msg_id):
        await self.client.table("event_notify").delete().eq("msg_id", msg_id).execute()

    @supabase_error_handler(default_return=None)
    async def add_joined_user(self, event_id, user_id):
        await self.client.table("event_joined_user").insert({"event_id": event_id, "user_id": user_id}).execute()

    @supabase_error_handler(default_return=None)
    async def delete_joined_user(self, event_id, user_id):
        await self.client.table("event_joined_user").delete().eq("event_id", event_id).eq("user_id", user_id).execute()

    @supabase_error_handler(default_return=None)
    async def delete_all_joined_users(self, event_id):
        await self.client.table("event_joined_user").delete().eq("event_id", event_id).execute()

    @supabase_error_handler(default_return=None, notfound_return=[])
    async def get_joined_user_ids(self, event_id):
        result = await self.client.table("event_joined_user").select("*").eq("event_id", event_id).execute()
        if not result.data or len(result.data) == 0:
            logger.info(f"No joined users found for event_id: {event_id}")
            return []
        user_ids = [user["user_id"] for user in result.data]
        return user_ids

    @supabase_error_handler(default_return=None)
    async def init_point(self, server_id, user_id):
        await self.client.table("point_earned").insert({"server_id": server_id, "user_id": user_id}).execute()

    @supabase_error_handler(default_return=None)
    async def update_point(self, server_id, user_id, point):
        await self.client.table("point_earned").update({"point": point}).eq("server_id", server_id).eq("user_id", user_id).execute()

    @supabase_error_handler(default_return=None)
    async def remove_point(self, server_id, user_id):
        await self.client.table("point_earned").delete().eq("server_id", server_id).eq("user_id", user_id).execute()

    @supabase_error_handler(default_return=0)
    async def get_point(self, server_id, user_id):
        result = await self.client.table("point_earned").select("*").eq("server_id", server_id).eq("user_id", user_id).execute()
        if not result.data or len(result.data) == 0:
            await self.init_point(server_id, user_id)
            return 0
        return result.data[0]["point"]

    @supabase_error_handler(default_return=[])
    async def get_user_points_on_server(self, server_id, limit=10):
        result = await self.client.table("point_earned").select("*").eq("server_id", server_id).order("point", desc=True).limit(limit).execute()
        if not result.data or len(result.data) == 0:
            logger.info(f"No points found for server_id: {server_id}")
            return []
        return result.data

    @supabase_error_handler(default_return=None)
    async def increment_point(self, server_id, user_id, point):
        current_points = await self.get_point(server_id, user_id)
        if current_points:
            await self.update_point(server_id, user_id, current_points + point)
        else:
            await self.init_point(server_id, user_id)

    @supabase_error_handler(default_return=None)
    async def decrement_point(self, server_id, user_id, point):
        current_points = await self.get_point(server_id, user_id)
        if current_points:
            new_point = max(0, current_points - point)
            await self.update_point(server_id, user_id, new_point)
        else:
            await self.init_point(server_id, user_id)
