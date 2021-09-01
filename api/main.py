from mangum import Mangum
from api_gateway import api
from logger import log
from database.migrate import migrate_head
from aws_lambda_powertools import Metrics
import os

app = api.app
metrics = Metrics(namespace="ListManager", service="api")


def print_env_variables():
    rapi = os.getenv("AWS_LAMBDA_RUNTIME_API", "NOT_FOUND")
    log.info(f"AWS_LAMBDA_RUNTIME_API: {rapi}")


@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event, context):
    print_env_variables()
    log.debug(event)
    if "httpMethod" in event:
        # Assume it is an API Gateway event
        asgi_handler = Mangum(app)
        response = asgi_handler(event, context)
        return response

    elif event.get("task", "") == "migrate":
        try:
            migrate_head()
            return "Success"
        except Exception as err:
            log.error(err)
            return "Error"

    elif event.get("task", "") == "heartbeat":
        return "Success"

    else:
        log.warning("Handler received unrecognised event")

    return False
