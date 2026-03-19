from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Database
    database_url: str = "sqlite+aiosqlite:///./hyacine_gallery.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Storage
    storage_backend: str = "local"  # "local" or "s3"
    storage_local_path: str = "./uploads"

    # S3
    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = ""
    s3_region: str = ""
    s3_public_url: str = ""  # Public CDN/URL prefix for S3 objects

    # Image processing
    thumb_max_edge: int = 1536
    webp_quality: int = 80

    # Backend public URL (used to build absolute image URLs for frontend)
    backend_url: str = "http://localhost:8000"

    # Admin
    admin_panel_slug: str = "change-me-to-random-string"
    admin_token: str = "change-me-to-a-secure-token"

    # CORS
    backend_cors_origins: list[str] = ["http://localhost:3000"]

    # Debug
    debug: bool = True


settings = Settings()
