"""FastAPI application entrypoint for Appeal Agent."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import get_settings

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load optional configuration when the application starts."""

    get_settings()
    yield


app = FastAPI(
    title="Appeal Agent",
    description="Evidence-grounded appeal preparation for user review.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Report whether the API process is available."""

    return {"status": "ok"}
