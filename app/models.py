"""Pydantic models for request/response validation."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class VolumeConfig(BaseModel):
    """Volume binding configuration."""

    bind: str = Field(..., description="Container path to mount to")
    mode: Literal["ro", "rw"] = Field(default="rw", description="Mount mode")


class PortBinding(BaseModel):
    """Port binding configuration."""

    host_ip: str = Field(default="0.0.0.0", description="Host IP to bind to")
    host_port: int = Field(..., description="Host port to bind to")


class RestartPolicy(BaseModel):
    """Container restart policy."""

    name: Literal["no", "always", "on-failure", "unless-stopped"] = Field(
        default="no", description="Restart policy name"
    )
    maximum_retry_count: int = Field(
        default=0, description="Max retries for on-failure policy"
    )


class ContainerCreate(BaseModel):
    """Request model for creating a container."""

    image: str = Field(..., description="Docker image to use")
    name: Optional[str] = Field(None, description="Container name")
    command: Optional[Union[str, List[str]]] = Field(
        None, description="Command to run"
    )
    entrypoint: Optional[Union[str, List[str]]] = Field(
        None, description="Container entrypoint"
    )
    environment: Optional[Dict[str, str]] = Field(
        None, description="Environment variables"
    )
    ports: Optional[Dict[str, Union[int, PortBinding, List[PortBinding]]]] = Field(
        None,
        description="Port bindings: {'80/tcp': 8080} or {'80/tcp': {'host_ip': '0.0.0.0', 'host_port': 8080}}",
    )
    volumes: Optional[Dict[str, VolumeConfig]] = Field(
        None,
        description="Volume bindings: {'/host/path': {'bind': '/container/path', 'mode': 'rw'}}",
    )
    labels: Optional[Dict[str, str]] = Field(None, description="Container labels")
    restart_policy: Optional[RestartPolicy] = Field(
        None, description="Restart policy configuration"
    )
    working_dir: Optional[str] = Field(None, description="Working directory")
    user: Optional[str] = Field(None, description="User to run as")
    hostname: Optional[str] = Field(None, description="Container hostname")
    network: Optional[str] = Field(None, description="Network to connect to")
    mem_limit: Optional[str] = Field(None, description="Memory limit (e.g., '512m')")
    cpu_period: Optional[int] = Field(None, description="CPU period in microseconds")
    cpu_quota: Optional[int] = Field(None, description="CPU quota in microseconds")

    model_config = {"extra": "forbid"}


class ContainerResponse(BaseModel):
    """Response model for container information."""

    id: str = Field(..., description="Container ID")
    short_id: str = Field(..., description="Short container ID")
    name: str = Field(..., description="Container name")
    image: str = Field(..., description="Image name")
    status: str = Field(..., description="Container status")
    created: datetime = Field(..., description="Creation timestamp")
    ports: Dict[str, Any] = Field(default_factory=dict, description="Port bindings")
    labels: Dict[str, str] = Field(default_factory=dict, description="Container labels")


class ContainerListResponse(BaseModel):
    """Response model for listing containers."""

    containers: List[ContainerResponse]
    count: int


class ContainerCreateResponse(BaseModel):
    """Response model for container creation."""

    id: str
    name: str
    warnings: List[str] = Field(default_factory=list)


class ContainerLogsResponse(BaseModel):
    """Response model for container logs."""

    logs: str
    container_id: str


class ContainerStatsResponse(BaseModel):
    """Response model for container stats."""

    container_id: str
    cpu_percent: float
    memory_usage: int
    memory_limit: int
    memory_percent: float
    network_rx_bytes: int
    network_tx_bytes: int


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: Optional[str] = None


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
    container_id: Optional[str] = None
