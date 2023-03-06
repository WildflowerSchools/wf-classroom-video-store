from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import routes_video_retention, routes_video_storage
from .config import logger
from .mongo.client import mongo_session

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


@app.on_event("startup")
async def startup():
    logger.info("Starting API...")
    app.state.mongo_db = mongo_session.connect()

app.include_router(routes_video_storage.router)
app.include_router(routes_video_retention.router)


@app.get("/")
async def root():
    return {"message": "happy"}
