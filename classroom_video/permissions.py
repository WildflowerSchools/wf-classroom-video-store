from fastapi import Depends
from wf_fastapi_auth0 import get_subject_domain
from wf_fastapi_auth0.wf_permissions import AuthRequest, check_requests


async def can_read(perm_info: tuple = Depends(get_subject_domain)):
    resp = await check_requests([AuthRequest(sub=perm_info[0], dom=perm_info[1], obj="classroom:videos", act="read")])
    return resp[0]["allow"]


async def can_write(perm_info: tuple = Depends(get_subject_domain)):
    resp = await check_requests([AuthRequest(sub=perm_info[0], dom=perm_info[1], obj="classroom:videos", act="write")])
    return resp[0]["allow"]
