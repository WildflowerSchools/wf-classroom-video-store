import concurrent.futures
import datetime
import functools
import json
import os
from pathlib import Path
from typing import List, Union, Optional

import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pymongo
from wf_fastapi_auth0 import verify_token

from .config import logger
from .mongo.models import (
        Video,
        ExistingVideo
)
from .permissions import can_read, can_write
from .routes import StatusResponse

WF_DATA_PATH = os.getenv("WF_DATA_PATH", "./")


def video_check(video_meta_collection, path):
    existing = video_meta_collection.find_one({"meta.path": path}, {"_id": 1})
    if existing is not None:
        return VideoStatus(id=str(existing["_id"]), path=path, exists=True).json()
    return VideoStatus(path=path, exists=False).json()


class ServiceStatusResponse(BaseModel):
    estimated_document_count: int


class VideoStatus(BaseModel):
    id: Optional[str]
    path: str
    exists: bool


class VideoExistsError(BaseModel):
    path: str
    id: str
    disposition: str = "video-exists"


router = APIRouter(
    tags=["videos"],
    dependencies=[Depends(verify_token)])

########################################################################
# Routes
########################################################################
@router.get("/videos/{environment_id}", response_model=List[ExistingVideo], dependencies=[Depends(can_read)])
async def list_videos(request: Request, environment_id: str, start_date: datetime.datetime, end_date: datetime.datetime, skip: int=0, limit: int=100):
    video_meta_collection = request.app.state.mongo_db.video_meta_collection()
    
    results = []
    for video in video_meta_collection.find({"meta.environment_id": environment_id, "timestamp": {"$gte": start_date, "$lt": end_date}})[skip:(skip+limit)]:
        results.append(ExistingVideo.from_mongo(video))
    return results


@router.get("/videos/{environment_id}/device/{camera_id}", response_model=List[ExistingVideo], dependencies=[Depends(can_read)])
async def list_videos_for_camera(request: Request, environment_id: str, camera_id: str, start_date: datetime.datetime, end_date: datetime.datetime, skip: int=0, limit: int=100):
    video_meta_collection = request.app.state.mongo_db.video_meta_collection()
    
    results = []
    for video in video_meta_collection.find({"meta.environment_id": environment_id, "meta.camera_id": camera_id, "timestamp": {"$gte": start_date, "$lt": end_date}})[skip:(skip+limit)]:
        results.append(ExistingVideo.from_mongo(video))
    return results


@router.get("/video/{environment_id}/{camera_id}/{path:path}/data", dependencies=[Depends(can_read)])
async def load_video_data(request: Request, environment_id: str, camera_id: str, path: str):
    video_meta_collection = request.app.state.mongo_db.video_meta_collection()
    
    existing = video_meta_collection.find_one(
        {"meta.path": f"{environment_id}/{camera_id}/{path}"},
        {"_id": 1, "meta": {"path": 1}}
    )
    if existing is not None:
        realpath = f"{WF_DATA_PATH}/{environment_id}/{camera_id}/{path}"
        logger.debug(realpath)
        return FileResponse(realpath)
    raise HTTPException(status_code=404, detail="video not found")


@router.get("/video/{environment_id}/{camera_id}/{path:path}", response_model=ExistingVideo, dependencies=[Depends(can_read)])
async def load_video_metadata(request: Request, environment_id: str, camera_id: str, path: str):
    video_meta_collection = request.app.state.mongo_db.video_meta_collection()
    
    existing = video_meta_collection.find_one({"meta.path": f"{environment_id}/{camera_id}/{path}"})
    if existing is not None:
        return ExistingVideo.from_mongo(existing)
    raise HTTPException(status_code=404, detail="video not found")


@router.delete("/video/{environment_id}/{camera_id}/{path:path}", response_model=StatusResponse, dependencies=[Depends(can_write)])
async def expunge_video(request: Request, environment_id: str, camera_id: str, path: str):
    video_meta_collection = request.app.state.mongo_db.video_meta_collection()
    
    existing = video_meta_collection.find_one({"meta.path": f"{environment_id}/{camera_id}/{path}"})
    if existing is not None:
        # TODO - remove from db, and remove from filesystem
        video_meta_collection.delete_one({"_id": existing["_id"]})
        file_path = Path(WF_DATA_PATH) / path
        file_path.unlink()
        return StatusResponse(status="200")
    return StatusResponse(status="404")


@router.post("/videos", response_model=List[Union[ExistingVideo, VideoExistsError]], dependencies=[Depends(can_write)])
async def create_videos(request: Request, videos: str = Form(...), files: List[UploadFile] = File(...)):
    video_meta_collection = request.app.state.mongo_db.video_meta_collection()
    
    d_videos = json.loads(videos)
    if len(d_videos) != len(files):
        raise HTTPException(status_code=400, detail="number of videos does not match number of files" )
    batch = []
    results = []
    for vid in d_videos:
        batch.append(Video(**vid).mongo())
    for vid in batch:
        pth = vid.get("meta").get("path")
        while pth.startswith("/"):
            pth = pth[1:]
        vid.get("meta")["path"] = pth
    try:
        result = video_meta_collection.insert_many(batch, ordered=False)
        iids = result.inserted_ids
    except pymongo.errors.BulkWriteError as err:
        # handle duplicate paths, cannot overwrite a video
        iids = [item["_id"] for item in batch]
        for write_err in err.details["writeErrors"]:
            existing = video_meta_collection.find({"meta.path": write_err["keyValue"]["meta.path"]}, {"_id": 1})
            iids[write_err["index"]] = VideoExistsError(path=write_err["keyValue"]["meta.path"], id=str(existing[0]["_id"]))
    for i, file in enumerate(files):
        if isinstance(iids[i], VideoExistsError):
            results.append(iids[i])
        else:
            vid = batch[i]
            file_path = os.path.join(WF_DATA_PATH, vid.get("meta").get("path"))
            if os.path.exists(file_path):
                results.append(ExistingVideo(id=iids[i], **vid))
            else:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                async with aiofiles.open(file_path, 'wb') as out_file:
                    while contents := await file.read(1024):
                        await out_file.write(contents)
                results.append(ExistingVideo(id=iids[i], **vid))
    return results


@router.post("/videos/check", response_model=List[VideoStatus], dependencies=[Depends(can_write)])
async def video_existence_check(request: Request, videos: List[str]):
    video_meta_collection = request.app.state.mongo_db.video_meta_collection()
    video_check_partial = functools.partial(video_check, video_meta_collection=video_meta_collection)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = executor.map(lambda video_path: video_check_partial(path=video_path), videos)
        for future in futures:
            results.append(VideoStatus.parse_raw(future))
    return results


@router.post("/status", response_model=ServiceStatusResponse, dependencies=[Depends(can_write)])
async def service_status(request: Request):
    video_meta_collection = request.app.state.mongo_db.video_meta_collection()
    
    return ServiceStatusResponse(
        estimated_document_count=video_meta_collection.estimated_document_count(),
    )

