"""Handler for delivering original (uncompressed) images in the comment group.

When the bot posts compressed images to a channel, Telegram automatically
forwards a notification to the linked comment group (from system user 777000).
This handler detects that forwarded notification and replies with the original
images as documents (InputMediaDocument), preserving full quality.
"""

from __future__ import annotations

import logging

from telegram import InputMediaDocument, MessageOriginChannel, Update
from telegram.ext import ContextTypes

from client import ArtworkData

logger = logging.getLogger(__name__)

# Telegram system user ID that forwards channel posts to comment groups
TELEGRAM_SYSTEM_USER_ID = 777000


async def channel_post_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle forwarded channel posts in the comment group — reply with original images."""
    message = update.effective_message
    if not message:
        return

    # Extract the original channel message ID from the forward origin
    forward_origin = message.forward_origin
    if not isinstance(forward_origin, MessageOriginChannel):
        return

    channel_msg_id = forward_origin.message_id
    channel_posts: dict[int, ArtworkData] = context.bot_data.get("channel_posts", {})

    # Pop the cached artwork (one-time consumption to avoid memory leak)
    artwork = channel_posts.pop(channel_msg_id, None)
    if artwork is None:
        logger.debug("No cached artwork for channel message %d", channel_msg_id)
        return

    urls = artwork.image_urls
    if not urls:
        return

    logger.info(
        "Sending %d original image(s) for artwork #%d in comment group",
        len(urls),
        artwork.id,
    )

    # Send original images as documents in batches of 10 (Telegram limit)
    for batch_start in range(0, len(urls), 10):
        batch = urls[batch_start : batch_start + 10]
        if len(batch) == 1:
            await message.reply_document(document=batch[0])
        else:
            media = [InputMediaDocument(media=url) for url in batch]
            await message.reply_media_group(media=media)
