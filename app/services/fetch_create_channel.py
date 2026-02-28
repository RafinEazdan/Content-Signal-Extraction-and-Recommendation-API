import json

from app.services.api_get_channel import get_channel

redis_expiry = 604800

async def fetch_create_channel(channel_handle, db, redis):
    cache_key = f"channel:{channel_handle}"

    cached = await redis.get(cache_key)
    if cached:
        print("From Redis")
        return json.loads(cached)
    
    channel = db.execute(
        ''' SELECT  channel_id, channel_title, channel_handle, subscriber_count, upload_playlist from channels WHERE channel_handle = %s;''', (channel_handle,) 
    ).fetchone()

    if channel:
        print("From DataBase")
        channel = dict(channel)
        await redis.set(cache_key, json.dumps(channel), expire=redis_expiry)
        return channel
    print("From API")
    channel_data = await get_channel(channel_handle)

    insert_query = """
        INSERT INTO channels (
            channel_id,
            platform,
            channel_title,
            channel_handle,
            subscriber_count,
            upload_playlist
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING *;
    """

    inserted = db.execute(
        insert_query,
        (
            channel_data["channel_id"],
            "youtube",
            channel_data["channel_title"],
            channel_handle,
            channel_data["subscriber_count"],
            channel_data["upload_playlist"],
        )
    ).fetchone()

    db.commit()

    inserted_dict = dict(inserted)

    await redis.set(cache_key, json.dumps(inserted_dict), expire=redis_expiry)

    return inserted_dict
