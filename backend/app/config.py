from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # 数据库
    database_url: str = "sqlite+aiosqlite:///./hyacine_gallery.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

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

    # CORS
    backend_cors_origins: list[str] = ["http://localhost:3000"]

    # 调试
    debug: bool = False


settings = Settings()
