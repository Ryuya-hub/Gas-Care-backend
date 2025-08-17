@"
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
import logging

from app.database import get_db
from app.models.user import User
from app.models.eco_activity import EcoActivity
from app.models.badge import UserBadge, Badge
from app.schemas.user import (
    UserResponse, UserUpdate, UserPasswordUpdate, UserPublicResponse,
    UserStats, UserRanking, UserActivitySummary, UserNotificationSettings
)
from app.schemas.badge import UserBadgeResponse
from app.core.security import get_current_active_user, SecurityUtils
from app.utils.helpers import calculate_level_progress, paginate, time_ago_jp
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: User = Depends(get_current_active_user)):
    """
    現在のユーザー情報を取得
    """
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    現在のユーザー情報を更新
    """
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.put("/me/password")
async def update_password(
    password_update: UserPasswordUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    パスワードを更新
    """
    # 現在のパスワード確認
    if not SecurityUtils.verify_password(
        password_update.current_password, 
        current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="現在のパスワードが正しくありません"
        )
    
    # 新しいパスワードの強度チェック
    password_validation = SecurityUtils.validate_password_strength(
        password_update.new_password
    )
    if not password_validation["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=", ".join(password_validation["issues"])
        )
    
    # パスワード更新
    current_user.hashed_password = SecurityUtils.get_password_hash(
        password_update.new_password
    )
    
    db.commit()
    
    return {"message": "パスワードが更新されました"}

@router.get("/me/stats", response_model=UserStats)
async def get_user_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    ユーザーの活動統計を取得
    """
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())
    month_start = now.replace(day=1)
    
    # 基本統計
    total_activities = db.query(EcoActivity).filter(
        EcoActivity.user_id == current_user.id
    ).count()
    
    activities_this_week = db.query(EcoActivity).filter(
        EcoActivity.user_id == current_user.id,
        EcoActivity.created_at >= week_start
    ).count()
    
    activities_this_month = db.query(EcoActivity).filter(
        EcoActivity.user_id == current_user.id,
        EcoActivity.created_at >= month_start
    ).count()
    
    # ポイント統計
    points_this_week = db.query(func.sum(EcoActivity.points)).filter(
        EcoActivity.user_id == current_user.id,
        EcoActivity.created_at >= week_start
    ).scalar() or 0
    
    points_this_month = db.query(func.sum(EcoActivity.points)).filter(
        EcoActivity.user_id == current_user.id,
        EcoActivity.created_at >= month_start
    ).scalar() or 0
    
    # 好きなカテゴリ
    favorite_category_result = db.query(
        EcoActivity.category,
        func.count(EcoActivity.id).label('count')
    ).filter(
        EcoActivity.user_id == current_user.id
    ).group_by(EcoActivity.category).order_by(desc('count')).first()
    
    favorite_category = favorite_category_result[0] if favorite_category_result else None
    
    # レベル進捗
    level_progress_data = calculate_level_progress(current_user.experience_points)
    
    # ランキング（簡易版）
    rank_query = db.query(User).filter(
        User.total_points > current_user.total_points
    ).count()
    rank_globally = rank_query + 1
    
    return UserStats(
        total_activities=current_user.total_activities,
        total_points=current_user.total_points,
        total_co2_saved=current_user.total_co2_saved,
        level=current_user.level,
        experience_points=current_user.experience_points,
        streak_days=current_user.streak_days,
        activities_this_week=activities_this_week,
        activities_this_month=activities_this_month,
        points_this_week=points_this_week,
        points_this_month=points_this_month,
        favorite_category=favorite_category,
        level_progress=level_progress_data["progress_percentage"] / 100,
        rank_globally=rank_globally
    )

@router.get("/me/badges", response_model=List[UserBadgeResponse])
async def get_user_badges(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    ユーザーの獲得バッジ一覧
    """
    user_badges = db.query(UserBadge).filter(
        UserBadge.user_id == current_user.id
    ).order_by(desc(UserBadge.earned_at)).all()
    
    return user_badges

@router.get("/me/activity-summary", response_model=UserActivitySummary)
async def get_user_activity_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    ユーザーの活動サマリー
    """
    from datetime import datetime, timedelta
    
    # 最近の活動数
    recent_activities = db.query(EcoActivity).filter(
        EcoActivity.user_id == current_user.id,
        EcoActivity.created_at >= datetime.utcnow() - timedelta(days=7)
    ).count()
    
    # 最後の活動日時
    last_activity = db.query(EcoActivity).filter(
        EcoActivity.user_id == current_user.id
    ).order_by(desc(EcoActivity.created_at)).first()
    
    return UserActivitySummary(
        user_id=current_user.id,
        username=current_user.username,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        recent_activities=recent_activities,
        total_points=current_user.total_points,
        level=current_user.level,
        last_activity=last_activity.created_at if last_activity else None
    )

@router.get("/{user_id}", response_model=UserPublicResponse)
async def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    指定されたユーザーの公開情報を取得
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません"
        )
    
    # 非公開プロフィールの場合は制限された情報のみ
    if not user.is_public_profile and user.id != current_user.id:
        return UserPublicResponse(
            id=user.id,
            username=user.username,
            full_name=None,
            avatar_url=None,
            bio="このユーザーは非公開プロフィールです",
            location=None,
            level=user.level,
            total_points=0,
            total_activities=0,
            created_at=user.created_at
        )
    
    return UserPublicResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        location=user.location,
        level=user.level,
        total_points=user.total_points,
        total_activities=user.total_activities,
        created_at=user.created_at
    )

@router.get("/", response_model=List[UserPublicResponse])
async def search_users(
    q: Optional[str] = Query(None, description="検索クエリ"),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    ユーザー検索
    """
    query = db.query(User).filter(
        User.is_active == True,
        User.is_public_profile == True
    )
    
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            (User.username.ilike(search_term)) |
            (User.full_name.ilike(search_term))
        )
    
    query = query.order_by(desc(User.total_points))
    users = query.offset(skip).limit(limit).all()
    
    return [
        UserPublicResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            bio=user.bio,
            location=user.location,
            level=user.level,
            total_points=user.total_points,
            total_activities=user.total_activities,
            created_at=user.created_at
        )
        for user in users
    ]

@router.get("/ranking/points", response_model=List[UserRanking])
async def get_points_ranking(
    period: str = Query("all", regex="^(daily|weekly|monthly|all)$"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    ポイントランキング取得
    """
    from datetime import datetime, timedelta
    
    query = db.query(User).filter(User.is_active == True)
    
    # 期間フィルタ
    if period == "daily":
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0)
        # TODO: 日別ポイント統計テーブルから取得
    elif period == "weekly":
        start_date = datetime.utcnow() - timedelta(days=7)
        # TODO: 週別ポイント統計テーブルから取得
    elif period == "monthly":
        start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        # TODO: 月別ポイント統計テーブルから取得
    
    # 現在は総合ランキングのみ実装
    users = query.order_by(desc(User.total_points)).limit(limit).all()
    
    ranking = []
    for rank, user in enumerate(users, 1):
        ranking.append(UserRanking(
            user=UserPublicResponse(
                id=user.id,
                username=user.username,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                bio=user.bio,
                location=user.location,
                level=user.level,
                total_points=user.total_points,
                total_activities=user.total_activities,
                created_at=user.created_at
            ),
            rank=rank,
            points=user.total_points,
            activities_count=user.total_activities,
            co2_saved=user.total_co2_saved
        ))
    
    return ranking

@router.get("/me/notifications/settings", response_model=UserNotificationSettings)
async def get_notification_settings(
    current_user: User = Depends(get_current_active_user)
):
    """
    通知設定を取得
    """
    return UserNotificationSettings(
        email_notifications=current_user.notification_enabled,
        push_notifications=current_user.notification_enabled,
        activity_reminders=current_user.notification_enabled,
        family_updates=current_user.notification_enabled,
        badge_notifications=current_user.notification_enabled,
        mission_notifications=current_user.notification_enabled,
        weekly_summary=current_user.notification_enabled
    )

@router.put("/me/notifications/settings", response_model=UserNotificationSettings)
async def update_notification_settings(
    settings_update: UserNotificationSettings,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    通知設定を更新
    """
    # TODO: 詳細な通知設定テーブルの実装
    # 現在は基本的な notification_enabled のみ更新
    current_user.notification_enabled = settings_update.email_notifications
    
    db.commit()
    
    return settings_update

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    アカウント削除
    """
    # ソフト削除（is_active = False）
    current_user.is_active = False
    db.commit()
    
    # TODO: 関連データの処理
    # - エコ活動データの匿名化
    # - 家族から脱退
    # - アップロードファイルの削除
    
    return None

@router.post("/me/deactivate")
async def deactivate_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    アカウント一時停止
    """
    current_user.is_active = False
    db.commit()
    
    return {"message": "アカウントが一時停止されました"}

@router.post("/me/reactivate")
async def reactivate_account(
    current_user: User = Depends(get_current_user),  # is_active=Falseでも取得
    db: Session = Depends(get_db)
):
    """
    アカウント再開
    """
    current_user.is_active = True
    db.commit()
    
    return {"message": "アカウントが再開されました"}
"@ | Out-File -FilePath app\api\users.py -Encoding UTF8