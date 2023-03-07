from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, Request
from wf_fastapi_auth0 import verify_token

from .mongo.models import ExistingRetentionRule, RetentionRule
from .permissions import can_read, can_write
from .routes import StatusResponse

router = APIRouter(prefix="/retention_rules", tags=["retention_rules"], dependencies=[Depends(verify_token)])


@router.post("/", response_model=ExistingRetentionRule, dependencies=[Depends(can_write)])
async def create_rule(request: Request, rule: RetentionRule):
    video_retention_collection = request.app.state.mongo_client.video_retention_collection()

    result = video_retention_collection.insert_one(rule.mongo())
    new_retention_record = video_retention_collection.find_one(result.inserted_id)
    if new_retention_record is not None:
        return ExistingRetentionRule.from_mongo(new_retention_record)


@router.get("/", response_model=List[ExistingRetentionRule], dependencies=[Depends(can_read)])
async def list_rules(request: Request):
    video_retention_collection = request.app.state.mongo_client.video_retention_collection()

    results = []
    for retention_record in video_retention_collection.find({}):
        results.append(ExistingRetentionRule.from_mongo(retention_record))
    return results


@router.delete("/{rule_id}", response_model=StatusResponse, dependencies=[Depends(can_write)])
async def delete_rule(request: Request, rule_id: str):
    video_retention_collection = request.app.state.mongo_client.video_retention_collection()

    existing = video_retention_collection.find_one({"_id": ObjectId(rule_id)})
    if existing is not None:
        video_retention_collection.delete_one({"_id": ObjectId(rule_id)})
        return StatusResponse(status="200")
    return StatusResponse(status="404")
