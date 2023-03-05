import datetime
from enum import Enum
from uuid import UUID
from typing import Optional, List


from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel, BaseConfig, NonNegativeFloat


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


class RetentionRule(MongoModel):
    environment_id: str
    camera_ids: Optional[List[str]]
    start: datetime.datetime
    end: datetime.datetime
    description: Optional[str]


class ExistingRetentionRule(RetentionRule):
    id: Optional[OID]
