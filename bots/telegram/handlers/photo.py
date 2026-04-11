"""图片消息处理器 — 以图搜图 + 转发消息自动提取 + 外部溯源。"""

from __future__ import annotations

import io
import logging
import re
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatType, ParseMode
from telegram.ext import ContextTypes

from config import bot_settings
from handlers.artwork import (
    _get_client,
    _is_admin,
    _log_post,
    _resolve_target_channel,
    post_to_channel,
)
from handlers.settings import is_setting_enabled, settings_callback

logger = logging.getLogger(__name__)

# 作品 URL 特征模式（用于区分作品链接和作者主页）
_ARTWORK_URL_PATTERNS = [
    re.compile(r"pixiv\.net/(?:en/)?artworks/\d+"),
    re.compile(r"phixiv\.net/(?:en/)?artworks/\d+"),
    re.compile(r"(?:twitter|x|fxtwitter|vxtwitter|fixupx)\.com/\w+/status/\d+"),
    re.compile(r"(?:t\.bilibili\.com|bilibili\.com/opus)/\d+"),
    re.compile(r"(?:miyoushe|hoyolab|bbs\.mihoyo)\.com/\w+/article/\d+"),
]


def _extract_urls_from_message(message) -> list[str]:  # type: ignore[no-untyped-def]
    """从消息中提取可导入的 URL（支持纯文本 url 和 text_link entity）。

    优先返回作品链接；若有作品链接则过滤掉作者主页等无关链接，
    若无作品链接则返回所有 URL（供 gallery-dl fallback）。
    """
    seen: set[str] = set()
    artwork_urls: list[str] = []
    other_urls: list[str] = []

    entities = message.caption_entities or []
    caption = message.caption or ""

    for entity in entities:
        url = ""
        if entity.type == "url":
            # 纯文本 URL：从 caption 中截取
            url = caption[entity.offset : entity.offset + entity.length]
        elif entity.type == "text_link" and entity.url:
            # 文字链接：URL 在 entity.url 中
            url = entity.url

        if not url or url in seen:
            continue
        seen.add(url)

        if any(p.search(url) for p in _ARTWORK_URL_PATTERNS):
            artwork_urls.append(url)
        else:
            other_urls.append(url)

    # 有作品链接时只返回作品链接，避免导入作者主页
    return artwork_urls if artwork_urls else other_urls


async def _download_telegram_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bytes:
    """下载 Telegram 消息中最大尺寸的图片。"""
    message = update.effective_message
    photo = message.photo[-1]  # largest size
    file = await context.bot.get_file(photo.file_id)
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    return buf.getvalue()


def _store_url(context: ContextTypes.DEFAULT_TYPE, url: str) -> str:
    """将 URL 存入 bot_data 并返回短 key（解决 callback_data 64 字节限制）。"""
    key = uuid.uuid4().hex[:8]
    context.bot_data.setdefault("pending_urls", {})[key] = url
    return key


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """统一入口：处理所有收到的图片消息。"""
    chat = update.effective_chat
    if chat and chat.type == ChatType.CHANNEL:
        logger.info("忽略频道图片消息，避免 bot 将交互提示发到公开频道")
        return

    message = update.effective_message
    if not message or not message.photo:
        return

    user = update.effective_user
    user_id = user.id if user else None
    is_admin_user = await _is_admin(user_id, context)
    is_forwarded = message.forward_origin is not None

    # 路由逻辑
    if is_forwarded and is_admin_user:
        urls = _extract_urls_from_message(message)
        if urls:
            await _handle_forwarded_with_url(update, context, urls)
            return
        await _handle_forwarded_reverse_search(update, context)
        return

    await _handle_phash_search(update, context, is_admin_user)


async def _handle_phash_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    is_admin_user: bool,
) -> None:
    """本地 pHash 相似图搜索。"""
    message = update.effective_message
    status = await message.reply_text("正在搜索相似图片...")

    image_data = await _download_telegram_photo(update, context)
    client = _get_client(context)

    try:
        results = await client.search_by_image(image_data, threshold=10)
    except Exception:
        logger.exception("pHash 搜索失败")
        await status.edit_text("搜索失败，请稍后再试。")
        return

    if results:
        lines = ["找到以下相似作品：\n"]
        buttons = []
        gallery_base = bot_settings.gallery_url.rstrip("/")
        for r in results[:5]:
            title = r.title or r.pid
            if gallery_base:
                link = f"{gallery_base}/artwork/{r.artwork_id}"
                lines.append(f'• <a href="{link}">{title}</a> ({r.platform}, 距离={r.distance})')
            else:
                lines.append(f"• <b>{title}</b> ({r.platform}, 距离={r.distance})")
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"#{r.artwork_id} {title[:30]}",
                        callback_data=f"view_{r.artwork_id}",
                    )
                ]
            )
        await status.edit_text(
            "\n".join(lines),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    elif is_admin_user:
        await status.edit_text("本地未找到相似图片，正在通过外部服务搜索...")
        await _do_reverse_search(update, context, image_data, status)
    else:
        await status.edit_text("未找到相似图片。")


async def _handle_forwarded_with_url(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    urls: list[str],
) -> None:
    """管理员转发了带链接的消息 → 自动导入或提示确认。"""
    message = update.effective_message
    settings = context.bot_data.get("bot_settings", {})

    # 自动导入模式：直接导入并发布
    if is_setting_enabled(settings, "auto_import_url"):
        await _auto_import_urls(update, context, urls)
        return

    # 手动确认模式：显示导入按钮
    buttons = []
    for url in urls[:3]:
        key = _store_url(context, url)
        display = url[:50] + ("..." if len(url) > 50 else "")
        buttons.append([InlineKeyboardButton(f"导入: {display}", callback_data=f"imp:{key}")])
    buttons.append([InlineKeyboardButton("忽略", callback_data="dismiss")])

    await message.reply_text(
        f"检测到 {len(urls)} 个链接，是否导入？",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def _auto_import_urls(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    urls: list[str],
) -> None:
    """自动导入 URL 列表并发布到频道。"""
    message = update.effective_message
    user = update.effective_user
    user_name = user.username or str(user.id) if user else "unknown"
    client = _get_client(context)

    for url in urls[:3]:
        status = await message.reply_text(f"正在导入 {url[:50]}...")
        try:
            artwork = await client.import_artwork(url)
        except Exception as e:
            await status.edit_text(f"导入失败: {str(e)[:200]}")
            continue

        channel_id = await _resolve_target_channel(context, artwork)
        if not channel_id:
            await status.edit_text(f"已导入 #{artwork.id}，但未配置频道。")
            continue

        result = await post_to_channel(context, artwork, channel_id)
        if result:
            await _log_post(context, artwork, result, posted_by=user_name)
            await status.edit_text(
                f"已导入 #{artwork.id} 并发布。",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("跳转频道", url=result.message_link)]]
                ),
            )
        else:
            await status.edit_text(f"已导入 #{artwork.id}，但频道发布失败。")


async def _handle_forwarded_reverse_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """管理员转发了无链接的图片 → 先 pHash 再外部溯源。"""
    message = update.effective_message
    status = await message.reply_text("正在搜索来源...")

    image_data = await _download_telegram_photo(update, context)
    client = _get_client(context)

    try:
        local_results = await client.search_by_image(image_data, threshold=10)
    except Exception:
        local_results = []

    if local_results:
        lines = ["本地找到相似作品：\n"]
        buttons = []
        gallery_base = bot_settings.gallery_url.rstrip("/")
        for r in local_results[:3]:
            title = r.title or r.pid
            if gallery_base:
                link = f"{gallery_base}/artwork/{r.artwork_id}"
                lines.append(f'• <a href="{link}">{title}</a> ({r.platform}, 距离={r.distance})')
            else:
                lines.append(f"• <b>{title}</b> ({r.platform}, 距离={r.distance})")
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"#{r.artwork_id} {title[:30]}",
                        callback_data=f"view_{r.artwork_id}",
                    )
                ]
            )
        await status.edit_text(
            "\n".join(lines),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    await _do_reverse_search(update, context, image_data, status)


async def _do_reverse_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    image_data: bytes,
    status_message,
) -> None:
    """执行外部逆向搜索并展示结果。"""
    client = _get_client(context)

    try:
        results = await client.reverse_search_image(image_data)
    except Exception:
        logger.exception("外部搜索失败")
        await status_message.edit_text("外部搜索服务不可用。")
        return

    if not results:
        await status_message.edit_text("未找到来源，请手动处理。")
        return

    settings = context.bot_data.get("bot_settings", {})

    # 自动导入搜图模式：直接导入最佳结果
    if is_setting_enabled(settings, "auto_import_search"):
        best = results[0]
        await status_message.edit_text(
            f'找到最佳来源：<a href="{best.source_url}">{best.title or "未知"}</a>'
            f" ({best.platform}, {best.similarity:.0f}%)，正在导入...",
            parse_mode=ParseMode.HTML,
        )
        user = update.effective_user
        user_name = user.username or str(user.id) if user else "unknown"
        try:
            artwork = await client.import_artwork(best.source_url)
        except Exception as e:
            await status_message.edit_text(f"自动导入失败: {str(e)[:200]}")
            return

        channel_id = await _resolve_target_channel(context, artwork)
        if not channel_id:
            await status_message.edit_text(f"已导入 #{artwork.id}，但未配置频道。")
            return

        result = await post_to_channel(context, artwork, channel_id)
        if result:
            await _log_post(context, artwork, result, posted_by=user_name)
            await status_message.edit_text(
                f"已导入 #{artwork.id} 并发布。",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("跳转频道", url=result.message_link)]]
                ),
            )
        else:
            await status_message.edit_text(f"已导入 #{artwork.id}，但频道发布失败。")
        return

    # 手动确认模式：显示所有结果供选择
    lines = ["找到以下来源：\n"]
    buttons = []
    for r in results[:5]:
        title = r.title or "未知"
        lines.append(
            f'• [{r.provider}] <a href="{r.source_url}">{title}</a>'
            f" ({r.platform}, {r.similarity:.0f}%)"
        )
        key = _store_url(context, r.source_url)
        btn_text = f"导入 {r.platform} ({r.similarity:.0f}%)"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"imp:{key}")])

    buttons.append([InlineKeyboardButton("忽略", callback_data="dismiss")])
    await status_message.edit_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 InlineKeyboard 回调。"""
    query = update.callback_query
    if not query or not query.data:
        return

    # 设置面板回调（自行处理 answer）
    if await settings_callback(update, context):
        return

    await query.answer()

    data = query.data

    if data == "dismiss":
        await query.edit_message_reply_markup(reply_markup=None)
        return

    if data.startswith("view_"):
        artwork_id = int(data.removeprefix("view_"))
        client = _get_client(context)
        artwork = await client.get_artwork(artwork_id)
        if artwork:
            title = artwork.title_zh or artwork.title or artwork.pid
            await query.message.reply_text(
                f"<b>{title}</b>\n作者: {artwork.author}\n来源: {artwork.source_url}",
                parse_mode=ParseMode.HTML,
            )
        return

    if data.startswith("imp:"):
        key = data.removeprefix("imp:")
        pending = context.bot_data.get("pending_urls", {})
        url = pending.pop(key, None)
        if not url:
            await query.edit_message_text("链接已过期，请重新发送。")
            return
        user_id = query.from_user.id if query.from_user else None
        if not await _is_admin(user_id, context):
            await query.edit_message_text("权限不足。")
            return
        await query.edit_message_text(f"正在导入 {url} ...")
        client = _get_client(context)
        try:
            artwork = await client.import_artwork(url)
        except Exception as e:
            await query.edit_message_text(f"导入失败: {str(e)[:200]}")
            return

        # 导入成功后发布到频道
        channel_id = await _resolve_target_channel(context, artwork)
        if not channel_id:
            await query.edit_message_text(
                f"已导入 #{artwork.id}（{artwork.platform}/{artwork.pid}），但未配置频道。"
            )
            return

        result = await post_to_channel(context, artwork, channel_id)
        if result:
            user_name = query.from_user.username or str(user_id) if query.from_user else "unknown"
            await _log_post(context, artwork, result, posted_by=user_name)
            await query.edit_message_text(
                f"已导入 #{artwork.id} 并发布到频道。",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("跳转频道", url=result.message_link)]]
                ),
            )
        else:
            await query.edit_message_text(
                f"已导入 #{artwork.id}（{artwork.platform}/{artwork.pid}），但频道发布失败。"
            )
