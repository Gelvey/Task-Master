from __future__ import annotations

import configparser
import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_JSON = "configuration.json"
DEFAULT_CONFIG_INI = "config.ini"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}


def _load_ini(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    if path.is_file():
        parser.read(path, encoding="utf-8")
    return parser


def _split_owners(raw_value: str) -> list[str]:
    if not raw_value:
        return []
    cleaned = raw_value.replace(";", ",")
    if "," in cleaned:
        return [owner.strip() for owner in cleaned.split(",") if owner.strip()]
    return [owner.strip() for owner in cleaned.split() if owner.strip()]


def load_config(base_dir: Path) -> Dict[str, Any]:
    config_json_path = Path(
        os.getenv("CONFIGURATION_JSON_PATH", base_dir / DEFAULT_CONFIG_JSON)
    )
    config_ini_path = Path(
        os.getenv("CONFIG_INI_PATH", base_dir / DEFAULT_CONFIG_INI)
    )

    config_json = _load_json(config_json_path)
    config_ini = _load_ini(config_ini_path)

    firebase_json = config_json.get("firebase", {})
    if not isinstance(firebase_json, dict):
        firebase_json = {}

    firebase = {
        "database_url": os.getenv("FIREBASE_DATABASE_URL")
        or firebase_json.get("database_url", ""),
        "project_id": os.getenv("FIREBASE_PROJECT_ID")
        or firebase_json.get("project_id", ""),
    }

    owners_env = os.getenv("OWNERS", "").strip()
    owners_ini = config_ini.get("owners", "list", fallback="").strip()

    user_defaults = {
        "default_owner": os.getenv("DEFAULT_OWNER")
        or config_ini.get("user", "username", fallback="").strip(),
        "owners": _split_owners(owners_env)
        if owners_env
        else _split_owners(owners_ini),
    }

    return {
        "firebase": firebase,
        "user_defaults": user_defaults,
    }


def write_runtime_config(base_dir: Path, output_path: Path) -> Dict[str, Any]:
    """Write the merged config to disk and return the generated data."""
    config = load_config(base_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)
    return config
