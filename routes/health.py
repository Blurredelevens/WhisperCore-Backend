import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify
from flask.views import MethodView

from extensions import db, redis_client

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)


class HealthCheckAPI(MethodView):
    """Simple server health check endpoint - no external dependencies."""

    def get(self):
        """Basic health check that only checks if the server is running."""
        return (
            jsonify(
                {
                    "status": "healthy",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": "Server is running",
                },
            ),
            200,
        )


class DetailedHealthCheckAPI(MethodView):
    """Detailed health check endpoint that tests all system components."""

    def get(self):
        """Comprehensive health check that tests database, Redis, and other services."""
        health_data = {"timestamp": datetime.now(timezone.utc).isoformat(), "status": "unknown", "components": {}}

        # Check database
        try:
            db.session.execute(db.text("SELECT 1"))
            db_status = "healthy"
            health_data["components"]["database"] = {"status": db_status}
        except Exception as e:
            db_status = "unhealthy"
            health_data["components"]["database"] = {"status": db_status, "error": str(e)}

        # Check Redis
        try:
            redis_client.ping()
            redis_status = "healthy"
            health_data["components"]["redis"] = {"status": redis_status}
        except Exception as e:
            redis_status = "unhealthy"
            health_data["components"]["redis"] = {"status": redis_status, "error": str(e)}

        # Determine overall status
        try:
            component_statuses = [comp["status"] for comp in health_data["components"].values()]
            if all(status == "healthy" for status in component_statuses):
                overall_status = "healthy"
                status_code = 200
            elif any(status == "healthy" for status in component_statuses):
                overall_status = "degraded"
                status_code = 503
            else:
                overall_status = "unhealthy"
                status_code = 503
        except Exception as e:
            logger.error(f"Error determining overall health status: {e}")
            overall_status = "error"
            status_code = 500

        health_data["status"] = overall_status

        return jsonify(health_data), status_code


# Register URL rules
health_bp.add_url_rule("/health", view_func=HealthCheckAPI.as_view("health"))
health_bp.add_url_rule("/health/detailed", view_func=DetailedHealthCheckAPI.as_view("detailed_health"))
