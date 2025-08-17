@"
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class BadgeCategoryEnum(enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    SPECIAL = "special"
    SEASONAL = "seasonal"

class RequirementTypeEnum(enum.Enum):
    ACTIVITY_COUNT = "activity_count"
    POINTS_TOTAL = "points_total"
    DAYS_STREAK = "days_streak"
    CO2_REDUCTION = "co2_reduction"
    CATEGORY_SPECIFIC = "category_specific"
    FAMILY_ACTIVITIES = "family_activities"

class MissionTypeEnum(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SPECIAL = "special"
    CHALLENGE = "challenge"

class Badge(Base):
    __tablename__ = "badges"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(100), nullable=True)
    color = Column(String(7), default="#fbbf24")
    
    # カテゴリー・難易度
    category = Column(Enum(BadgeCategoryEnum), nullable=False)
    difficulty_level = Column(Integer, default=1)  # 1-5
    
    # 取得条件
    requirement_type = Column(Enum(RequirementTypeEnum), nullable=False)
    requirement_value = Column(Integer, nullable=False)
    requirement_data = Column(JSON, nullable=True)  # 追加条件データ
    
    # 報酬
    points_reward = Column(Integer, default=0)
    experience_reward = Column(Integer, default=0)
    
    # 設定
    is_active = Column(Boolean, default=True)
    is_hidden = Column(Boolean, default=False)  # 隠しバッジ
    max_earned_count = Column(Integer, default=1)  # 取得回数制限
    
    # 有効期間
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    user_badges = relationship("UserBadge", back_populates="badge")
    
    def __repr__(self):
        return f"<Badge(id={self.id}, name='{self.name}', category='{self.category}')>"
    
    def is_valid_now(self):
        """現在有効なバッジかどうか"""
        now = func.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True
    
    def check_requirement(self, user_stats: dict):
        """ユーザーの統計に基づいて取得条件をチェック"""
        if self.requirement_type == RequirementTypeEnum.ACTIVITY_COUNT:
            return user_stats.get('total_activities', 0) >= self.requirement_value
        elif self.requirement_type == RequirementTypeEnum.POINTS_TOTAL:
            return user_stats.get('total_points', 0) >= self.requirement_value
        elif self.requirement_type == RequirementTypeEnum.DAYS_STREAK:
            return user_stats.get('streak_days', 0) >= self.requirement_value
        elif self.requirement_type == RequirementTypeEnum.CO2_REDUCTION:
            return user_stats.get('total_co2_saved', 0) >= self.requirement_value
        return False

class UserBadge(Base):
    __tablename__ = "user_badges"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    
    # 取得情報
    earned_count = Column(Integer, default=1)
    progress_data = Column(JSON, nullable=True)  # 進捗データ
    
    # タイムスタンプ
    earned_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーション
    user = relationship("User", back_populates="badges")
    badge = relationship("Badge", back_populates="user_badges")
    
    def __repr__(self):
        return f"<UserBadge(user_id={self.user_id}, badge_id={self.badge_id}, earned_at='{self.earned_at}')>"

class Mission(Base):
    __tablename__ = "missions"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    short_description = Column(String(500), nullable=True)
    
    # ミッション設定
    mission_type = Column(Enum(MissionTypeEnum), nullable=False)
    category = Column(String(50), nullable=False)
    difficulty_level = Column(Integer, default=1)  # 1-5
    
    # 目標設定
    target_type = Column(String(50), nullable=False)  # activity_count, points, co2_reduction
    target_value = Column(Integer, nullable=False)
    target_data = Column(JSON, nullable=True)  # 追加目標データ
    
    # 報酬
    points_reward = Column(Integer, default=0)
    experience_reward = Column(Integer, default=0)
    badge_reward_id = Column(Integer, ForeignKey("badges.id"), nullable=True)
    
    # 期間設定
    duration_hours = Column(Integer, nullable=True)  # ミッション期間（時間）
    cooldown_hours = Column(Integer, default=24)     # 再実行までの待機時間
    
    # 条件
    prerequisites = Column(JSON, nullable=True)  # 前提条件
    max_participants = Column(Integer, nullable=True)
    
    # 有効期間
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    user_missions = relationship("UserMission", back_populates="mission")
    badge_reward = relationship("Badge")
    
    def __repr__(self):
        return f"<Mission(id={self.id}, title='{self.title}', type='{self.mission_type}')>"
    
    def is_available_for_user(self, user):
        """ユーザーがこのミッションを実行可能かチェック"""
        if not self.is_active:
            return False
        
        # 期間チェック
        now = func.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        
        # 前提条件チェック
        if self.prerequisites:
            # 実装: ユーザーの条件確認
            pass
        
        return True

class UserMission(Base):
    __tablename__ = "user_missions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False)
    
    # 進捗情報
    progress = Column(Integer, default=0)
    progress_data = Column(JSON, nullable=True)  # 詳細進捗データ
    
    # ステータス
    is_completed = Column(Boolean, default=False)
    is_claimed = Column(Boolean, default=False)  # 報酬受取済み
    
    # タイムスタンプ
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # リレーション
    user = relationship("User", back_populates="missions")
    mission = relationship("Mission", back_populates="user_missions")
    
    def __repr__(self):
        return f"<UserMission(user_id={self.user_id}, mission_id={self.mission_id}, progress={self.progress}/{self.mission.target_value})>"
    
    @property
    def progress_percentage(self):
        """進捗パーセンテージ"""
        if self.mission and self.mission.target_value > 0:
            return min(100, (self.progress / self.mission.target_value) * 100)
        return 0
    
    @property
    def is_expired(self):
        """期限切れかどうか"""
        if self.expires_at:
            return func.now() > self.expires_at
        return False
    
    def update_progress(self, increment: int = 1):
        """進捗を更新"""
        self.progress += increment
        if self.mission and self.progress >= self.mission.target_value:
            self.is_completed = True
            self.completed_at = func.now()
        return self.is_completed
"@ | Out-File -FilePath app\models\badge.py -Encoding UTF8