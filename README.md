# Light Docker API

A Python/FastAPI REST API that provides a simplified, secure interface to Docker container operations. It runs as a Docker container itself and only manages containers it creates (tracked via labels).

## Features

- **Container Management**: Create, start, stop, restart, and remove containers
- **Container Isolation**: Only manages containers it creates (via labels)
- **Security Filters**: Blocks dangerous Docker options (privileged mode, host networking, etc.)
- **Resource Monitoring**: Get container logs and stats
- **Docker-like API**: Familiar endpoint structure for Docker users

## Quick Start

### Using Docker Compose

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`.

### Manual Docker Build

```bash
docker build -t light-docker-api .
docker run -p 8000:8000 -v /var/run/docker.sock:/var/run/docker.sock:ro light-docker-api
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/containers` | List managed containers |
| POST | `/containers/create` | Create a new container |
| GET | `/containers/{id}` | Inspect a container |
| POST | `/containers/{id}/start` | Start a container |
| POST | `/containers/{id}/stop` | Stop a container |
| POST | `/containers/{id}/restart` | Restart a container |
| DELETE | `/containers/{id}` | Remove a container |
| GET | `/containers/{id}/logs` | Get container logs |
| GET | `/containers/{id}/stats` | Get container stats |

## Usage Examples

### Create a container

```bash
curl -X POST http://localhost:8000/containers/create \
  -H "Content-Type: application/json" \
  -d '{"image": "nginx", "name": "my-nginx"}'
```

### List containers

```bash
curl http://localhost:8000/containers
```

### Start a container

```bash
curl -X POST http://localhost:8000/containers/{id}/start
```

### Get container logs

```bash
curl http://localhost:8000/containers/{id}/logs
```

### Remove a container

```bash
curl -X DELETE http://localhost:8000/containers/{id}
```

## Security Restrictions

The following options are blocked for security:

- `privileged: true` - Rejected
- `network_mode: host` - Rejected
- `pid_mode: host` - Rejected
- `ipc_mode: host` - Rejected
- `devices` - Rejected
- `cap_add` - Only allowed capabilities (none by default)
- Volume mounts to sensitive paths (`/`, `/etc`, `/var/run/docker.sock`, etc.)

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `INSTANCE_ID` | Unique instance identifier | Random UUID |
| `LIGHT_DOCKER_API_CORS_ORIGINS` | CORS allowed origins | `["*"]` |
| `LIGHT_DOCKER_API_ALLOWED_IMAGES` | Allowed image list (empty = all) | `[]` |

## API Documentation

When running, interactive API documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Container Tracking

Every container created through this API is labeled with:

- `light-docker-api.managed=true`
- `light-docker-api.instance={instance_id}`

Only containers with these labels are visible and manageable through the API.

## Development

### Local Development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Note: Local development requires access to the Docker socket.
