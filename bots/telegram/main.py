"""Telegram bot 工作进程 — 通过 HTTP API 与后端通信的独立进程。"""

import logging

from telegram import BotCommand
from telegram.ext import Application, ApplicationBuilder

from client import GalleryClient
from config import bot_settings
from handlers import register_handlers
from handlers.queue import process_post_queue

logging.basicConfig(
    level=logging.DEBUG if bot_settings.debug else logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


BOT_COMMANDS = [
    BotCommand("start", "启动 bot"),
    BotCommand("help", "显示帮助信息"),
    BotCommand("random", "获取随机图片"),
    BotCommand("ping", "检查 bot 是否在线"),
    BotCommand("import", "（管理员）从 URL 导入作品"),
    BotCommand("post", "（管理员）发送作品到频道"),
    BotCommand("settings", "（管理员）Bot 设置面板"),
]


async def set_commands(app: Application) -> None:  # type: ignore[type-arg]
    """bot 初始化后注册命令列表到 Telegram，使 / 菜单生效。"""
    await app.bot.set_my_commands(BOT_COMMANDS)
    logger.info("已注册 %d 条 bot 命令到 Telegram", len(BOT_COMMANDS))


async def refresh_bot_settings(context) -> None:  # type: ignore[no-untyped-def]
    """定时任务：从后端获取 bot 设置并缓存到 bot_data。"""
    client: GalleryClient = context.bot_data["gallery_client"]
    try:
        settings = await client.get_bot_settings()
        context.bot_data["bot_settings"] = settings
        logger.debug("已刷新 bot 设置：%s", settings)
    except Exception:
        logger.warning("从后端刷新 bot 设置失败", exc_info=True)


def main() -> None:
    if not bot_settings.telegram_bot_token:
        logger.error("未设置 TELEGRAM_BOT_TOKEN")
        return

    gallery_client = GalleryClient(
        base_url=bot_settings.backend_url,
        admin_token=bot_settings.admin_token,
    )

    app: Application = (
        ApplicationBuilder()
        .read_timeout(15)
        .connect_timeout(15)
        .write_timeout(15)
        .token(bot_settings.telegram_bot_token)
        .post_init(set_commands)
        .build()
    )
    app.bot_data["gallery_client"] = gallery_client  # type: ignore[index]
    app.bot_data["bot_settings"] = {}  # type: ignore[index]
    app.bot_data["last_post_time"] = 0.0  # type: ignore[index]
    app.bot_data["last_queue_post_time"] = 0.0  # type: ignore[index]

    register_handlers(app)

    # 每 60 秒从后端刷新 bot 设置
    app.job_queue.run_repeating(refresh_bot_settings, interval=60, first=5)  # type: ignore[union-attr]
    # 每 60 秒检查发布队列（实际发布间隔由 queue_interval_minutes 设置控制）
    app.job_queue.run_repeating(process_post_queue, interval=60, first=35)  # type: ignore[union-attr]

    logger.info("Telegram bot 工作进程已启动")
    app.run_polling()


if __name__ == "__main__":
    main()
