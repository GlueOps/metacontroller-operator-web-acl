from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
import json
from utils.aws_web_acl import *
import threading
import signal
import socket
import os
import glueops.logging

logger = glueops.logging.configure()


class Controller(BaseHTTPRequestHandler):

    semaphore = threading.Semaphore(100)

    def sync(self, parent, children):
        uid, aws_resource_tags, web_acl_definition, status_dict, web_acl_arn = self._get_parent_data(parent)
        if "error_message" in status_dict:
            status_dict = {}
        try:
            if self.path.endswith('/sync'):
                if web_acl_arn is None:
                    logger.info("Yolooooooo")
                    acl_config = generate_web_acl_configuration(web_acl_definition, aws_resource_tags)
                    status_dict["web_acl_request"] = create_web_acl(acl_config)
                else:
                    lock_token = get_lock_token(web_acl_arn)
                    acl_config = generate_web_acl_configuration(web_acl_definition, aws_resource_tags, lock_token=lock_token)
                    update_web_acl(acl_config)
                    status_dict["web_acl_request"] = get_current_state_of_web_acl_arn(web_acl_arn)

            if self.path.endswith('/finalize'):
                return self.finalize_hook(aws_resource_tags)
            
            return {"status": status_dict}
        except Exception as e:
            status_dict = {}
            status_dict["error_message"] = str(e)
            return {"status": status_dict}

    def finalize_hook(self, aws_resource_tags):
        try:
            arns = get_resource_arns_using_tags(aws_resource_tags,["wafv2"])
            if len(arns) > 1:
                raise Exception("There are data integrity issues. We seem to have multiple WebACL's with the same tags. Manual cleanup is required.")
            elif len(arns) == 1:
                delete_web_acl(arns[0])
                return {"finalized": True}
            return {"finalized": True}
        except Exception as e:
            logger.error(f"Unexpected exception occurred: {e}. We will try again shortly.")
    
    def _get_parent_data(self, parent):
        uid = parent.get("metadata").get("uid")
        captain_domain = os.environ.get('CAPTAIN_DOMAIN')
        aws_resource_tags = [
            {"Key": "kubernetes_resource_uid", "Value": uid},
            {"Key": "captain_domain",
             "Value": captain_domain}
        ]
        web_acl_definition = parent.get("spec", {}).get("web_acl_definition")
        if web_acl_definition is not None:
            web_acl_definition = json.loads(web_acl_definition)
            web_acl_definition["Name"] = parent.get("metadata").get("name")
        status_dict = parent.get("status", {})
        web_acl_arn = status_dict.get("web_acl_request", {}).get("arn", None)
        
        # in case something gets deleted outside of kubernetes setting these to None will let them be recreated by the controller
        if not does_web_acl_exist(web_acl_arn):
            web_acl_arn = None
            
        return uid, aws_resource_tags, web_acl_definition, status_dict, web_acl_arn

    def do_POST(self):
        try:
            acquired = Controller.semaphore.acquire(blocking=False)
            if not acquired:
                self.send_response(429)  # 429 Too Many Requests
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"error": "Too many requests, please try again later."}).encode())
                return

            # Serve the sync() function as a JSON webhook.
            observed = json.loads(self.rfile.read(
                int(self.headers.get("content-length"))))
            desired = self.sync(observed["parent"], observed["children"])

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(desired).encode())
        except Exception as e:
            # Handle generic exceptions (like writing issues) here
            # Logging the exception could be beneficial
            print(f"Error occurred: {e}")
        finally:
            if acquired:
                Controller.semaphore.release()


# HTTPServer(("", 8080), Controller).serve_forever()


def run(server_class=HTTPServer, handler_class=Controller, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)

    # Set a timeout on the socket to periodically check the shutdown flag
    httpd.timeout = 1  # 1 second

    # Signal handler for graceful shutdown
    should_shutdown = False

    def sig_handler(_signo, _stack_frame):
        nonlocal should_shutdown  # Use nonlocal since we're in a nested function
        should_shutdown = True
        logger.info("Received signal. Shutting down soon.")

    # Register signals
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    logger.info(f'Starting server on port {port}')
    while not should_shutdown:
        try:
            httpd.handle_request()
        except socket.timeout:
            continue

    logger.info("Server has shut down.")
    
    


run()
