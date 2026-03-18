"""Telegram bot worker — independent process that communicates with the backend via HTTP API."""

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


def main() -> None:
    if not bot_settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        return

    # Initialize backend client (stored in bot_data for handlers to access)
    gallery_client = GalleryClient(
        base_url=bot_settings.backend_url,
        admin_token=bot_settings.admin_token,
    )

    app = ApplicationBuilder().token(bot_settings.telegram_bot_token).build()
    app.bot_data["gallery_client"] = gallery_client  # type: ignore[index]

    register_handlers(app)

    logger.info("Telegram bot worker started")
    app.run_polling()


if __name__ == "__main__":
    main()
