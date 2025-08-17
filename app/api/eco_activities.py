@"
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.family import FamilyMember
from app.models.eco_activity import EcoActivity, ActivityCategory
from app.schemas.eco_activity import (
    EcoActivityCreate, EcoActivityResponse, EcoActivityUpdate,
    EcoActivityListResponse, ActivityCategoryResponse, ActivityStats,
    ActivityFilter, ActivityVerification, ActivityRanking
)
from app.core.security import get_current_active_user
from app.core.azure_storage import upload_photo
from app.utils.helpers import calculate_points, calculate_co2_reduction, paginate

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=EcoActivityListResponse)
async def get_activities(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    family_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """エコ活動一覧を取得"""
    query = db.query(EcoActivity)
    
    # 家族フィルタ
    if family_id:
        # 家族メンバーかチェック
        membership = db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == current_user.id,
            FamilyMember.is_active == True
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="この家族の活動を見る権限がありません")
        query = query.filter(EcoActivity.family_id == family_id)
    else:
        # 自分の活動のみ
        query = query.filter(EcoActivity.user_id == current_user.id)
    
    # その他のフィルタ
    if category:
        query = query.filter(EcoActivity.category == category)
    if status:
        query = query.filter(EcoActivity.status == status)
    
    query = query.order_by(desc(EcoActivity.created_at))
    
    # ページネーション
    result = paginate(query, page, size)
    
    return EcoActivityListResponse(
        activities=result["items"],
        total=result["total"],
        page=page,
        size=size,
        pages=result["pages"]
    )

@router.post("/", response_model=EcoActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    activity_data: EcoActivityCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """新しいエコ活動を記録"""
    # 家族メンバーかチェック
    membership = db.query(FamilyMember).filter(
        FamilyMember.family_id == activity_data.family_id,
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_active == True
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="この家族に活動を記録する権限がありません")
    
    # ポイント計算
    points = calculate_points(
        activity_data.category,
        activity_data.co2_reduction
    )
    
    # 活動を作成
    db_activity = EcoActivity(
        title=activity_data.title,
        description=activity_data.description,
        category=activity_data.category,
        points=points,
        co2_reduction=activity_data.co2_reduction,
        water_saved=activity_data.water_saved,
        energy_saved=activity_data.energy_saved,
        location_name=activity_data.location_name,
        latitude=activity_data.latitude,
        longitude=activity_data.longitude,
        user_id=current_user.id,
        family_id=activity_data.family_id,
        activity_date=activity_data.activity_date,
        photo_filename=activity_data.photo_filename
    )
    
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    
    # ユーザー統計を更新
    current_user.total_points += points
    current_user.total_activities += 1
    current_user.total_co2_saved += activity_data.co2_reduction
    current_user.add_experience(points)
    
    db.commit()
    
    return db_activity

@router.get("/stats", response_model=ActivityStats)
async def get_activity_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """活動統計を取得"""
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())
    month_start = now.replace(day=1)
    
    # 基本統計
    activities_this_week = db.query(EcoActivity).filter(
        EcoActivity.user_id == current_user.id,
        EcoActivity.created_at >= week_start
    ).count()
    
    activities_this_month = db.query(EcoActivity).filter(
        EcoActivity.user_id == current_user.id,
        EcoActivity.created_at >= month_start
    ).count()
    
    return ActivityStats(
        total_activities=current_user.total_activities,
        total_points=current_user.total_points,
        total_co2_saved=current_user.total_co2_saved,
        total_water_saved=0,  # TODO: 実装
        total_energy_saved=0,  # TODO: 実装
        activities_this_week=activities_this_week,
        activities_this_month=activities_this_month,
        points_this_week=0,  # TODO: 実装
        points_this_month=0,  # TODO: 実装
        favorite_category=None,  # TODO: 実装
        streak_days=current_user.streak_days,
        average_points_per_activity=current_user.total_points / max(current_user.total_activities, 1),
        environmental_impact_score=current_user.total_co2_saved * 10
    )

@router.post("/{activity_id}/upload-photo")
async def upload_activity_photo(
    activity_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """活動写真をアップロード"""
    activity = db.query(EcoActivity).filter(
        EcoActivity.id == activity_id,
        EcoActivity.user_id == current_user.id
    ).first()
    
    if not activity:
        raise HTTPException(status_code=404, detail="活動が見つかりません")
    
    # 写真をアップロード
    upload_result = await upload_photo(file)
    
    # 活動に写真情報を保存
    activity.photo_url = upload_result["url"]
    activity.photo_filename = upload_result["filename"]
    
    db.commit()
    
    return {
        "message": "写真がアップロードされました",
        "photo_url": upload_result["url"]
    }
"@ | Out-File -FilePath app\api\eco_activities.py -Encoding UTF8