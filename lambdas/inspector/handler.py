"""
Inspector Lambda

Given a layer descriptor (output from discovery), downloads the layer zip
and catalogues all packages found inside it.

Supported formats:
  Python — .dist-info/METADATA  (PEP 566, modern pip)
           .egg-info/PKG-INFO   (older setuptools)
  Node.js — node_modules/<pkg>/package.json  (top-level only, no nested deps)
"""

import email.parser
import json
import logging
import os
import urllib.request
import zipfile

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TMP_ZIP = "/tmp/layer.zip"


def handler(event, context):
    layer_version_arn: str = event["latest_version_arn"]
    logger.info("Inspecting layer: %s", layer_version_arn)

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
    logger.info("Downloading %.1f MB", content_size / 1024 / 1024)

    if os.path.exists(TMP_ZIP):
        os.remove(TMP_ZIP)
    urllib.request.urlretrieve(download_url, TMP_ZIP)

    packages = _extract_packages(TMP_ZIP)
    os.remove(TMP_ZIP)

    logger.info("Found %d packages in %s", len(packages), event["name"])

    return {
        **event,
        "packages": sorted(packages, key=lambda p: p["name"].lower()),
        "package_count": len(packages),
        "layer_size_bytes": content_size,
    }


def _extract_packages(zip_path: str) -> list[dict]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()

        # ── Python ───────────────────────────────────────────────────────────
        meta_files = [n for n in names if ".dist-info/METADATA" in n]
        if not meta_files:
            meta_files = [n for n in names if ".egg-info/PKG-INFO" in n]

        if meta_files:
            return _parse_python_packages(zf, meta_files)

        # ── Node.js ───────────────────────────────────────────────────────────
        pkg_json_files = [n for n in names if _is_top_level_package_json(n)]
        if pkg_json_files:
            return _parse_node_packages(zf, pkg_json_files)

    return []


# ── Python ────────────────────────────────────────────────────────────────────

def _parse_python_packages(zf: zipfile.ZipFile, paths: list[str]) -> list[dict]:
    packages, seen = [], set()
    for path in paths:
        try:
            with zf.open(path) as f:
                content = f.read().decode("utf-8", errors="replace")
            pkg = _parse_python_metadata(content)
            if pkg and pkg["name"] not in seen:
                seen.add(pkg["name"])
                packages.append(pkg)
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", path, exc)
    return packages


def _parse_python_metadata(content: str) -> dict | None:
    msg = email.parser.Parser().parsestr(content)
    name = msg.get("Name")
    version = msg.get("Version")
    if not name or not version:
        return None
    return {
        "name": name,
        "version": version,
        "summary": msg.get("Summary", ""),
        "home_page": msg.get("Home-page") or _python_homepage(msg) or "",
        "license": msg.get("License", ""),
    }


def _python_homepage(msg) -> str:
    for entry in msg.get_all("Project-URL") or []:
        if "," not in entry:
            continue
        label, url = entry.split(",", 1)
        if label.strip() in {"Homepage", "Source", "Repository"}:
            return url.strip()
    return ""


# ── Node.js ───────────────────────────────────────────────────────────────────

def _is_top_level_package_json(path: str) -> bool:
    """
    Match only direct children of a node_modules directory, not nested deps.

    Valid:
      nodejs/node_modules/express/package.json          (regular)
      nodejs/node_modules/@aws-sdk/client-s3/package.json  (scoped)
    Invalid:
      nodejs/node_modules/express/node_modules/mime/package.json  (nested)
      nodejs/node_modules/express/lib/package.json               (sub-path)
    """
    parts = path.split("/")
    if parts[-1] != "package.json":
        return False
    try:
        nm_idx = parts.index("node_modules")
    except ValueError:
        return False
    # Reject nested node_modules
    if "node_modules" in parts[nm_idx + 1:]:
        return False
    after = parts[nm_idx + 1:]  # segments after node_modules
    # Regular:  [name, package.json]
    if len(after) == 2:
        return True
    # Scoped:   [@scope, name, package.json]
    if len(after) == 3 and after[0].startswith("@"):
        return True
    return False


def _parse_node_packages(zf: zipfile.ZipFile, paths: list[str]) -> list[dict]:
    packages, seen = [], set()
    for path in paths:
        try:
            with zf.open(path) as f:
                data = json.loads(f.read().decode("utf-8", errors="replace"))
            pkg = _parse_package_json(data)
            if pkg and pkg["name"] not in seen:
                seen.add(pkg["name"])
                packages.append(pkg)
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", path, exc)
    return packages


def _parse_package_json(data: dict) -> dict | None:
    name = data.get("name")
    version = data.get("version")
    if not name or not version:
        return None

    license_raw = data.get("license", "")
    license_str = license_raw.get("type", "") if isinstance(license_raw, dict) else license_raw

    return {
        "name": name,
        "version": version,
        "summary": data.get("description", ""),
        "home_page": data.get("homepage", ""),
        "license": license_str,
    }
