"""作品相关命令处理器：/random、/post、/import。"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

import asyncio
import io

import httpx
from PIL import Image
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, InputMediaPhoto, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from client import ArtworkData, GalleryClient
from config import bot_settings

logger = logging.getLogger(__name__)

# \w 在 Python re 中 Unicode 感知，自动保留汉字、假名、韩文、字母、数字、下划线
_HASHTAG_UNSAFE_RE = re.compile(r"[^\w]")


def _to_hashtag(tag: str) -> str:
    """将 tag 名称转换为合法的 Telegram hashtag（含 # 前缀）。"""
    tag = tag.replace(" ", "_").replace("-", "_")
    tag = _HASHTAG_UNSAFE_RE.sub("", tag)
    tag = tag.strip("_")
    return f"#{tag}" if tag else ""


def _get_client(context: ContextTypes.DEFAULT_TYPE) -> GalleryClient:
    return context.bot_data["gallery_client"]  # type: ignore[return-value]


async def _is_admin(user_id: int | None, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """判断用户是否有管理权限。优先查询后端 users 表；后端不可达时回退到本地配置。"""
    if user_id is None:
        return False

    client = _get_client(context)
    try:
        return await client.check_admin(user_id)
    except Exception:
        logger.warning("后端管理员查询失败，回退到本地 telegram_admin_chats 配置", exc_info=True)

    return user_id in bot_settings.telegram_admin_chats


def _get_setting(context: ContextTypes.DEFAULT_TYPE, key: str, default: str = "") -> str:
    """获取 bot 设置：优先检查后端缓存，回退到 .env 配置。"""
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
    """为作品生成 Telegram 格式的图片说明。"""
    parts: list[str] = []

    title = artwork.title_zh or artwork.title or "无题"
    if artwork.author:
        parts.append(f"<b>{title}</b> by <b>{artwork.author}</b>")
    else:
        parts.append(f"<b>{title}</b>")

    if artwork.tag_names:
        tag_line = " ".join(filter(None, (_to_hashtag(t) for t in artwork.tag_names)))
        if tag_line:
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


async def _download_images(client: GalleryClient, urls: list[str]) -> list[bytes]:
    """并发下载图片，返回原始字节列表（兼容本地存储和 S3）。"""
    return list(await asyncio.gather(*[client.download_image(url) for url in urls]))


_TG_MAX_EDGE = 2560


def _as_input_files(image_bytes: list[bytes]) -> list[InputFile]:
    """将图片字节缩放到 Telegram 最大尺寸限制（2560px），返回 InputFile 列表。"""
    files = []
    for i, data in enumerate(image_bytes):
        img = Image.open(io.BytesIO(data))
        w, h = img.size
        if max(w, h) > _TG_MAX_EDGE:
            scale = _TG_MAX_EDGE / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        files.append(InputFile(buf, filename=f"image_{i}.jpg"))
    return files


async def send_artwork(
    update: Update,
    artwork: ArtworkData,
    client: GalleryClient,
) -> None:
    """将作品图片和说明发送到触发命令的聊天中。"""
    message = update.effective_message
    if not message:
        return

    caption = format_caption(artwork)
    urls = artwork.image_urls

    if not urls:
        await message.reply_text(f"作品 #{artwork.id} 没有图片。")
        return

    spoiler = artwork.is_nsfw
    files = _as_input_files(await _download_images(client, urls[:10]))

    if len(files) == 1:
        await message.reply_photo(
            photo=files[0],
            caption=caption,
            parse_mode=ParseMode.HTML,
            has_spoiler=spoiler,
        )
    else:
        media = [
            InputMediaPhoto(
                media=f,
                caption=caption if i == 0 else None,
                parse_mode=ParseMode.HTML if i == 0 else None,
                has_spoiler=spoiler,
            )
            for i, f in enumerate(files)
        ]
        await message.reply_media_group(media=media)


async def post_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    artwork: ArtworkData,
    channel_id: str,
) -> PostResult | None:
    """将作品发布到指定 Telegram 频道。成功返回 PostResult，否则返回 None。"""
    if not channel_id:
        return None

    tail_text = _get_setting(context, "message_tail_text", bot_settings.message_tail_text)
    caption = format_caption(artwork, tail_text=tail_text)
    urls = artwork.image_urls

    if not urls:
        return None

    spoiler = artwork.is_nsfw

    # 防刷屏：发布过于频繁时静默通知
    notification_interval = _get_setting_int(
        context, "notification_interval", bot_settings.notification_interval
    )
    now = time.time()
    last_post_time = context.bot_data.get("last_post_time", 0.0)
    disable_notification = (now - last_post_time) < notification_interval

    client = _get_client(context)
    files = _as_input_files(await _download_images(client, urls[:10]))

    if len(files) == 1:
        msg = await context.bot.send_photo(
            chat_id=channel_id,
            photo=files[0],
            caption=caption,
            parse_mode=ParseMode.HTML,
            has_spoiler=spoiler,
            disable_notification=disable_notification,
        )
        msg_id = str(msg.message_id)
    else:
        media = [
            InputMediaPhoto(
                media=f,
                caption=caption if i == 0 else None,
                parse_mode=ParseMode.HTML if i == 0 else None,
                has_spoiler=spoiler,
            )
            for i, f in enumerate(files)
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

    # 缓存频道消息 → 作品映射，用于在评论群中发送原图
    context.bot_data.setdefault("channel_posts", {})[int(msg_id)] = artwork

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
    """通过后端路由确定发布目标频道，回退到 .env 配置。"""
    client = _get_client(context)
    try:
        ch = await client.resolve_channel(artwork.id)
        if ch:
            return ch.channel_id
    except Exception:
        logger.warning("从后端解析频道失败，使用回退配置", exc_info=True)
    return bot_settings.telegram_channel


async def _log_post(
    context: ContextTypes.DEFAULT_TYPE,
    artwork: ArtworkData,
    result: PostResult,
    posted_by: str,
) -> None:
    """通过后端 API 将发布记录写入 bot_post_logs。"""
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
        logger.warning("记录发布日志失败", exc_info=True)


# ── 命令处理器 ──────────────────────────────────────────────────────


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /search — 语义搜索作品。"""
    message = update.effective_message
    if not message or not context.args:
        if message:
            await message.reply_text("用法: /search <关键词>")
        return

    query = " ".join(context.args)
    client = _get_client(context)

    try:
        results = await client.semantic_search(query, top_k=5)
    except Exception:
        logger.exception("语义搜索失败")
        await message.reply_text("搜索失败，请稍后再试。")
        return

    if not results:
        await message.reply_text(f"未找到与「{query}」相关的作品。")
        return

    lines = [f"🔍 搜索「{query}」的结果：\n"]
    for artwork, score in results:
        display_title = artwork.title_zh or artwork.title or artwork.pid
        lines.append(f"• <b>{display_title}</b> (#{artwork.id}, 相似度 {score:.2f})")
    await message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /random — 随机发送一个作品到聊天中。"""
    client = _get_client(context)
    artwork = await client.get_random()
    if artwork is None:
        if update.message:
            await update.message.reply_text("数据库中暂无作品。")
        return

    await send_artwork(update, artwork, client)


_URL_RE = re.compile(r"https?://\S+")
_TAG_RE = re.compile(r"#(\S+)")


async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /post — 统一的导入发布命令。

    用法：
        /post <url> [#tag1 #tag2]         — 抓取 URL，保存并发布到频道
        /post <url> [#tag1] --no-post     — 仅抓取并保存（不发布到频道）
        /post <id>                        — 将已有作品发布到频道
        /post <id> --no-post              — 预览已有作品（发送到当前聊天）
    """
    if not update.message or not update.effective_user:
        return

    if not await _is_admin(update.effective_user.id, context):
        await update.message.reply_text("权限不足。")
        return

    text = update.message.text or ""
    no_post = "--no-post" in text
    user_name = update.effective_user.username or str(update.effective_user.id)

    # 判断参数是 URL 还是作品 ID
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
    """从 URL 导入作品，可选发布到频道。"""
    assert update.message is not None

    tags = _TAG_RE.findall(text)
    status_msg = await update.message.reply_text(f"正在导入 {url} ...")

    client = _get_client(context)
    try:
        artwork = await client.import_artwork(url, tags=tags or None)
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text[:200] if e.response else str(e)
        await status_msg.edit_text(f"导入失败：{error_detail}")
        return


    if no_post:
        # 在聊天中展示导入的作品
        await send_artwork(update, artwork, client)
        await status_msg.edit_text(f"已导入作品 #{artwork.id}（{artwork.platform}）。")
        return

    # 解析目标频道并发布
    channel_id = await _resolve_target_channel(context, artwork)
    if not channel_id:
        await status_msg.edit_text(f"已导入 #{artwork.id}，但未配置频道。")
        return

    result = await post_to_channel(context, artwork, channel_id)
    if result:
        await _log_post(context, artwork, result, posted_by=user_name)
        await status_msg.edit_text(
            f"已导入 #{artwork.id} 并发布。",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("跳转频道", url=result.message_link)]]
            ),
        )
    else:
        await status_msg.edit_text(f"已导入 #{artwork.id}，但频道发布失败。")


async def _handle_post_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    no_post: bool,
    user_name: str,
) -> None:
    """通过 ID 发布已有作品。"""
    assert update.message is not None

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "用法：\n"
            "/post <url> [#tag1 #tag2] — 导入并发布\n"
            "/post <id> — 发布已有作品"
        )
        return

    try:
        artwork_id = int(args[0])
    except ValueError:
        await update.message.reply_text("无效的作品 ID，请使用 URL 或数字 ID。")
        return

    client = _get_client(context)
    artwork = await client.get_artwork(artwork_id)
    if artwork is None:
        await update.message.reply_text(f"未找到作品 #{artwork_id}。")
        return

    if no_post:
        # 仅预览
        await send_artwork(update, artwork, client)
        return

    channel_id = await _resolve_target_channel(context, artwork)
    if not channel_id:
        await update.message.reply_text("未配置频道。")
        return

    result = await post_to_channel(context, artwork, channel_id)
    if result:
        await _log_post(context, artwork, result, posted_by=user_name)
        await update.message.reply_text(
            f"已发布 #{artwork.id}。",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("跳转频道", url=result.message_link)]]
            ),
        )
    else:
        await update.message.reply_text("发布失败（无图片或频道错误）。")


async def import_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /import <url> [#tag1 #tag2] — 抓取 URL 并保存作品（不发布到频道）。

    这是 `/post <url> --no-post` 的别名。
    """
    if not update.message or not update.effective_user:
        return

    if not await _is_admin(update.effective_user.id, context):
        await update.message.reply_text("权限不足。")
        return

    text = update.message.text or ""
    url_match = _URL_RE.search(text)
    if not url_match:
        await update.message.reply_text("用法：/import <url> [#tag1 #tag2]")
        return

    tags = _TAG_RE.findall(text)
    status_msg = await update.message.reply_text(f"正在导入 {url_match.group(0)} ...")

    client = _get_client(context)
    try:
        artwork = await client.import_artwork(url_match.group(0), tags=tags or None)
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text[:200] if e.response else str(e)
        await status_msg.edit_text(f"导入失败：{error_detail}")
        return

    await send_artwork(update, artwork, client)
    await status_msg.edit_text(f"已导入作品 #{artwork.id}（{artwork.platform}）。")
