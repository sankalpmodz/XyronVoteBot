import motor.motor_asyncio
import datetime
from config import MONGO_URI, DB_NAME

_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
_db = _client[DB_NAME]

users_col = _db["users"]
plans_col = _db["plans"]
subscriptions_col = _db["subscriptions"]
redeem_codes_col = _db["redeem_codes"]
giveaways_col = _db["giveaways"]
participants_col = _db["participants"]
vote_log_col = _db["vote_log"]
bot_channels_col = _db["bot_channels"]
banned_users_col = _db["banned_users"]
purchase_requests_col = _db["purchase_requests"]


async def init_db():
    await users_col.create_index("user_id", unique=True)

    await plans_col.create_index("name", unique=True)

    await subscriptions_col.create_index("user_id")
    await subscriptions_col.create_index([("user_id", 1), ("status", 1)])
    await subscriptions_col.create_index([("status", 1), ("expiry_date", 1)])

    await redeem_codes_col.create_index("code", unique=True)

    await giveaways_col.create_index("giveaway_id", unique=True)
    await giveaways_col.create_index([("owner_id", 1), ("status", 1)])
    await giveaways_col.create_index([("channel_id", 1), ("status", 1)])

    await participants_col.create_index([("giveaway_id", 1), ("user_id", 1)], unique=True)
    await participants_col.create_index("giveaway_id")

    await vote_log_col.create_index([("giveaway_id", 1), ("voter_id", 1), ("participant_user_id", 1)])
    await vote_log_col.create_index([("giveaway_id", 1), ("voter_id", 1)])

    await bot_channels_col.create_index("channel_id", unique=True)

    await banned_users_col.create_index("user_id", unique=True)


def safe_int(value) -> int:
    if value is None:
        return 0
    return int(value)


async def add_user(user_id: int, username: str = None, first_name: str = None):
    user_id = safe_int(user_id)
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"username": username, "first_name": first_name},
         "$setOnInsert": {"joined_at": datetime.datetime.utcnow()}},
        upsert=True
    )


async def get_user(user_id: int):
    return await users_col.find_one({"user_id": safe_int(user_id)})


async def ban_user(user_id: int, reason: str = "Illegal content detected"):
    user_id = safe_int(user_id)
    await banned_users_col.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "reason": reason,
            "banned_at": datetime.datetime.utcnow()
        }},
        upsert=True
    )


async def unban_user(user_id: int):
    await banned_users_col.delete_one({"user_id": safe_int(user_id)})


async def is_user_banned(user_id: int) -> bool:
    doc = await banned_users_col.find_one({"user_id": safe_int(user_id)})
    return doc is not None


async def get_ban_info(user_id: int):
    return await banned_users_col.find_one({"user_id": safe_int(user_id)})


async def get_active_subscription(user_id: int):
    user_id = safe_int(user_id)
    sub = await subscriptions_col.find_one(
        {"user_id": user_id, "status": "Running"},
        sort=[("expiry_date", -1)]
    )
    if sub:
        if sub["expiry_date"] < datetime.datetime.utcnow():
            await subscriptions_col.update_one(
                {"_id": sub["_id"]},
                {"$set": {"status": "Ended"}}
            )
            return None
    return sub


async def create_subscription(user_id: int, plan_name: str, sub_id: str,
                              duration_days: int, max_giveaways: int):
    user_id = safe_int(user_id)
    now = datetime.datetime.utcnow()
    expiry = now + datetime.timedelta(days=duration_days)

    await subscriptions_col.update_many(
        {"user_id": user_id, "status": "Running"},
        {"$set": {"status": "Ended"}}
    )

    await subscriptions_col.insert_one({
        "user_id": user_id,
        "plan_name": plan_name,
        "sub_id": sub_id,
        "status": "Running",
        "start_date": now,
        "expiry_date": expiry,
        "max_giveaways": max_giveaways,
        "notified_24h": False,
        "notified_3h": False
    })


async def get_subscription_info(user_id: int) -> dict:
    sub = await get_active_subscription(user_id)
    if not sub:
        return {
            "sub_id": "Free",
            "status": "No Plan",
            "expires_in": "null",
            "expiry_date": "null",
            "max_giveaways": 0,
            "plan_name": "Free"
        }

    now = datetime.datetime.utcnow()
    diff = sub["expiry_date"] - now
    total_seconds = int(diff.total_seconds())

    if total_seconds <= 0:
        expires_in = "Expired"
    elif total_seconds >= 86400:
        days = total_seconds // 86400
        expires_in = f"{days} days"
    elif total_seconds >= 3600:
        hours = total_seconds // 3600
        expires_in = f"{hours} hours"
    else:
        minutes = max(1, total_seconds // 60)
        expires_in = f"{minutes} minutes"

    expiry_formatted = sub["expiry_date"].strftime("%d/%m/%Y")

    return {
        "sub_id": f"{sub['plan_name']}-{sub['sub_id']}",
        "status": sub["status"],
        "expires_in": expires_in,
        "expiry_date": expiry_formatted,
        "max_giveaways": sub["max_giveaways"],
        "plan_name": sub["plan_name"]
    }


async def get_subscriptions_nearing_expiry():
    now = datetime.datetime.utcnow()
    cursor = subscriptions_col.find({
        "status": "Running",
        "expiry_date": {"$gt": now}
    })
    return await cursor.to_list(length=500)


async def mark_subscription_notified(sub_id, field: str):
    await subscriptions_col.update_one(
        {"_id": sub_id},
        {"$set": {field: True}}
    )


async def has_user_ever_subscribed(user_id: int) -> bool:
    user_id = safe_int(user_id)
    count = await subscriptions_col.count_documents({"user_id": user_id})
    return count > 0


async def create_plan(name: str, duration_days: int, max_giveaways: int, price_label: str):
    await plans_col.insert_one({
        "name": name,
        "duration_days": duration_days,
        "max_giveaways": max_giveaways,
        "price_label": price_label,
        "created_at": datetime.datetime.utcnow()
    })


async def delete_plan(name: str):
    await plans_col.delete_one({"name": name})


async def get_all_plans():
    cursor = plans_col.find().sort("duration_days", 1)
    return await cursor.to_list(length=100)


async def get_plan_by_id(plan_id):
    from bson import ObjectId
    if isinstance(plan_id, str):
        plan_id = ObjectId(plan_id)
    return await plans_col.find_one({"_id": plan_id})


async def get_plan_by_name(name: str):
    return await plans_col.find_one({"name": name})


async def create_redeem_code(code: str, plan_id):
    await redeem_codes_col.insert_one({
        "code": code,
        "plan_id": plan_id,
        "created_at": datetime.datetime.utcnow(),
        "expires_at": datetime.datetime.utcnow() + datetime.timedelta(hours=12),
        "redeemed_by": None,
        "redeemed_at": None,
        "is_used": False
    })


async def get_redeem_code(code: str):
    now = datetime.datetime.utcnow()
    return await redeem_codes_col.find_one({
        "code": code,
        "is_used": False,
        "expires_at": {"$gt": now}
    })


async def use_redeem_code(code: str, user_id: int):
    await redeem_codes_col.update_one(
        {"code": code},
        {"$set": {
            "is_used": True,
            "redeemed_by": user_id,
            "redeemed_at": datetime.datetime.utcnow()
        }}
    )


async def get_unused_codes():
    now = datetime.datetime.utcnow()
    pipeline = [
        {"$match": {"is_used": False, "expires_at": {"$gt": now}}},
        {"$lookup": {
            "from": "plans",
            "localField": "plan_id",
            "foreignField": "_id",
            "as": "plan_info"
        }},
        {"$unwind": {"path": "$plan_info", "preserveNullAndEmptyArrays": True}},
        {"$addFields": {"plan_name": "$plan_info.name"}},
        {"$sort": {"created_at": -1}}
    ]
    cursor = redeem_codes_col.aggregate(pipeline)
    return await cursor.to_list(length=100)


async def cleanup_expired_codes():
    now = datetime.datetime.utcnow()
    result = await redeem_codes_col.delete_many({
        "is_used": False,
        "expires_at": {"$lte": now}
    })
    if result.deleted_count > 0:
        print(f"[CLEANUP] Deleted {result.deleted_count} expired redeem code(s)")
    return result.deleted_count


async def create_giveaway(giveaway_id: str, owner_id: int, channel_id: int,
                          channel_name: str, channel_username: str = None):
    owner_id = safe_int(owner_id)
    channel_id = safe_int(channel_id)
    await giveaways_col.insert_one({
        "giveaway_id": giveaway_id,
        "owner_id": owner_id,
        "channel_id": channel_id,
        "channel_name": channel_name,
        "channel_username": channel_username,
        "status": "active",
        "created_at": datetime.datetime.utcnow(),
        "channel_message_id": None
    })


async def get_giveaway(giveaway_id: str):
    return await giveaways_col.find_one({"giveaway_id": giveaway_id})


async def get_active_giveaways_by_owner(owner_id: int):
    cursor = giveaways_col.find({"owner_id": owner_id, "status": "active"})
    return await cursor.to_list(length=100)


async def get_active_giveaways_in_channel(channel_id: int):
    cursor = giveaways_col.find({"channel_id": channel_id, "status": "active"})
    return await cursor.to_list(length=100)


async def count_active_giveaways(owner_id: int) -> int:
    return await giveaways_col.count_documents({"owner_id": safe_int(owner_id), "status": "active"})


async def get_giveaways_with_expired_subs():
    now = datetime.datetime.utcnow()
    active_giveaways = await giveaways_col.find({"status": "active"}).to_list(length=500)
    
    expired_giveaways = []
    checked_owners = {}
    
    for ga in active_giveaways:
        owner_id = ga["owner_id"]
        
        if owner_id not in checked_owners:
            sub = await subscriptions_col.find_one(
                {"user_id": owner_id, "status": "Running"},
                sort=[("expiry_date", -1)]
            )
            if sub and sub["expiry_date"] < now:
                await subscriptions_col.update_one(
                    {"_id": sub["_id"]},
                    {"$set": {"status": "Ended"}}
                )
                checked_owners[owner_id] = True
            elif sub:
                checked_owners[owner_id] = False
            else:
                checked_owners[owner_id] = True
        
        if checked_owners[owner_id]:
            expired_giveaways.append(ga)
    
    return expired_giveaways


async def end_giveaway(giveaway_id: str):
    await giveaways_col.update_one(
        {"giveaway_id": giveaway_id},
        {"$set": {"status": "ended"}}
    )


async def update_giveaway_channel_message(giveaway_id: str, message_id: int):
    await giveaways_col.update_one(
        {"giveaway_id": giveaway_id},
        {"$set": {"channel_message_id": safe_int(message_id)}}
    )


async def add_participant(giveaway_id: str, user_id: int, username: str = None,
                          first_name: str = None, channel_message_id: int = None):
    user_id = safe_int(user_id)
    try:
        await participants_col.insert_one({
            "giveaway_id": giveaway_id,
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "votes": 0,
            "joined_at": datetime.datetime.utcnow(),
            "channel_message_id": safe_int(channel_message_id) if channel_message_id else None
        })
        return True
    except Exception:
        return False


async def get_participant(giveaway_id: str, user_id: int):
    return await participants_col.find_one({"giveaway_id": giveaway_id, "user_id": safe_int(user_id)})


async def get_participants(giveaway_id: str):
    cursor = participants_col.find({"giveaway_id": giveaway_id}).sort("votes", -1)
    return await cursor.to_list(length=500)


async def get_participant_count(giveaway_id: str) -> int:
    return await participants_col.count_documents({"giveaway_id": giveaway_id})


async def update_participant_votes(giveaway_id: str, user_id: int, vote_change: int):
    user_id = safe_int(user_id)
    participant = await get_participant(giveaway_id, user_id)
    if participant:
        new_votes = max(0, participant["votes"] + vote_change)
        await participants_col.update_one(
            {"giveaway_id": giveaway_id, "user_id": user_id},
            {"$set": {"votes": new_votes}}
        )


async def update_participant_channel_message(giveaway_id: str, user_id: int, message_id: int):
    await participants_col.update_one(
        {"giveaway_id": giveaway_id, "user_id": user_id},
        {"$set": {"channel_message_id": message_id}}
    )


async def get_leaderboard(giveaway_id: str, limit: int = 20):
    cursor = participants_col.find({"giveaway_id": giveaway_id}).sort("votes", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def add_vote_log(giveaway_id: str, voter_id: int, participant_user_id: int,
                       vote_type: str, count: int = 1):
    await vote_log_col.insert_one({
        "giveaway_id": giveaway_id,
        "voter_id": safe_int(voter_id),
        "participant_user_id": safe_int(participant_user_id),
        "vote_type": vote_type,
        "count": count,
        "timestamp": datetime.datetime.utcnow()
    })


async def has_user_voted(giveaway_id: str, voter_id: int, participant_user_id: int) -> bool:
    doc = await vote_log_col.find_one({
        "giveaway_id": giveaway_id,
        "voter_id": safe_int(voter_id),
        "participant_user_id": safe_int(participant_user_id),
        "vote_type": "public"
    })
    return doc is not None


async def get_votes_by_user_in_channel(channel_id: int, voter_id: int):
    channel_id = safe_int(channel_id)
    voter_id = safe_int(voter_id)
    active_giveaways = await get_active_giveaways_in_channel(channel_id)
    ga_ids = [ga["giveaway_id"] for ga in active_giveaways]

    if not ga_ids:
        return []

    cursor = vote_log_col.find({
        "giveaway_id": {"$in": ga_ids},
        "voter_id": voter_id,
        "vote_type": "public"
    })
    return await cursor.to_list(length=1000)


async def remove_votes_by_user(giveaway_id: str, voter_id: int):
    voter_id = safe_int(voter_id)
    pipeline = [
        {"$match": {
            "giveaway_id": giveaway_id,
            "voter_id": voter_id,
            "vote_type": "public"
        }},
        {"$group": {
            "_id": "$participant_user_id",
            "total": {"$sum": "$count"}
        }}
    ]
    cursor = vote_log_col.aggregate(pipeline)
    affected = await cursor.to_list(length=500)

    for entry in affected:
        participant_user_id = entry["_id"]
        total_remove = entry["total"]
        await update_participant_votes(giveaway_id, participant_user_id, -total_remove)

    await vote_log_col.delete_many({
        "giveaway_id": giveaway_id,
        "voter_id": voter_id,
        "vote_type": "public"
    })

    return affected


async def get_distinct_voters_in_giveaway(giveaway_id: str):
    return await vote_log_col.distinct("voter_id", {
        "giveaway_id": giveaway_id,
        "vote_type": "public"
    })


async def get_voters_for_participant(giveaway_id: str, participant_user_id: int):
    return await vote_log_col.distinct("voter_id", {
        "giveaway_id": giveaway_id,
        "participant_user_id": safe_int(participant_user_id),
        "vote_type": "public"
    })


async def add_bot_channel(channel_id: int, channel_name: str = None, channel_username: str = None):
    channel_id = safe_int(channel_id)
    await bot_channels_col.update_one(
        {"channel_id": channel_id},
        {"$set": {
            "channel_name": channel_name,
            "channel_username": channel_username,
            "added_at": datetime.datetime.utcnow()
        }},
        upsert=True
    )


async def remove_bot_channel(channel_id: int):
    await bot_channels_col.delete_one({"channel_id": safe_int(channel_id)})


async def get_all_bot_channels():
    cursor = bot_channels_col.find()
    return await cursor.to_list(length=500)


async def get_stats():
    return {
        "total_users": await users_col.count_documents({}),
        "active_giveaways": await giveaways_col.count_documents({"status": "active"}),
        "total_giveaways": await giveaways_col.count_documents({}),
        "active_subscriptions": await subscriptions_col.count_documents({"status": "Running"}),
        "unused_codes": await redeem_codes_col.count_documents({"is_used": False}),
        "banned_users": await banned_users_col.count_documents({})
    }


async def create_purchase_request(user_id: int, plan_name: str, plan_price: str):
    user_id = safe_int(user_id)
    await purchase_requests_col.update_one(
        {"user_id": user_id, "status": "pending"},
        {"$set": {
            "user_id": user_id,
            "plan_name": plan_name,
            "plan_price": plan_price,
            "status": "pending",
            "created_at": datetime.datetime.utcnow()
        }},
        upsert=True
    )


async def get_pending_purchase(user_id: int):
    return await purchase_requests_col.find_one(
        {"user_id": user_id, "status": "pending"}
    )


async def complete_purchase_request(user_id: int):
    await purchase_requests_col.update_one(
        {"user_id": user_id, "status": "pending"},
        {"$set": {"status": "completed", "completed_at": datetime.datetime.utcnow()}}
    )


async def cancel_purchase_request(user_id: int):
    await purchase_requests_col.delete_many(
        {"user_id": user_id, "status": "pending"}
    )


async def can_send_purchase_request(user_id: int, cooldown_hours: int = 24) -> bool:
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=cooldown_hours)
    recent = await purchase_requests_col.find_one({
        "user_id": user_id,
        "status": "completed",
        "completed_at": {"$gte": cutoff}
    })
    return recent is None


async def get_cooldown_remaining(user_id: int, cooldown_hours: int = 24) -> str:
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=cooldown_hours)
    recent = await purchase_requests_col.find_one(
        {"user_id": user_id, "status": "completed", "completed_at": {"$gte": cutoff}},
        sort=[("completed_at", -1)]
    )
    if not recent:
        return "0 minutes"
    
    next_allowed = recent["completed_at"] + datetime.timedelta(hours=cooldown_hours)
    remaining = next_allowed - datetime.datetime.utcnow()
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
