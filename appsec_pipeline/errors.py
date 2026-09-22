from flask import jsonify


class ApiError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def error_response(code, message, status):
    return jsonify(error={"code": code, "message": message}), status
