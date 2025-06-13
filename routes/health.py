from flask import Blueprint, jsonify, current_app
from flask.views import MethodView
from datetime import datetime
import redis
from sqlalchemy import text
from extensions import db, redis_client
from tasks.celery_app import celery_init_app

health_bp = Blueprint('health', __name__)

class HealthCheckAPI(MethodView):
    def get(self):
        """Comprehensive health check endpoint."""
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'healthy',
            'version': '1.0.0',
            'services': {}
        }
        
        overall_healthy = True
        
        # Check database connectivity
        try:
            db.session.execute(text('SELECT 1'))
            health_status['services']['database'] = {
                'status': 'healthy',
                'message': 'Database connection successful'
            }
        except Exception as e:
            overall_healthy = False
            health_status['services']['database'] = {
                'status': 'unhealthy',
                'message': f'Database connection failed: {str(e)}'
            }
        
        # Check Redis connectivity
        try:
            redis_client.ping()
            health_status['services']['redis'] = {
                'status': 'healthy',
                'message': 'Redis connection successful'
            }
        except Exception as e:
            overall_healthy = False
            health_status['services']['redis'] = {
                'status': 'unhealthy',
                'message': f'Redis connection failed: {str(e)}'
            }
        
        # Check Celery worker status
        try:
            celery_app = current_app.extensions.get('celery')
            if celery_app:
                # Get active workers
                inspect = celery_app.control.inspect()
                active_workers = inspect.active()
                
                if active_workers:
                    worker_count = len(active_workers)
                    health_status['services']['celery'] = {
                        'status': 'healthy',
                        'message': f'{worker_count} Celery worker(s) active',
                        'workers': list(active_workers.keys())
                    }
                else:
                    overall_healthy = False
                    health_status['services']['celery'] = {
                        'status': 'unhealthy',
                        'message': 'No active Celery workers found'
                    }
            else:
                overall_healthy = False
                health_status['services']['celery'] = {
                    'status': 'unhealthy',
                    'message': 'Celery app not initialized'
                }
        except Exception as e:
            overall_healthy = False
            health_status['services']['celery'] = {
                'status': 'unhealthy',
                'message': f'Celery check failed: {str(e)}'
            }
        
        # Set overall status
        health_status['status'] = 'healthy' if overall_healthy else 'unhealthy'
        
        # Return appropriate HTTP status code
        status_code = 200 if overall_healthy else 503
        
        return jsonify(health_status), status_code

class ReadinessCheckAPI(MethodView):
    def get(self):
        """Readiness check for Kubernetes/deployment systems."""
        try:
            # Basic database check
            db.session.execute(text('SELECT 1'))
            
            # Basic Redis check
            redis_client.ping()
            
            return jsonify({
                'status': 'ready',
                'timestamp': datetime.utcnow().isoformat()
            }), 200
            
        except Exception as e:
            return jsonify({
                'status': 'not ready',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 503

class LivenessCheckAPI(MethodView):
    def get(self):
        """Liveness check for Kubernetes/deployment systems."""
        return jsonify({
            'status': 'alive',
            'timestamp': datetime.utcnow().isoformat()
        }), 200

# Register the class-based views
health_bp.add_url_rule('/health', view_func=HealthCheckAPI.as_view('health_check'))
health_bp.add_url_rule('/ready', view_func=ReadinessCheckAPI.as_view('readiness_check'))
health_bp.add_url_rule('/live', view_func=LivenessCheckAPI.as_view('liveness_check')) 