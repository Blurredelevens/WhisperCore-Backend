from flask import Blueprint, request, jsonify, current_app, send_file
from flask.views import MethodView
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, 
    get_jwt_identity, get_jwt, decode_token
)
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, and_
from extensions import db
from models.user import User
from models.token import Token
from models.memory import Memory
from models.reflection import Reflection
from schemas.auth import (
    UserCreate, UserResponse, UserDetailResponse, LoginRequest, 
    PassphraseLoginRequest, CombinedLoginRequest, LoginResponse,
    RefreshTokenRequest, TokenResponse, ProfileUpdateRequest,
    PasswordChangeRequest, PassphraseSetRequest, PassphraseChangeRequest,
    RegisterResponse, LogoutResponse, SuccessResponse, DashboardResponse,
    DashboardStats
)
auth_bp = Blueprint('auth', __name__)

class AuthRegisterAPI(MethodView):
    def post(self):
        """Register a new user with email/password and optional passphrase."""
        try:
            data = UserCreate.model_validate(request.get_json())
        except Exception as e:
            return jsonify({'error': f'Validation error: {str(e)}'}), 400
        
        # Check if email already exists
        if User.query.filter_by(email=data.email).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create new user
        user = User(
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name
        )
        user.set_password(data.password)
        
        # Set passphrase if provided
        if data.passphrase:
            user.set_passphrase(data.passphrase)
        
        db.session.add(user)
        db.session.commit()
        
        try:
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            access_token_decoded = decode_token(access_token)
            refresh_token_decoded = decode_token(refresh_token)
            
            Token.create_token(
                jti=access_token_decoded['jti'],
                token_type='access',
                user_id=user.id,
                token_value=access_token,
                expires_at=datetime.fromtimestamp(access_token_decoded['exp'], tz=timezone.utc)
            )

            Token.create_token(
                jti=refresh_token_decoded['jti'],
                token_type='refresh',
                user_id=user.id,
                token_value=refresh_token,
                expires_at=datetime.fromtimestamp(refresh_token_decoded['exp'], tz=timezone.utc)
            )
        except Exception as e:
            # Log the error and return a clear message
            print(f"Token creation error: {e}")
            return jsonify({'error': f'Token creation error: {str(e)}'}), 400
        
        return RegisterResponse(
            message='User registered successfully',
            user=UserResponse.model_validate(user.to_dict()),
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES').total_seconds())
        ).model_dump(), 201

class AuthLoginAPI(MethodView):
    def post(self):
        """Login with email/password."""
        try:
            data = LoginRequest.model_validate(request.get_json())
        except Exception as e:
            return jsonify({'error': f'Validation error: {str(e)}'}), 400
        
        user = User.query.filter_by(email=data.email).first()
        
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check if account is locked
        if user.is_account_locked():
            return jsonify({'error': 'Account is temporarily locked due to failed login attempts'}), 423
        
        # Check if account is active
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 403
        
        # Verify password
        if not user.check_password(data.password):
            user.increment_failed_attempts()
            db.session.commit()
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Reset failed attempts and update last login
        user.reset_failed_attempts()
        user.update_last_login()
        db.session.commit()
        
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        access_token_decoded = decode_token(access_token)
        refresh_token_decoded = decode_token(refresh_token)

        Token.upsert_token(
            jti=access_token_decoded['jti'],
            token_type='access',
            user_id=user.id,
            token_value=access_token,
            expires_at=datetime.fromtimestamp(access_token_decoded['exp'], tz=timezone.utc)
        )
        Token.upsert_token(
            jti=refresh_token_decoded['jti'],
            token_type='refresh',
            user_id=user.id,
            token_value=refresh_token,
            expires_at=datetime.fromtimestamp(refresh_token_decoded['exp'], tz=timezone.utc)
        )
        
        return LoginResponse(
            message='Login successful',
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user.to_dict()),
            expires_in=int(current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES').total_seconds())
        ).model_dump(), 200

class AuthPassphraseLoginAPI(MethodView):
    def post(self):
        """Login with email/passphrase."""
        try:
            data = PassphraseLoginRequest.model_validate(request.get_json())
        except Exception as e:
            return jsonify({'error': f'Validation error: {str(e)}'}), 400
        
        user = User.query.filter_by(email=data.email).first()
        
        if not user or not user.passphrase_hash:
            return jsonify({'error': 'Invalid credentials or passphrase not set'}), 401
        
        # Check if account is locked
        if user.is_account_locked():
            return jsonify({'error': 'Account is temporarily locked'}), 423
        
        # Check if account is active
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 403
        
        # Verify passphrase
        if not user.check_passphrase(data.passphrase):
            user.increment_failed_attempts()
            db.session.commit()
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Reset failed attempts and update last login
        user.reset_failed_attempts()
        user.update_last_login()
        db.session.commit()
        
        # Create tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        
        # Store tokens in database
        access_token_decoded = decode_token(access_token)
        refresh_token_decoded = decode_token(refresh_token)
        
        Token.create_token(
            jti=access_token_decoded['jti'],
            token_type='access',
            user_id=user.id,
            token_value=access_token,
            expires_at=datetime.fromtimestamp(access_token_decoded['exp'], tz=timezone.utc)
        )
        
        Token.create_token(
            jti=refresh_token_decoded['jti'],
            token_type='refresh',
            user_id=user.id,
            token_value=refresh_token,
            expires_at=datetime.fromtimestamp(refresh_token_decoded['exp'], tz=timezone.utc)
        )
        
        return LoginResponse(
            message='Login successful',
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user.to_dict()),
            expires_in=int(current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES').total_seconds())
        ).model_dump(), 200

class AuthRefreshAPI(MethodView):
    decorators = [jwt_required(refresh=True)]
    
    def post(self):
        """Refresh access token using refresh token."""
        user_id = get_jwt_identity()
        current_token = get_jwt()
        
        # Check if refresh token is active
        if not Token.is_token_active(current_token['jti']):
            return jsonify({'error': 'Token has been revoked or expired'}), 401
        
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 404
        
        # Create new access token
        access_token = create_access_token(identity=str(user_id))
        
        # Store new access token in database
        access_token_decoded = decode_token(access_token)
        Token.create_token(
            jti=access_token_decoded['jti'],
            token_type='access',
            user_id=user_id,
            token_value=access_token,
            expires_at=datetime.fromtimestamp(access_token_decoded['exp'], tz=timezone.utc)
        )
        
        return TokenResponse(
            message='Token refreshed successfully',
            access_token=access_token,
            expires_in=int(current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES').total_seconds())
        ).model_dump(), 200

class AuthLogoutAPI(MethodView):
    decorators = [jwt_required()]
    
    def post(self):
        """Logout user and revoke the token."""
        current_token = get_jwt()
        user_id = get_jwt_identity()
        
        # Revoke curren     t token and deactivate all user tokens
        Token.revoke_token(current_token['jti'])
        Token.deactivate_user_tokens(user_id)
        
        return LogoutResponse(message='Successfully logged out').model_dump(), 200

class AuthMeAPI(MethodView):
    decorators = [jwt_required()]
    def get(self):
        """Get current user information."""
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        include_sensitive = request.args.get('include_sensitive', 'false').lower() == 'true'
        
        if include_sensitive:
            return UserDetailResponse.model_validate(user.to_dict(include_sensitive=True)).model_dump(), 200
        else:
            return UserResponse.model_validate(user.to_dict()).model_dump(), 200

class ProfileAPI(MethodView):
    decorators = [jwt_required()]
    
    def put(self):
        """Update user profile information."""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        try:
            data = ProfileUpdateRequest.model_validate(request.get_json())
        except Exception as e:
            return jsonify({'error': f'Validation error: {str(e)}'}), 400
        
        # Update profile fields
        if data.first_name is not None:
            user.first_name = data.first_name
        if data.last_name is not None:
            user.last_name = data.last_name
        if data.bio is not None:
            user.bio = data.bio
        
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return UserResponse.model_validate(user.to_dict()).model_dump(), 200

class PasswordChangeAPI(MethodView):
    decorators = [jwt_required()]
    
    def post(self):
        """Change user password."""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        try:
            data = PasswordChangeRequest.model_validate(request.get_json())
        except Exception as e:
            return jsonify({'error': f'Validation error: {str(e)}'}), 400
        
        # Verify current password
        if not user.check_password(data.current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Set new password
        user.set_password(data.new_password)
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return SuccessResponse(message='Password changed successfully').model_dump(), 200

class PassphraseSetAPI(MethodView):
    decorators = [jwt_required()]
    
    def post(self):
        """Set or update user passphrase."""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        try:
            data = PassphraseSetRequest.model_validate(request.get_json())
        except Exception as e:
            return jsonify({'error': f'Validation error: {str(e)}'}), 400
        
        # Verify current password
        if not user.check_password(data.current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Set passphrase
        user.set_passphrase(data.passphrase)
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return SuccessResponse(message='Passphrase set successfully').model_dump(), 200

class PassphraseChangeAPI(MethodView):
    decorators = [jwt_required()]
    
    def post(self):
        """Change user passphrase."""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.passphrase_hash:
            return jsonify({'error': 'No passphrase is currently set'}), 400
        
        try:
            data = PassphraseChangeRequest.model_validate(request.get_json())
        except Exception as e:
            return jsonify({'error': f'Validation error: {str(e)}'}), 400
        
        # Verify current passphrase
        if not user.check_passphrase(data.current_passphrase):
            return jsonify({'error': 'Current passphrase is incorrect'}), 400
        
        # Set new passphrase
        user.set_passphrase(data.new_passphrase)
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return SuccessResponse(message='Passphrase changed successfully').model_dump(), 200

class DashboardAPI(MethodView):
    decorators = [jwt_required()]
    
    def get(self):
        """Get user dashboard with stats and recent activity."""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        key = user.encryption_key.encode()  # Get the encryption key

        # Get recent memories with the key
        recent_memories = Memory.query.filter_by(user_id=user_id)\
            .order_by(Memory.created_at.desc())\
            .limit(5)\
            .all()
        
        
        # Get mood statistics
        mood_stats = db.session.query(
            Memory.mood, 
            db.func.count(Memory.id)
        ).filter_by(user_id=user_id)\
         .group_by(Memory.mood)\
         .all()

        # Get tag statistics
        tag_stats = db.session.query(
            Memory.tags, 
            db.func.count(Memory.id)
        ).filter_by(user_id=user_id)\
         .group_by(Memory.tags)\
         .all()

        # Convert memories to dict with the key
        memories_data = [memory.to_dict(key) for memory in recent_memories]

        return jsonify({
            'recent_memories': memories_data,
            'mood_statistics': dict(mood_stats),
            'tag_statistics': dict(tag_stats)
        }), 200
    
class UserImageUploadAPI(MethodView):
    decorators = [jwt_required()]
    
    def post(self):
        """Upload user profile image."""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image part in request'}), 400
        
        image = request.files['image']
        if image.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        filename = secure_filename(image.filename)
        upload_folder = os.path.join(current_app.root_path, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        image.save(file_path)
        
        user.image_path = file_path
        db.session.commit()
        
        return jsonify({'message': 'Image uploaded successfully', 'image_path': file_path}), 200

class UserImageDownloadAPI(MethodView):
    decorators = [jwt_required()]   
    
    def get(self):
        """Download user profile image."""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.image_path:
            return jsonify({'error': 'No image found for this user'}), 404
        
        return send_file(user.image_path, mimetype='image/jpeg')
    
    

# Register the class-based views
auth_bp.add_url_rule('/register', view_func=AuthRegisterAPI.as_view('register'))
auth_bp.add_url_rule('/login', view_func=AuthLoginAPI.as_view('login'))
auth_bp.add_url_rule('/login/passphrase', view_func=AuthPassphraseLoginAPI.as_view('passphrase_login'))
auth_bp.add_url_rule('/refresh', view_func=AuthRefreshAPI.as_view('refresh'))
auth_bp.add_url_rule('/logout', view_func=AuthLogoutAPI.as_view('logout'))
auth_bp.add_url_rule('/me', view_func=AuthMeAPI.as_view('me'))
auth_bp.add_url_rule('/profile', view_func=ProfileAPI.as_view('profile'))
auth_bp.add_url_rule('/password/change', view_func=PasswordChangeAPI.as_view('password_change'))
auth_bp.add_url_rule('/passphrase/set', view_func=PassphraseSetAPI.as_view('passphrase_set'))
auth_bp.add_url_rule('/passphrase/change', view_func=PassphraseChangeAPI.as_view('passphrase_change'))
auth_bp.add_url_rule('/dashboard', view_func=DashboardAPI.as_view('dashboard'))
auth_bp.add_url_rule('/image/upload', view_func=UserImageUploadAPI.as_view('user_image_upload'))
auth_bp.add_url_rule('/image/download', view_func=UserImageDownloadAPI.as_view('user_image_download'))