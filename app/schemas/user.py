@"
from pydantic import BaseModel, EmailStr, validator, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=100)
    is_public_profile: bool = True
    notification_enabled: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('パスワードが一致しません')
        return v
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('ユーザー名は英数字、アンダースコア、ハイフンのみ使用可能です')
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=100)
    is_public_profile: Optional[bool] = None
    notification_enabled: Optional[bool] = None
    avatar_url: Optional[str] = None

class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_new_password: str
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('新しいパスワードが一致しません')
        return v

class UserResponse(UserBase):
    id: int
    avatar_url: Optional[str] = None
    total_points: int
    level: int
    experience_points: int
    streak_days: int
    total_co2_saved: float
    total_activities: int
    is_active: bool
    is_email_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserPublicResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    level: int
    total_points: int
    total_activities: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserStats(BaseModel):
    total_activities: int
    total_points: int
    total_co2_saved: float
    level: int
    experience_points: int
    streak_days: int
    activities_this_week: int
    activities_this_month: int
    points_this_week: int
    points_this_month: int
    favorite_category: Optional[str] = None
    level_progress: float
    rank_in_family: Optional[int] = None
    rank_globally: Optional[int] = None

class UserRanking(BaseModel):
    user: UserPublicResponse
    rank: int
    points: int
    activities_count: int
    co2_saved: float

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    scopes: List[str] = []

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False

class EmailVerificationRequest(BaseModel):
    email: EmailStr

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('パスワードが一致しません')
        return v

class UserActivitySummary(BaseModel):
    user_id: int
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    recent_activities: int
    total_points: int
    level: int
    last_activity: Optional[datetime]
    
class UserNotificationSettings(BaseModel):
    email_notifications: bool = True
    push_notifications: bool = True
    activity_reminders: bool = True
    family_updates: bool = True
    badge_notifications: bool = True
    mission_notifications: bool = True
    weekly_summary: bool = True
"@ | Out-File -FilePath app\schemas\user.py -Encoding UTF8