from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message
import database as db
from utils.keyboards import (
    channel_list_keyboard, confirm_giveaway_keyboard, giveaway_created_keyboard,
    giveaway_channel_post_keyboard, giveaway_list_keyboard, manage_giveaway_keyboard,
    participant_list_keyboard, confirm_end_giveaway_keyboard, create_giveaway_keyboard,
    back_to_menu_keyboard, paginated_participant_list_keyboard
)
from utils.helpers import generate_giveaway_id, get_user_owned_channels
from config import BOT_USERNAME, FREE_PLAN_MAX_GIVEAWAYS

pending_vote_ops = {}


def register_giveaway_handlers(app: Client):

    @app.on_callback_query(filters.regex(r"^create_giveaway$"))
    async def create_giveaway_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        user = callback_query.from_user

        sub_info = await db.get_subscription_info(user.id)
        max_giveaways = sub_info["max_giveaways"]
        active_count = await db.count_active_giveaways(user.id)

        if active_count >= max_giveaways:
            plan_text = sub_info["plan_name"]
            if max_giveaways == 0:
                await callback_query.message.edit_text(
                    "<emoji id=5447644880824181073>⚠️</emoji> <b>No Active Plan!</b>\n\n"
                    "You need a subscription plan to create giveaways.\n"
                    "Your current <b>Free</b> plan does not include any giveaways.\n\n"
                    "<emoji id=5249037681727404734>💰</emoji> Buy a subscription to get started!",
                    reply_markup=back_to_menu_keyboard()
                )
            else:
                await callback_query.message.edit_text(
                    f"<emoji id=5447644880824181073>⚠️</emoji> <b>Giveaway Limit Reached!</b>\n\n"
                    f"Your <b>{plan_text}</b> plan allows <b>{max_giveaways}</b> simultaneous giveaway(s).\n"
                    f"You currently have <b>{active_count}</b> active giveaway(s).\n\n"
                    f"Upgrade your plan or end an existing giveaway first.",
                    reply_markup=back_to_menu_keyboard()
                )
            return

        bot_channels = await db.get_all_bot_channels()
        if not bot_channels:
            await callback_query.message.edit_text(
                "<emoji id=5399849634350768407>❌</emoji> <b>No Channels Found!</b>\n\n"
                "I'm not added to any channels yet.\n"
                "Add me to your channel as an admin first, then try again.",
                reply_markup=back_to_menu_keyboard()
            )
            return

        owned_channels = await get_user_owned_channels(client, user.id, bot_channels)
        if not owned_channels:
            await callback_query.message.edit_text(
                "<emoji id=5399849634350768407>❌</emoji> <b>No Owned Channels Found!</b>\n\n"
                "I couldn't find any channels where you are the owner "
                "and I am an admin.\n\n"
                "Make sure:\n"
                "1. You own the channel\n"
                "2. I am added as an admin with send &amp; edit permissions",
                reply_markup=back_to_menu_keyboard()
            )
            return

        await callback_query.message.edit_text(
            "<emoji id=5424818078833715060>📢</emoji> <b>Select a Channel</b>\n\n"
            "Choose a channel where you want to create the giveaway:",
            reply_markup=channel_list_keyboard(owned_channels, prefix="select_channel")
        )

    @app.on_callback_query(filters.regex(r"^select_channel:"))
    async def select_channel_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        channel_id = int(callback_query.data.split(":")[1])

        try:
            chat = await client.get_chat(channel_id)
            channel_name = chat.title or f"Channel {channel_id}"
        except Exception:
            channel_name = f"Channel {channel_id}"

        await callback_query.message.edit_text(
            f"<emoji id=5436113877181941026>❓</emoji> <b>Confirm Giveaway Creation</b>\n\n"
            f"Are you sure you want to create a giveaway in:\n"
            f"<emoji id=5424818078833715060>📢</emoji> <b>{channel_name}</b>?",
            reply_markup=confirm_giveaway_keyboard(channel_id)
        )

    @app.on_callback_query(filters.regex(r"^cancel_giveaway$"))
    async def cancel_giveaway_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer("Cancelled!")
        from utils.keyboards import main_menu_keyboard
        await callback_query.message.edit_text(
            "<emoji id=5399849634350768407>❌</emoji> <b>Giveaway creation cancelled.</b>\n\n"
            "Returning to main menu.",
            reply_markup=main_menu_keyboard()
        )

    @app.on_callback_query(filters.regex(r"^confirm_giveaway:"))
    async def confirm_giveaway_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        user = callback_query.from_user
        channel_id = int(callback_query.data.split(":")[1])

        try:
            chat = await client.get_chat(channel_id)
            channel_name = chat.title or f"Channel {channel_id}"
            channel_username = chat.username
        except Exception:
            channel_name = f"Channel {channel_id}"
            channel_username = None

        giveaway_id = generate_giveaway_id()
        while await db.get_giveaway(giveaway_id):
            giveaway_id = generate_giveaway_id()

        await db.create_giveaway(
            giveaway_id=giveaway_id,
            owner_id=user.id,
            channel_id=channel_id,
            channel_name=channel_name,
            channel_username=channel_username
        )

        giveaway_link = f"https://t.me/{BOT_USERNAME}?start={giveaway_id}"

        if channel_username:
            channel_display = f"@{channel_username}"
        else:
            channel_display = f"<code>{channel_id}</code>"

        await callback_query.message.edit_text(
            f"<emoji id=5249226475604811538>✅</emoji> <b>Giveaway Created Successfully!</b>\n\n"
            f"<emoji id=6255512604110751681>⚠️</emoji> <b>Giveaway ID:</b> <code>{giveaway_id}</code>\n"
            f"<emoji id=6255512604110751681>⚠️</emoji> <b>Channel:</b> {channel_display}\n"
            f"<emoji id=5229211777681604441>🔗</emoji> <b>Link:</b> <code>{giveaway_link}</code>\n\n"
            f"The giveaway has been posted to your channel!",
            reply_markup=giveaway_created_keyboard(giveaway_id)
        )

        try:
            channel_msg = await client.send_message(
                chat_id=channel_id,
                text=(
                    "<emoji id=5461131730968651745>🎉</emoji> <b>New Giveaway Started!</b>\n\n"
                    "Click the button below to participate in this exciting giveaway!"
                ),
                reply_markup=giveaway_channel_post_keyboard(giveaway_id)
            )
            await db.update_giveaway_channel_message(giveaway_id, channel_msg.id)
        except Exception as e:
            print(f"[ERROR] Failed to post giveaway to channel {channel_id}: {e}")

    @app.on_callback_query(filters.regex(r"^manage_giveaways$"))
    async def manage_giveaways_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        user = callback_query.from_user

        active_giveaways = await db.get_active_giveaways_by_owner(user.id)

        if not active_giveaways:
            await callback_query.message.edit_text(
                "<emoji id=5445002853166885679>📭</emoji> <b>No Active Giveaways</b>\n\n"
                "You don't have any active giveaways.\n"
                "Create a new one to get started!",
                reply_markup=create_giveaway_keyboard()
            )
            return

        await callback_query.message.edit_text(
            "<emoji id=5341715473882955310>⚙️</emoji> <b>Manage Giveaways</b>\n\n"
            "Select a giveaway to manage:",
            reply_markup=giveaway_list_keyboard(active_giveaways)
        )

    @app.on_callback_query(filters.regex(r"^manage_ga:"))
    async def manage_specific_giveaway_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        giveaway_id = callback_query.data.split(":")[1]

        giveaway = await db.get_giveaway(giveaway_id)
        if not giveaway:
            await callback_query.message.edit_text(
                "❌ Giveaway not found.",
                reply_markup=back_to_menu_keyboard()
            )
            return

        participant_count = await db.get_participant_count(giveaway_id)
        channel_name = giveaway["channel_name"] or "Unknown"

        await callback_query.message.edit_text(
            f"<emoji id=5341715473882955310>⚙️</emoji> <b>Giveaway Management Panel</b>\n\n"
            f"<b>Channel:</b> {channel_name}\n"
            f"<b>Giveaway ID:</b> <code>{giveaway_id}</code>\n"
            f"<b>Status:</b> {giveaway['status'].title()}\n"
            f"<b>Participants:</b> {participant_count}\n\n"
            f"Select an action:",
            reply_markup=manage_giveaway_keyboard(giveaway_id)
        )

    @app.on_callback_query(filters.regex(r"^add_votes:"))
    async def add_votes_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        giveaway_id = callback_query.data.split(":")[1]

        participants = await db.get_participants(giveaway_id)
        if not participants:
            await callback_query.message.edit_text(
                "<emoji id=6296341890371422476>📭</emoji> <b>No Participants Yet</b>\n\nNo one has joined this giveaway yet.",
                reply_markup=back_to_menu_keyboard()
            )
            return

        await callback_query.message.edit_text(
            "<emoji id=5397916757333654639>➕</emoji> <b>Add Votes</b>\n\n"
            "Select a participant to add votes:",
            reply_markup=paginated_participant_list_keyboard(participants, giveaway_id, "addv", page=0)
        )

    @app.on_callback_query(filters.regex(r"^addv_user:"))
    async def addv_user_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        parts = callback_query.data.split(":")
        giveaway_id = parts[1]
        participant_id = int(parts[2])

        participant = await db.get_participant(giveaway_id, participant_id)
        if not participant:
            await callback_query.answer("Participant not found!", show_alert=True)
            return

        display_name = participant["first_name"] or participant["username"] or f"User {participant_id}"

        pending_vote_ops[callback_query.from_user.id] = {
            "giveaway_id": giveaway_id,
            "participant_id": participant_id,
            "participant_name": display_name,
            "action": "add"
        }

        await callback_query.message.edit_text(
            f"<emoji id=5397916757333654639>➕</emoji> <b>Add Votes to {display_name}</b>\n\n"
            f"Current Votes: <b>{participant['votes']}</b>\n\n"
            f"<b>Reply to this message</b> with the number of votes you want to add.",
            reply_markup=back_to_menu_keyboard()
        )

    @app.on_callback_query(filters.regex(r"^remove_votes:"))
    async def remove_votes_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        giveaway_id = callback_query.data.split(":")[1]

        participants = await db.get_participants(giveaway_id)
        if not participants:
            await callback_query.message.edit_text(
                "<emoji id=6296341890371422476>📭</emoji> <b>No Participants Yet</b>\n\nNo one has joined this giveaway yet.",
                reply_markup=back_to_menu_keyboard()
            )
            return

        await callback_query.message.edit_text(
            "<emoji id=6298394017155516458>➖</emoji> <b>Remove Votes</b>\n\n"
            "Select a participant to remove votes:",
            reply_markup=paginated_participant_list_keyboard(participants, giveaway_id, "rmv", page=0)
        )

    @app.on_callback_query(filters.regex(r"^addv_page:"))
    async def addv_page_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        parts = callback_query.data.split(":")
        giveaway_id = parts[1]
        page = int(parts[2])

        participants = await db.get_participants(giveaway_id)
        await callback_query.message.edit_text(
            "<emoji id=5397916757333654639>➕</emoji> <b>Add Votes</b>\n\n"
            "Select a participant to add votes:",
            reply_markup=paginated_participant_list_keyboard(participants, giveaway_id, "addv", page=page)
        )

    @app.on_callback_query(filters.regex(r"^rmv_page:"))
    async def rmv_page_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        parts = callback_query.data.split(":")
        giveaway_id = parts[1]
        page = int(parts[2])

        participants = await db.get_participants(giveaway_id)
        await callback_query.message.edit_text(
            "<emoji id=6298394017155516458>➖</emoji> <b>Remove Votes</b>\n\n"
            "Select a participant to remove votes:",
            reply_markup=paginated_participant_list_keyboard(participants, giveaway_id, "rmv", page=page)
        )

    @app.on_callback_query(filters.regex(r"^rmv_user:"))
    async def rmv_user_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        parts = callback_query.data.split(":")
        giveaway_id = parts[1]
        participant_id = int(parts[2])

        participant = await db.get_participant(giveaway_id, participant_id)
        if not participant:
            await callback_query.answer("Participant not found!", show_alert=True)
            return

        display_name = participant["first_name"] or participant["username"] or f"User {participant_id}"

        pending_vote_ops[callback_query.from_user.id] = {
            "giveaway_id": giveaway_id,
            "participant_id": participant_id,
            "participant_name": display_name,
            "action": "remove"
        }

        await callback_query.message.edit_text(
            f"<emoji id=6298394017155516458>➖</emoji> <b>Remove Votes from {display_name}</b>\n\n"
            f"Current Votes: <b>{participant['votes']}</b>\n\n"
            f"<b>Reply to this message</b> with the number of votes you want to remove.",
            reply_markup=back_to_menu_keyboard()
        )

    @app.on_message(filters.private & filters.reply & filters.text)
    async def handle_vote_input(client: Client, message: Message):
        user_id = message.from_user.id

        if await db.is_user_banned(user_id):
            return

        if user_id not in pending_vote_ops:
            return

        op = pending_vote_ops[user_id]
        text = message.text.strip()

        if not text.isdigit() or int(text) <= 0:
            await message.reply("<emoji id=5399849634350768407>❌</emoji> Please send a valid positive number.")
            return

        count = int(text)
        giveaway_id = op["giveaway_id"]
        participant_id = op["participant_id"]
        action = op["action"]

        if action == "add":
            await db.update_participant_votes(giveaway_id, participant_id, count)
            await db.add_vote_log(giveaway_id, user_id, participant_id, "admin_add", count)
            action_text = f"Added <b>{count}</b> votes to"
        else:
            await db.update_participant_votes(giveaway_id, participant_id, -count)
            await db.add_vote_log(giveaway_id, user_id, participant_id, "admin_remove", count)
            action_text = f"Removed <b>{count}</b> votes from"

        participant = await db.get_participant(giveaway_id, participant_id)
        new_votes = participant["votes"] if participant else 0

        if participant and participant.get("channel_message_id"):
            giveaway = await db.get_giveaway(giveaway_id)
            if giveaway:
                try:
                    from utils.keyboards import vote_button_keyboard
                    await client.edit_message_reply_markup(
                        chat_id=giveaway["channel_id"],
                        message_id=participant["channel_message_id"],
                        reply_markup=vote_button_keyboard(giveaway_id, participant_id, new_votes)
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to sync channel vote: {e}")

        del pending_vote_ops[user_id]

        await message.reply(
            f"<emoji id=5445241374175667041>✅</emoji> {action_text} <b>{op['participant_name']}</b>\n\n"
            f"New vote count: <b>{new_votes}</b>",
            reply_markup=manage_giveaway_keyboard(giveaway_id)
        )

    @app.on_callback_query(filters.regex(r"^leaderboard:"))
    async def leaderboard_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        giveaway_id = callback_query.data.split(":")[1]

        from utils.helpers import sync_giveaway_invalid_votes
        await sync_giveaway_invalid_votes(client, giveaway_id)

        leaders = await db.get_leaderboard(giveaway_id, limit=10)
        giveaway = await db.get_giveaway(giveaway_id)
        total_participants = await db.get_participant_count(giveaway_id)

        if not leaders:
            await callback_query.message.edit_text(
                "<emoji id=6296341890371422476>📭</emoji> <b>No Participants Yet</b>\n\nNo one has joined this giveaway yet.",
                reply_markup=manage_giveaway_keyboard(giveaway_id)
            )
            return

        channel_name = giveaway["channel_name"] if giveaway else "Unknown"
        text = f"<emoji id=5231200819986047254>🏆</emoji> <b>Leaderboard — {channel_name}</b>\n\n"

        medals = ["<emoji id=5440539497383087970>🥇</emoji>", "<emoji id=5447203607294265305>🥈</emoji>", "<emoji id=5453902265922376865>🥉</emoji>"]
        leaderboard_lines = []
        for i, p in enumerate(leaders):
            rank = medals[i] if i < 3 else f" {i + 1}."
            name = p["first_name"] or p["username"] or f"User {p['user_id']}"
            leaderboard_lines.append(f"{rank} <b>{name}</b> — {p['votes']} votes")

        text += "<blockquote>" + "\n".join(leaderboard_lines) + "</blockquote>"
        text += f"\n\n<emoji id=5334544901428229844>📊</emoji> <i>Total participants: {total_participants}</i>"

        try:
            await callback_query.message.edit_text(
                text,
                reply_markup=manage_giveaway_keyboard(giveaway_id)
            )
        except Exception:
            pass

    @app.on_callback_query(filters.regex(r"^end_giveaway:"))
    async def end_giveaway_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        giveaway_id = callback_query.data.split(":")[1]

        giveaway = await db.get_giveaway(giveaway_id)
        if not giveaway:
            await callback_query.answer("Giveaway not found!", show_alert=True)
            return

        await callback_query.message.edit_text(
            f"<emoji id=5395695537687123235>🛑</emoji> <b>End Giveaway?</b>\n\n"
            f"Are you sure you want to end the giveaway in <b>{giveaway['channel_name']}</b>?\n\n"
            f"This action cannot be undone.",
            reply_markup=confirm_end_giveaway_keyboard(giveaway_id)
        )

    @app.on_callback_query(filters.regex(r"^confirm_end:"))
    async def confirm_end_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer()
        giveaway_id = callback_query.data.split(":")[1]

        giveaway = await db.get_giveaway(giveaway_id)
        if not giveaway:
            await callback_query.answer("Giveaway not found!", show_alert=True)
            return

        from utils.helpers import sync_giveaway_invalid_votes
        await sync_giveaway_invalid_votes(client, giveaway_id)

        await db.end_giveaway(giveaway_id)

        leaders = await db.get_leaderboard(giveaway_id, limit=10)
        top_3 = leaders[:3] if leaders else []

        channel_text = "<emoji id=6296504553667823627>🏁</emoji> <b>Giveaway Ended!</b>\n\n"

        if top_3:
            channel_text += "<emoji id=5231200819986047254>🏆</emoji> <b>Top Participants:</b>\n\n"
            medals = ["<emoji id=5440539497383087970>🥇</emoji>", "<emoji id=5447203607294265305>🥈</emoji>", "<emoji id=5453902265922376865>🥉</emoji>"]
            for i, p in enumerate(top_3):
                name = p["first_name"] or p["username"] or f"User {p['user_id']}"
                channel_text += f"{medals[i]} <b>{name}</b> — {p['votes']} votes\n"

        channel_text += (
            "\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Thank you to everyone who participated in this giveaway. "
            "Stay tuned for more giveaways! <emoji id=5330090758349271612>🎉</emoji>\n\n"
            "Respective winners are requested to connect with admins "
            "to claim their rewards. <emoji id=5330312778093704176>🎁</emoji>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Best Regards,\n@{BOT_USERNAME}"
        )

        try:
            await client.send_message(
                chat_id=giveaway["channel_id"],
                text=channel_text
            )
        except Exception as e:
            print(f"[ERROR] Failed to post end message to channel: {e}")

        try:
            if giveaway.get("channel_message_id"):
                await client.edit_message_text(
                    chat_id=giveaway["channel_id"],
                    message_id=giveaway["channel_message_id"],
                    text="<emoji id=6296504553667823627>🏁</emoji> <b>This Giveaway Has Ended!</b>"
                )
        except Exception as e:
            print(f"[ERROR] Failed to update original channel message: {e}")

        result_text = f"<emoji id=6296504553667823627>🏁</emoji> <b>Giveaway Ended!</b>\n\n"
        result_text += f"<b>Channel:</b> {giveaway['channel_name']}\n"
        result_text += f"<b>Giveaway ID:</b> <code>{giveaway_id}</code>\n\n"

        if leaders:
            result_text += "<emoji id=5231200819986047254>🏆</emoji> <b>Final Results:</b>\n\n"
            medals = ["<emoji id=5440539497383087970>🥇</emoji>", "<emoji id=5447203607294265305>🥈</emoji>", "<emoji id=5453902265922376865>🥉</emoji>"]
            for i, p in enumerate(leaders):
                rank = medals[i] if i < 3 else f"<b>{i + 1}.</b>"
                name = p["first_name"] or p["username"] or f"User {p['user_id']}"
                result_text += f"{rank} {name} — <b>{p['votes']}</b> votes\n"
        else:
            result_text += "No participants joined this giveaway."

        await callback_query.message.edit_text(
            result_text,
            reply_markup=back_to_menu_keyboard()
        )

    @app.on_callback_query(filters.regex(r"^ai_analyser:"))
    async def ai_analyser_cb(client: Client, callback_query: CallbackQuery):
        if await db.is_user_banned(callback_query.from_user.id):
            return
        await callback_query.answer("AI Analyser is enabled by default for all giveaways!", show_alert=True)
