import datetime
from enum import Enum
import os
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel, BaseConfig, NonNegativeFloat
import pymongo
from bson import ObjectId
from bson.errors import InvalidId
from bson.binary import UuidRepresentation
from bson.codec_options import CodecOptions
import pytz


codec_options = CodecOptions(tz_aware=True, uuid_representation=UuidRepresentation.STANDARD)

client = pymongo.MongoClient(
    os.environ.get("WF_MONGODB_HOST")
)

db = client["video_storage"]
try:
    db.create_collection("video_meta")
except pymongo.errors.PyMongoError:
    pass


videos = db.video_meta.with_options(codec_options=CodecOptions(
    tz_aware=True,
    tzinfo=pytz.timezone('UTC')))

videos.create_index([('meta.path', pymongo.ASCENDING)], unique=True)
videos.create_index([('timestamp', pymongo.ASCENDING), ("meta.environment_id", pymongo.ASCENDING), ("meta.camera_id", pymongo.ASCENDING)])


class OID(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        try:
            return UUID(str(v))
        except ValueError:
            try:
                return ObjectId(str(v))
            except InvalidId as err:
                print(f"invalid id {v} {type(v)}")
                raise ValueError("Not a valid UUID") from err


class MongoModel(BaseModel):

    class Config(BaseConfig):
        allow_population_by_field_name = True
        use_enum_values = True
        json_encoders = {
            datetime.datetime: lambda dt: dt.isoformat(),
            datetime.date: lambda dt: dt.isoformat(),
            ObjectId: lambda oid: str(oid),
            UUID: lambda uu: str(uu),
            Enum: lambda e: e.value,
        }

    @classmethod
    def from_mongo(cls, data: dict):
        """We must convert _id into "id". """
        if not data:
            return data
        _id = data.pop('_id', None)
        return cls(**dict(data, id=_id))

    def mongo(self, **kwargs):
        exclude_unset = kwargs.pop('exclude_unset', True)
        by_alias = kwargs.pop('by_alias', True)

        parsed = self.dict(
            exclude_none=False,
            exclude_unset=exclude_unset,
            by_alias=by_alias,
            **kwargs,
        )
        # Mongo uses `_id` as default key. We should stick to that as well.
        if '_id' not in parsed and 'id' in parsed:
            parsed['_id'] = parsed.pop('id')
        return parsed


class VideoMeta(MongoModel):
    environment_id: str
    camera_id: str
    assignment_id: Optional[str]
    path: Optional[str] # path to file in filesystem, mirrored to S3
    duration_seconds: Optional[NonNegativeFloat]
    fps: Optional[float]
    frame_offsets: Optional[List[float]] # milliseconds from timestamp for each frame in the video


class Video(MongoModel):
    timestamp: datetime.datetime
    meta: VideoMeta


class ExistingVideo(Video):
    id: Optional[OID]
