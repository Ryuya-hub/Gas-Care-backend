@"
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class ActivityCategory(str, Enum):
    RECYCLE = "リサイクル"
    ENERGY_SAVING = "節電"
    WATER_SAVING = "節水"
    TRANSPORTATION = "交通"
    WASTE_REDUCTION = "廃棄物削減"
    GREEN_PURCHASE = "グリーン購入"
    OTHER = "その他"

class ActivityStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class EcoActivityBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: ActivityCategory
    co2_reduction: float = Field(0.0, ge=0)
    water_saved: float = Field(0.0, ge=0)
    energy_saved: float = Field(0.0, ge=0)
    location_name: Optional[str] = Field(None, max_length=100)
    activity_date: datetime

class EcoActivityCreate(EcoActivityBase):
    family_id: int = Field(..., gt=0)
    photo_filename: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class EcoActivityUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[ActivityCategory] = None
    co2_reduction: Optional[float] = Field(None, ge=0)
    water_saved: Optional[float] = Field(None, ge=0)
    energy_saved: Optional[float] = Field(None, ge=0)
    location_name: Optional[str] = Field(None, max_length=100)
    activity_date: Optional[datetime] = None

class EcoActivityResponse(EcoActivityBase):
    id: int
    points: int
    photo_url: Optional[str] = None
    photo_filename: Optional[str] = None
    user_id: int
    family_id: int
    status: ActivityStatus
    verified_by: Optional[int] = None
    verification_note: Optional[str] = None
    verified_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_environmental_impact: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # 関連情報
    username: Optional[str] = None
    user_full_name: Optional[str] = None
    user_avatar_url: Optional[str] = None
    family_name: Optional[str] = None
    verifier_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class EcoActivityListResponse(BaseModel):
    activities: List[EcoActivityResponse]
    total: int
    page: int
    size: int
    pages: int

class ActivityCategoryResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: str
    base_points: int
    max_daily_points: int
    co2_factor: float
    water_factor: float
    energy_factor: float
    is_active: bool
    requires_verification: bool
    
    class Config:
        from_attributes = True

class ActivityStats(BaseModel):
    total_activities: int
    total_points: int
    total_co2_saved: float
    total_water_saved: float
    total_energy_saved: float
    activities_this_week: int
    activities_this_month: int
    points_this_week: int
    points_this_month: int
    favorite_category: Optional[str] = None
    streak_days: int
    average_points_per_activity: float
    environmental_impact_score: float

class ActivityVerification(BaseModel):
    activity_id: int
    status: ActivityStatus
    verification_note: Optional[str] = Field(None, max_length=500)
    points_override: Optional[int] = Field(None, ge=0)

class ActivityFilter(BaseModel):
    user_id: Optional[int] = None
    family_id: Optional[int] = None
    category: Optional[ActivityCategory] = None
    status: Optional[ActivityStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    verified_only: bool = False
    with_photos_only: bool = False
    min_points: Optional[int] = None
    location: Optional[str] = None

class ActivitySearch(BaseModel):
    query: str = Field(..., min_length=1)
    category: Optional[ActivityCategory] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Field(20, ge=1, le=100)

class ActivityRanking(BaseModel):
    user: Dict[str, Any]
    total_activities: int
    total_points: int
    total_co2_saved: float
    rank: int
    period: str  # "daily", "weekly", "monthly", "all"

class ActivityTrend(BaseModel):
    date: datetime
    activities_count: int
    points_earned: int
    co2_saved: float
    category_breakdown: Dict[str, int]

class ActivitySuggestion(BaseModel):
    id: int
    title: str
    description: str
    category: ActivityCategory
    estimated_points: int
    estimated_co2_reduction: float
    difficulty_level: int
    required_items: List[str]
    instructions: List[str]
    tips: List[str]

class ActivityChallenge(BaseModel):
    id: int
    title: str
    description: str
    category: ActivityCategory
    target_value: int
    target_type: str  # "count", "points", "co2"
    duration_days: int
    reward_points: int
    reward_badge_id: Optional[int] = None
    start_date: datetime
    end_date: datetime
    participants_count: int
    is_participating: bool = False
    current_progress: int = 0

class BulkActivityCreate(BaseModel):
    activities: List[EcoActivityCreate] = Field(..., max_items=10)
    
    @validator('activities')
    def validate_activities(cls, v):
        if not v:
            raise ValueError('少なくとも1つの活動が必要です')
        return v

class ActivityImport(BaseModel):
    source: str  # "csv", "excel", "json"
    data: str  # Base64 encoded file data
    mapping: Dict[str, str]  # Column mapping
    validate_only: bool = False

class ActivityExport(BaseModel):
    format: str = "csv"  # "csv", "excel", "json", "pdf"
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    include_photos: bool = False
    filters: Optional[ActivityFilter] = None
"@ | Out-File -FilePath app\schemas\eco_activity.py -Encoding UTF8