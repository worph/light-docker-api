"""Container management API routes."""

from typing import Optional

from fastapi import APIRouter, Body, Depends, Query

from app.docker_client import DockerManager, get_docker_manager
from app.models import (
    ContainerCreate,
    ContainerCreateResponse,
    ContainerListResponse,
    ContainerLogsResponse,
    ContainerResponse,
    ContainerStatsResponse,
    MessageResponse,
)
from app.security import validate_container_request

router = APIRouter(prefix="/containers", tags=["containers"])


@router.get("", response_model=ContainerListResponse)
async def list_containers(
    all: bool = Query(True, description="Include stopped containers"),
    docker: DockerManager = Depends(get_docker_manager),
) -> ContainerListResponse:
    """
    List all containers managed by this API.

    Only containers created through this API (with managed labels) will be returned.
    """
    containers = docker.list_managed(all_containers=all)
    return ContainerListResponse(containers=containers, count=len(containers))


@router.post("/create", response_model=ContainerCreateResponse)
async def create_container(
    request: ContainerCreate = Body(...),
    docker: DockerManager = Depends(get_docker_manager),
) -> ContainerCreateResponse:
    """
    Create a new container.

    The container will be labeled as managed by this API and will only be accessible
    through this API's endpoints.

    Security restrictions apply:
    - Privileged mode is not allowed
    - Host network mode is not allowed
    - Host PID mode is not allowed
    - Certain volume mounts are blocked
    - Device mappings are not allowed
    """
    # Validate security
    validate_container_request(request)

    # Create the container
    return docker.create_container(request)


@router.get("/{container_id}", response_model=ContainerResponse)
async def inspect_container(
    container_id: str,
    docker: DockerManager = Depends(get_docker_manager),
) -> ContainerResponse:
    """
    Get detailed information about a container.

    Only managed containers can be inspected.
    """
    return docker.inspect_container(container_id)


@router.post("/{container_id}/start", response_model=MessageResponse)
async def start_container(
    container_id: str,
    docker: DockerManager = Depends(get_docker_manager),
) -> MessageResponse:
    """
    Start a stopped container.

    Only managed containers can be started.
    """
    docker.start_container(container_id)
    return MessageResponse(message="Container started", container_id=container_id)


@router.post("/{container_id}/stop", response_model=MessageResponse)
async def stop_container(
    container_id: str,
    timeout: int = Query(10, ge=0, description="Seconds to wait before killing"),
    docker: DockerManager = Depends(get_docker_manager),
) -> MessageResponse:
    """
    Stop a running container.

    Only managed containers can be stopped.
    """
    docker.stop_container(container_id, timeout=timeout)
    return MessageResponse(message="Container stopped", container_id=container_id)


@router.post("/{container_id}/restart", response_model=MessageResponse)
async def restart_container(
    container_id: str,
    timeout: int = Query(10, ge=0, description="Seconds to wait before killing"),
    docker: DockerManager = Depends(get_docker_manager),
) -> MessageResponse:
    """
    Restart a container.

    Only managed containers can be restarted.
    """
    docker.restart_container(container_id, timeout=timeout)
    return MessageResponse(message="Container restarted", container_id=container_id)


@router.delete("/{container_id}", response_model=MessageResponse)
async def remove_container(
    container_id: str,
    force: bool = Query(False, description="Force removal of running container"),
    v: bool = Query(False, description="Remove associated volumes"),
    docker: DockerManager = Depends(get_docker_manager),
) -> MessageResponse:
    """
    Remove a container.

    Only managed containers can be removed.
    """
    docker.remove_container(container_id, force=force, v=v)
    return MessageResponse(message="Container removed", container_id=container_id)


@router.get("/{container_id}/logs", response_model=ContainerLogsResponse)
async def get_container_logs(
    container_id: str,
    stdout: bool = Query(True, description="Include stdout"),
    stderr: bool = Query(True, description="Include stderr"),
    tail: int = Query(100, ge=0, description="Number of lines from end (0 for all)"),
    since: Optional[int] = Query(None, description="Unix timestamp to start from"),
    until: Optional[int] = Query(None, description="Unix timestamp to end at"),
    docker: DockerManager = Depends(get_docker_manager),
) -> ContainerLogsResponse:
    """
    Get logs from a container.

    Only managed containers can have their logs retrieved.
    """
    tail_value = "all" if tail == 0 else tail
    return docker.get_logs(
        container_id,
        stdout=stdout,
        stderr=stderr,
        tail=tail_value,
        since=since,
        until=until,
    )


@router.get("/{container_id}/stats", response_model=ContainerStatsResponse)
async def get_container_stats(
    container_id: str,
    docker: DockerManager = Depends(get_docker_manager),
) -> ContainerStatsResponse:
    """
    Get resource usage statistics for a container.

    Returns CPU, memory, and network statistics.
    Only managed containers can have their stats retrieved.
    """
    return docker.get_stats(container_id)
