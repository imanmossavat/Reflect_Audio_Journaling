import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from app.db import engine
from app.routes import source, query, tags

app = FastAPI(title="Source Reflection API")

default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
extra_origins = [origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
allow_all_origins = os.getenv("CORS_ALLOW_ALL_ORIGINS", "true").lower() in {"1", "true", "yes", "on"}

if allow_all_origins:
    allowed_origins = ["*"]
    allowed_origin_regex = ".*"
else:
    allowed_origins = list(dict.fromkeys(default_origins + extra_origins))
    default_origin_regex = r"^https?://(localhost|127\.0\.0\.1|\d{1,3}(?:\.\d{1,3}){3})(:\d+)?$"
    allowed_origin_regex = os.getenv("CORS_ALLOWED_ORIGIN_REGEX", default_origin_regex)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(source.router)
app.include_router(query.router)
app.include_router(tags.router)
app.include_router(tags.search_router)