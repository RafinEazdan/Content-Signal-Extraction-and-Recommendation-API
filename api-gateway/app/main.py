from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.core.config import ROUTE_MAP

_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client
    _client = httpx.AsyncClient(timeout=60.0)
    yield
    await _client.aclose()


app = FastAPI(title="API Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Headers that must not be forwarded to the upstream service.
_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
}


def _resolve_upstream(path: str) -> tuple[str, str] | None:
    """Return (upstream_base_url, stripped_path) for the first matching prefix."""
    for prefix, upstream in ROUTE_MAP:
        if path.startswith(prefix):
            return upstream, path[len(prefix):]
    return None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy(request: Request, path: str):
    full_path = "/" + path
    match = _resolve_upstream(full_path)

    if match is None:
        return Response(
            content=f"No upstream found for path: {full_path}",
            status_code=404,
        )

    upstream_base, stripped_path = match
    if not stripped_path:
        stripped_path = "/"

    qs = request.url.query
    upstream_url = upstream_base + stripped_path
    if qs:
        upstream_url += f"?{qs}"

    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }

    body = await request.body()

    upstream_response = await _client.request(
        method=request.method,
        url=upstream_url,
        headers=headers,
        content=body,
    )

    response_headers = {
        k: v
        for k, v in upstream_response.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }

    return StreamingResponse(
        content=iter([upstream_response.content]),
        status_code=upstream_response.status_code,
        headers=response_headers,
    )
