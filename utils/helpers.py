import random
import string
import asyncio
from pyrogram.types import ChatMember
from pyrogram.enums import ChatMemberStatus, ChatType
import database as db
from utils.keyboards import vote_button_keyboard


def generate_giveaway_id() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def generate_sub_id() -> str:
    return ''.join(random.choices(string.digits, k=6))


def generate_redeem_code() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))


def format_subscription_info(info: dict) -> str:
    return (
        f"<emoji id=5852987302761991595>📋</emoji> <b>Subscription Details</b>\n\n"
        f"<emoji id=6255512604110751681>⚠️</emoji> <b>Subscription ID:</b> <code>{info['sub_id']}</code>\n"
        f"<emoji id=6255512604110751681>⚠️</emoji> <b>Status:</b> {info['status']}\n"
        f"<emoji id=6255512604110751681>⚠️</emoji> <b>Expires In:</b> {info['expires_in']}\n"
        f"<emoji id=6255512604110751681>⚠️</emoji> <b>Expiry Date:</b> {info['expiry_date']}\n\n"
        f"<emoji id=6255512604110751681>⚠️</emoji> <b>Simultaneous Giveaways:</b> {info['max_giveaways']}"
    )


async def get_user_owned_channels(app, user_id: int, bot_channels: list) -> list:
    owned = []
    for ch in bot_channels:
        try:
            member = await app.get_chat_member(ch["channel_id"], user_id)
            if member.status == ChatMemberStatus.OWNER:
                owned.append({
                    "channel_id": ch["channel_id"],
                    "channel_name": ch["channel_name"],
                    "channel_username": ch["channel_username"]
                })
        except Exception:
            continue
    return owned


async def check_bot_admin_permissions(app, channel_id: int) -> bool:
    try:
        bot_me = await app.get_me()
        member = await app.get_chat_member(channel_id, bot_me.id)
        if member.status == ChatMemberStatus.ADMINISTRATOR:
            privs = member.privileges
            return privs.can_post_messages and privs.can_edit_messages
        return False
    except Exception:
        return False


def censor_text(text: str) -> str:
    if not text:
        return text
    words = text.split()
    censored = []
    for word in words:
        prefix = ""
        suffix = ""
        core = word
        while core and not core[0].isalnum():
            prefix += core[0]
            core = core[1:]
        while core and not core[-1].isalnum():
            suffix = core[-1] + suffix
            core = core[:-1]

        if len(core) <= 3:
            censored.append(word)
        else:
            masked = core[0] + "*" * (len(core) - 2) + core[-1]
            censored.append(prefix + masked + suffix)
    return " ".join(censored)


def censor_profile_field(text: str) -> str:
    return censor_text(text) if text else "N/A"


async def sync_giveaway_invalid_votes(client, giveaway_id: str) -> list:
    giveaway = await db.get_giveaway(giveaway_id)
    if not giveaway or giveaway["status"] != "active":
        return []

    channel_id = giveaway["channel_id"]
    voter_ids = await db.get_distinct_voters_in_giveaway(giveaway_id)
    if not voter_ids:
        return []

    affected_participants = {}

    for voter_id in voter_ids:
        is_member = False
        try:
            member = await client.get_chat_member(channel_id, voter_id)
            if member.status not in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                is_member = True
        except Exception:
            is_member = False

        if not is_member:
            print(f"[VOTE_CLEANUP] Left voter {voter_id} detected in giveaway {giveaway_id}. Removing votes.")
            affected = await db.remove_votes_by_user(giveaway_id, voter_id)
            for entry in affected:
                pid = entry["_id"]
                affected_participants[pid] = True

        await asyncio.sleep(0.05)

    for participant_user_id in affected_participants.keys():
        participant = await db.get_participant(giveaway_id, participant_user_id)
        if participant and participant.get("channel_message_id"):
            try:
                await client.edit_message_reply_markup(
                    chat_id=channel_id,
                    message_id=participant["channel_message_id"],
                    reply_markup=vote_button_keyboard(
                        giveaway_id,
                        participant_user_id,
                        participant["votes"]
                    )
                )
            except Exception as e:
                print(f"[VOTE_CLEANUP] Failed to update vote button for user {participant_user_id}: {e}")
            await asyncio.sleep(0.4)

    return list(affected_participants.keys())


async def clean_participant_invalid_votes(client, giveaway_id: str, channel_id: int, participant_user_id: int):
    voter_ids = await db.get_voters_for_participant(giveaway_id, participant_user_id)
    if not voter_ids:
        participant = await db.get_participant(giveaway_id, participant_user_id)
        return participant["votes"] if participant else 0

    removed_any = False
    for voter_id in voter_ids:
        is_member = False
        try:
            member = await client.get_chat_member(channel_id, voter_id)
            if member.status not in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                is_member = True
        except Exception:
            is_member = False

        if not is_member:
            print(f"[VOTE_CLEANUP] Left voter {voter_id} detected for participant {participant_user_id}. Removing.")
            await db.remove_votes_by_user(giveaway_id, voter_id)
            removed_any = True

    participant = await db.get_participant(giveaway_id, participant_user_id)
    new_votes = participant["votes"] if participant else 0

    if removed_any and participant and participant.get("channel_message_id"):
        try:
            await client.edit_message_reply_markup(
                chat_id=channel_id,
                message_id=participant["channel_message_id"],
                reply_markup=vote_button_keyboard(giveaway_id, participant_user_id, new_votes)
            )
        except Exception as e:
            print(f"[VOTE_CLEANUP] Error syncing button for {participant_user_id}: {e}")

    return new_votes
