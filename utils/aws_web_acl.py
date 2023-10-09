

from glueops.aws import *
import glueops.logging

logger = glueops.logging.configure()


WEB_ACL_SCOPE="CLOUDFRONT"

def parse_web_acl_arn(web_acl_arn):
    parts = web_acl_arn.split('/')
    if len(parts) < 3:
        return None, None  # or raise an error if preferred
    web_acl_name = parts[-2]
    web_acl_id = parts[-1]
    return web_acl_arn, web_acl_name, web_acl_id


def does_web_acl_exist(web_acl_arn):
    logger.info(f"Checking to see if {web_acl_arn} exists")
    waf = create_aws_client('wafv2')
    try:
        web_acl_arn, web_acl_name, web_acl_id = parse_web_acl_arn(web_acl_arn)
        waf.get_web_acl(
            Name=web_acl_name,
            Scope=WEB_ACL_SCOPE,
            Id=web_acl_id
        )
        return True
    except Exception as e:
        logger.error(
            f"Unable to find existing {web_acl_arn}. Error: {e}")
        return False


def generate_web_acl_configuration(web_acl_definition, aws_resource_tags, lock_token=None):
    web_acl_params = {
        "Name": web_acl_definition["Name"],
        "Scope": WEB_ACL_SCOPE,
        "DefaultAction": web_acl_definition["DefaultAction"],
        "Description": web_acl_definition.get("Description", ""),
        "Rules": web_acl_definition["Rules"],
        "VisibilityConfig": web_acl_definition["VisibilityConfig"],
        "CustomResponseBodies": web_acl_definition.get("CustomResponseBodies", {}),
        "Tags": aws_resource_tags  # Including tags in the creation process
    }
    if lock_token is not None:
        web_acl_params["LockToken"] = lock_token
        del web_acl_params["Tags"] # remove tags when there is an update

    return web_acl_params
    
    
def delete_web_acl(web_acl_arn):
    state = get_current_state_of_web_acl_arn(web_acl_arn)
    waf = create_aws_client('wafv2')
    waf.delete_web_acl(Name=state["Name"], Scope=WEB_ACL_SCOPE,Id=state["Id"],LockToken=state["LockToken"])


def create_web_acl(web_acl_configuration):
    logger.info("Creating WEB ACL")
    
    existing_arn = get_existing_web_acl(web_acl_configuration)
    if existing_arn:
        return existing_arn
    
    waf = create_aws_client('wafv2')
    response = waf.create_web_acl(**web_acl_configuration)
    logger.info(f"Created new webacl {response['Summary']['Arn']}")
    return response["Summary"]

def get_existing_web_acl(web_acl_configuration):
    arns = get_resource_arns_using_tags(web_acl_configuration["Tags"], ["wafv2"])
    if len(arns) > 1:
        raise Exception("There are data integrity issues. We seem to have multiple WebACL's with the same tags. Manual cleanup is required.")
    elif len(arns) == 1:
        logger.info(f"Found existing Web ACL {arns[0]}")
        return get_current_state_of_web_acl_arn(arns[0])

def update_web_acl(web_acl_configuration, update_web_acl):
    logger.info(f"Updating webacl {web_acl_configuration}")
    web_acl_arn, web_acl_name, web_acl_id = parse_web_acl_arn(update_web_acl)
    web_acl_configuration["Id"] = web_acl_id
    waf = create_aws_client('wafv2')
    waf.update_web_acl(**web_acl_configuration)
    logger.info(f"Finished updating webacl")
    return True


def get_current_state_of_web_acl_arn(web_acl_arn):
    logger.info(f"Getting current state of {web_acl_arn}")
    web_acl_arn, web_acl_name, web_acl_id = parse_web_acl_arn(web_acl_arn)
    waf = create_aws_client('wafv2')
    response = waf.get_web_acl(
        Name=web_acl_name,
        Scope='CLOUDFRONT',
        Id=web_acl_id
    )
    return {
        'Name': response['WebACL']['Name'],
        'Id': response['WebACL']['Id'],
        # Using .get in case 'Description' is not present
        'Description': response['WebACL'].get('Description', ''),
        'LockToken': response['LockToken'],
        'ARN': response['WebACL']['ARN']
    }


def get_lock_token(web_acl_arn):
    logger.info(f"Getting LockToken for: {web_acl_arn}")
    web_acl_arn, web_acl_name, web_acl_id = parse_web_acl_arn(web_acl_arn)
    waf = create_aws_client('wafv2')
    response = waf.get_web_acl(
        Name=web_acl_name, Id=web_acl_id, Scope=WEB_ACL_SCOPE)
    lock_token = response['LockToken']
    logger.info(f"Recieved LockToken of {lock_token} for: {web_acl_arn}")
    return lock_token
