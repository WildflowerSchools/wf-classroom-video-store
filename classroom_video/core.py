from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from classroom_video import video_storage
from .config import logger

logger.info("starting app")
app = FastAPI()

origins = [
    "*",
    "https://video-storage.api.wildflower-tech.org",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(video_storage.router)


@app.get("/")
async def root():
    return {"message": "happy"}
