"""Artwork-related command handlers: /random, /post."""

from __future__ import annotations

import logging

from telegram import InputMediaPhoto, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from client import ArtworkData, GalleryClient
from config import bot_settings

logger = logging.getLogger(__name__)


def _get_client(context: ContextTypes.DEFAULT_TYPE) -> GalleryClient:
    return context.bot_data["gallery_client"]  # type: ignore[return-value]


def _is_admin(user_id: int | None) -> bool:
    if user_id is None:
        return False
    return user_id in bot_settings.telegram_admin_chats


def format_caption(artwork: ArtworkData) -> str:
    """Build a Telegram-friendly caption for an artwork."""
    parts: list[str] = []

    # Title + author
    title = artwork.title or "Untitled"
    if artwork.author:
        parts.append(f"<b>{title}</b> by <b>{artwork.author}</b>")
    else:
        parts.append(f"<b>{title}</b>")

    # Tags
    if artwork.tag_names:
        tag_line = " ".join(f"#{t}" for t in artwork.tag_names)
        parts.append(tag_line)

    # Source link
    if artwork.source_url:
        parts.append(f'<a href="{artwork.source_url}">source</a>')

    # Flags
    flags: list[str] = []
    if artwork.is_nsfw:
        flags.append("NSFW")
    if artwork.is_ai:
        flags.append("AI")
    if flags:
        parts.append(" | ".join(flags))

    return "\n".join(parts)


async def send_artwork(
    update: Update,
    artwork: ArtworkData,
    *,
    reply: bool = True,
) -> None:
    """Send artwork images + caption to the chat where the command was issued."""
    message = update.effective_message
    if not message:
        return

    caption = format_caption(artwork)
    urls = artwork.image_urls

    if not urls:
        await message.reply_text(f"Artwork #{artwork.id} has no images.")
        return

    if len(urls) == 1:
        await message.reply_photo(
            photo=urls[0],
            caption=caption,
            parse_mode=ParseMode.HTML,
        )
    else:
        # Media group: caption goes on the first item
        media = [
            InputMediaPhoto(
                media=url,
                caption=caption if i == 0 else None,
                parse_mode=ParseMode.HTML if i == 0 else None,
            )
            for i, url in enumerate(urls[:10])  # Telegram limit: 10 per group
        ]
        await message.reply_media_group(media=media)


async def post_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    artwork: ArtworkData,
) -> str | None:
    """Post artwork to the configured Telegram channel. Returns message link or None."""
    channel = bot_settings.telegram_channel
    if not channel:
        return None

    caption = format_caption(artwork)
    urls = artwork.image_urls

    if not urls:
        return None

    if len(urls) == 1:
        msg = await context.bot.send_photo(
            chat_id=channel,
            photo=urls[0],
            caption=caption,
            parse_mode=ParseMode.HTML,
        )
        return _message_link(channel, msg.message_id)
    else:
        media = [
            InputMediaPhoto(
                media=url,
                caption=caption if i == 0 else None,
                parse_mode=ParseMode.HTML if i == 0 else None,
            )
            for i, url in enumerate(urls[:10])
        ]
        msgs = await context.bot.send_media_group(chat_id=channel, media=media)
        if msgs:
            return _message_link(channel, msgs[0].message_id)
        return None


def _message_link(channel: str, message_id: int) -> str:
    """Construct a t.me link for a channel message."""
    # channel can be "@channelname" or a numeric ID like "-100xxx"
    if channel.startswith("@"):
        return f"https://t.me/{channel[1:]}/{message_id}"
    # For numeric IDs, strip the -100 prefix
    chat_id = str(channel).replace("-100", "")
    return f"https://t.me/c/{chat_id}/{message_id}"


# ── Command handlers ──────────────────────────────────────────────


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /random — send a random artwork to the chat."""
    client = _get_client(context)
    artwork = await client.get_random()
    if artwork is None:
        if update.message:
            await update.message.reply_text("No artworks in the database yet.")
        return

    await send_artwork(update, artwork)


async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /post <artwork_id> — post an artwork to the channel (admin only)."""
    if not update.message or not update.effective_user:
        return

    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("Permission denied.")
        return

    if not bot_settings.telegram_channel:
        await update.message.reply_text("No channel configured (TELEGRAM_CHANNEL).")
        return

    args = context.args or []
    if not args:
        await update.message.reply_text("Usage: /post <artwork_id>")
        return

    try:
        artwork_id = int(args[0])
    except ValueError:
        await update.message.reply_text("Invalid artwork ID.")
        return

    client = _get_client(context)
    artwork = await client.get_artwork(artwork_id)
    if artwork is None:
        await update.message.reply_text(f"Artwork #{artwork_id} not found.")
        return

    link = await post_to_channel(context, artwork)
    if link:
        await update.message.reply_text(f"Posted: {link}")
    else:
        await update.message.reply_text("Failed to post (no images or channel error).")
