@"
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # ゲーミフィケーション
    total_points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    experience_points = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    
    # プロフィール情報
    bio = Column(Text, nullable=True)
    location = Column(String(100), nullable=True)
    birth_date = Column(DateTime, nullable=True)
    
    # 設定
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    is_public_profile = Column(Boolean, default=True)
    notification_enabled = Column(Boolean, default=True)
    
    # 統計情報
    total_co2_saved = Column(Float, default=0.0)
    total_activities = Column(Integer, default=0)
    
    # タイムスタンプ
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    created_families = relationship("Family", back_populates="creator")
    family_memberships = relationship("FamilyMember", back_populates="user")
    eco_activities = relationship("EcoActivity", foreign_keys="EcoActivity.user_id", back_populates="user")
    badges = relationship("UserBadge", back_populates="user")
    missions = relationship("UserMission", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def get_level_progress(self):
        """レベル進捗を計算"""
        current_level_xp = (self.level - 1) * 1000
        next_level_xp = self.level * 1000
        progress = (self.experience_points - current_level_xp) / (next_level_xp - current_level_xp)
        return min(max(progress, 0), 1)
    
    def add_experience(self, points: int):
        """経験値を追加してレベルアップをチェック"""
        self.experience_points += points
        new_level = (self.experience_points // 1000) + 1
        if new_level > self.level:
            self.level = new_level
            return True  # レベルアップした
        return False
    
    def get_family_role(self, family_id: int):
        """指定された家族での役割を取得"""
        for membership in self.family_memberships:
            if membership.family_id == family_id:
                return membership.role
        return None
"@ | Out-File -FilePath app\models\user.py -Encoding UTF8