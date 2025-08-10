from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class MotivationType(str, Enum):
    """学习动机类型"""
    CAREER_ADVANCEMENT = "career_advancement"    # 职业发展
    SKILL_UPGRADE = "skill_upgrade"             # 技能提升  
    CAREER_CHANGE = "career_change"             # 转行
    PERSONAL_INTEREST = "personal_interest"     # 个人兴趣
    PROBLEM_SOLVING = "problem_solving"         # 解决问题


class SkillLevel(str, Enum):
    """技能水平"""
    BEGINNER = "beginner"       # 初学者
    INTERMEDIATE = "intermediate"   # 中级
    ADVANCED = "advanced"       # 高级
    EXPERT = "expert"          # 专家


class BudgetRange(str, Enum):
    """预算范围"""
    UNDER_1K = "<1000"         # 1000以下
    RANGE_1K_5K = "1000-5000"  # 1000-5000
    RANGE_5K_10K = "5000-10000" # 5000-10000
    OVER_10K = "10000+"        # 10000以上


class TimeAvailability(str, Enum):
    """时间可用性"""
    VERY_LIMITED = "very_limited"  # 非常有限
    LIMITED = "limited"            # 有限
    MODERATE = "moderate"          # 中等
    FLEXIBLE = "flexible"          # 灵活
    VERY_FLEXIBLE = "very_flexible" # 非常灵活


class LearningDuration(str, Enum):
    """学习周期"""
    SHORT_TERM = "short_term"      # 短期(1-3月)
    MEDIUM_TERM = "medium_term"    # 中期(3-6月)
    LONG_TERM = "long_term"        # 长期(6-12月)
    ONGOING = "ongoing"            # 持续学习


class LearningAbility(str, Enum):
    """学习能力评估"""
    SLOW = "slow"          # 学习较慢
    AVERAGE = "average"    # 平均水平
    FAST = "fast"          # 学习较快
    VERY_FAST = "very_fast" # 学习很快


class CommunicationStyle(str, Enum):
    """沟通风格"""
    DIRECT = "direct"              # 直接型
    ANALYTICAL = "analytical"      # 分析型
    EMOTIONAL = "emotional"        # 情感型
    DETAIL_ORIENTED = "detail_oriented" # 细节型
    BIG_PICTURE = "big_picture"    # 大局型


class DecisionPattern(str, Enum):
    """决策模式"""
    QUICK_DECISIVE = "quick_decisive"    # 快速决策
    CAREFUL_RESEARCH = "careful_research" # 仔细研究
    CONSENSUS_SEEKING = "consensus_seeking" # 寻求共识
    PROCRASTINATING = "procrastinating"  # 拖延决策
    IMPULSIVE = "impulsive"             # 冲动决策


class ResponseSpeed(str, Enum):
    """响应速度特征"""
    IMMEDIATE = "immediate"    # 立即回复
    QUICK = "quick"           # 快速回复
    NORMAL = "normal"         # 正常回复
    SLOW = "slow"            # 较慢回复
    VERY_SLOW = "very_slow"  # 很慢回复


class PriceSensitivity(str, Enum):
    """价格敏感度"""
    HIGH = "high"      # 高敏感度
    MEDIUM = "medium"  # 中等敏感度  
    LOW = "low"        # 低敏感度


class PaymentPreference(str, Enum):
    """支付偏好"""
    FULL_PAYMENT = "full_payment"      # 全款支付
    INSTALLMENT = "installment"        # 分期付款
    TRIAL_FIRST = "trial_first"        # 先试后买
    GROUP_DISCOUNT = "group_discount"  # 团购优惠


class DiscountResponse(str, Enum):
    """优惠反应"""
    HIGHLY_MOTIVATED = "highly_motivated"  # 高度激励
    MODERATELY_MOTIVATED = "moderately_motivated" # 中度激励
    SLIGHTLY_MOTIVATED = "slightly_motivated"     # 轻度激励
    NOT_MOTIVATED = "not_motivated"               # 不受激励


class UserProfile(BaseModel):
    """用户画像核心数据模型"""
    
    # 基础信息
    user_id: str = Field(..., description="用户唯一标识")
    session_id: str = Field(..., description="会话唯一标识")
    channel_source: str = Field(..., description="渠道来源")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    # 学习需求维度
    learning_goals: Optional[List[str]] = Field(default=[], description="学习目标")
    pain_points: Optional[List[str]] = Field(default=[], description="痛点问题")
    motivation_type: Optional[MotivationType] = Field(None, description="学习动机类型")
    urgency_level: Optional[int] = Field(None, ge=1, le=5, description="紧急程度 1-5")
    
    # 预算时间维度
    budget_range: Optional[BudgetRange] = Field(None, description="预算范围")
    time_availability: Optional[TimeAvailability] = Field(None, description="时间可用性")
    learning_duration: Optional[LearningDuration] = Field(None, description="期望学习周期")
    
    # 技能背景维度
    current_skill_level: Optional[SkillLevel] = Field(None, description="当前技能水平")
    related_experience: Optional[List[str]] = Field(default=[], description="相关经验")
    learning_ability: Optional[LearningAbility] = Field(None, description="学习能力评估")
    
    # 行为特征维度
    communication_style: Optional[CommunicationStyle] = Field(None, description="沟通风格")
    decision_pattern: Optional[DecisionPattern] = Field(None, description="决策模式")
    response_speed: Optional[ResponseSpeed] = Field(None, description="响应速度特征")
    
    # 价格敏感度维度
    price_sensitivity: Optional[PriceSensitivity] = Field(None, description="价格敏感度")
    payment_preference: Optional[PaymentPreference] = Field(None, description="支付偏好")
    discount_response: Optional[DiscountResponse] = Field(None, description="优惠反应")
    
    # 置信度和元信息
    field_confidence: Dict[str, float] = Field(default_factory=dict, description="各字段置信度")
    update_count: int = Field(default=0, description="更新次数")
    data_completeness: float = Field(default=0.0, ge=0.0, le=1.0, description="数据完整度")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @validator('field_confidence')
    def validate_confidence_scores(cls, v):
        """验证置信度分数"""
        for field, score in v.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"置信度分数必须在0.0-1.0之间: {field}={score}")
        return v

    def calculate_completeness(self) -> float:
        """计算数据完整度"""
        total_fields = 18  # 主要可填充字段数量
        filled_fields = 0
        
        # 检查各维度字段完整度
        if self.learning_goals:
            filled_fields += 1
        if self.pain_points:
            filled_fields += 1
        if self.motivation_type:
            filled_fields += 1
        if self.urgency_level is not None:
            filled_fields += 1
        if self.budget_range:
            filled_fields += 1
        if self.time_availability:
            filled_fields += 1
        if self.learning_duration:
            filled_fields += 1
        if self.current_skill_level:
            filled_fields += 1
        if self.related_experience:
            filled_fields += 1
        if self.learning_ability:
            filled_fields += 1
        if self.communication_style:
            filled_fields += 1
        if self.decision_pattern:
            filled_fields += 1
        if self.response_speed:
            filled_fields += 1
        if self.price_sensitivity:
            filled_fields += 1
        if self.payment_preference:
            filled_fields += 1
        if self.discount_response:
            filled_fields += 1
        
        completeness = filled_fields / total_fields
        return round(completeness, 2)

    def update_completeness(self):
        """更新数据完整度"""
        self.data_completeness = self.calculate_completeness()
        self.updated_at = datetime.now()

    def get_confidence_for_field(self, field_name: str) -> float:
        """获取指定字段的置信度"""
        return self.field_confidence.get(field_name, 0.0)

    def set_confidence_for_field(self, field_name: str, confidence: float):
        """设置指定字段的置信度"""
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"置信度必须在0.0-1.0之间: {confidence}")
        self.field_confidence[field_name] = confidence


class UserProfileUpdate(BaseModel):
    """用户画像更新模型"""
    
    # 可更新的字段
    learning_goals: Optional[List[str]] = None
    pain_points: Optional[List[str]] = None
    motivation_type: Optional[MotivationType] = None
    urgency_level: Optional[int] = Field(None, ge=1, le=5)
    budget_range: Optional[BudgetRange] = None
    time_availability: Optional[TimeAvailability] = None
    learning_duration: Optional[LearningDuration] = None
    current_skill_level: Optional[SkillLevel] = None
    related_experience: Optional[List[str]] = None
    learning_ability: Optional[LearningAbility] = None
    communication_style: Optional[CommunicationStyle] = None
    decision_pattern: Optional[DecisionPattern] = None
    response_speed: Optional[ResponseSpeed] = None
    price_sensitivity: Optional[PriceSensitivity] = None
    payment_preference: Optional[PaymentPreference] = None
    discount_response: Optional[DiscountResponse] = None
    
    # 置信度更新
    field_confidence: Optional[Dict[str, float]] = None
    
    class Config:
        use_enum_values = True


class UserProfileCreate(BaseModel):
    """用户画像创建模型"""
    
    user_id: str
    session_id: str
    channel_source: str
    
    # 可选的初始数据
    learning_goals: Optional[List[str]] = []
    pain_points: Optional[List[str]] = []
    motivation_type: Optional[MotivationType] = None
    urgency_level: Optional[int] = Field(None, ge=1, le=5)
    
    class Config:
        use_enum_values = True


class UserProfileResponse(BaseModel):
    """用户画像响应模型"""
    
    profile: UserProfile
    completeness_score: float
    last_updated: datetime
    confidence_summary: Dict[str, float]
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProfileValidationRules:
    """画像字段验证规则"""
    
    URGENCY_LEVELS = [1, 2, 3, 4, 5]
    SKILL_LEVELS = list(SkillLevel)
    BUDGET_RANGES = list(BudgetRange)
    PRICE_SENSITIVITY_LEVELS = list(PriceSensitivity)
    
    @classmethod
    def validate_urgency_level(cls, level: int) -> bool:
        """验证紧急程度"""
        return level in cls.URGENCY_LEVELS
    
    @classmethod
    def validate_skill_level(cls, level: str) -> bool:
        """验证技能水平"""
        return level in [sl.value for sl in cls.SKILL_LEVELS]
    
    @classmethod
    def validate_budget_range(cls, budget: str) -> bool:
        """验证预算范围"""
        return budget in [br.value for br in cls.BUDGET_RANGES]
    
    @classmethod
    def validate_confidence_score(cls, score: float) -> bool:
        """验证置信度分数"""
        return 0.0 <= score <= 1.0