from flask import Blueprint, request, jsonify
from celery.result import AsyncResult
from extensions import celery
from tasks.query import process_query
from flask.views import MethodView


task_bp = Blueprint('task', __name__)


class TaskAPI(MethodView):
    def post(self):
        print("Request received")
        query = request.json.get('query')
        if not query:
         return jsonify({"error": "No query provided"}), 400
    
        task = process_query.delay(query)
        return jsonify({"task_id": task.id}), 202


class TaskStatusAPI(MethodView):
    def get(self, task_id):
        task_result = AsyncResult(task_id, app=celery)
        if task_result.state == 'PENDING':
         response = {
            'state': task_result.state,
            'status': 'Pending...'
        }
        elif task_result.state != 'FAILURE':
         response = {
            'state': task_result.state,
            'result': task_result.result
        }
        else:
            response = {
                'state': task_result.state,
                'status': str(task_result.info),
            }
        return jsonify(response)

# Register the blueprint

task_bp.add_url_rule('/query', view_func=TaskAPI.as_view('task'), methods=['POST'], )
task_bp.add_url_rule('/<task_id>', view_func=TaskStatusAPI.as_view('task_status'), methods=['GET'],) 


