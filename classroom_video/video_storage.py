import concurrent.futures
import datetime
import json
import os
from typing import List, Union, Optional

import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pymongo
from wf_fastapi_auth0 import verify_token, get_subject_domain
from wf_fastapi_auth0.wf_permissions import AuthRequest, check_requests
# from pymongo import InsertOne

from .config import logger


from classroom_video.models import (
        # OID,
        Video,
        ExistingVideo,
        videos as video_db,
)

WF_DATA_PATH = os.environ.get("WF_DATA_PATH", "./")


async def can_read(perm_info: tuple = Depends(get_subject_domain)):
    resp = await check_requests([AuthRequest(sub=perm_info[0], dom=perm_info[1], obj="classroom:videos", act='read')])
    return resp[0]["allow"]


async def can_write(perm_info: tuple = Depends(get_subject_domain)):
    resp = await check_requests([AuthRequest(sub=perm_info[0], dom=perm_info[1], obj="classroom:videos", act='write')])
    return resp[0]["allow"]


def video_check(path):
    existing = video_db.find_one({"meta.path": path}, {"_id": 1})
    if existing is not None:
        return VideoStatus(id=str(existing["_id"]), path=path, exists=True).json()
    return VideoStatus(path=path, exists=False).json()


class StatusResponse(BaseModel):
    status: str = "OK"


class VideoStatus(BaseModel):
    id: Optional[str]
    path: str
    exists: bool

class VideoExistsError(BaseModel):
    path: str
    id: str
    disposition: str = "video-exists"

router = APIRouter()

########################################################################
# Routes
########################################################################
@router.get("/videos/{environment_id}", response_model=List[ExistingVideo], dependencies=[Depends(verify_token), Depends(can_read)])
async def list_videos(environment_id: str, start_date: datetime.datetime, end_date: datetime.datetime, skip: int=0, limit: int=100):
    results = []
    for video in video_db.find({"meta.environment_id": environment_id, "timestamp": {"$gte": start_date, "$lt": end_date}})[skip:(skip+limit)]:
        results.append(ExistingVideo.from_mongo(video))
    return results


@router.get("/videos/{environment_id}/device/{camera_id}", response_model=List[ExistingVideo], dependencies=[Depends(verify_token), Depends(can_read)])
async def list_videos_for_camera(environment_id: str, camera_id: str, start_date: datetime.datetime, end_date: datetime.datetime, skip: int=0, limit: int=100):
    results = []
    for video in video_db.find({"meta.environment_id": environment_id, "meta.camera_id": camera_id, "timestamp": {"$gte": start_date, "$lt": end_date}})[skip:(skip+limit)]:
        results.append(ExistingVideo.from_mongo(video))
    return results


@router.get("/video/{environment_id}/{camera_id}/{year}/{month}/{day}/{hour}/{file}.mp4", dependencies=[Depends(verify_token), Depends(can_read)])
async def load_video_data(environment_id: str, camera_id: str, year: str, month: str, day: str, hour: str, file: str):
    logger.info(f"{environment_id}/{camera_id}/{year}/{month}/{day}/{hour}/{file}.mp4")
    existing = video_db.find_one({"meta.path": f"{environment_id}/{camera_id}/{year}/{month}/{day}/{hour}/{file}.mp4"}, {"_id": 1, "meta": {"path": 1}})
    if existing is not None:
        realpath = f"{WF_DATA_PATH}/{environment_id}/{camera_id}/{year}/{month}/{day}/{hour}/{file}.mp4"
        logger.debug(realpath)
        return FileResponse(realpath)
    raise HTTPException(status_code=404, detail="video not found")


@router.get("/video/{environment_id}/{camera_id}/{year}/{month}/{day}/{hour}/{file}", response_model=ExistingVideo, dependencies=[Depends(verify_token), Depends(can_read)])
async def load_video_metadata(environment_id: str, camera_id: str, year: str, month: str, day: str, hour: str, file: str):
    existing = video_db.find_one({"meta.path": f"{environment_id}/{camera_id}/{year}/{month}/{day}/{hour}/{file}.mp4"})
    if existing is not None:
        return ExistingVideo.from_mongo(existing)
    raise HTTPException(status_code=404, detail="video not found")


@router.post("/videos", response_model=List[Union[ExistingVideo, VideoExistsError]], dependencies=[Depends(verify_token), Depends(can_write)])
async def create_videos(videos:str = Form(...), files:List[UploadFile] = File(...)):
    d_videos = json.loads(videos)
    if len(d_videos) != len(files):
        raise HTTPException(status_code=400, detail="number of videos does not match number of files" )
    batch = []
    results = []
    for vid in d_videos:
        batch.append(Video(**vid).mongo())
    try:
        result = video_db.insert_many(batch, ordered=False)
        iids = result.inserted_ids
    except pymongo.errors.BulkWriteError as err:
        # handle duplicate paths, cannot overwrite a video
        iids = [item["_id"] for item in batch]
        for write_err in err.details["writeErrors"]:
            existing = video_db.find({"meta.path": write_err["keyValue"]["meta.path"]}, {"_id": 1})
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

@router.get("/videos/check", response_model=List[VideoStatus], dependencies=[Depends(verify_token), Depends(can_write)])
async def video_existence_check(videos:List[str]):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = executor.map(video_check, videos)
        for future in futures:
            results.append(VideoStatus.parse_raw(future))
    return results


class ServiceStatusResponse(BaseModel):
    estimated_document_count: int


@router.post("/status", response_model=ServiceStatusResponse, dependencies=[Depends(verify_token), Depends(can_write)])
async def service_status():
    return ServiceStatusResponse(
        estimated_document_count=video_db.estimated_document_count(),
    )
