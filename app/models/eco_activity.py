@"
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class ActivityCategoryEnum(enum.Enum):
    RECYCLE = "リサイクル"
    ENERGY_SAVING = "節電"
    WATER_SAVING = "節水"
    TRANSPORTATION = "交通"
    WASTE_REDUCTION = "廃棄物削減"
    GREEN_PURCHASE = "グリーン購入"
    OTHER = "その他"

class ActivityStatusEnum(enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class EcoActivity(Base):
    __tablename__ = "eco_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(ActivityCategoryEnum), nullable=False)
    
    # ポイント・環境影響
    points = Column(Integer, default=0)
    co2_reduction = Column(Float, default=0.0)  # CO2削減量(kg)
    water_saved = Column(Float, default=0.0)    # 節水量(L)
    energy_saved = Column(Float, default=0.0)   # 節電量(kWh)
    
    # メディア
    photo_url = Column(String(500), nullable=True)
    photo_filename = Column(String(255), nullable=True)
    
    # 関連情報
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    
    # 検証システム
    status = Column(Enum(ActivityStatusEnum), default=ActivityStatusEnum.PENDING)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verification_note = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # 位置情報（オプション）
    location_name = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # タイムスタンプ
    activity_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    user = relationship("User", foreign_keys=[user_id], back_populates="eco_activities")
    family = relationship("Family", back_populates="eco_activities")
    verifier = relationship("User", foreign_keys=[verified_by])
    
    def __repr__(self):
        return f"<EcoActivity(id={self.id}, title='{self.title}', category='{self.category}', points={self.points})>"
    
    @property
    def is_verified(self):
        return self.status == ActivityStatusEnum.VERIFIED
    
    @property
    def is_pending(self):
        return self.status == ActivityStatusEnum.PENDING
    
    @property
    def total_environmental_impact(self):
        """総合的な環境影響スコア"""
        score = 0
        if self.co2_reduction:
            score += self.co2_reduction * 10  # CO2 1kg = 10点
        if self.water_saved:
            score += self.water_saved * 0.1   # 水 1L = 0.1点
        if self.energy_saved:
            score += self.energy_saved * 5    # 電力 1kWh = 5点
        return round(score, 2)

class ActivityCategory(Base):
    __tablename__ = "activity_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    color = Column(String(7), default="#22c55e")  # HEXカラー
    
    # ポイント設定
    base_points = Column(Integer, default=10)
    max_daily_points = Column(Integer, default=100)
    
    # 環境影響係数
    co2_factor = Column(Float, default=1.0)
    water_factor = Column(Float, default=1.0)
    energy_factor = Column(Float, default=1.0)
    
    # 設定
    is_active = Column(Boolean, default=True)
    requires_verification = Column(Boolean, default=False)
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<ActivityCategory(id={self.id}, name='{self.name}', base_points={self.base_points})>"
    
    def calculate_points(self, base_amount: float = 1.0):
        """活動量に基づいてポイントを計算"""
        return min(int(self.base_points * base_amount), self.max_daily_points)
"@ | Out-File -FilePath app\models\eco_activity.py -Encoding UTF8