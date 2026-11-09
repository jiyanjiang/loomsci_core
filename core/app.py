"""Minimal local HTTP app for the S1 Core slice."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from flask import Flask, g, jsonify, request

from core.local_auth import check_request
from core.packs import Registry

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 8787


def _version() -> str:
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def create_app(env: Mapping[str, str] | None = None) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    registry = Registry.from_env(env)
    app.extensions["loomsci_registry"] = registry

    @app.before_request
    def _local_gate():
        decision = check_request(
            method=request.method,
            path=request.path,
            host=request.host,
            origin=request.headers.get("Origin"),
            content_type=request.headers.get("Content-Type"),
            agent=request.headers.get("X-Loomsci-Agent"),
            registry=registry,
        )
        if not decision.ok:
            return jsonify(decision.payload or {"ok": False}), decision.status
        g.loomsci_agent = decision.agent
        return None

    @app.after_request
    def _headers(response):
        response.headers.setdefault("X-Loomsci-Protocol", "1.0")
        return response

    @app.get("/v1/health")
    def health():
        return jsonify({
            "ok": True,
            "service": "loomsci_core",
            "version": _version(),
            "profile": registry.profile,
        })

    @app.get("/v1/version")
    def version():
        return jsonify({
            "ok": True,
            "product": "loomsci_core",
            "version": _version(),
            "profile": registry.profile,
            "protocol": "1.0",
        })

    @app.get("/v1/meta/features")
    def features():
        return jsonify({"ok": True, **registry.features()})

    @app.get("/v1/whoami")
    def whoami():
        return jsonify({"ok": True, "agent": g.loomsci_agent})

    @app.post("/v1/echo")
    def echo():
        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({"ok": False, "error": "json_required"}), 400
        return jsonify({"ok": True, "agent": g.loomsci_agent, "echo": payload})

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"ok": False, "error": "not_found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify({"ok": False, "error": "method_not_allowed"}), 405

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"ok": False, "error": "body_too_large"}), 413

    return app
