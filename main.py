from fastapi import FastAPI, HTTPException, Request
import json
import os
import glueops.logging
from utils.aws_web_acl import *
from glueops.fastapi import limiter, custom_rate_limit_exceeded

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

logger = glueops.logging.configure()
app = FastAPI()

@app.exception_handler(RateLimitExceeded)
async def handle_rate_limit_exception(request, exc):
    return await custom_rate_limit_exceeded(request, exc, retry_after_seconds=30)


@app.post("/sync")
@limiter.limit("1/minute")
async def post_sync(request: Request):
    try:
        data = await request.json()
        parent = data["parent"]
        children = data["children"]
        return sync(parent, children)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {e}")

@app.post("/finalize")
async def post_finalize(request: Request):
    try:
        data = await request.json()
        parent = data["parent"]
        aws_resource_tags = [
            {"Key": "kubernetes_resource_uid", "Value": parent["metadata"]["uid"]},
            {"Key": "captain_domain", "Value": os.environ.get('CAPTAIN_DOMAIN')}
        ]
        return finalize_hook(aws_resource_tags)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {e}")

def sync(parent, children):
    uid, aws_resource_tags, web_acl_definition, status_dict, web_acl_arn = get_parent_data(parent)
    if "error_message" in status_dict:
        status_dict = {}
    try:
        if web_acl_arn is None:
            acl_config = generate_web_acl_configuration(web_acl_definition, aws_resource_tags)
            status_dict["web_acl_request"] = create_web_acl(acl_config)
        else:
            lock_token = get_lock_token(web_acl_arn)
            acl_config = generate_web_acl_configuration(web_acl_definition, aws_resource_tags, lock_token=lock_token)
            update_web_acl(acl_config)
            status_dict["web_acl_request"] = get_current_state_of_web_acl_arn(web_acl_arn)

        return {"status": status_dict}
    except Exception as e:
        status_dict["error_message"] = str(e)
        return {"status": status_dict}

def finalize_hook(aws_resource_tags):
    try:
        arns = get_resource_arns_using_tags(aws_resource_tags, ["wafv2"])
        if len(arns) > 1:
            raise Exception("Multiple WebACL's with the same tags. Manual cleanup is required.")
        elif len(arns) == 1:
            delete_web_acl(arns[0])
        return {"finalized": True}
    except Exception as e:
        logger.error(f"Unexpected exception occurred: {e}")
        return {"finalized": False, "error": str(e)}

def get_parent_data(parent):
    uid = parent["metadata"].get("uid")
    captain_domain = os.environ.get('CAPTAIN_DOMAIN')
    aws_resource_tags = [
        {"Key": "kubernetes_resource_uid", "Value": uid},
        {"Key": "captain_domain", "Value": captain_domain}
    ]
    web_acl_definition = parent.get("spec", {}).get("web_acl_definition")
    if web_acl_definition:
        web_acl_definition = json.loads(web_acl_definition)
        web_acl_definition["Name"] = parent["metadata"].get("name")
    status_dict = parent.get("status", {})
    web_acl_arn = status_dict.get("web_acl_request", {}).get("arn", None)
    if not does_web_acl_exist(web_acl_arn):
        web_acl_arn = None
    return uid, aws_resource_tags, web_acl_definition, status_dict, web_acl_arn
