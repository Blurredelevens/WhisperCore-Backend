import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, constr, field_validator

from .base import BaseResponse, TimestampMixin, UserBase


# Registration schemas
class UserCreate(UserBase):
    model_config = ConfigDict()

    email: EmailStr
    password: constr(min_length=8)
    first_name: str = ""
    last_name: str = ""
    passphrase: str | None = ""

    @field_validator("password")
    @classmethod
    def password_validation(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*()_+{}\[\]:;<>,.?~\\/-]", v):
            raise ValueError("Password must contain at least one special character")
        return v


# Login schemas
class LoginRequest(BaseModel):
    model_config = ConfigDict()

    email: EmailStr
    password: str


class PassphraseLoginRequest(BaseModel):
    model_config = ConfigDict()

    email: EmailStr
    passphrase: str


class CombinedLoginRequest(UserBase):
    model_config = ConfigDict()

    password: Optional[str] = None
    passphrase: Optional[str] = None

    @field_validator("password", "passphrase")
    @classmethod
    def at_least_one_auth_method(cls, v, info):
        if not v and not info.data.get("password") and not info.data.get("passphrase"):
            raise ValueError("Either password or passphrase must be provided")
        return v


# Response schemas
class UserResponse(UserBase, TimestampMixin):
    model_config = ConfigDict()

    id: int
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    full_name: str
    bio: Optional[str] = ""
    is_active: bool
    email_verified: bool
    last_login: Optional[str] = ""
    image_path: Optional[str] = ""
    has_passphrase: bool = False


class UserDetailResponse(UserResponse):
    model_config = ConfigDict()

    failed_login_attempts: int
    is_locked: bool
    has_passphrase: bool


class LoginResponse(BaseResponse):
    model_config = ConfigDict()

    access_token: str
    refresh_token: str
    user: UserResponse
    expires_in: int


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict()

    refresh_token: str


class TokenResponse(BaseResponse):
    model_config = ConfigDict()

    access_token: str
    expires_in: int


# Profile management schemas
class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict()

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v):
        if v is not None and v.strip() == "":
            raise ValueError("Name cannot be empty")
        return v


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict()

    current_password: str
    new_password: constr(min_length=8)


class PassphraseSetRequest(BaseModel):
    model_config = ConfigDict()

    current_password: str
    passphrase: constr(min_length=12)


class PassphraseChangeRequest(BaseModel):
    model_config = ConfigDict()

    current_passphrase: str
    new_passphrase: constr(min_length=12)


# Account settings schemas
class AccountSettingsResponse(BaseModel):
    model_config = ConfigDict()

    email_notifications: bool = True
    security_alerts: bool = True
    data_retention_days: int = 365


class AccountSettingsUpdateRequest(BaseModel):
    model_config = ConfigDict()

    email_notifications: Optional[bool] = None
    security_alerts: Optional[bool] = None
    data_retention_days: Optional[int] = None


# Dashboard schemas
class DashboardStats(BaseModel):
    model_config = ConfigDict()

    total_memories: int
    total_reflections: int
    weekly_reflections: int
    monthly_reflections: int
    recent_activity_count: int


class DashboardResponse(BaseResponse):
    model_config = ConfigDict()

    user: UserResponse
    stats: DashboardStats
    recent_memories: list
    upcoming_reflections: list


# Standard responses
class RegisterResponse(BaseModel):
    model_config = ConfigDict()

    message: str
    user: UserResponse
    access_token: str
    refresh_token: str
    expires_in: int


class LogoutResponse(BaseResponse):
    model_config = ConfigDict()
    pass


class SuccessResponse(BaseResponse):
    model_config = ConfigDict()
    pass
