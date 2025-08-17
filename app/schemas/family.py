@"
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class FamilyRole(str, Enum):
    CREATOR = "creator"
    ADMIN = "admin"
    MEMBER = "member"

class FamilyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_public: bool = False
    family_goal: Optional[str] = Field(None, max_length=500)
    monthly_target_points: int = Field(1000, ge=0)

class FamilyCreate(FamilyBase):
    pass

class FamilyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None
    family_goal: Optional[str] = Field(None, max_length=500)
    monthly_target_points: Optional[int] = Field(None, ge=0)

class FamilyMemberBase(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50)
    notification_enabled: bool = True

class FamilyMemberUpdate(FamilyMemberBase):
    role: Optional[FamilyRole] = None

class FamilyMemberResponse(BaseModel):
    id: int
    user_id: int
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    nickname: Optional[str] = None
    role: FamilyRole
    points_contributed: int
    activities_count: int
    is_active: bool
    joined_at: datetime
    last_activity_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class FamilyResponse(FamilyBase):
    id: int
    invite_code: str
    creator_id: int
    total_points: int
    total_activities: int
    total_co2_saved: int
    member_count: int
    members: List[FamilyMemberResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # 現在のユーザーの権限情報
    current_user_role: Optional[FamilyRole] = None
    current_user_is_member: bool = False
    
    class Config:
        from_attributes = True

class FamilyListResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    member_count: int
    total_points: int
    total_activities: int
    current_user_role: FamilyRole
    invite_code: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class FamilyInvite(BaseModel):
    invite_code: str = Field(..., min_length=6, max_length=50)

class FamilyInviteResponse(BaseModel):
    success: bool
    message: str
    family: Optional[FamilyResponse] = None

class FamilyStats(BaseModel):
    total_activities: int
    total_points: int
    total_co2_saved: float
    member_count: int
    activities_this_week: int
    activities_this_month: int
    points_this_week: int
    points_this_month: int
    average_points_per_member: float
    most_active_member: Optional[Dict[str, Any]] = None
    favorite_activity_category: Optional[str] = None
    monthly_goal_progress: float

class FamilyRanking(BaseModel):
    family: FamilyListResponse
    rank: int
    total_points: int
    total_activities: int
    member_count: int
    average_points_per_member: float

class FamilyActivitySummary(BaseModel):
    family_id: int
    family_name: str
    period: str  # "today", "week", "month"
    total_activities: int
    total_points: int
    co2_saved: float
    member_activities: List[Dict[str, Any]]
    top_categories: List[Dict[str, Any]]

class FamilyMemberInvite(BaseModel):
    email: str
    role: FamilyRole = FamilyRole.MEMBER
    nickname: Optional[str] = None
    message: Optional[str] = None

class FamilyJoinRequest(BaseModel):
    invite_code: str
    message: Optional[str] = None

class FamilyLeaveRequest(BaseModel):
    confirm: bool = True
    transfer_to_user_id: Optional[int] = None  # 管理者権限移譲先

class FamilySearch(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(10, ge=1, le=50)
    public_only: bool = True

class FamilyGoalUpdate(BaseModel):
    monthly_target_points: int = Field(..., ge=0)
    family_goal: Optional[str] = Field(None, max_length=500)

class FamilyChallenge(BaseModel):
    id: int
    title: str
    description: str
    target_points: int
    current_points: int
    start_date: datetime
    end_date: datetime
    is_active: bool
    participants: List[FamilyMemberResponse]
    
class FamilySettings(BaseModel):
    auto_approve_activities: bool = True
    require_photo_verification: bool = False
    allow_member_invites: bool = True
    public_leaderboard: bool = True
    activity_notifications: bool = True
    weekly_summary: bool = True
"@ | Out-File -FilePath app\schemas\family.py -Encoding UTF8