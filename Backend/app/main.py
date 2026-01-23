import torch
import transformers.utils.import_utils
import transformers.modeling_utils

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="REFLECT – AI Audio Journaling API")

from app.api.routes import router
from app.api.setup_routes import router as setup_router

app.include_router(router, prefix="/api")
app.include_router(setup_router, prefix="/api/setup")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(app, port=8000)