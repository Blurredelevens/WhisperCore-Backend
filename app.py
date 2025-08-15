import logging

from flask import request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_openapi3 import Info, OpenAPI
from sqlalchemy.exc import IntegrityError

from config import EnvConfig
from extensions import init_extensions
from models.token import Token


def create_app(config_class=EnvConfig):
    """Application factory function."""
    info = Info(title="WhisperCore API", version="1.0.0")
    app = OpenAPI(__name__, info=info)

    # Load configuration
    app_config = config_class()
    app.config.update(app_config.get_config())
    jwt = JWTManager(app)

    # Initialize extensions
    init_extensions(app)

    # JWT Configuration - Add token validation check
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        result = not Token.is_token_active(jti)
        return result

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return {"error": "The token has been revoked"}, 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {"error": "The token has expired"}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {"error": "Invalid token"}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {"error": "Authorization token is required"}, 401

    # Enable CORS
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
        methods=app.config.get("CORS_METHODS", ["GET", "POST", "PUT", "DELETE", "OPTIONS"]),
        allow_headers=app.config.get("CORS_HEADERS", ["Content-Type", "Authorization"]),
    )

    # Register error handlers
    from error_handlers import (
        handle_api_error,
        handle_bad_request_error,
        handle_integrity_error,
        handle_method_not_allowed_error,
    )
    from exceptions import BadRequestException, MethodNotAllowedException

    app.register_error_handler(Exception, handle_api_error)
    app.register_error_handler(IntegrityError, handle_integrity_error)
    app.register_error_handler(BadRequestException, handle_bad_request_error)
    app.register_error_handler(MethodNotAllowedException, handle_method_not_allowed_error)

    # Register blueprints (routes only, no views)
    from routes.auth import auth_bp
    from routes.health import health_bp
    from routes.memory import memory_bp
    from routes.memory_weighting import memory_weighting_bp
    from routes.notification import notification_bp
    from routes.prompt import prompt_bp
    from routes.reflection import reflection_bp
    from routes.settings import settings_bp
    from routes.summary import summary_bp
    from routes.task import task_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(memory_bp, url_prefix="/api/memories")
    app.register_blueprint(memory_weighting_bp, url_prefix="/api/memory-weighting")
    app.register_blueprint(notification_bp, url_prefix="/api/notifications")
    app.register_blueprint(reflection_bp, url_prefix="/api/reflections")
    app.register_blueprint(settings_bp, url_prefix="/api/settings")
    app.register_blueprint(task_bp, url_prefix="/api/task")
    app.register_blueprint(summary_bp, url_prefix="/api/summary")
    app.register_blueprint(prompt_bp, url_prefix="/api/prompts")
    app.logger.setLevel(logging.INFO)

    @app.before_request
    def log_request_info():
        app.logger.info(
            f"Request: {request.method} {request.path} - {request.remote_addr}\n"
            f"Body: {request.get_data(as_text=True)}",
        )

    @app.after_request
    def log_response_info(response):
        app.logger.info(f"Response: {request.method} {request.path} - Status: {response.status_code}")
        return response

    return app
