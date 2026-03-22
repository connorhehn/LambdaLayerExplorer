"""
Quick diagnostic — tests the seed-based version probe locally.

    python3 main.py
"""

import boto3
from botocore.exceptions import ClientError

client = boto3.client("lambda", region_name="us-east-1")


def try_version(arn: str, v: int) -> dict | None:
    try:
        return client.get_layer_version(LayerName=arn, VersionNumber=v)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("ResourceNotFoundException", "AccessDeniedException"):
            return None
        raise


def get_latest(arn: str, seed: int) -> dict | None:
    result = try_version(arn, seed)
    if result is None:
        print(f"  seed v{seed} not accessible!")
        return None

    last_good = result
    low, delta = seed, 1
    while True:
        probe = low + delta
        result = try_version(arn, probe)
        if result is None:
            high = probe
            break
        last_good = result
        low, delta = probe, delta * 2
        if delta > 10_000:
            return last_good

    while low < high - 1:
        mid = (low + high) // 2
        result = try_version(arn, mid)
        if result is not None:
            last_good = result
            low = mid
        else:
            high = mid

    return last_good


TESTS = [
    ("arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV2",              78),
    ("arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV3-python312-x86_64", 19),
    ("arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python312",                   22),
    ("arn:aws:lambda:us-east-1:615299751070:layer:AWSOpenTelemetryDistroPython",             24),
]

for arn, seed in TESTS:
    name = arn.split(":layer:")[1]
    print(f"\n{name} (seed={seed})")
    r = get_latest(arn, seed)
    if r:
        print(f"  latest: v{r['Version']}  ({r['LayerVersionArn']})")
    else:
        print("  FAILED — not accessible")
