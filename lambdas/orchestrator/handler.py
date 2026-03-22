"""
Orchestrator Lambda

1. Invokes the Discovery Lambda to get all AWS-owned Python layers.
2. Invokes the Inspector Lambda once per layer to catalogue its packages.
3. Writes the compiled result to S3 as /data/layers.json.
4. Invalidates the CloudFront cache for that path so the site reflects
   the latest data immediately.
"""

import datetime
import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DATA_BUCKET = os.environ["DATA_BUCKET"]
DISCOVERY_FUNCTION_NAME = os.environ["DISCOVERY_FUNCTION_NAME"]
INSPECTOR_FUNCTION_NAME = os.environ["INSPECTOR_FUNCTION_NAME"]
CF_DISTRIBUTION_ID = os.environ["CF_DISTRIBUTION_ID"]
DATA_KEY = "data/layers.json"


def _invoke_sync(lambda_client, function_name: str, payload: dict) -> dict | list:
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    raw = response["Payload"].read()
    result = json.loads(raw)

    # Lambda returns a {"errorMessage": ...} dict when the function throws
    if isinstance(result, dict) and "errorMessage" in result:
        raise RuntimeError(
            f"{function_name} raised an error: {result['errorMessage']}"
        )
    return result


def handler(event, context):
    lambda_client = boto3.client("lambda")
    s3_client = boto3.client("s3")
    cf_client = boto3.client("cloudfront")

    # ── Step 1: Discover layers ───────────────────────────────────────────────
    logger.info("Invoking discovery Lambda")
    layers = _invoke_sync(lambda_client, DISCOVERY_FUNCTION_NAME, {})
    logger.info("Discovery returned %d layers", len(layers))

    # ── Step 2: Inspect each layer ────────────────────────────────────────────
    inspected = []
    for layer in layers:
        logger.info("Inspecting: %s", layer["name"])
        try:
            result = _invoke_sync(lambda_client, INSPECTOR_FUNCTION_NAME, layer)
            inspected.append(result)
        except Exception as exc:
            logger.error("Inspection failed for %s: %s", layer["name"], exc)
            # Include the layer with an error flag rather than dropping it
            inspected.append({**layer, "packages": [], "package_count": 0, "error": str(exc)})

    # ── Step 3: Write layers.json to S3 ───────────────────────────────────────
    payload = {
        "updated_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "layer_count": len(inspected),
        "layers": inspected,
    }

    s3_client.put_object(
        Bucket=DATA_BUCKET,
        Key=DATA_KEY,
        Body=json.dumps(payload, indent=2),
        ContentType="application/json",
        CacheControl="max-age=900",  # 15 min, matches CloudFront default TTL
    )
    logger.info("Wrote %s to s3://%s/%s", DATA_KEY, DATA_BUCKET, DATA_KEY)

    # ── Step 4: Invalidate CloudFront so the new data is served immediately ───
    cf_client.create_invalidation(
        DistributionId=CF_DISTRIBUTION_ID,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": [f"/{DATA_KEY}"]},
            "CallerReference": payload["updated_at"],
        },
    )
    logger.info("Created CloudFront invalidation for /%s", DATA_KEY)

    return {
        "status": "ok",
        "updated_at": payload["updated_at"],
        "layer_count": len(inspected),
        "layers": [
            {"name": l["name"], "package_count": l.get("package_count", 0)}
            for l in inspected
        ],
    }
