@"
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import secrets
import string

class Family(Base):
    __tablename__ = "families"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    invite_code = Column(String(50), unique=True, index=True, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 家族設定
    is_public = Column(Boolean, default=False)
    max_members = Column(Integer, default=10)
    family_goal = Column(Text, nullable=True)
    monthly_target_points = Column(Integer, default=1000)
    
    # 統計情報
    total_points = Column(Integer, default=0)
    total_activities = Column(Integer, default=0)
    total_co2_saved = Column(Integer, default=0)
    member_count = Column(Integer, default=1)
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    creator = relationship("User", back_populates="created_families")
    members = relationship("FamilyMember", back_populates="family", cascade="all, delete-orphan")
    eco_activities = relationship("EcoActivity", back_populates="family")
    
    def __repr__(self):
        return f"<Family(id={self.id}, name='{self.name}', members={self.member_count})>"
    
    @classmethod
    def generate_invite_code(cls):
        """招待コードを生成"""
        length = 8
        characters = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    def get_member_role(self, user_id: int):
        """指定ユーザーの役割を取得"""
        for member in self.members:
            if member.user_id == user_id:
                return member.role
        return None
    
    def is_member(self, user_id: int):
        """ユーザーがメンバーかどうか確認"""
        return any(member.user_id == user_id for member in self.members)
    
    def is_admin(self, user_id: int):
        """ユーザーが管理者かどうか確認"""
        role = self.get_member_role(user_id)
        return role in ["admin", "creator"]

class FamilyMember(Base):
    __tablename__ = "family_members"
    
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="member")  # creator, admin, member
    nickname = Column(String(50), nullable=True)
    
    # 統計情報
    points_contributed = Column(Integer, default=0)
    activities_count = Column(Integer, default=0)
    
    # 設定
    is_active = Column(Boolean, default=True)
    notification_enabled = Column(Boolean, default=True)
    
    # タイムスタンプ
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    
    # リレーション
    family = relationship("Family", back_populates="members")
    user = relationship("User", back_populates="family_memberships")
    
    def __repr__(self):
        return f"<FamilyMember(family_id={self.family_id}, user_id={self.user_id}, role='{self.role}')>"
"@ | Out-File -FilePath app\models\family.py -Encoding UTF8