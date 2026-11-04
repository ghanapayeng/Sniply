from flask import jsonify
from typing import Any, Dict, Optional


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
    meta: Optional[Dict[str, Any]] = None,
):
    """Format a consistent JSON success response."""
    payload = {
        "status": "success",
        "message": message,
        "data": data,
    }
    if meta is not None:
        payload["meta"] = meta
    return jsonify(payload), status_code


def error_response(
    message: str = "An error occurred",
    status_code: int = 400,
    errors: Optional[Any] = None,
    code: Optional[str] = None,
):
    """Format a consistent JSON error response."""
    payload = {
        "status": "error",
        "message": message,
    }
    if code is not None:
        payload["code"] = code
    if errors is not None:
        payload["errors"] = errors
    return jsonify(payload), status_code
