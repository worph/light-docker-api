"""Light Docker API - FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.docker_client import get_docker_manager
from app.routes import containers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Initialize Docker client and verify connection
    docker = get_docker_manager()
    if not docker.ping():
        raise RuntimeError("Cannot connect to Docker daemon")
    print(f"Connected to Docker daemon, instance ID: {docker.instance_id}")
    yield
    # Shutdown: Cleanup if needed
    print("Shutting down Light Docker API")


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="A simplified, secure REST API for Docker container operations",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(containers.router)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "instance_id": settings.instance_id,
    }


@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint."""
    docker = get_docker_manager()
    docker_ok = docker.ping()
    return {
        "status": "healthy" if docker_ok else "unhealthy",
        "docker": "connected" if docker_ok else "disconnected",
    }
