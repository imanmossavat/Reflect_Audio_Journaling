import warnings
import datetime

import torch
import transformers.utils.import_utils
import transformers.modeling_utils

# --- Global Warning Filters (Third-Party Noise) ---
warnings.filterwarnings("ignore", message=".*weights_only=False.*")
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")
warnings.filterwarnings("ignore", message=".*declare_namespace.*")
warnings.filterwarnings("ignore", message=".*get_cmap.*")
warnings.filterwarnings("ignore", message=".*parser.split_arg_string.*")
warnings.filterwarnings("ignore", message=".*speechbrain.pretrained.*")
warnings.filterwarnings("ignore", message=".*swigvarlink has no __module__ attribute.*")
warnings.filterwarnings("ignore", message=".*Swig.* has no __module__ attribute.*")

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize Logging
from app.core.logging_config import setup_logging, logger
setup_logging()

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