"""评论群原图自动回复处理器。

当 bot 将压缩图片发布到频道后，Telegram 会自动将通知转发到关联的评论群
（来自系统用户 777000）。此处理器检测到该转发通知后，以文档形式
（InputMediaDocument）回复原图，保留完整画质。
"""

from __future__ import annotations

import logging

from telegram import InputMediaDocument, MessageOriginChannel, Update
from telegram.ext import ContextTypes

from client import ArtworkData

logger = logging.getLogger(__name__)

# Telegram 系统用户 ID，用于将频道帖子转发到评论群
TELEGRAM_SYSTEM_USER_ID = 777000


async def channel_post_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """处理评论群中转发的频道帖子 — 回复原图。"""
    message = update.effective_message
    if not message:
        return

    # 从转发来源中提取原始频道消息 ID
    forward_origin = message.forward_origin
    if not isinstance(forward_origin, MessageOriginChannel):
        return

    channel_msg_id = forward_origin.message_id
    channel_posts: dict[int, ArtworkData] = context.bot_data.get("channel_posts", {})

    # 弹出缓存的作品（一次性消费，避免内存泄漏）
    artwork = channel_posts.pop(channel_msg_id, None)
    if artwork is None:
        logger.debug("未找到频道消息 %d 对应的缓存作品", channel_msg_id)
        return

    urls = artwork.image_urls
    if not urls:
        return

    logger.info(
        "正在为作品 #%d 在评论群中发送 %d 张原图",
        artwork.id,
        len(urls),
    )

    # 以文档形式分批发送原图（Telegram 限制每批 10 张）
    for batch_start in range(0, len(urls), 10):
        batch = urls[batch_start : batch_start + 10]
        if len(batch) == 1:
            await message.reply_document(document=batch[0])
        else:
            media = [InputMediaDocument(media=url) for url in batch]
            await message.reply_media_group(media=media)
