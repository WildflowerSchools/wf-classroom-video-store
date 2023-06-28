from fastapi import Depends
from wf_fastapi_auth0 import get_subject_domain

from .cacheable_check_requests import cached_check_requests, CacheableAuthRequest


async def can_read(perm_subject_domain: tuple = Depends(get_subject_domain)) -> bool:
    resp = await cached_check_requests(
        tuple(
            [
                CacheableAuthRequest(
                    sub=perm_subject_domain[0], dom=perm_subject_domain[1], obj="classroom:videos", act="read"
                )
            ]
        )
    )
    return resp[0]["allow"]


async def can_write(perm_subject_domain: tuple = Depends(get_subject_domain)) -> bool:
    resp = await cached_check_requests(
        tuple(
            [
                CacheableAuthRequest(
                    sub=perm_subject_domain[0], dom=perm_subject_domain[1], obj="classroom:videos", act="write"
                )
            ]
        )
    )
    return resp[0]["allow"]
