"""Artwork-related command handlers: /random, /post, /import."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

import httpx
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


def _get_setting(context: ContextTypes.DEFAULT_TYPE, key: str, default: str = "") -> str:
    """Get a bot setting: check backend settings cache first, fall back to .env."""
    remote = context.bot_data.get("bot_settings", {})
    if key in remote:
        return remote[key]
    return default


def _get_setting_int(context: ContextTypes.DEFAULT_TYPE, key: str, default: int) -> int:
    val = _get_setting(context, key, "")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return default


def format_caption(artwork: ArtworkData, tail_text: str = "") -> str:
    """Build a Telegram-friendly caption for an artwork."""
    parts: list[str] = []

    title = artwork.title or "Untitled"
    if artwork.author:
        parts.append(f"<b>{title}</b> by <b>{artwork.author}</b>")
    else:
        parts.append(f"<b>{title}</b>")

    if artwork.tag_names:
        tag_line = " ".join(f"#{t}" for t in artwork.tag_names)
        parts.append(tag_line)

    if artwork.source_url:
        parts.append(f'<a href="{artwork.source_url}">source</a>')

    flags: list[str] = []
    if artwork.is_nsfw:
        flags.append("NSFW")
    if artwork.is_ai:
        flags.append("AI")
    if flags:
        parts.append(" | ".join(flags))

    if tail_text:
        parts.append(tail_text)

    return "\n".join(parts)


@dataclass
class PostResult:
    message_link: str
    message_id: str
    channel_id: str


async def send_artwork(
    update: Update,
    artwork: ArtworkData,
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

    spoiler = artwork.is_nsfw

    if len(urls) == 1:
        await message.reply_photo(
            photo=urls[0],
            caption=caption,
            parse_mode=ParseMode.HTML,
            has_spoiler=spoiler,
        )
    else:
        media = [
            InputMediaPhoto(
                media=url,
                caption=caption if i == 0 else None,
                parse_mode=ParseMode.HTML if i == 0 else None,
                has_spoiler=spoiler,
            )
            for i, url in enumerate(urls[:10])
        ]
        await message.reply_media_group(media=media)


async def post_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    artwork: ArtworkData,
    channel_id: str,
) -> PostResult | None:
    """Post artwork to a specific Telegram channel. Returns PostResult or None."""
    if not channel_id:
        return None

    tail_text = _get_setting(context, "message_tail_text", bot_settings.message_tail_text)
    caption = format_caption(artwork, tail_text=tail_text)
    urls = artwork.image_urls

    if not urls:
        return None

    spoiler = artwork.is_nsfw

    # Anti-spam: disable notification if posting too frequently
    notification_interval = _get_setting_int(
        context, "notification_interval", bot_settings.notification_interval
    )
    now = time.time()
    last_post_time = context.bot_data.get("last_post_time", 0.0)
    disable_notification = (now - last_post_time) < notification_interval

    if len(urls) == 1:
        msg = await context.bot.send_photo(
            chat_id=channel_id,
            photo=urls[0],
            caption=caption,
            parse_mode=ParseMode.HTML,
            has_spoiler=spoiler,
            disable_notification=disable_notification,
        )
        msg_id = str(msg.message_id)
    else:
        media = [
            InputMediaPhoto(
                media=url,
                caption=caption if i == 0 else None,
                parse_mode=ParseMode.HTML if i == 0 else None,
                has_spoiler=spoiler,
            )
            for i, url in enumerate(urls[:10])
        ]
        msgs = await context.bot.send_media_group(
            chat_id=channel_id,
            media=media,
            disable_notification=disable_notification,
        )
        if not msgs:
            return None
        msg_id = str(msgs[0].message_id)

    context.bot_data["last_post_time"] = now

    link = _message_link(channel_id, int(msg_id))
    return PostResult(message_link=link, message_id=msg_id, channel_id=channel_id)


def _message_link(channel: str, message_id: int) -> str:
    if channel.startswith("@"):
        return f"https://t.me/{channel[1:]}/{message_id}"
    chat_id = str(channel).replace("-100", "")
    return f"https://t.me/c/{chat_id}/{message_id}"


async def _resolve_target_channel(
    context: ContextTypes.DEFAULT_TYPE,
    artwork: ArtworkData,
) -> str:
    """Determine which channel to post to via backend routing, with .env fallback."""
    client = _get_client(context)
    try:
        ch = await client.resolve_channel(artwork.id)
        if ch:
            return ch.channel_id
    except Exception:
        logger.warning("Failed to resolve channel from backend, using fallback", exc_info=True)
    return bot_settings.telegram_channel


async def _log_post(
    context: ContextTypes.DEFAULT_TYPE,
    artwork: ArtworkData,
    result: PostResult,
    posted_by: str,
) -> None:
    """Record the post to bot_post_logs via backend API."""
    client = _get_client(context)
    try:
        await client.create_post_log(
            artwork_id=artwork.id,
            channel_id=result.channel_id,
            message_id=result.message_id,
            message_link=result.message_link,
            posted_by=posted_by,
        )
    except Exception:
        logger.warning("Failed to record post log", exc_info=True)


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


_URL_RE = re.compile(r"https?://\S+")
_TAG_RE = re.compile(r"#(\S+)")


async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /post — unified command for import+post and post-existing.

    Usage:
        /post <url> [#tag1 #tag2]         — crawl URL, save, and post to channel
        /post <url> [#tag1] --no-post     — crawl URL and save only (alias for /import)
        /post <id>                        — post existing artwork to channel
        /post <id> --no-post              — preview existing artwork (send to chat)
    """
    if not update.message or not update.effective_user:
        return

    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("Permission denied.")
        return

    text = update.message.text or ""
    no_post = "--no-post" in text
    user_name = update.effective_user.username or str(update.effective_user.id)

    # Try to detect if argument is a URL or an artwork ID
    url_match = _URL_RE.search(text)

    if url_match:
        await _handle_post_url(update, context, text, url_match.group(0), no_post, user_name)
    else:
        await _handle_post_id(update, context, no_post, user_name)


async def _handle_post_url(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    url: str,
    no_post: bool,
    user_name: str,
) -> None:
    """Import from URL and optionally post to channel."""
    assert update.message is not None

    tags = _TAG_RE.findall(text)
    status_msg = await update.message.reply_text(f"Importing {url} ...")

    client = _get_client(context)
    try:
        artwork = await client.import_artwork(url, tags=tags or None)
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text[:200] if e.response else str(e)
        await status_msg.edit_text(f"Import failed: {error_detail}")
        return

    # Show the imported artwork in chat
    await send_artwork(update, artwork)

    if no_post:
        await status_msg.edit_text(f"Imported artwork #{artwork.id} ({artwork.platform}).")
        return

    # Resolve target channel and post
    channel_id = await _resolve_target_channel(context, artwork)
    if not channel_id:
        await status_msg.edit_text(f"Imported #{artwork.id}, but no channel configured.")
        return

    result = await post_to_channel(context, artwork, channel_id)
    if result:
        await _log_post(context, artwork, result, posted_by=user_name)
        await status_msg.edit_text(f"Imported #{artwork.id} and posted: {result.message_link}")
    else:
        await status_msg.edit_text(f"Imported #{artwork.id}, but channel post failed.")


async def _handle_post_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    no_post: bool,
    user_name: str,
) -> None:
    """Post an existing artwork by ID."""
    assert update.message is not None

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Usage:\n"
            "/post <url> [#tag1 #tag2] — import and post\n"
            "/post <id> — post existing artwork"
        )
        return

    try:
        artwork_id = int(args[0])
    except ValueError:
        await update.message.reply_text("Invalid artwork ID. Use a URL or numeric ID.")
        return

    client = _get_client(context)
    artwork = await client.get_artwork(artwork_id)
    if artwork is None:
        await update.message.reply_text(f"Artwork #{artwork_id} not found.")
        return

    if no_post:
        # Preview only
        await send_artwork(update, artwork)
        return

    channel_id = await _resolve_target_channel(context, artwork)
    if not channel_id:
        await update.message.reply_text("No channel configured.")
        return

    result = await post_to_channel(context, artwork, channel_id)
    if result:
        await _log_post(context, artwork, result, posted_by=user_name)
        await update.message.reply_text(f"Posted: {result.message_link}")
    else:
        await update.message.reply_text("Failed to post (no images or channel error).")


async def import_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /import <url> [#tag1 #tag2] — crawl URL and save artwork (no channel post).

    This is an alias for `/post <url> --no-post`.
    """
    if not update.message or not update.effective_user:
        return

    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("Permission denied.")
        return

    text = update.message.text or ""
    url_match = _URL_RE.search(text)
    if not url_match:
        await update.message.reply_text("Usage: /import <url> [#tag1 #tag2]")
        return

    tags = _TAG_RE.findall(text)
    status_msg = await update.message.reply_text(f"Importing {url_match.group(0)} ...")

    client = _get_client(context)
    try:
        artwork = await client.import_artwork(url_match.group(0), tags=tags or None)
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text[:200] if e.response else str(e)
        await status_msg.edit_text(f"Import failed: {error_detail}")
        return

    await send_artwork(update, artwork)
    await status_msg.edit_text(f"Imported artwork #{artwork.id} ({artwork.platform}).")
