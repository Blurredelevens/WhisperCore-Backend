from flask import Blueprint, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User

test_bp = Blueprint('test', __name__)

class TestAuthAPI(MethodView):
    decorators = [jwt_required()]
    
    def get(self):
        """Test endpoint to verify authentication is working."""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        return jsonify({
            'message': 'Authentication working!',
            'user_id': user_id,
            'user_email': user.email if user else None,
            'timestamp': '2024-01-01T00:00:00Z'
        }), 200

class TestPublicAPI(MethodView):
    def get(self):
        """Test public endpoint."""
        return jsonify({
            'message': 'Public endpoint working!',
            'timestamp': '2024-01-01T00:00:00Z'
        }), 200

# Register the class-based views
test_bp.add_url_rule('/auth-test', view_func=TestAuthAPI.as_view('auth_test'))
test_bp.add_url_rule('/public-test', view_func=TestPublicAPI.as_view('public_test')) 