from fastapi import FastAPI, HTTPException, Request
import json
import os
import glueops.logging
from utils.aws_web_acl import *
import traceback
import glueops.checksum_tools

logger = glueops.logging.configure()
app = FastAPI()


@app.post("/sync")
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
            {"Key": "kubernetes_resource_name", "Value": parent["metadata"]["name"]},
            {"Key": "captain_domain", "Value": os.environ.get('CAPTAIN_DOMAIN')}
        ]
        return finalize_hook(aws_resource_tags)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {e}")

def sync(parent, children):
    try:
        name, aws_resource_tags, web_acl_definition, status_dict, web_acl_arn, checksum_updated, web_acl_definition_hash = get_parent_data(parent)

        if web_acl_arn is None:
            acl_config = generate_web_acl_configuration(web_acl_definition, aws_resource_tags)
            status_dict["web_acl_request"] = create_web_acl(acl_config)
        elif checksum_updated:
            logger.info("Updating existing web_acl_arn")
            acl_config = generate_web_acl_configuration(web_acl_definition, aws_resource_tags)
            status_dict["web_acl_request"] = get_existing_web_acl(acl_config)
            acl_config = generate_web_acl_configuration(web_acl_definition, aws_resource_tags, lock_token=status_dict["web_acl_request"]["LockToken"])
            update_web_acl(acl_config, web_acl_arn)
            status_dict["web_acl_request"] = get_current_state_of_web_acl_arn(web_acl_arn)
        elif not checksum_updated:
            logger.info(f"No Updates to be made for {web_acl_arn}")

        if "error_message" in status_dict:
            logger.info("Deleting old error_message")
            del status_dict["error_message"]
        
        status_dict["CRC32_HASH"] = web_acl_definition_hash
        status_dict["HEALTHY"] = "True"
        return {"status": status_dict}
    except Exception as e:
        status_dict["error_message"] = traceback.format_exc()
        status_dict["HEALTHY"] = "False"   
        logger.error(status_dict["error_message"])
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
    name = parent["metadata"].get("name")
    captain_domain = os.environ.get('CAPTAIN_DOMAIN')
    aws_resource_tags = [
        {"Key": "kubernetes_resource_name", "Value": name},
        {"Key": "captain_domain", "Value": captain_domain}
    ]
    web_acl_definition = parent.get("spec", {}).get("web_acl_definition")
    if web_acl_definition:
        web_acl_definition = json.loads(web_acl_definition)
        web_acl_definition["Name"] = parent["metadata"].get("name")
        web_acl_definition_hash = glueops.checksum_tools.string_to_crc32(json.dumps(web_acl_definition))
        
    status_dict = parent.get("status", {})
    status_dict["HEALTHY"] = "False"
    web_acl_arn = status_dict.get("web_acl_request", {}).get("ARN", None)
    checksum_updated = False
    if status_dict.get("CRC32_HASH"):
        if status_dict["CRC32_HASH"] != web_acl_definition_hash:
            checksum_updated = True
    if not does_web_acl_exist(web_acl_arn):
        web_acl_arn = None
    return name, aws_resource_tags, web_acl_definition, status_dict, web_acl_arn, checksum_updated, web_acl_definition_hash
