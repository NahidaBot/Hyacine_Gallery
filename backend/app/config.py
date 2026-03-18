from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/hyacine_gallery"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Storage
    storage_backend: str = "local"
    storage_local_path: str = "./uploads"

    # Admin
    admin_panel_slug: str = "change-me-to-random-string"
    admin_token: str = "change-me-to-a-secure-token"

    # CORS
    backend_cors_origins: list[str] = ["http://localhost:3000"]

    # Debug
    debug: bool = False


settings = Settings()
