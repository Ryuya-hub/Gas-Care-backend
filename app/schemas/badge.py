@"
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class BadgeCategory(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    SPECIAL = "special"
    SEASONAL = "seasonal"

class RequirementType(str, Enum):
    ACTIVITY_COUNT = "activity_count"
    POINTS_TOTAL = "points_total"
    DAYS_STREAK = "days_streak"
    CO2_REDUCTION = "co2_reduction"
    CATEGORY_SPECIFIC = "category_specific"
    FAMILY_ACTIVITIES = "family_activities"

class MissionType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SPECIAL = "special"
    CHALLENGE = "challenge"

class BadgeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=1000)
    icon: Optional[str] = None
    color: str = "#fbbf24"
    category: BadgeCategory
    difficulty_level: int = Field(1, ge=1, le=5)
    requirement_type: RequirementType
    requirement_value: int = Field(..., gt=0)
    points_reward: int = Field(0, ge=0)
    experience_reward: int = Field(0, ge=0)
    is_hidden: bool = False
    max_earned_count: int = Field(1, gt=0)

class BadgeCreate(BadgeBase):
    requirement_data: Optional[Dict[str, Any]] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

class BadgeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    icon: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None
    is_hidden: Optional[bool] = None
    points_reward: Optional[int] = Field(None, ge=0)
    experience_reward: Optional[int] = Field(None, ge=0)

class BadgeResponse(BadgeBase):
    id: int
    requirement_data: Optional[Dict[str, Any]] = None
    is_active: bool
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # 統計情報
    earned_count: int = 0
    total_users_earned: int = 0
    
    class Config:
        from_attributes = True

class UserBadgeResponse(BaseModel):
    id: int
    badge_id: int
    earned_count: int
    earned_at: datetime
    badge: BadgeResponse
    progress_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class BadgeProgress(BaseModel):
    badge: BadgeResponse
    current_progress: int
    required_progress: int
    progress_percentage: float
    is_earned: bool
    can_earn: bool
    next_milestone: Optional[int] = None

class MissionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    short_description: Optional[str] = Field(None, max_length=500)
    mission_type: MissionType
    category: str = Field(..., min_length=1, max_length=50)
    difficulty_level: int = Field(1, ge=1, le=5)
    target_type: str = Field(..., min_length=1, max_length=50)
    target_value: int = Field(..., gt=0)
    points_reward: int = Field(0, ge=0)
    experience_reward: int = Field(0, ge=0)
    duration_hours: Optional[int] = Field(None, gt=0)
    cooldown_hours: int = Field(24, ge=0)

class MissionCreate(MissionBase):
    target_data: Optional[Dict[str, Any]] = None
    prerequisites: Optional[Dict[str, Any]] = None
    badge_reward_id: Optional[int] = None
    max_participants: Optional[int] = Field(None, gt=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class MissionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    short_description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    points_reward: Optional[int] = Field(None, ge=0)
    experience_reward: Optional[int] = Field(None, ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class MissionResponse(MissionBase):
    id: int
    target_data: Optional[Dict[str, Any]] = None
    prerequisites: Optional[Dict[str, Any]] = None
    badge_reward_id: Optional[int] = None
    max_participants: Optional[int] = None
    is_active: bool
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # 統計情報
    participants_count: int = 0
    completion_rate: float = 0.0
    
    # ユーザー固有情報
    user_progress: Optional[int] = None
    user_is_participating: bool = False
    user_can_participate: bool = True
    
    class Config:
        from_attributes = True

class UserMissionResponse(BaseModel):
    id: int
    mission_id: int
    progress: int
    progress_data: Optional[Dict[str, Any]] = None
    is_completed: bool
    is_claimed: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    claimed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    mission: MissionResponse
    progress_percentage: float
    is_expired: bool = False
    
    class Config:
        from_attributes = True

class MissionProgress(BaseModel):
    mission_id: int
    progress: int
    additional_data: Optional[Dict[str, Any]] = None

class MissionClaim(BaseModel):
    mission_id: int

class MissionParticipate(BaseModel):
    mission_id: int

class BadgeEarn(BaseModel):
    badge_id: int
    progress_data: Optional[Dict[str, Any]] = None

class BadgeStats(BaseModel):
    total_badges_available: int
    total_badges_earned: int
    badges_by_category: Dict[str, int]
    recent_badges: List[UserBadgeResponse]
    rarest_badge: Optional[BadgeResponse] = None
    next_available_badges: List[BadgeProgress]

class MissionStats(BaseModel):
    total_missions_available: int
    total_missions_completed: int
    total_missions_in_progress: int
    missions_by_type: Dict[str, int]
    completion_rate: float
    total_rewards_earned: int
    current_streak: int
    best_streak: int

class LeaderboardEntry(BaseModel):
    user_id: int
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    score: int
    rank: int
    badges_count: int
    missions_completed: int

class BadgeLeaderboard(BaseModel):
    period: str  # "daily", "weekly", "monthly", "all"
    entries: List[LeaderboardEntry]
    user_rank: Optional[int] = None
    total_participants: int

class SeasonalEvent(BaseModel):
    id: int
    name: str
    description: str
    start_date: datetime
    end_date: datetime
    is_active: bool
    special_badges: List[BadgeResponse]
    special_missions: List[MissionResponse]
    participation_count: int
    rewards: Dict[str, Any]
"@ | Out-File -FilePath app\schemas\badge.py -Encoding UTF8