from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from .api import routes, ws
from .config import get_settings
from .services import Services

settings = get_settings()

PORT_TOKEN = "__PORT__"


def serve_html(path: Path) -> Response:
    text = path.read_text(encoding="utf-8")
    if PORT_TOKEN in text:
        text = text.replace(PORT_TOKEN, str(settings.port))
    return Response(content=text, media_type="text/html")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.services = Services()
    yield
    await app.state.services.shutdown()


app = FastAPI(title="SENTINEL", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)
app.include_router(ws.router)


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


@app.api_route("/{path:path}", methods=["GET", "HEAD"])
async def demo_sites(request: Request, path: str):
    """Reverse-proxies the local demo sites (each .localhost origin and any
    /sites/<name>/ fallback) from the static demo-sites directory."""
    settings_ = get_settings()
    host = (request.headers.get("host") or "").split(":")[0].lower()

    if path.startswith("sites/"):
        parts = path.split("/", 2)
        site = parts[1] if len(parts) > 1 else "home"
        rest = parts[2] if len(parts) > 2 else ""
    else:
        site = settings_.demo_hosts.get(host, "home")
        rest = path

    base = settings_.demo_sites_dir / site
    if not base.exists():
        return serve_html(settings_.demo_sites_dir / "home" / "index.html")

    if rest.startswith("assets/"):
        asset = settings_.demo_sites_dir / rest
        if asset.is_file():
            return FileResponse(asset)
        return FileResponse(settings_.demo_sites_dir / "assets" / rest.split("/", 1)[1])

    candidate = base / rest if rest else base / "index.html"
    if rest and candidate.is_file():
        return serve_html(candidate)
    if rest and (base / f"{rest}.html").is_file():
        return serve_html(base / f"{rest}.html")
    index = base / "index.html"
    if index.exists():
        return serve_html(index)
    return serve_html(settings_.demo_sites_dir / "home" / "index.html")