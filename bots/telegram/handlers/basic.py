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
        "/import <url> [#tag1 #tag2] [--post] — Crawl URL and save artwork\n"
        "/post <artwork_id> — Post artwork to channel\n"
        "/random — Get a random artwork\n"
        "/help — Show this message"
    )
    if update.message:
        await update.message.reply_text(text)
