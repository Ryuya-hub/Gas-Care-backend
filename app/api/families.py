@"
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.family import Family, FamilyMember
from app.models.eco_activity import EcoActivity
from app.schemas.family import (
    FamilyCreate, FamilyResponse, FamilyUpdate, FamilyListResponse,
    FamilyInvite, FamilyInviteResponse, FamilyStats, FamilyRanking,
    FamilyMemberUpdate, FamilyJoinRequest, FamilyLeaveRequest,
    FamilyGoalUpdate, FamilySettings
)
from app.core.security import get_current_active_user
from app.utils.helpers import paginate
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[FamilyListResponse])
async def get_user_families(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    ユーザーが所属する家族一覧を取得
    """
    family_memberships = db.query(FamilyMember).filter(
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_active == True
    ).all()
    
    families = []
    for membership in family_memberships:
        family = membership.family
        families.append(FamilyListResponse(
            id=family.id,
            name=family.name,
            description=family.description,
            member_count=family.member_count,
            total_points=family.total_points,
            total_activities=family.total_activities,
            current_user_role=membership.role,
            invite_code=family.invite_code,
            created_at=family.created_at
        ))
    
    return families

@router.post("/", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
async def create_family(
    family_data: FamilyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    新しい家族グループを作成
    """
    # 招待コードを生成
    invite_code = Family.generate_invite_code()
    
    # 重複チェック
    while db.query(Family).filter(Family.invite_code == invite_code).first():
        invite_code = Family.generate_invite_code()
    
    # 家族作成
    db_family = Family(
        name=family_data.name,
        description=family_data.description,
        invite_code=invite_code,
        creator_id=current_user.id,
        is_public=family_data.is_public,
        family_goal=family_data.family_goal,
        monthly_target_points=family_data.monthly_target_points
    )
    
    db.add(db_family)
    db.commit()
    db.refresh(db_family)
    
    # 作成者をメンバーとして追加
    family_member = FamilyMember(
        family_id=db_family.id,
        user_id=current_user.id,
        role="creator"
    )
    
    db.add(family_member)
    db.commit()
    
    # レスポンス用データを構築
    return FamilyResponse(
        **family_data.dict(),
        id=db_family.id,
        invite_code=db_family.invite_code,
        creator_id=current_user.id,
        total_points=0,
        total_activities=0,
        total_co2_saved=0,
        member_count=1,
        members=[{
            "id": family_member.id,
            "user_id": current_user.id,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "avatar_url": current_user.avatar_url,
            "nickname": None,
            "role": "creator",
            "points_contributed": 0,
            "activities_count": 0,
            "is_active": True,
            "joined_at": family_member.joined_at,
            "last_activity_at": None
        }],
        created_at=db_family.created_at,
        current_user_role="creator",
        current_user_is_member=True
    )

@router.get("/{family_id}", response_model=FamilyResponse)
async def get_family(
    family_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    家族詳細情報を取得
    """
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="家族が見つかりません"
        )
    
    # メンバーシップ確認
    membership = db.query(FamilyMember).filter(
        FamilyMember.family_id == family_id,
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_active == True
    ).first()
    
    if not membership and not family.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この家族にアクセスする権限がありません"
        )
    
    # メンバー情報を取得
    members_data = []
    for member in family.members:
        if member.is_active:
            members_data.append({
                "id": member.id,
                "user_id": member.user_id,
                "username": member.user.username,
                "full_name": member.user.full_name,
                "avatar_url": member.user.avatar_url,
                "nickname": member.nickname,
                "role": member.role,
                "points_contributed": member.points_contributed,
                "activities_count": member.activities_count,
                "is_active": member.is_active,
                "joined_at": member.joined_at,
                "last_activity_at": member.last_activity_at
            })
    
    return FamilyResponse(
        id=family.id,
        name=family.name,
        description=family.description,
        is_public=family.is_public,
        family_goal=family.family_goal,
        monthly_target_points=family.monthly_target_points,
        invite_code=family.invite_code,
        creator_id=family.creator_id,
        total_points=family.total_points,
        total_activities=family.total_activities,
        total_co2_saved=family.total_co2_saved,
        member_count=family.member_count,
        members=members_data,
        created_at=family.created_at,
        updated_at=family.updated_at,
        current_user_role=membership.role if membership else None,
        current_user_is_member=membership is not None
    )

@router.put("/{family_id}", response_model=FamilyResponse)
async def update_family(
    family_id: int,
    family_update: FamilyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    家族情報を更新
    """
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="家族が見つかりません"
        )
    
    # 権限チェック（管理者またはクリエイター）
    membership = db.query(FamilyMember).filter(
        FamilyMember.family_id == family_id,
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_active == True
    ).first()
    
    if not membership or membership.role not in ["creator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="家族情報を更新する権限がありません"
        )
    
    # 更新データを適用
    update_data = family_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(family, field, value)
    
    db.commit()
    db.refresh(family)
    
    # 更新後の情報を返す
    return await get_family(family_id, current_user, db)

@router.post("/{family_id}/join", response_model=FamilyInviteResponse)
async def join_family_by_code(
    family_id: int,
    join_request: FamilyJoinRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    招待コードで家族に参加
    """
    family = db.query(Family).filter(
        and_(
            Family.id == family_id,
            Family.invite_code == join_request.invite_code
        )
    ).first()
    
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="無効な招待コードです"
        )
    
    # 既にメンバーかチェック
    existing_membership = db.query(FamilyMember).filter(
        FamilyMember.family_id == family_id,
        FamilyMember.user_id == current_user.id
    ).first()
    
    if existing_membership:
        if existing_membership.is_active:
            return FamilyInviteResponse(
                success=False,
                message="既にこの家族のメンバーです"
            )
        else:
            # 非アクティブメンバーシップを再アクティブ化
            existing_membership.is_active = True
            db.commit()
            return FamilyInviteResponse(
                success=True,
                message="家族に再参加しました"
            )
    
    # メンバー数制限チェック
    if family.member_count >= family.max_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="この家族は既に最大メンバー数に達しています"
        )
    
    # 新しいメンバーシップを作成
    family_member = FamilyMember(
        family_id=family_id,
        user_id=current_user.id,
        role="member"
    )
    
    db.add(family_member)
    
    # 家族のメンバー数を更新
    family.member_count += 1
    
    db.commit()
    
    return FamilyInviteResponse(
        success=True,
        message="家族に参加しました",
        family=await get_family(family_id, current_user, db)
    )

@router.post("/join-by-code", response_model=FamilyInviteResponse)
async def join_family_by_invite_code(
    invite_data: FamilyInvite,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    招待コードのみで家族に参加
    """
    family = db.query(Family).filter(
        Family.invite_code == invite_data.invite_code
    ).first()
    
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="無効な招待コードです"
        )
    
    return await join_family_by_code(
        family.id,
        FamilyJoinRequest(invite_code=invite_data.invite_code),
        current_user,
        db
    )

@router.delete("/{family_id}/leave")
async def leave_family(
    family_id: int,
    leave_request: FamilyLeaveRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    家族から脱退
    """
    membership = db.query(FamilyMember).filter(
        FamilyMember.family_id == family_id,
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_active == True
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="家族のメンバーではありません"
        )
    
    family = membership.family
    
    # クリエイターの場合は権限移譲が必要
    if membership.role == "creator":
        if not leave_request.transfer_to_user_id:
            # 他にメンバーがいるかチェック
            other_members = db.query(FamilyMember).filter(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id != current_user.id,
                FamilyMember.is_active == True
            ).count()
            
            if other_members > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="クリエイターとして脱退するには、他のメンバーに権限を移譲する必要があります"
                )
        else:
            # 権限移譲
            new_creator = db.query(FamilyMember).filter(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id == leave_request.transfer_to_user_id,
                FamilyMember.is_active == True
            ).first()
            
            if not new_creator:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="権限移譲先のユーザーが見つかりません"
                )
            
            new_creator.role = "creator"
            family.creator_id = new_creator.user_id
    
    # メンバーシップを非アクティブ化
    membership.is_active = False
    
    # 家族のメンバー数を更新
    family.member_count -= 1
    
    # 家族にメンバーがいなくなった場合は削除
    if family.member_count == 0:
        db.delete(family)
    
    db.commit()
    
    return {"message": "家族から脱退しました"}

@router.get("/{family_id}/stats", response_model=FamilyStats)
async def get_family_stats(
    family_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    家族の活動統計を取得
    """
    # メンバーシップ確認
    membership = db.query(FamilyMember).filter(
        FamilyMember.family_id == family_id,
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_active == True
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この家族の統計を見る権限がありません"
        )
    
    family = membership.family
    
    # 期間別統計
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())
    month_start = now.replace(day=1)
    
    activities_this_week = db.query(EcoActivity).filter(
        EcoActivity.family_id == family_id,
        EcoActivity.created_at >= week_start
    ).count()
    
    activities_this_month = db.query(EcoActivity).filter(
        EcoActivity.family_id == family_id,
        EcoActivity.created_at >= month_start
    ).count()
    
    points_this_week = db.query(func.sum(EcoActivity.points)).filter(
        EcoActivity.family_id == family_id,
        EcoActivity.created_at >= week_start
    ).scalar() or 0
    
    points_this_month = db.query(func.sum(EcoActivity.points)).filter(
        EcoActivity.family_id == family_id,
        EcoActivity.created_at >= month_start
    ).scalar() or 0
    
    # 最もアクティブなメンバー
    most_active_member = db.query(
        FamilyMember.user_id,
        func.count(EcoActivity.id).label('activity_count')
    ).join(
        EcoActivity, EcoActivity.user_id == FamilyMember.user_id
    ).filter(
        FamilyMember.family_id == family_id,
        FamilyMember.is_active == True,
        EcoActivity.created_at >= month_start
    ).group_by(
        FamilyMember.user_id
    ).order_by(desc('activity_count')).first()
    
    most_active_data = None
    if most_active_member:
        user = db.query(User).filter(User.id == most_active_member.user_id).first()
        most_active_data = {
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "activity_count": most_active_member.activity_count
        }
    
    # 人気カテゴリ
    favorite_category = db.query(
        EcoActivity.category,
        func.count(EcoActivity.id).label('count')
    ).filter(
        EcoActivity.family_id == family_id,
        EcoActivity.created_at >= month_start
    ).group_by(EcoActivity.category).order_by(desc('count')).first()
    
    # 月間目標進捗
    monthly_goal_progress = 0
    if family.monthly_target_points > 0:
        monthly_goal_progress = (points_this_month / family.monthly_target_points) * 100
    
    return FamilyStats(
        total_activities=family.total_activities,
        total_points=family.total_points,
        total_co2_saved=family.total_co2_saved,
        member_count=family.member_count,
        activities_this_week=activities_this_week,
        activities_this_month=activities_this_month,
        points_this_week=points_this_week,
        points_this_month=points_this_month,
        average_points_per_member=family.total_points / family.member_count if family.member_count > 0 else 0,
        most_active_member=most_active_data,
        favorite_activity_category=favorite_category[0] if favorite_category else None,
        monthly_goal_progress=min(monthly_goal_progress, 100)
    )

@router.put("/{family_id}/members/{member_id}", response_model=dict)
async def update_family_member(
    family_id: int,
    member_id: int,
    member_update: FamilyMemberUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    家族メンバーの情報を更新
    """
    # 権限チェック
    current_membership = db.query(FamilyMember).filter(
        FamilyMember.family_id == family_id,
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_active == True
    ).first()
    
    if not current_membership or current_membership.role not in ["creator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="メンバー情報を更新する権限がありません"
        )
    
    # 対象メンバーを取得
    target_member = db.query(FamilyMember).filter(
        FamilyMember.id == member_id,
        FamilyMember.family_id == family_id
    ).first()
    
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メンバーが見つかりません"
        )
    
    # 更新データを適用
    update_data = member_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(target_member, field, value)
    
    db.commit()
    
    return {"message": "メンバー情報が更新されました"}

@router.delete("/{family_id}/members/{member_id}")
async def remove_family_member(
    family_id: int,
    member_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    家族からメンバーを除名
    """
    # 権限チェック（クリエイターのみ）
    current_membership = db.query(FamilyMember).filter(
        FamilyMember.family_id == family_id,
        FamilyMember.user_id == current_user.id,
        FamilyMember.is_active == True
    ).first()
    
    if not current_membership or current_membership.role != "creator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="メンバーを除名する権限がありません"
        )
    
    # 対象メンバーを取得
    target_member = db.query(FamilyMember).filter(
        FamilyMember.id == member_id,
        FamilyMember.family_id == family_id,
        FamilyMember.is_active == True
    ).first()
    
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メンバーが見つかりません"
        )
    
    # 自分自身を除名することはできない
    if target_member.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="自分自身を除名することはできません"
        )
    
    # メンバーシップを非アクティブ化
    target_member.is_active = False
    
    # 家族のメンバー数を更新
    family = target_member.family
    family.member_count -= 1
    
    db.commit()
    
    return {"message": "メンバーが除名されました"}
"@ | Out-File -FilePath app\api\families.py -Encoding UTF8