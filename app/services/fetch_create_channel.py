import json

from app.services.api_get_channel import get_channel

redis_expiry = 604800

async def fetch_create_channel(channel_handle, user_id, db, redis):
    cache_key = f"channel:{user_id}:{channel_handle}"

    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    channel = db.execute(
        ''' SELECT  channel_id, channel_title, channel_handle, subscriber_count, upload_playlist from channels WHERE channel_handle = %s;''', (channel_handle,) 
    ).fetchone()

    if channel:
        await redis.set(cache_key, json.dumps(channel), ex=redis_expiry)
        return channel
    
    channel_data = await get_channel(channel_handle)

    insert_query = """
        INSERT INTO channels (
            user_id,
            channel_id,
            platform,
            channel_title,
            channel_handle,
            subscriber_count,
            upload_playlist
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, user_id, channel_id, platform,
                  channel_title, channel_handle,
                  subscriber_count, upload_playlist;
    """

    inserted = db.execute(
        insert_query,
        (
            user_id,
            channel_data["channel_id"],
            "youtube",
            channel_data["channel_name"],
            channel_handle,
            channel_data["subscriber_count"],
            channel_data["uploads_playlist"],
        )
    ).fetchone()

    db.commit()

    inserted_dict = dict(inserted)

    # 5️⃣ Store in Redis
    await redis.set(cache_key, json.dumps(inserted_dict), ex=redis_expiry)

    return inserted_dict
