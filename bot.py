import asyncio
import datetime
from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated, Message, CallbackQuery
from pyrogram.enums import ChatMemberStatus, ChatType, ParseMode

from config import API_ID, API_HASH, BOT_TOKEN
import database as db
from utils.keyboards import vote_button_keyboard

app = Client(
    "votingbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    parse_mode=ParseMode.HTML
)


@app.on_message(filters.private, group=-999)
async def global_ban_check_message(client: Client, message: Message):
    if message.from_user and await db.is_user_banned(message.from_user.id):
        message.stop_propagation()


@app.on_callback_query(group=-999)
async def global_ban_check_callback(client: Client, callback_query: CallbackQuery):
    if callback_query.from_user and await db.is_user_banned(callback_query.from_user.id):
        callback_query.stop_propagation()


@app.on_chat_member_updated()
async def track_bot_and_user_membership(client: Client, update: ChatMemberUpdated):
    if update.chat.type not in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
        return

    bot_me = await client.get_me()
    channel_id = update.chat.id

    if update.new_chat_member and update.new_chat_member.user.id == bot_me.id:
        new_status = update.new_chat_member.status

        if new_status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
            await db.add_bot_channel(
                channel_id=channel_id,
                channel_name=update.chat.title,
                channel_username=update.chat.username
            )
            print(f"[INFO] Bot added to channel: {update.chat.title} ({channel_id})")

        elif new_status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            await db.remove_bot_channel(channel_id)
            print(f"[INFO] Bot removed from channel: {update.chat.title} ({channel_id})")

        return

    if update.new_chat_member:
        new_status = update.new_chat_member.status
        user = update.new_chat_member.user

        if user.is_bot:
            return

        if new_status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            user_id = int(user.id)
            ch_id = int(channel_id)

            active_giveaways = await db.get_active_giveaways_in_channel(ch_id)

            if not active_giveaways:
                return

            print(f"[VOTE_REMOVAL] User {user_id} left channel {ch_id}. "
                  f"Checking {len(active_giveaways)} active giveaway(s).")

            for giveaway in active_giveaways:
                giveaway_id = giveaway["giveaway_id"]

                try:
                    affected = await db.remove_votes_by_user(giveaway_id, user_id)
                except Exception as e:
                    print(f"[VOTE_REMOVAL] Error removing votes: {e}")
                    continue

                if not affected:
                    continue

                print(f"[VOTE_REMOVAL] Removed votes from {len(affected)} participant(s) "
                      f"in giveaway {giveaway_id}")

                for entry in affected:
                    participant_user_id = entry["_id"]
                    participant = await db.get_participant(giveaway_id, participant_user_id)
                    if participant and participant.get("channel_message_id"):
                        try:
                            await client.edit_message_reply_markup(
                                chat_id=ch_id,
                                message_id=participant["channel_message_id"],
                                reply_markup=vote_button_keyboard(
                                    giveaway_id,
                                    participant_user_id,
                                    participant["votes"]
                                )
                            )
                        except Exception as e:
                            print(f"[VOTE_REMOVAL] Failed to sync vote button: {e}")


from handlers.start import register_start_handlers, register_join_handler
from handlers.giveaway import register_giveaway_handlers
from handlers.subscription import register_subscription_handlers
from handlers.voting import register_voting_handlers
from handlers.owner import register_owner_handlers

register_start_handlers(app)
register_join_handler(app)
register_giveaway_handlers(app)
register_subscription_handlers(app)
register_voting_handlers(app)
register_owner_handlers(app)

_bg_started = False


@app.on_message(filters.private, group=-1000)
async def _trigger_bg_tasks(client, message):
    global _bg_started
    if _bg_started:
        return
    _bg_started = True
    me = await client.get_me()
    print(f"[INFO] Bot running as @{me.username} ({me.id})")
    asyncio.create_task(periodic_cleanup())
    asyncio.create_task(auto_end_expired_giveaways())
    asyncio.create_task(periodic_vote_membership_sync())
    asyncio.create_task(auto_notify_expiring_subscriptions())


async def auto_notify_expiring_subscriptions():
    from utils.keyboards import subscription_keyboard
    await asyncio.sleep(20)
    while True:
        try:
            now = datetime.datetime.utcnow()
            active_subs = await db.get_subscriptions_nearing_expiry()
            for sub in active_subs:
                user_id = sub["user_id"]
                expiry = sub["expiry_date"]
                plan_name = sub.get("plan_name", "Subscription")
                time_left = expiry - now

                if time_left <= datetime.timedelta(hours=24) and not sub.get("notified_24h"):
                    await db.mark_subscription_notified(sub["_id"], "notified_24h")
                    try:
                        await app.send_message(
                            chat_id=user_id,
                            text=(
                                f"<emoji id=5447644880824181073>⚠️</emoji> <b>Subscription Expiring Soon!</b>\n\n"
                                f"Your <b>{plan_name}</b> plan will expire in <b>1 day (24 hours)</b> on <code>{expiry.strftime('%d/%m/%Y')}</code>.\n\n"
                                f"Renew your subscription to enjoy uninterrupted service and keep your giveaways active! <emoji id=5332290778037235887>💎</emoji>"
                            ),
                            reply_markup=subscription_keyboard(has_plan=True, can_renew=True)
                        )
                        print(f"[EXPIRY_NOTIFY] Sent 24h warning to user {user_id} ({plan_name})")
                    except Exception as e:
                        print(f"[EXPIRY_NOTIFY] Failed to send 24h warning to {user_id}: {e}")

                if time_left <= datetime.timedelta(hours=3) and not sub.get("notified_3h"):
                    await db.mark_subscription_notified(sub["_id"], "notified_3h")
                    try:
                        await app.send_message(
                            chat_id=user_id,
                            text=(
                                f"<emoji id=5447644880824181073>🚨</emoji> <b>Urgent: Subscription Expiring in 3 Hours!</b>\n\n"
                                f"Your <b>{plan_name}</b> plan will expire in less than <b>3 hours</b>.\n\n"
                                f"Renew your subscription now to avoid automatic termination of your active giveaways! <emoji id=5332290778037235887>💎</emoji>"
                            ),
                            reply_markup=subscription_keyboard(has_plan=True, can_renew=True)
                        )
                        print(f"[EXPIRY_NOTIFY] Sent 3h warning to user {user_id} ({plan_name})")
                    except Exception as e:
                        print(f"[EXPIRY_NOTIFY] Failed to send 3h warning to {user_id}: {e}")

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[EXPIRY_NOTIFY_ERROR] {e}")

        await asyncio.sleep(300)


async def periodic_cleanup():
    while True:
        try:
            await asyncio.sleep(3600)
            await db.cleanup_expired_codes()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[CLEANUP_ERROR] {e}")


async def periodic_vote_membership_sync():
    from utils.helpers import sync_giveaway_invalid_votes
    await asyncio.sleep(15)
    while True:
        try:
            active_giveaways = await db.giveaways_col.find({"status": "active"}).to_list(length=100)
            for ga in active_giveaways:
                giveaway_id = ga["giveaway_id"]
                await sync_giveaway_invalid_votes(app, giveaway_id)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[VOTE_SYNC_ERROR] {e}")

        await asyncio.sleep(45)


async def auto_end_expired_giveaways():
    await asyncio.sleep(30)
    while True:
        try:
            expired_giveaways = await db.get_giveaways_with_expired_subs()
            for ga in expired_giveaways:
                giveaway_id = ga["giveaway_id"]
                channel_id = ga["channel_id"]
                owner_id = ga["owner_id"]
                channel_name = ga.get("channel_name", "Unknown")

                await db.end_giveaway(giveaway_id)
                print(f"[AUTO-END] Giveaway {giveaway_id} in {channel_name} auto-ended (subscription expired)")

                try:
                    leaders = await db.get_leaderboard(giveaway_id, limit=3)
                    medals = ["🥇", "🥈", "🥉"]
                    top_text = ""
                    for i, p in enumerate(leaders):
                        name = p["first_name"] or p["username"] or f"User {p['user_id']}"
                        top_text += f"{medals[i]} <b>{name}</b> — {p['votes']} votes\n"

                    bot_me = await app.get_me()
                    text = (
                        f"🏁 <b>Giveaway Ended (Plan Expired)</b>\n\n"
                        f"The giveaway in this channel has been automatically ended "
                        f"because the host's subscription plan has expired.\n\n"
                    )
                    if top_text:
                        text += f"🏆 <b>Top Participants:</b>\n{top_text}\n"
                    text += (
                        f"Thank you to everyone who participated! 🎉\n"
                        f"Stay tuned for more giveaways.\n\n"
                        f"Best Regards,\n@{bot_me.username}"
                    )
                    await app.send_message(chat_id=channel_id, text=text)
                except Exception as e:
                    print(f"[AUTO-END] Failed to post end message for {giveaway_id}: {e}")

                try:
                    await app.send_message(
                        chat_id=owner_id,
                        text=(
                            f"⚠️ <b>Giveaway Auto-Ended</b>\n\n"
                            f"Your giveaway in <b>{channel_name}</b> (ID: <code>{giveaway_id}</code>) "
                            f"has been automatically ended because your subscription plan expired.\n\n"
                            f"Renew your plan to create new giveaways."
                        )
                    )
                except Exception:
                    pass

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[AUTO-END_ERROR] {e}")

        await asyncio.sleep(300)


async def _init_db():
    await db.init_db()
    print("[INFO] MongoDB connected & indexes created.")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_init_db())

    print("[INFO] Starting bot...")
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n[INFO] Bot stopped.")
