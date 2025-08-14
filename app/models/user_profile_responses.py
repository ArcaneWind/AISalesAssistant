"""
用户画像响应模型
为API提供统一的响应格式
"""

from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.user_profile import UserProfile, MotivationType, BudgetRange, SkillLevel


class UserProfileResponse(BaseModel):
    """用户画像响应模型"""
    
    user_id: str
    session_id: str
    channel_source: str
    learning_goals: List[str]
    pain_points: List[str]
    motivation_type: Optional[str]
    urgency_level: Optional[int]
    budget_range: Optional[str]
    time_availability: Optional[str]
    learning_duration: Optional[str]
    current_skill_level: Optional[str]
    related_experience: List[str]
    learning_ability: Optional[str]
    communication_style: Optional[str]
    decision_pattern: Optional[str]
    response_speed: Optional[str]
    price_sensitivity: Optional[str]
    payment_preference: Optional[str]
    discount_response: Optional[str]
    field_confidence: Dict[str, float]
    update_count: int
    data_completeness: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @classmethod
    def from_profile(cls, profile: UserProfile) -> "UserProfileResponse":
        """从UserProfile创建响应对象"""
        return cls(
            user_id=profile.user_id,
            session_id=profile.session_id,
            channel_source=profile.channel_source,
            learning_goals=profile.learning_goals or [],
            pain_points=profile.pain_points or [],
            motivation_type=profile.motivation_type.value if profile.motivation_type else None,
            urgency_level=profile.urgency_level,
            budget_range=profile.budget_range.value if profile.budget_range else None,
            time_availability=profile.time_availability.value if profile.time_availability else None,
            learning_duration=profile.learning_duration.value if profile.learning_duration else None,
            current_skill_level=profile.current_skill_level.value if profile.current_skill_level else None,
            related_experience=profile.related_experience or [],
            learning_ability=profile.learning_ability.value if profile.learning_ability else None,
            communication_style=profile.communication_style.value if profile.communication_style else None,
            decision_pattern=profile.decision_pattern.value if profile.decision_pattern else None,
            response_speed=profile.response_speed.value if profile.response_speed else None,
            price_sensitivity=profile.price_sensitivity.value if profile.price_sensitivity else None,
            payment_preference=profile.payment_preference.value if profile.payment_preference else None,
            discount_response=profile.discount_response.value if profile.discount_response else None,
            field_confidence=profile.field_confidence,
            update_count=profile.update_count,
            data_completeness=profile.data_completeness,
            created_at=profile.created_at,
            updated_at=profile.updated_at
        )


class UserProfileSearchQuery(BaseModel):
    """用户画像搜索查询模型"""
    
    motivation_type: Optional[MotivationType] = None
    budget_range: Optional[BudgetRange] = None
    skill_level: Optional[SkillLevel] = None
    min_completeness: Optional[float] = Field(None, ge=0.0, le=1.0)
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None