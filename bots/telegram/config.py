from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # 后端 API
    backend_url: str = "http://localhost:8000"
    admin_token: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_channel: str = ""
    telegram_comment_group: str = ""
    telegram_admin_chats: list[int] = []

    # 画廊前端
    gallery_url: str = "http://localhost"

    # 行为配置（默认值，可被后端 bot_settings 覆盖）
    notification_interval: int = 600
    message_tail_text: str = ""

    # 调试
    debug: bool = False


bot_settings = BotSettings()
