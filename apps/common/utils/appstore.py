import json
import os
import tempfile
import zipfile
from typing import Iterable

import requests

from common.utils.logger import maxkb_logger
from lzkb.const import CONFIG

EMPTY_APPSTORE_TEMPLATE = {
    "apps": [],
    "additionalProperties": {"tags": []},
}


def _fetch_appstore_payload(timeout: int = 5) -> dict:
    appstore_url = CONFIG.get_appstore_url()
    response = requests.get(appstore_url, timeout=timeout)
    response.raise_for_status()

    if not appstore_url.endswith(".zip"):
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Invalid AppStore payload format.")
        payload.setdefault("apps", [])
        payload.setdefault("additionalProperties", {"tags": []})
        payload["additionalProperties"].setdefault("tags", [])
        return payload

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
        temp_zip.write(response.content)
        temp_zip_path = temp_zip.name

    try:
        with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
            names = zip_ref.namelist()
            if len(names) == 0:
                raise ValueError("AppStore payload is empty.")
            json_filename = next((name for name in names if name.endswith(".json")), names[0])
            json_content = zip_ref.read(json_filename)
        payload = json.loads(json_content.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Invalid AppStore payload format.")
        payload.setdefault("apps", [])
        payload.setdefault("additionalProperties", {"tags": []})
        payload["additionalProperties"].setdefault("tags", [])
        return payload
    finally:
        if os.path.exists(temp_zip_path):
            os.unlink(temp_zip_path)


def fetch_filtered_appstore_apps(
    keyword: str = "",
    suffix: str | None = None,
    required_tag_keys: Iterable[str] | None = None,
) -> dict:
    try:
        tool_store = _fetch_appstore_payload()
        tags = tool_store.get("additionalProperties", {}).get("tags") or []
        tag_dict = {
            tag.get("name"): tag.get("key")
            for tag in tags
            if isinstance(tag, dict) and tag.get("name") and tag.get("key")
        }

        keyword = (keyword or "").strip().lower()
        required_tag_keys_set = set(required_tag_keys or [])
        filtered_apps = []
        for app in tool_store.get("apps", []):
            if not isinstance(app, dict):
                continue
            app_name = (app.get("name") or "").lower()
            if keyword and keyword not in app_name:
                continue

            download_url = app.get("downloadUrl") or ""
            if suffix and not download_url.endswith(suffix):
                continue

            app_tags = app.get("tags") or []
            app_tag_keys = [tag_dict.get(tag, tag) for tag in app_tags]
            if required_tag_keys_set and not required_tag_keys_set.issubset(set(app_tag_keys)):
                continue

            app_item = dict(app)
            app_item["label"] = tag_dict.get(app_tags[0], "") if app_tags else ""
            versions = app_item.get("versions", [])
            app_item["version"] = next(
                (version.get("name") for version in versions if version.get("downloadUrl") == download_url),
                None,
            )
            filtered_apps.append(app_item)

        tool_store["apps"] = filtered_apps
        return tool_store
    except Exception as e:
        maxkb_logger.error(f"fetch appstore tools error: {e}")
        return dict(EMPTY_APPSTORE_TEMPLATE)
