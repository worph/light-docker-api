"""Security validation for container creation requests."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.config import settings
from app.models import ContainerCreate


class SecurityValidationError(HTTPException):
    """Exception raised when security validation fails."""

    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security validation failed: {message}",
        )


def validate_image(image: str) -> None:
    """Validate that the image is allowed."""
    if not settings.allowed_images:
        return  # All images allowed if list is empty

    # Check if image matches any allowed pattern
    for allowed in settings.allowed_images:
        if image == allowed or image.startswith(f"{allowed}:"):
            return

    raise SecurityValidationError(
        f"Image '{image}' is not in the allowed images list"
    )


def validate_volume_path(host_path: str) -> None:
    """Validate that a volume mount path is safe."""
    # Normalize the path
    try:
        normalized = Path(host_path).resolve()
    except Exception:
        raise SecurityValidationError(f"Invalid volume path: {host_path}")

    # Check against blocked paths
    normalized_str = str(normalized)
    for blocked in settings.blocked_volume_paths:
        blocked_path = Path(blocked).resolve()
        # Block exact matches and subdirectories of blocked paths
        if normalized == blocked_path:
            raise SecurityValidationError(
                f"Volume mount to '{host_path}' is not allowed"
            )
        # Also block if it's trying to mount a parent of a sensitive path
        try:
            normalized.relative_to(blocked_path)
            raise SecurityValidationError(
                f"Volume mount to '{host_path}' is not allowed (overlaps with protected path)"
            )
        except ValueError:
            pass  # Not a subdirectory, which is fine

        # Block if the blocked path is a subdirectory of the mount
        try:
            blocked_path.relative_to(normalized)
            raise SecurityValidationError(
                f"Volume mount to '{host_path}' is not allowed (would expose protected paths)"
            )
        except ValueError:
            pass


def validate_volumes(volumes: Optional[Dict[str, Any]]) -> None:
    """Validate all volume mounts."""
    if not volumes:
        return

    for host_path in volumes.keys():
        validate_volume_path(host_path)


def validate_capabilities(cap_add: Optional[List[str]]) -> None:
    """Validate requested capabilities."""
    if not cap_add:
        return

    if not settings.allowed_capabilities:
        raise SecurityValidationError(
            "Adding capabilities is not allowed"
        )

    for cap in cap_add:
        if cap.upper() not in settings.allowed_capabilities:
            raise SecurityValidationError(
                f"Capability '{cap}' is not allowed"
            )


def check_dangerous_options(raw_data: Dict[str, Any]) -> None:
    """Check for dangerous options that should never be allowed."""
    dangerous_options = {
        "privileged": "Privileged mode is not allowed",
        "network_mode": None,  # Special handling
        "pid_mode": "PID mode 'host' is not allowed",
        "ipc_mode": "IPC mode 'host' is not allowed",
        "cap_add": None,  # Handled separately
        "devices": "Device mappings are not allowed",
        "security_opt": "Security options are not allowed",
        "sysctls": "Sysctl settings are not allowed",
    }

    for option, message in dangerous_options.items():
        if option not in raw_data:
            continue

        value = raw_data[option]

        if option == "privileged" and value is True:
            raise SecurityValidationError(message)

        if option == "network_mode" and value == "host":
            raise SecurityValidationError("Network mode 'host' is not allowed")

        if option == "pid_mode" and value == "host":
            raise SecurityValidationError(message)

        if option == "ipc_mode" and value == "host":
            raise SecurityValidationError(message)

        if option == "devices" and value:
            raise SecurityValidationError(message)

        if option == "security_opt" and value:
            raise SecurityValidationError(message)

        if option == "sysctls" and value:
            raise SecurityValidationError(message)

        if option == "cap_add" and value:
            validate_capabilities(value)


def validate_container_request(
    request: ContainerCreate, raw_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Validate a container creation request for security issues.

    Args:
        request: The parsed ContainerCreate model
        raw_data: The raw request data (to check for extra fields)

    Raises:
        SecurityValidationError: If validation fails
    """
    # Validate image
    validate_image(request.image)

    # Validate volumes
    validate_volumes(
        {k: v.model_dump() for k, v in request.volumes.items()}
        if request.volumes
        else None
    )

    # Check for dangerous options in raw data
    if raw_data:
        check_dangerous_options(raw_data)
