"""Configuration settings for Light Docker API."""

import os
from typing import List, Set
from uuid import uuid4

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API settings
    api_title: str = "Light Docker API"
    api_version: str = "1.0.0"
    cors_origins: List[str] = ["*"]

    # Instance identification
    instance_id: str = os.environ.get("INSTANCE_ID", uuid4().hex[:8])

    # Label configuration
    label_prefix: str = "light-docker-api"

    # Security settings
    allowed_images: List[str] = []  # Empty means all images allowed
    blocked_volume_paths: Set[str] = {
        "/",
        "/etc",
        "/var/run/docker.sock",
        "/var/run",
        "/proc",
        "/sys",
        "/dev",
        "/boot",
        "/root",
        "/home",
    }

    # Allowed capabilities (empty means none allowed)
    allowed_capabilities: Set[str] = set()

    class Config:
        env_prefix = "LIGHT_DOCKER_API_"


settings = Settings()

# Label constants
MANAGED_LABEL = f"{settings.label_prefix}.managed"
INSTANCE_LABEL = f"{settings.label_prefix}.instance"
