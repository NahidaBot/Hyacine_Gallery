"""Telegram bot 工作进程 — 通过 HTTP API 与后端通信的独立进程。"""

import logging

from telegram.ext import ApplicationBuilder

from config import bot_settings
from client import GalleryClient
from handlers import register_handlers

logging.basicConfig(
    level=logging.DEBUG if bot_settings.debug else logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


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

    app = ApplicationBuilder().token(bot_settings.telegram_bot_token).build()
    app.bot_data["gallery_client"] = gallery_client  # type: ignore[index]
    app.bot_data["bot_settings"] = {}  # type: ignore[index]
    app.bot_data["last_post_time"] = 0.0  # type: ignore[index]

    register_handlers(app)

    # 每 60 秒从后端刷新 bot 设置
    app.job_queue.run_repeating(refresh_bot_settings, interval=60, first=5)  # type: ignore[union-attr]

    logger.info("Telegram bot 工作进程已启动")
    app.run_polling()


if __name__ == "__main__":
    main()
