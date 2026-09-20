from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Core Deployment
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    PROJECT_NAME: str = "Noted Ma'am"
    VERSION: str = "1.0.0"

    # PostgreSQL Relational DB
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres_secure_pass"
    POSTGRES_DB: str = "noted_maam_dev"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres_secure_pass@db:5432/noted_maam_dev"
    )

    # Redis Cache & Sessions
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://redis:6379/0"

    # Redis Streams Local MQ
    REDIS_STREAM_URL: str = "redis://redis:6379/1"

    # Object Storage (MinIO / S3)
    MINIO_ROOT_USER: str = "minio_admin"
    MINIO_ROOT_PASSWORD: str = "minio_admin_secure_pass"
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_EXTERNAL_ENDPOINT: str = "http://localhost:9000"
    MINIO_BUCKET_NAME: str = "noted-maam-audio-chunks"

    # Cryptography & Security
    JWT_SECRET_KEY: str = (
        "9d8df283bc9dfc01bc89a7df2b89d8efd2389d83c27189defd893fcebdf89e1b"  # noqa: E501
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # External Identity Providers (OAuth)
    GOOGLE_CLIENT_ID: str = "mock-google-client-id"
    GOOGLE_CLIENT_SECRET: str = "mock-google-client-secret"
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/oauth/google/callback"


# Instantiate singleton configurations
settings = Settings()
