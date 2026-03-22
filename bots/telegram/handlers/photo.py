"""图片消息处理器 — 以图搜图 + 转发消息自动提取 + 外部溯源。"""

from __future__ import annotations

import io
import logging
import re
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from handlers.artwork import _get_client, _is_admin

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://\S+")


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
    message = update.effective_message
    if not message or not message.photo:
        return

    user = update.effective_user
    user_id = user.id if user else None
    is_admin_user = await _is_admin(user_id, context)
    is_forwarded = message.forward_origin is not None

    # 路由逻辑
    if is_forwarded and is_admin_user:
        caption = message.caption or ""
        urls = _URL_RE.findall(caption)
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
        for r in results[:5]:
            title = r.title or r.pid
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
    """管理员转发了带链接的消息 → 提示导入。"""
    message = update.effective_message
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
        for r in local_results[:3]:
            title = r.title or r.pid
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

    lines = ["找到以下来源：\n"]
    buttons = []
    for r in results[:5]:
        title = r.title or "未知"
        lines.append(f"• [{r.provider}] <b>{title}</b> ({r.platform}, {r.similarity:.0f}%)")
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
            await query.edit_message_text(
                f"已导入作品 #{artwork.id}（{artwork.platform}/{artwork.pid}）。"
            )
        except Exception as e:
            await query.edit_message_text(f"导入失败: {str(e)[:200]}")
