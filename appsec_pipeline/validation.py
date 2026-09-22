import re

from flask import request

from appsec_pipeline.errors import ApiError


def json_object(allowed, required=()):
    data = request.get_json()
    if not isinstance(data, dict):
        raise ApiError("invalid_input", "A JSON object is required.")
    if set(data) - set(allowed) or set(required) - set(data):
        raise ApiError("invalid_input", "Unexpected or missing fields.")
    return data


def string_field(value, name, minimum, maximum, strip=False):
    if not isinstance(value, str):
        raise ApiError("invalid_input", f"{name} must be a string.")
    if strip:
        value = value.strip()
    if not minimum <= len(value) <= maximum or "\x00" in value:
        raise ApiError("invalid_input", f"{name} must contain {minimum} to {maximum} characters.")
    return value


def username_value(value):
    value = string_field(value, "username", 3, 64, strip=True).lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", value):
        raise ApiError("invalid_input", "username has an invalid format.")
    return value


def document_input(partial=False):
    fields = {"title", "content"}
    data = json_object(fields, () if partial else fields)
    if not data:
        raise ApiError("invalid_input", "At least one field is required.")
    result = {}
    if "title" in data:
        result["title"] = string_field(data["title"], "title", 1, 200, strip=True)
    if "content" in data:
        result["content"] = string_field(data["content"], "content", 0, 50000)
    return result


def pagination():
    if set(request.args) - {"page", "per_page"}:
        raise ApiError("invalid_input", "Unexpected query parameters.")
    values = {}
    for name, default, maximum in (("page", 1, 1000000), ("per_page", 20, 100)):
        raw = request.args.get(name, str(default))
        if len(request.args.getlist(name)) > 1 or not re.fullmatch(r"[0-9]{1,7}", raw):
            raise ApiError("invalid_input", "Invalid pagination.")
        number = int(raw)
        if not 1 <= number <= maximum:
            raise ApiError("invalid_input", "Invalid pagination.")
        values[name] = number
    return values["page"], values["per_page"]
