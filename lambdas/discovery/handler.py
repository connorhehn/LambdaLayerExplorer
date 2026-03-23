"""
Discovery Lambda

Public AWS-owned layers grant `lambda:GetLayerVersion` only on *recent*
versions — old versions (v1, v2, ...) often lack the public resource policy.
Starting a probe at version 1 therefore fails immediately.

Fix: each layer entry includes a seed_version (known from the AWS console
/aws-vended-layers endpoint). We start the probe at the seed, confirm it's
accessible, then probe upward to detect any newer versions released since.

To add new layers: append a tuple to KNOWN_LAYERS.
To update seed versions: bump the fourth element after AWS publishes new ones.
"""

import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = "us-east-1"

_PT3 = ["38", "39", "310", "311", "312", "313"]

# (account_id, layer_name, publisher, seed_version)
# seed_version = latest known version from the AWS console /aws-vended-layers
KNOWN_LAYERS: list[tuple[str, str, str, int]] = [
    # ── Powertools V2 ─────────────────────────────────────────────────────────
    ("017000801446", "AWSLambdaPowertoolsPythonV2",       "AWS Lambda Powertools for Python", 78),
    ("017000801446", "AWSLambdaPowertoolsPythonV2-Arm64", "AWS Lambda Powertools for Python", 78),

    # ── Powertools V3 (per-runtime, per-arch) ────────────────────────────────
    *[("017000801446", f"AWSLambdaPowertoolsPythonV3-python{v}-x86_64", "AWS Lambda Powertools for Python", 19) for v in _PT3],
    *[("017000801446", f"AWSLambdaPowertoolsPythonV3-python{v}-arm64",  "AWS Lambda Powertools for Python", 19) for v in _PT3],

    # ── AWS SDK for pandas ────────────────────────────────────────────────────
    ("336392948345", "AWSSDKPandas-Python37",         "AWS SDK for pandas (Data Wrangler)",  5),
    ("336392948345", "AWSSDKPandas-Python38",         "AWS SDK for pandas (Data Wrangler)", 27),
    ("336392948345", "AWSSDKPandas-Python38-Arm64",   "AWS SDK for pandas (Data Wrangler)", 27),
    ("336392948345", "AWSSDKPandas-Python39",         "AWS SDK for pandas (Data Wrangler)", 32),
    ("336392948345", "AWSSDKPandas-Python39-Arm64",   "AWS SDK for pandas (Data Wrangler)", 32),
    ("336392948345", "AWSSDKPandas-Python310",        "AWS SDK for pandas (Data Wrangler)", 29),
    ("336392948345", "AWSSDKPandas-Python310-Arm64",  "AWS SDK for pandas (Data Wrangler)", 29),
    ("336392948345", "AWSSDKPandas-Python311",        "AWS SDK for pandas (Data Wrangler)", 26),
    ("336392948345", "AWSSDKPandas-Python311-Arm64",  "AWS SDK for pandas (Data Wrangler)", 26),
    ("336392948345", "AWSSDKPandas-Python312",        "AWS SDK for pandas (Data Wrangler)", 22),
    ("336392948345", "AWSSDKPandas-Python312-Arm64",  "AWS SDK for pandas (Data Wrangler)", 22),
    ("336392948345", "AWSSDKPandas-Python313",        "AWS SDK for pandas (Data Wrangler)",  7),
    ("336392948345", "AWSSDKPandas-Python313-Arm64",  "AWS SDK for pandas (Data Wrangler)",  7),
    ("336392948345", "AWSSDKPandas-Python314",        "AWS SDK for pandas (Data Wrangler)",  2),
    ("336392948345", "AWSSDKPandas-Python314-Arm64",  "AWS SDK for pandas (Data Wrangler)",  2),

    # ── OpenTelemetry — Python ────────────────────────────────────────────────
    ("615299751070", "AWSOpenTelemetryDistroPython", "AWS Distro for OpenTelemetry", 24),

    # ── CodeGuru Profiler — Python ────────────────────────────────────────────
    ("157417159150", "AWSCodeGuruProfilerPythonAgentLambdaLayer", "AWS CodeGuru Profiler", 11),

    # ── Node.js ───────────────────────────────────────────────────────────────
    ("094274105915", "AWSLambdaPowertoolsTypeScriptV2",  "AWS Lambda Powertools for TypeScript", 30),
    ("615299751070", "AWSOpenTelemetryDistroJs",         "AWS Distro for OpenTelemetry",         12),

    # ── SciPy (legacy) ────────────────────────────────────────────────────────
    ("668099181075", "AWSLambda-Python27-SciPy1x", "AWS Lambda (SciPy)", 117),
    ("668099181075", "AWSLambda-Python36-SciPy1x", "AWS Lambda (SciPy)", 115),
    ("668099181075", "AWSLambda-Python37-SciPy1x", "AWS Lambda (SciPy)", 115),
    ("668099181075", "AWSLambda-Python38-SciPy1x", "AWS Lambda (SciPy)", 107),
]


def _try_get_version(lambda_client, layer_arn: str, version: int) -> dict | None:
    try:
        return lambda_client.get_layer_version(LayerName=layer_arn, VersionNumber=version)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("ResourceNotFoundException", "AccessDeniedException"):
            return None
        logger.warning("Unexpected error on %s v%d: %s", layer_arn, version, code)
        raise


def _get_latest_version(lambda_client, layer_arn: str, seed: int) -> dict | None:
    """
    Find the latest accessible version, starting from `seed`.

    1. Confirm the seed version is accessible.
    2. Probe upward with exponentially growing steps to bracket the max.
    3. Binary search between last success and first failure.
    """
    result = _try_get_version(lambda_client, layer_arn, seed)
    if result is None:
        logger.warning("Seed v%d not accessible for %s — layer skipped", seed, layer_arn)
        return None

    last_good = result
    low = seed
    delta = 1

    # Probe upward to bracket the maximum
    while True:
        probe = low + delta
        result = _try_get_version(lambda_client, layer_arn, probe)
        if result is None:
            high = probe
            break
        last_good = result
        low = probe
        delta *= 2
        if delta > 10_000:
            return last_good  # safety cap

    # Binary search between low (last found) and high (first gap)
    while low < high - 1:
        mid = (low + high) // 2
        result = _try_get_version(lambda_client, layer_arn, mid)
        if result is not None:
            last_good = result
            low = mid
        else:
            high = mid

    return last_good


def handler(_event, _context):
    lambda_client = boto3.client("lambda", region_name=REGION)
    layers = []

    for account_id, layer_name, publisher, seed_version in KNOWN_LAYERS:
        layer_arn = f"arn:aws:lambda:{REGION}:{account_id}:layer:{layer_name}"
        logger.info("Probing %s (seed v%d)", layer_name, seed_version)

        try:
            latest = _get_latest_version(lambda_client, layer_arn, seed_version)
        except ClientError as e:
            logger.error("Error probing %s: %s", layer_name, e)
            continue

        if latest is None:
            continue

        logger.info("  → v%d", latest["Version"])
        layers.append({
            "name": layer_name,
            "arn": layer_arn,
            "publisher": publisher,
            "publisher_account": account_id,
            "latest_version": latest["Version"],
            "latest_version_arn": latest["LayerVersionArn"],
            "compatible_runtimes": list(latest.get("CompatibleRuntimes", [])),
            "compatible_architectures": list(latest.get("CompatibleArchitectures", [])),
            "description": latest.get("Description", ""),
            "license": latest.get("LicenseInfo", ""),
        })

    logger.info("Discovered %d layers total", len(layers))
    return layers
