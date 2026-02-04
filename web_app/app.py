from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import BadRequest

from config_loader import load_config


BASE_DIR = Path(__file__).resolve().parent


def create_app() -> Flask:
    app = Flask(__name__, static_folder="public", template_folder="templates")
    config = load_config(BASE_DIR)

    # In-memory demo storage (resets on restart).
    tasks: list[Dict[str, Any]] = []

    @app.get("/")
    def index():
        firebase = config["firebase"]
        user_defaults = config["user_defaults"]
        return render_template(
            "index.html",
            database_url=firebase.get("database_url") or "Not configured",
            default_owner=user_defaults.get("default_owner", ""),
            owners=user_defaults.get("owners", []),
        )

    @app.get("/api/tasks")
    def get_tasks():
        return jsonify(tasks)

    @app.post("/api/tasks")
    def add_task():
        if request.mimetype != "application/json":
            return (
                jsonify({"error": "Expected application/json payload."}),
                415,
            )
        try:
            payload = request.get_json()
        except BadRequest:
            return jsonify({"error": "Invalid JSON payload."}), 400
        name = str(payload.get("name", "")).strip()
        status = str(payload.get("status", "To Do")).strip()
        if not status:
            status = "To Do"
        owner = str(payload.get("owner", "")).strip()
        deadline = str(payload.get("deadline", "")).strip()

        if not name:
            return jsonify({"error": "Task name is required."}), 400

        task = {
            "name": name,
            "status": status,
            "owner": owner,
            "deadline": deadline,
        }
        tasks.append(task)
        return jsonify(task), 201

    @app.get("/api/config")
    def get_config():
        return jsonify(config)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=bool(int(os.getenv("FLASK_DEBUG", "0"))),
    )
