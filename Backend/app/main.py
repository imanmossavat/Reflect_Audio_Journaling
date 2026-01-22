import uvicorn
from fastapi import FastAPI
from app.api.routes import router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="REFLECT – AI Audio Journaling API")
app.include_router(router, prefix="/api")

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
    print("[Engine] Starting server on http://localhost:8000")
    uvicorn.run(app, port=8000)