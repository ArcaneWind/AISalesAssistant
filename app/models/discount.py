"""
折扣相关数据模型 - 简化版，Agent通过提示词自行判断
"""

from decimal import Decimal
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class DiscountType(str, Enum):
    """折扣类型枚举"""
    PERCENTAGE = "percentage"  # 百分比折扣
    FIXED_AMOUNT = "fixed_amount"  # 固定金额折扣


class DiscountOptionType(str, Enum):
    """折扣选项类型枚举"""
    NEW_USER = "new_user"  # 新用户折扣
    URGENT_CONVERSION = "urgent_conversion"  # 紧急转化折扣
    RETURNING_USER = "returning_user"  # 老用户回购折扣
    BULK_PURCHASE = "bulk_purchase"  # 批量购买折扣
    VIP_DISCOUNT = "vip_discount"  # VIP专享折扣


class DiscountOption(BaseModel):
    """折扣选项配置 - 静态配置，供Agent选择"""
    
    option_type: DiscountOptionType = Field(..., description="选项类型")
    option_name: str = Field(..., description="选项名称")
    discount_type: DiscountType = Field(..., description="折扣计算类型")
    min_discount: float = Field(..., ge=0, le=1, description="最小折扣")
    max_discount: float = Field(..., ge=0, le=1, description="最大折扣")
    description: str = Field(..., description="选项描述")
    is_active: bool = Field(default=True, description="是否启用")
    
    @validator('max_discount')
    def validate_discount_range(cls, v, values):
        """验证折扣范围"""
        if 'min_discount' in values and v < values['min_discount']:
            raise ValueError('最大折扣不能小于最小折扣')
        return v


class AppliedDiscount(BaseModel):
    """应用的折扣记录"""
    
    discount_id: str = Field(..., description="折扣记录ID")
    user_id: str = Field(..., description="用户ID")
    option_type: DiscountOptionType = Field(..., description="折扣选项类型")
    discount_type: DiscountType = Field(..., description="折扣计算类型")
    discount_value: float = Field(..., ge=0, le=1, description="Agent选择的具体折扣值")
    applicable_course_ids: List[str] = Field(..., description="适用课程ID列表")
    original_amount: Decimal = Field(..., ge=0, description="原始金额")
    discount_amount: Decimal = Field(..., ge=0, description="折扣金额")
    final_amount: Decimal = Field(..., ge=0, description="最终金额")
    agent_reasoning: Optional[str] = Field(None, description="Agent决策理由")
    valid_until: Optional[datetime] = Field(None, description="有效期至")
    is_used: bool = Field(default=False, description="是否已使用")
    used_at: Optional[datetime] = Field(None, description="使用时间")
    created_at: datetime = Field(default_factory=datetime.now)
    
    @validator('final_amount')
    def validate_final_amount(cls, v, values):
        """验证最终金额"""
        if 'original_amount' in values and 'discount_amount' in values:
            expected = values['original_amount'] - values['discount_amount']
            if abs(v - expected) > Decimal('0.01'):
                raise ValueError('最终金额计算错误')
        return v
    
    def mark_as_used(self):
        """标记为已使用"""
        self.is_used = True
        self.used_at = datetime.now()


class DiscountApplication(BaseModel):
    """Agent应用折扣的请求模型"""
    
    user_id: str = Field(..., description="用户ID")
    option_type: DiscountOptionType = Field(..., description="Agent选择的折扣类型")
    discount_value: float = Field(..., ge=0, le=1, description="Agent决定的具体折扣值")
    course_ids: List[str] = Field(..., min_items=1, description="应用的课程ID列表")
    agent_reasoning: Optional[str] = Field(None, description="Agent的决策理由")
    valid_hours: Optional[int] = Field(default=24, ge=1, le=168, description="有效时长(小时)")
    
    @validator('discount_value')
    def validate_discount_value(cls, v):
        """验证折扣值范围"""
        if v < 0 or v > 1:
            raise ValueError('折扣值必须在0-1之间')
        return v


class DiscountValidationResult(BaseModel):
    """折扣验证结果"""
    
    is_valid: bool = Field(..., description="是否有效")
    validation_errors: List[str] = Field(default_factory=list, description="验证错误")
    estimated_discount_amount: Optional[Decimal] = Field(None, description="预估折扣金额")
    
    
class DiscountConfig(BaseModel):
    """折扣配置模型 - 用于存储系统配置"""
    
    config_id: str = Field(..., description="配置ID")
    options: Dict[str, DiscountOption] = Field(..., description="折扣选项配置")
    global_settings: Dict[str, Any] = Field(default_factory=dict, description="全局设置")
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def get_option(self, option_type: DiscountOptionType) -> Optional[DiscountOption]:
        """获取指定类型的折扣选项"""
        return self.options.get(option_type.value)
    
    def is_discount_in_range(self, option_type: DiscountOptionType, discount_value: float) -> bool:
        """检查折扣值是否在允许范围内"""
        option = self.get_option(option_type)
        if not option:
            return False
        return option.min_discount <= discount_value <= option.max_discount