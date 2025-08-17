@"
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.eco_activity import EcoActivity
from app.core.security import get_current_active_user

router = APIRouter()

@router.get("/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """ダッシュボードサマリー情報"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    
    # 今日の活動
    today_activities = db.query(EcoActivity).filter(
        EcoActivity.user_id == current_user.id,
        EcoActivity.created_at >= today_start
    ).count()
    
    # 今週の活動
    week_activities = db.query(EcoActivity).filter(
        EcoActivity.user_id == current_user.id,
        EcoActivity.created_at >= week_start
    ).count()
    
    return {
        "user": {
            "username": current_user.username,
            "level": current_user.level,
            "total_points": current_user.total_points,
            "total_activities": current_user.total_activities,
            "streak_days": current_user.streak_days
        },
        "today": {
            "activities": today_activities,
            "points": 0  # TODO: 実装
        },
        "week": {
            "activities": week_activities,
            "points": 0  # TODO: 実装
        },
        "environmental_impact": {
            "total_co2_saved": current_user.total_co2_saved,
            "equivalent_trees": int(current_user.total_co2_saved / 0.02)  # 概算
        }
    }
"@ | Out-File -FilePath app\api\dashboard.py -Encoding UTF8