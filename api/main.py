from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api.routes import auth
from api.routes import care
from config.settings import get_settings

settings = get_settings()

if not settings.auth_cookie_secret.strip():
    raise RuntimeError("Set AUTH_COOKIE_SECRET before starting the API.")

app = FastAPI(
    title="CareCompanion API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

ALLOWED_ORIGINS = {
    settings.app_url.rstrip("/"),
    "http://localhost:5173",
    "http://localhost:8000",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def reject_foreign_origins(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") not in ALLOWED_ORIGINS:
            return JSONResponse(
                {"error": {"code": "bad_origin", "message": "Request origin not allowed."}},
                status_code=403,
            )
    return await call_next(request)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(exc.detail, status_code=exc.status_code)
    return JSONResponse(
        {"error": {"code": "http_error", "message": str(exc.detail)}},
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, __: RequestValidationError):
    return JSONResponse(
        {"error": {"code": "invalid_request", "message": "Please check the details you entered."}},
        status_code=422,
    )


app.include_router(auth.router)
app.include_router(care.router)

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST.exists():

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (DIST / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(DIST.resolve()):
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
