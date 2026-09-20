import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
import database as db
from utils.decorators import owner_only
from utils.helpers import generate_redeem_code, generate_sub_id
from config import OWNER_ID


def register_owner_handlers(app: Client):

    @app.on_message(filters.command("createplan") & filters.private)
    @owner_only
    async def create_plan_cmd(client: Client, message: Message):
        args = message.text.split(maxsplit=4)
        if len(args) < 5:
            await message.reply(
                "❌ <b>Usage:</b> <code>/createplan &lt;name&gt; &lt;duration_days&gt; &lt;max_giveaways&gt; &lt;price_label&gt;</code>\n\n"
                "<b>Example:</b> <code>/createplan Premium 30 5 ₹499</code>\n\n"
                "<b>Parameters:</b>\n"
                "• <code>name</code> — Plan name (no spaces)\n"
                "• <code>duration_days</code> — Subscription duration in days\n"
                "• <code>max_giveaways</code> — Max simultaneous giveaways\n"
                "• <code>price_label</code> — Display price (e.g., ₹499, $5)"
            )
            return

        name = args[1].strip()
        try:
            duration = int(args[2].strip())
            max_ga = int(args[3].strip())
        except ValueError:
            await message.reply("❌ Duration and max giveaways must be numbers.")
            return

        price_label = args[4].strip()

        existing = await db.get_plan_by_name(name)
        if existing:
            await message.reply(f"❌ Plan <b>{name}</b> already exists!")
            return

        await db.create_plan(name, duration, max_ga, price_label)
        await message.reply(
            f"✅ <b>Plan Created!</b>\n\n"
            f"<b>Name:</b> {name}\n"
            f"<b>Duration:</b> {duration} days\n"
            f"<b>Max Giveaways:</b> {max_ga}\n"
            f"<b>Price:</b> {price_label}"
        )

    @app.on_message(filters.command("deleteplan") & filters.private)
    @owner_only
    async def delete_plan_cmd(client: Client, message: Message):
        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ <b>Usage:</b> <code>/deleteplan &lt;plan_name&gt;</code>")
            return

        name = args[1].strip()
        plan = await db.get_plan_by_name(name)
        if not plan:
            await message.reply(f"❌ Plan <b>{name}</b> not found.")
            return

        await db.delete_plan(name)
        await message.reply(f"✅ Plan <b>{name}</b> deleted successfully.")

    @app.on_message(filters.command("listplans") & filters.private)
    @owner_only
    async def list_plans_cmd(client: Client, message: Message):
        plans = await db.get_all_plans()
        if not plans:
            await message.reply("📭 No plans created yet. Use <code>/createplan</code> to create one.")
            return

        text = "📦 <b>All Plans</b>\n\n"
        for plan in plans:
            text += (
                f"<b>{plan['name']}</b> (ID: {plan['_id']})\n"
                f"   ├ Duration: {plan['duration_days']} days\n"
                f"   ├ Max Giveaways: {plan['max_giveaways']}\n"
                f"   └ Price: {plan['price_label']}\n\n"
            )
        await message.reply(text)

    @app.on_message(filters.command("gencode") & filters.private)
    @owner_only
    async def gencode_cmd(client: Client, message: Message):
        args = message.text.split()
        if len(args) < 2:
            await message.reply(
                "❌ <b>Usage:</b> <code>/gencode &lt;plan_name&gt;</code>\n\n"
                "<b>Example:</b> <code>/gencode Premium</code>"
            )
            return

        plan_name = args[1].strip()
        plan = await db.get_plan_by_name(plan_name)
        if not plan:
            await message.reply(f"❌ Plan <b>{plan_name}</b> not found. Use <code>/listplans</code> to see available plans.")
            return

        code = generate_redeem_code()

        while await db.get_redeem_code(code):
            code = generate_redeem_code()

        await db.create_redeem_code(code, plan["_id"])

        await message.reply(
            f"🎟 <b>Redeem Code Generated!</b>\n\n"
            f"<b>Code:</b> <code>{code}</code>\n"
            f"<b>Plan:</b> {plan['name']}\n"
            f"<b>Duration:</b> {plan['duration_days']} days\n"
            f"<b>Max Giveaways:</b> {plan['max_giveaways']}\n"
            f"<b>⏳ Expires in:</b> 12 hours\n\n"
            f"Share this code with the user. They can activate it with:\n"
            f"<code>/redeem {code}</code>"
        )

    @app.on_message(filters.command("listcodes") & filters.private)
    @owner_only
    async def list_codes_cmd(client: Client, message: Message):
        codes = await db.get_unused_codes()
        if not codes:
            await message.reply("📭 No unused redeem codes. Use <code>/gencode &lt;plan_name&gt;</code> to generate one.")
            return

        text = "🎟 <b>Unused Redeem Codes</b>\n\n"
        now = datetime.datetime.utcnow()
        for code in codes:
            plan_name = code.get("plan_name", "Unknown")
            expires_at = code.get("expires_at")
            if expires_at:
                remaining = expires_at - now
                hours = int(remaining.total_seconds() // 3600)
                mins = int((remaining.total_seconds() % 3600) // 60)
                expiry_text = f"⏳ {hours}h {mins}m"
            else:
                expiry_text = "⏳ N/A"
            text += f"• <code>{code['code']}</code> → <b>{plan_name}</b> ({expiry_text})\n"
        await message.reply(text)

    @app.on_message(filters.command("unban") & filters.private)
    @owner_only
    async def unban_cmd(client: Client, message: Message):
        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ <b>Usage:</b> <code>/unban &lt;user_id&gt;</code>")
            return

        try:
            target_id = int(args[1].strip())
        except ValueError:
            await message.reply("❌ User ID must be a number.")
            return

        ban_info = await db.get_ban_info(target_id)
        if not ban_info:
            await message.reply(f"ℹ️ User <code>{target_id}</code> is not banned.")
            return

        await db.unban_user(target_id)
        await message.reply(
            f"✅ <b>User Unbanned!</b>\n\n"
            f"<b>User ID:</b> <code>{target_id}</code>\n"
            f"<b>Was banned for:</b> {ban_info.get('reason', 'N/A')}\n\n"
            f"The user can now use the bot again."
        )

    @app.on_message(filters.command("stats") & filters.private)
    @owner_only
    async def stats_cmd(client: Client, message: Message):
        stats = await db.get_stats()
        await message.reply(
            f"📊 <b>Bot Statistics</b>\n\n"
            f"👥 Total Users: <b>{stats['total_users']}</b>\n"
            f"🎉 Active Giveaways: <b>{stats['active_giveaways']}</b>\n"
            f"📋 Total Giveaways: <b>{stats['total_giveaways']}</b>\n"
            f"💎 Active Subscriptions: <b>{stats['active_subscriptions']}</b>\n"
            f"🎟 Unused Codes: <b>{stats['unused_codes']}</b>\n"
            f"🚫 Banned Users: <b>{stats['banned_users']}</b>"
        )

    @app.on_callback_query(filters.regex(r"^approve_purchase:"))
    async def approve_purchase_cb(client: Client, callback_query: CallbackQuery):
        if callback_query.from_user.id != OWNER_ID:
            await callback_query.answer("Owner only!", show_alert=True)
            return

        await callback_query.answer()
        parts = callback_query.data.split(":")
        user_id = int(parts[1])
        plan_name = parts[2]

        plan = await db.get_plan_by_name(plan_name)
        if not plan:
            await callback_query.message.edit_text(
                f"❌ Plan <b>{plan_name}</b> not found! It may have been deleted.\n"
                f"Use <code>/gencode</code> manually to create a code for a different plan."
            )
            return

        sub_id = generate_sub_id()
        await db.create_subscription(
            user_id=user_id,
            plan_name=plan["name"],
            sub_id=sub_id,
            duration_days=plan["duration_days"],
            max_giveaways=plan["max_giveaways"]
        )

        await callback_query.message.edit_text(
            callback_query.message.text + "\n\n✅ <b>APPROVED</b> — Subscription activated!"
        )

        try:
            from utils.helpers import format_subscription_info
            sub_info = await db.get_subscription_info(user_id)
            info_text = format_subscription_info(sub_info)
            await client.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 <b>Purchase Approved!</b>\n\n"
                    f"Your <b>{plan['name']}</b> plan has been activated!\n\n"
                    f"{info_text}\n\n"
                    f"Enjoy your subscription! 🚀"
                )
            )
        except Exception as e:
            print(f"[ERROR] Failed to notify user {user_id}: {e}")

    @app.on_callback_query(filters.regex(r"^reject_purchase:"))
    async def reject_purchase_cb(client: Client, callback_query: CallbackQuery):
        if callback_query.from_user.id != OWNER_ID:
            await callback_query.answer("Owner only!", show_alert=True)
            return

        await callback_query.answer()
        parts = callback_query.data.split(":")
        user_id = int(parts[1])

        await callback_query.message.edit_text(
            callback_query.message.text + "\n\n❌ <b>REJECTED</b>"
        )

        try:
            await client.send_message(
                chat_id=user_id,
                text=(
                    "❌ <b>Purchase Request Rejected</b>\n\n"
                    "Your purchase request has been rejected by the bot owner.\n"
                    "If you believe this is an error, please contact the owner directly."
                )
            )
        except Exception as e:
            print(f"[ERROR] Failed to notify user {user_id}: {e}")

    @app.on_callback_query(filters.regex(r"^noop$"))
    async def noop_cb(client: Client, callback_query: CallbackQuery):
        await callback_query.answer()
