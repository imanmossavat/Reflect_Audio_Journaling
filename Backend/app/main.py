from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="REFLECT – AI Audio Journaling API")
app.include_router(router, prefix="/api")
