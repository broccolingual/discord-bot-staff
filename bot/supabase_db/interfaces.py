import supabase

import settings


class SupabaseDB():
    async def get_client(self) -> supabase.AsyncClient:
        self.client = await supabase.acreate_client(
            settings.SUPABASE_API_URL,
            settings.SUPABASE_API_KEY)

    async def add_event_notify_channel(self, server_id, channel_id):
        await self.client.table("event_notify_channel").insert({"server_id": server_id, "channel_id": channel_id}).execute()

    async def get_event_notify_channel(self, server_id):
        result = await self.client.table("event_notify_channel").select("*").eq("server_id", server_id).execute()
        return result.data[0] if result.data else None

    async def update_event_notify_channel(self, server_id, channel_id):
        await self.client.table("event_notify_channel").update({"channel_id": channel_id}).eq("server_id", server_id).execute()

    async def add_event(self, msg_id, event_id, author_id):
        await self.client.table("event_notify").insert({"msg_id": msg_id, "event_id": event_id, "author_id": author_id}).execute()

    async def get_event(self, msg_id):
        result = await self.client.table("event_notify").select("*").eq("msg_id", msg_id).execute()
        return result.data[0] if result.data else None

    async def get_message(self, event_id):
        result = await self.client.table("event_notify").select("*").eq("event_id", event_id).execute()
        return result.data[0] if result.data else None

    async def update_event(self, msg_id, event_id, author_id):
        await self.client.table("event_notify").update({"event_id": event_id, "author_id": author_id}).eq("msg_id", msg_id).execute()

    async def add_joined_user(self, event_id, user_id):
        await self.client.table("event_joined_user").insert({"event_id": event_id, "user_id": user_id}).execute()

    async def delete_joined_user(self, event_id, user_id):
        await self.client.table("event_joined_user").delete().eq("event_id", event_id).eq("user_id", user_id).execute()

    async def get_joined_user_ids(self, event_id):
        result = await self.client.table("event_joined_user").select("*").eq("event_id", event_id).execute()
        if result.data:
            user_ids = [user["user_id"] for user in result.data]
            return user_ids
        return []

    async def init_earned_point(self, server_id, user_id):
        await self.client.table("point_earned").insert({"server_id": server_id, "user_id": user_id}).execute()

    async def update_earned_point(self, server_id, user_id, point):
        await self.client.table("point_earned").update({"point": point}).eq("server_id", server_id).eq("user_id", user_id).execute()

    async def remove_earned_point(self, server_id, user_id):
        await self.client.table("point_earned").delete().eq("server_id", server_id).eq("user_id", user_id).execute()

    async def get_earned_point(self, server_id, user_id):
        result = await self.client.table("point_earned").select("*").eq("server_id", server_id).eq("user_id", user_id).execute()
        return result.data[0] if result.data else None

    async def get_user_earned_points_on_server(self, server_id, limit=10):
        result = await self.client.table("point_earned").select("*").eq("server_id", server_id).order("point", desc=True).limit(limit).execute()
        return result.data if result.data else None
