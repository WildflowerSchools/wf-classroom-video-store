import json

from behave import *
import requests
from wf_fastapi_auth0 import admin_token, verify_token

from classroom_video import models


@given('a `{method}` method to `{url}`')
def step_impl(context, method, url):
    token = admin_token("wildflower-tech.org")
    context.request = {
        "method": method,
        "url": url,
        "headers": {
            "Authorization": f"bearer {token}",
        }
    }


@given('a set of videos')
def step_impl(context):
    request = context.request
    videos = []
    files = []
    for i, row in enumerate(context.table):
        files.append(("files", open(row['video_path'], 'rb'), ))
        videos.append(dict(
            timestamp=row["timestamp"],
            meta=dict(
                environment_id=row["environment_id"],
                camera_id=row["camera_id"],
                assignment_id=row["assignment_id"],
                duration_seconds=row["duration_seconds"],
                fps=row["fps"],
                path=row["path"],
            ),
        ))
    request["files"] = files
    request["data"] = {"videos": json.dumps(videos)}

@when('calling the request')
def call_request(context):
    try:
        request = requests.Request(**context.request)
        r = request.prepare()
        s = requests.Session()
        context.response = s.send(r)
    except Exception as err:
        print(err)
        assert False

@then('API returns videos with ids')
def step_impl(context):
    print(context.response.text)
    assert context.response.status_code == 200
    assert context.response.json()[0]["id"] is not None
