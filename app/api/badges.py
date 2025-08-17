@"
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.badge import Badge, UserBadge, Mission, UserMission
from app.schemas.badge import BadgeResponse, UserBadgeResponse, MissionResponse, UserMissionResponse
from app.core.security import get_current_active_user

router = APIRouter()

@router.get("/available", response_model=List[BadgeResponse])
async def get_available_badges(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """利用可能なバッジ一覧"""
    badges = db.query(Badge).filter(Badge.is_active == True).all()
    return badges

@router.get("/earned", response_model=List[UserBadgeResponse])
async def get_earned_badges(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """獲得済みバッジ一覧"""
    user_badges = db.query(UserBadge).filter(UserBadge.user_id == current_user.id).all()
    return user_badges

@router.get("/missions", response_model=List[MissionResponse])
async def get_available_missions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """利用可能なミッション一覧"""
    missions = db.query(Mission).filter(Mission.is_active == True).all()
    return missions

@router.get("/missions/mine", response_model=List[UserMissionResponse])
async def get_user_missions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """自分のミッション一覧"""
    user_missions = db.query(UserMission).filter(UserMission.user_id == current_user.id).all()
    return user_missions
"@ | Out-File -FilePath app\api\badges.py -Encoding UTF8