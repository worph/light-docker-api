"""Docker SDK wrapper with label-based container tracking."""

from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Union

import docker
from docker.errors import APIError, ImageNotFound, NotFound
from docker.models.containers import Container
from fastapi import HTTPException, status

from app.config import INSTANCE_LABEL, MANAGED_LABEL, settings
from app.models import (
    ContainerCreate,
    ContainerCreateResponse,
    ContainerLogsResponse,
    ContainerResponse,
    ContainerStatsResponse,
)


class DockerClientError(HTTPException):
    """Exception raised for Docker client errors."""

    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=message)


class DockerManager:
    """Manager for Docker operations with label-based tracking."""

    def __init__(self):
        """Initialize the Docker client."""
        try:
            self.client = docker.from_env()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Docker: {e}")

        self.instance_id = settings.instance_id

    def _get_managed_labels(self, extra_labels: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get the labels to apply to managed containers."""
        labels = {
            MANAGED_LABEL: "true",
            INSTANCE_LABEL: self.instance_id,
        }
        if extra_labels:
            labels.update(extra_labels)
        return labels

    def _container_to_response(self, container: Container) -> ContainerResponse:
        """Convert a Docker container to a response model."""
        container.reload()  # Ensure we have the latest state
        attrs = container.attrs

        # Parse creation time
        created_str = attrs.get("Created", "")
        try:
            # Docker uses ISO format with nanoseconds
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            created = datetime.now()

        # Get port bindings
        ports = {}
        network_settings = attrs.get("NetworkSettings", {})
        port_bindings = network_settings.get("Ports", {})
        if port_bindings:
            for container_port, bindings in port_bindings.items():
                if bindings:
                    ports[container_port] = [
                        {"HostIp": b.get("HostIp", ""), "HostPort": b.get("HostPort", "")}
                        for b in bindings
                    ]

        # Get image name
        image_name = attrs.get("Config", {}).get("Image", "")
        if not image_name and container.image:
            image_name = container.image.tags[0] if container.image.tags else container.image.short_id

        return ContainerResponse(
            id=container.id,
            short_id=container.short_id,
            name=container.name,
            image=image_name,
            status=container.status,
            created=created,
            ports=ports,
            labels=attrs.get("Config", {}).get("Labels", {}),
        )

    def is_managed(self, container: Container) -> bool:
        """Check if a container is managed by this API."""
        labels = container.labels or {}
        return labels.get(MANAGED_LABEL) == "true"

    def get_managed_container(self, container_id: str) -> Container:
        """Get a container by ID, ensuring it's managed by this API."""
        try:
            container = self.client.containers.get(container_id)
        except NotFound:
            raise DockerClientError(
                f"Container '{container_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if not self.is_managed(container):
            raise DockerClientError(
                f"Container '{container_id}' is not managed by this API",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        return container

    def list_managed(self, all_containers: bool = True) -> List[ContainerResponse]:
        """List all containers managed by this API."""
        try:
            containers = self.client.containers.list(
                all=all_containers,
                filters={"label": f"{MANAGED_LABEL}=true"},
            )
        except APIError as e:
            raise DockerClientError(f"Failed to list containers: {e}")

        return [self._container_to_response(c) for c in containers]

    def create_container(self, request: ContainerCreate) -> ContainerCreateResponse:
        """Create a new container with managed labels."""
        # Prepare labels
        labels = self._get_managed_labels(request.labels)

        # Prepare port bindings
        ports = None
        if request.ports:
            ports = {}
            for container_port, host_binding in request.ports.items():
                if isinstance(host_binding, int):
                    ports[container_port] = host_binding
                elif isinstance(host_binding, dict):
                    ports[container_port] = (
                        host_binding.get("host_ip", "0.0.0.0"),
                        host_binding.get("host_port"),
                    )
                elif isinstance(host_binding, list):
                    ports[container_port] = [
                        (b.get("host_ip", "0.0.0.0"), b.get("host_port"))
                        for b in host_binding
                    ]

        # Prepare volumes
        volumes = None
        if request.volumes:
            volumes = {
                host_path: {
                    "bind": config.bind,
                    "mode": config.mode,
                }
                for host_path, config in request.volumes.items()
            }

        # Prepare restart policy
        restart_policy = None
        if request.restart_policy:
            restart_policy = {
                "Name": request.restart_policy.name,
                "MaximumRetryCount": request.restart_policy.maximum_retry_count,
            }

        # Build container options
        container_options: Dict[str, Any] = {
            "image": request.image,
            "labels": labels,
            "detach": True,
        }

        if request.name:
            container_options["name"] = request.name
        if request.command:
            container_options["command"] = request.command
        if request.entrypoint:
            container_options["entrypoint"] = request.entrypoint
        if request.environment:
            container_options["environment"] = request.environment
        if ports:
            container_options["ports"] = ports
        if volumes:
            container_options["volumes"] = volumes
        if restart_policy:
            container_options["restart_policy"] = restart_policy
        if request.working_dir:
            container_options["working_dir"] = request.working_dir
        if request.user:
            container_options["user"] = request.user
        if request.hostname:
            container_options["hostname"] = request.hostname
        if request.network:
            container_options["network"] = request.network
        if request.mem_limit:
            container_options["mem_limit"] = request.mem_limit
        if request.cpu_period:
            container_options["cpu_period"] = request.cpu_period
        if request.cpu_quota:
            container_options["cpu_quota"] = request.cpu_quota

        try:
            container = self.client.containers.create(**container_options)
        except ImageNotFound:
            raise DockerClientError(
                f"Image '{request.image}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except APIError as e:
            raise DockerClientError(f"Failed to create container: {e}")

        return ContainerCreateResponse(
            id=container.id,
            name=container.name,
            warnings=[],
        )

    def inspect_container(self, container_id: str) -> ContainerResponse:
        """Get detailed information about a container."""
        container = self.get_managed_container(container_id)
        return self._container_to_response(container)

    def start_container(self, container_id: str) -> None:
        """Start a container."""
        container = self.get_managed_container(container_id)
        try:
            container.start()
        except APIError as e:
            raise DockerClientError(f"Failed to start container: {e}")

    def stop_container(self, container_id: str, timeout: int = 10) -> None:
        """Stop a container."""
        container = self.get_managed_container(container_id)
        try:
            container.stop(timeout=timeout)
        except APIError as e:
            raise DockerClientError(f"Failed to stop container: {e}")

    def restart_container(self, container_id: str, timeout: int = 10) -> None:
        """Restart a container."""
        container = self.get_managed_container(container_id)
        try:
            container.restart(timeout=timeout)
        except APIError as e:
            raise DockerClientError(f"Failed to restart container: {e}")

    def remove_container(self, container_id: str, force: bool = False, v: bool = False) -> None:
        """Remove a container."""
        container = self.get_managed_container(container_id)
        try:
            container.remove(force=force, v=v)
        except APIError as e:
            raise DockerClientError(f"Failed to remove container: {e}")

    def get_logs(
        self,
        container_id: str,
        stdout: bool = True,
        stderr: bool = True,
        tail: Union[int, str] = "all",
        since: Optional[int] = None,
        until: Optional[int] = None,
    ) -> ContainerLogsResponse:
        """Get container logs."""
        container = self.get_managed_container(container_id)
        try:
            logs = container.logs(
                stdout=stdout,
                stderr=stderr,
                tail=tail,
                since=since,
                until=until,
            )
            if isinstance(logs, bytes):
                logs = logs.decode("utf-8", errors="replace")
        except APIError as e:
            raise DockerClientError(f"Failed to get logs: {e}")

        return ContainerLogsResponse(
            logs=logs,
            container_id=container_id,
        )

    def get_stats(self, container_id: str, stream: bool = False) -> ContainerStatsResponse:
        """Get container stats."""
        container = self.get_managed_container(container_id)
        try:
            stats = container.stats(stream=stream)
            if isinstance(stats, Generator):
                stats = next(stats)
        except APIError as e:
            raise DockerClientError(f"Failed to get stats: {e}")

        # Parse CPU stats
        cpu_delta = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0) - \
            stats.get("precpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
        system_delta = stats.get("cpu_stats", {}).get("system_cpu_usage", 0) - \
            stats.get("precpu_stats", {}).get("system_cpu_usage", 0)
        num_cpus = len(stats.get("cpu_stats", {}).get("cpu_usage", {}).get("percpu_usage", [1]))

        cpu_percent = 0.0
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0

        # Parse memory stats
        memory_stats = stats.get("memory_stats", {})
        memory_usage = memory_stats.get("usage", 0)
        memory_limit = memory_stats.get("limit", 1)
        memory_percent = (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0.0

        # Parse network stats
        networks = stats.get("networks", {})
        network_rx = sum(n.get("rx_bytes", 0) for n in networks.values())
        network_tx = sum(n.get("tx_bytes", 0) for n in networks.values())

        return ContainerStatsResponse(
            container_id=container_id,
            cpu_percent=round(cpu_percent, 2),
            memory_usage=memory_usage,
            memory_limit=memory_limit,
            memory_percent=round(memory_percent, 2),
            network_rx_bytes=network_rx,
            network_tx_bytes=network_tx,
        )

    def ping(self) -> bool:
        """Check if Docker daemon is accessible."""
        try:
            self.client.ping()
            return True
        except Exception:
            return False


# Global instance (created on first import)
docker_manager: Optional[DockerManager] = None


def get_docker_manager() -> DockerManager:
    """Get or create the Docker manager instance."""
    global docker_manager
    if docker_manager is None:
        docker_manager = DockerManager()
    return docker_manager
