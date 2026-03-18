from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Backend API
    backend_url: str = "http://localhost:8000"
    admin_token: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_channel: str = ""
    telegram_comment_group: str = ""
    telegram_admin_chats: list[int] = []

    # Behavior (defaults, can be overridden by backend bot_settings)
    notification_interval: int = 600
    message_tail_text: str = ""

    # Debug
    debug: bool = False


bot_settings = BotSettings()
