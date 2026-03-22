"""
Inspector Lambda

Given a layer descriptor (output from discovery), downloads the layer zip,
unpacks it in /tmp, and catalogues all Python packages found in dist-info
or egg-info metadata files.
"""

import email.parser
import logging
import os
import urllib.request
import zipfile

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TMP_ZIP = "/tmp/layer.zip"


def handler(event, context):
    """
    event: a single layer dict as returned by the discovery Lambda, e.g.:
    {
        "name": "AWSLambdaPowertoolsPythonV3-python312",
        "arn": "arn:aws:lambda:us-east-1:017000801446:layer:...",
        "latest_version": 7,
        "latest_version_arn": "arn:aws:lambda:us-east-1:...:7",
        ...
    }
    """
    layer_version_arn: str = event["latest_version_arn"]
    logger.info("Inspecting layer: %s", layer_version_arn)

    # Derive LayerName (ARN without trailing :version) and VersionNumber
    parts = layer_version_arn.split(":")
    version_number = int(parts[-1])
    layer_name_arn = ":".join(parts[:-1])

    lambda_client = boto3.client("lambda", region_name="us-east-1")
    response = lambda_client.get_layer_version(
        LayerName=layer_name_arn,
        VersionNumber=version_number,
    )

    download_url: str = response["Content"]["Location"]
    content_size: int = response["Content"].get("CodeSize", 0)
    logger.info(
        "Downloading layer zip (%.1f MB) from presigned URL",
        content_size / 1024 / 1024,
    )

    # Download to /tmp to avoid exhausting Lambda memory for large layers
    if os.path.exists(TMP_ZIP):
        os.remove(TMP_ZIP)
    urllib.request.urlretrieve(download_url, TMP_ZIP)

    packages = _extract_packages(TMP_ZIP)
    os.remove(TMP_ZIP)

    logger.info("Found %d packages in layer %s", len(packages), event["name"])

    return {
        **event,
        "packages": sorted(packages, key=lambda p: p["name"].lower()),
        "package_count": len(packages),
        "layer_size_bytes": content_size,
    }


def _extract_packages(zip_path: str) -> list[dict]:
    """Return a list of package dicts found inside the layer zip."""
    packages = []
    seen_names: set[str] = set()

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()

        # Prefer .dist-info/METADATA (PEP 566, modern pip)
        metadata_files = [
            n for n in names if ".dist-info/METADATA" in n
        ]

        # Fall back to .egg-info/PKG-INFO (older setuptools)
        if not metadata_files:
            metadata_files = [
                n for n in names if ".egg-info/PKG-INFO" in n
            ]

        for meta_path in metadata_files:
            try:
                with zf.open(meta_path) as f:
                    content = f.read().decode("utf-8", errors="replace")
                pkg = _parse_metadata(content)
                if pkg and pkg["name"] not in seen_names:
                    seen_names.add(pkg["name"])
                    packages.append(pkg)
            except Exception as exc:
                logger.warning("Failed to parse %s: %s", meta_path, exc)

    return packages


def _parse_metadata(content: str) -> dict | None:
    """Parse an RFC 2822-style Python package METADATA / PKG-INFO file."""
    parser = email.parser.Parser()
    msg = parser.parsestr(content)

    name = msg.get("Name")
    version = msg.get("Version")
    if not name or not version:
        return None

    home_page = msg.get("Home-page") or _extract_homepage(msg)

    return {
        "name": name,
        "version": version,
        "summary": msg.get("Summary", ""),
        "home_page": home_page or "",
        "license": msg.get("License", ""),
        "requires_python": msg.get("Requires-Python", ""),
    }


def _extract_homepage(msg) -> str:
    """Extract homepage from Project-URL entries (PEP 753)."""
    preferred_labels = {"Homepage", "Source", "Repository"}
    for entry in msg.get_all("Project-URL") or []:
        if "," not in entry:
            continue
        label, url = entry.split(",", 1)
        if label.strip() in preferred_labels:
            return url.strip()
    return ""
