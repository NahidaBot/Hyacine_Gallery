from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # 数据库
    database_url: str = "sqlite+aiosqlite:///./hyacine_gallery.db"

    # 存储
    storage_backend: str = "local"  # "local" 或 "s3"
    storage_local_path: str = "./uploads"

    # S3
    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = ""
    s3_region: str = ""
    s3_public_url: str = ""  # S3 对象的公开 CDN/URL 前缀

    # 图片处理
    thumb_max_edge: int = 1536
    webp_quality: int = 80
    raw_ttl_days: int = 7  # raw 原始文件保留天数，0 表示禁用 raw 存储

    # 后端公开 URL（用于为前端构建绝对图片 URL）
    backend_url: str = "http://localhost:8000"

    # 管理
    admin_panel_slug: str = "change-me-to-random-string"
    admin_token: str = "change-me-to-a-secure-token"

    # Telegram OAuth（与 bot 进程共享同一 env var TELEGRAM_BOT_TOKEN）
    telegram_bot_token: str = ""  # 用于验证 Login Widget HMAC 签名
    telegram_bot_username: str = ""  # Login Widget 需要的 bot 用户名（不含 @）

    # JWT
    jwt_secret: str = "change-me-to-a-secure-jwt-secret"
    jwt_expire_hours: int = 720  # 30 天

    # WebAuthn（Passkeys）
    webauthn_rp_id: str = "localhost"  # 生产环境改为真实域名（不含 scheme/port）
    webauthn_rp_name: str = "Hyacine Gallery"
    webauthn_origin: str = "http://localhost"  # 前端 origin（含端口），生产改为 https://...

    # CORS
    backend_cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1",
        "http://localhost",
    ]

    # AI - LLM（标题润色）
    ai_llm_enabled: bool = False
    ai_llm_base_url: str = ""  # OpenAI 兼容 API 地址
    ai_llm_api_key: str = ""
    ai_llm_model: str = "gpt-4o-mini"

    # AI - Embedding（语义搜索）
    ai_embedding_enabled: bool = False
    ai_embedding_provider: str = "local"  # "local" 或 "api"
    ai_embedding_base_url: str = ""
    ai_embedding_api_key: str = ""
    ai_embedding_model: str = "BAAI/bge-m3"
    ai_embedding_dimension: int = 1024

    # 以图搜图
    saucenao_api_key: str = ""

    # AI 标签
    ai_auto_tag_on_import: bool = False
    ai_auto_tag_confidence: float = 0.8

    # 调试
    debug: bool = False


settings = Settings()
