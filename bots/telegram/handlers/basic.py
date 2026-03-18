from telegram import Update
from telegram.ext import ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Hyacine Gallery Bot is running.")


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("pong")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>Commands:</b>\n"
        "/post &lt;url&gt; [#tag1 #tag2] — Import and post to channel\n"
        "/post &lt;url&gt; --no-post — Import only (no channel post)\n"
        "/post &lt;id&gt; — Post existing artwork to channel\n"
        "/import &lt;url&gt; [#tag1 #tag2] — Import only (alias)\n"
        "/random — Get a random artwork\n"
        "/help — Show this message"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="HTML")
