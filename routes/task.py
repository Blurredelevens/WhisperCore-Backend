from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from celery.result import AsyncResult
from extensions import celery
from flask.views import MethodView
import logging

task_bp = Blueprint('task', __name__)   

logger = logging.getLogger(__name__)

class TaskAPI(MethodView):
    decorators = [jwt_required()]
    
    def post(self):
        print("Request received")
        user_id = get_jwt_identity()
        query = request.json.get('query')
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        try:
            task = celery.send_task('tasks.scheduled.process_query_task', args=[{"query": query}])
            
            return jsonify({
                "message": "Task started successfully",
                "task_id": task.id,
                "status": "processing" 
            }), 202
                
        except Exception as e:
                return jsonify({"error": f"Error starting task: {str(e)}"}), 500


class TaskStatusAPI(MethodView):
    decorators = [jwt_required()]
    
    def get(self, task_id):
        user_id = get_jwt_identity()
        task_result = AsyncResult(task_id, app=celery)
        
        if task_result.state == 'PENDING':
            response = {
                'task_id': task_id,
                'state': task_result.state,
                'status': 'Task is scheduled and waiting to be processed.'
            }
        elif task_result.state == 'SUCCESS':
            result_data = task_result.result
            response = {
                'task_id': task_id,
                'state': task_result.state,
                'status': 'Task completed successfully',
                'data': result_data
            }
        elif task_result.state == 'FAILURE':
            response = {
                'task_id': task_id,
                'state': task_result.state,
                'status': 'Task failed',
                'error': str(task_result.info)
            }
        else:
            response = {
                'task_id': task_id,
                'state': task_result.state,
                'status': 'Task is in progress...'
            }
            
        return jsonify(response)

# Register the blueprint

task_bp.add_url_rule('/query', view_func=TaskAPI.as_view('task'), methods=['POST'], )
task_bp.add_url_rule('/<task_id>', view_func=TaskStatusAPI.as_view('task_status'), methods=['GET'],) 


