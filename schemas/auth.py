from pydantic import BaseModel, constr, validator, EmailStr
from typing import Optional
from datetime import datetime
from .base import UserBase, BaseResponse, TimestampMixin
import re

# Registration schemas
class UserCreate(UserBase):
    email: EmailStr
    password: constr(min_length=8)
    first_name: str = ""
    last_name: str = ""
    passphrase: str | None = ""

    @validator('password')
    def password_validation(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)')
        return v

# Login schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PassphraseLoginRequest(BaseModel):
    email: EmailStr
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
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    full_name: str
    bio: Optional[str] = ""
    is_active: bool
    email_verified: bool
    last_login: Optional[str] = ""
    image_path: Optional[str] = ""
    

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