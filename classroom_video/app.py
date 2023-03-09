import random
import string
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware


from . import routes_video_retention, routes_video_storage
from .log import logger
from .mongo.client import MongoClient

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


# Thanks: https://philstories.medium.com/fastapi-logging-f6237b84ea64
@app.middleware("http")
async def log_requests(request: Request, call_next):
    rid = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    logger.info(f"rid={rid} started method={request.method} path={request.url.path}")
    start_time = time.time()

    request.state.rid = rid
    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    formatted_process_time = f"{process_time:.2f}"
    logger.info(f"rid={rid} done completed_in={formatted_process_time}ms status_code={response.status_code}")

    return response


@app.on_event("startup")
async def startup():
    logger.info("Starting API...")
    app.state.mongo_client = MongoClient().connect()


app.include_router(routes_video_storage.router)
app.include_router(routes_video_retention.router)


@app.get("/")
async def root():
    return {"message": "happy"}
