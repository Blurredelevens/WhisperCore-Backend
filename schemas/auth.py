from pydantic import BaseModel, constr, validator
from typing import Optional
from .base import UserBase, BaseResponse, TimestampMixin

# Registration schemas
class UserCreate(UserBase):
    password: constr(min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    passphrase: Optional[constr(min_length=12)] = None

# Login schemas
class LoginRequest(UserBase):
    password: str

class PassphraseLoginRequest(UserBase):
    passphrase: str

class CombinedLoginRequest(UserBase):
    password: Optional[str] = None
    passphrase: Optional[str] = None
    
    @validator('password', 'passphrase')
    def at_least_one_auth_method(cls, v, values):
        if not v and not values.get('password') and not values.get('passphrase'):
            raise ValueError('Either password or passphrase must be provided')
        return v

# Response schemas
class UserResponse(UserBase, TimestampMixin):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str
    bio: Optional[str] = None
    is_active: bool
    email_verified: bool
    last_login: Optional[str] = None
    image_path: Optional[str] = None
    

class UserDetailResponse(UserResponse):
    failed_login_attempts: int
    is_locked: bool
    has_passphrase: bool

class LoginResponse(BaseResponse):
    access_token: str
    refresh_token: str
    user: UserResponse
    expires_in: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseResponse):
    access_token: str
    expires_in: int

# Profile management schemas
class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: constr(min_length=8)

class PassphraseSetRequest(BaseModel):
    current_password: str
    passphrase: constr(min_length=12)

class PassphraseChangeRequest(BaseModel):
    current_passphrase: str
    new_passphrase: constr(min_length=12)

# Account settings schemas
class AccountSettingsResponse(BaseModel):
    email_notifications: bool = True
    security_alerts: bool = True
    data_retention_days: int = 365

class AccountSettingsUpdateRequest(BaseModel):
    email_notifications: Optional[bool] = None
    security_alerts: Optional[bool] = None
    data_retention_days: Optional[int] = None

# Dashboard schemas
class DashboardStats(BaseModel):
    total_memories: int
    total_reflections: int
    weekly_reflections: int
    monthly_reflections: int
    recent_activity_count: int

class DashboardResponse(BaseResponse):
    user: UserResponse
    stats: DashboardStats
    recent_memories: list
    upcoming_reflections: list

# Standard responses
class RegisterResponse(BaseModel):
    message: str
    user: UserResponse
    access_token: str
    refresh_token: str
    expires_in: int

class LogoutResponse(BaseResponse):
    pass

class SuccessResponse(BaseResponse):
    pass 