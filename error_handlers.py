from flask import jsonify


def handle_api_error(error):
    """Handle general API errors."""
    response = {"error": str(error), "message": "An unexpected error occurred"}
    return jsonify(response), 500


def handle_integrity_error(error):
    """Handle database integrity errors."""
    response = {"error": "Database integrity error", "message": str(error)}
    return jsonify(response), 400


def handle_bad_request_error(error):
    """Handle bad request errors."""
    response = {"error": "Bad request", "message": str(error)}
    return jsonify(response), 400


def handle_method_not_allowed_error(error):
    """Handle method not allowed errors."""
    response = {"error": "Method not allowed", "message": str(error)}
    return jsonify(response), 405
