"""
优惠券相关数据模型
"""

from decimal import Decimal
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class CouponType(str, Enum):
    """优惠券类型枚举"""
    PERCENTAGE = "percentage"  # 百分比折扣券
    FIXED_AMOUNT = "fixed_amount"  # 固定金额折扣券
    FREE_SHIPPING = "free_shipping"  # 免运费券（暂不使用）


class CouponStatus(str, Enum):
    """优惠券状态枚举"""
    ACTIVE = "active"  # 有效
    INACTIVE = "inactive"  # 无效
    EXPIRED = "expired"  # 已过期
    USED_UP = "used_up"  # 已用完


class Coupon(BaseModel):
    """优惠券基础模型"""
    
    coupon_id: str = Field(..., description="优惠券ID")
    coupon_code: str = Field(..., min_length=1, max_length=50, description="优惠券代码")
    coupon_name: str = Field(..., description="优惠券名称")
    coupon_type: CouponType = Field(..., description="优惠券类型")
    discount_value: Decimal = Field(..., ge=0, description="折扣值")
    min_order_amount: Decimal = Field(default=Decimal('0'), ge=0, description="最小订单金额")
    max_discount: Optional[Decimal] = Field(None, ge=0, description="最大折扣金额")
    valid_from: datetime = Field(..., description="有效开始时间")
    valid_to: datetime = Field(..., description="有效结束时间")
    usage_limit: Optional[int] = Field(None, ge=1, description="总使用次数限制")
    usage_limit_per_user: Optional[int] = Field(None, ge=1, description="单用户使用次数限制")
    used_count: int = Field(default=0, ge=0, description="已使用次数")
    applicable_courses: Optional[List[str]] = Field(None, description="适用课程ID列表")
    description: Optional[str] = Field(None, max_length=500, description="优惠券描述")
    status: CouponStatus = Field(default=CouponStatus.ACTIVE, description="优惠券状态")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @validator('valid_to')
    def validate_validity_period(cls, v, values):
        """验证有效期"""
        if 'valid_from' in values and v <= values['valid_from']:
            raise ValueError('结束时间必须晚于开始时间')
        return v
    
    @validator('discount_value')
    def validate_discount_value(cls, v, values):
        """验证折扣值"""
        if 'coupon_type' in values:
            if values['coupon_type'] == CouponType.PERCENTAGE and v > Decimal('1'):
                raise ValueError('百分比折扣值不能超过1')
            if values['coupon_type'] == CouponType.FIXED_AMOUNT and v <= 0:
                raise ValueError('固定金额折扣值必须大于0')
        return v
    
    def is_valid(self) -> bool:
        """检查优惠券是否有效"""
        now = datetime.now()
        return (
            self.status == CouponStatus.ACTIVE and
            self.valid_from <= now <= self.valid_to and
            (self.usage_limit is None or self.used_count < self.usage_limit)
        )
    
    def is_applicable_to_course(self, course_id: str) -> bool:
        """检查是否适用于指定课程"""
        if not self.applicable_courses:
            return True  # 无限制则适用于所有课程
        return course_id in self.applicable_courses
    
    def calculate_discount(self, order_amount: Decimal) -> Decimal:
        """计算具体折扣金额"""
        if order_amount < self.min_order_amount:
            return Decimal('0')
        
        if self.coupon_type == CouponType.PERCENTAGE:
            discount = order_amount * self.discount_value
        else:  # FIXED_AMOUNT
            discount = self.discount_value
        
        # 应用最大折扣限制
        if self.max_discount and discount > self.max_discount:
            discount = self.max_discount
        
        return min(discount, order_amount)  # 折扣不能超过订单金额


class CouponCreate(BaseModel):
    """创建优惠券模型"""
    
    coupon_code: str = Field(..., min_length=1, max_length=50)
    coupon_name: str = Field(...)
    coupon_type: CouponType = Field(...)
    discount_value: Decimal = Field(..., ge=0)
    min_order_amount: Decimal = Field(default=Decimal('0'), ge=0)
    max_discount: Optional[Decimal] = Field(None, ge=0)
    valid_from: datetime = Field(...)
    valid_to: datetime = Field(...)
    usage_limit: Optional[int] = Field(None, ge=1)
    usage_limit_per_user: Optional[int] = Field(None, ge=1)
    applicable_courses: Optional[List[str]] = None
    description: Optional[str] = Field(None, max_length=500)


class CouponUpdate(BaseModel):
    """更新优惠券模型"""
    
    coupon_name: Optional[str] = None
    discount_value: Optional[Decimal] = Field(None, ge=0)
    min_order_amount: Optional[Decimal] = Field(None, ge=0)
    max_discount: Optional[Decimal] = Field(None, ge=0)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    usage_limit: Optional[int] = Field(None, ge=1)
    usage_limit_per_user: Optional[int] = Field(None, ge=1)
    applicable_courses: Optional[List[str]] = None
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[CouponStatus] = None


class CouponValidation(BaseModel):
    """优惠券验证结果"""
    
    is_valid: bool = Field(..., description="是否有效")
    coupon: Optional[Coupon] = Field(None, description="优惠券信息")
    validation_errors: List[str] = Field(default_factory=list, description="验证错误")
    applicable_courses: List[str] = Field(default_factory=list, description="适用课程")
    estimated_discount: Optional[Decimal] = Field(None, description="预估折扣金额")
    min_order_required: Optional[Decimal] = Field(None, description="所需最小订单金额")


class CouponUsage(BaseModel):
    """优惠券使用记录"""
    
    usage_id: str = Field(..., description="使用记录ID")
    coupon_id: str = Field(..., description="优惠券ID")
    coupon_code: str = Field(..., description="优惠券代码")
    user_id: str = Field(..., description="使用用户ID")
    order_id: Optional[str] = Field(None, description="关联订单ID")
    course_ids: List[str] = Field(..., description="应用课程ID")
    original_amount: Decimal = Field(..., ge=0, description="原始金额")
    discount_amount: Decimal = Field(..., ge=0, description="折扣金额")
    final_amount: Decimal = Field(..., ge=0, description="最终金额")
    used_at: datetime = Field(default_factory=datetime.now, description="使用时间")
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class CouponApplication(BaseModel):
    """优惠券应用请求"""
    
    user_id: str = Field(..., description="用户ID")
    coupon_code: str = Field(..., description="优惠券代码")
    course_ids: List[str] = Field(..., min_items=1, description="应用课程ID")
    order_amount: Decimal = Field(..., ge=0, description="订单金额")


class CouponResponse(BaseModel):
    """优惠券响应模型"""
    
    coupon_id: str
    coupon_code: str
    coupon_name: str
    coupon_type: CouponType
    discount_value: Decimal
    min_order_amount: Decimal
    max_discount: Optional[Decimal]
    valid_from: datetime
    valid_to: datetime
    usage_limit: Optional[int]
    usage_limit_per_user: Optional[int]
    used_count: int
    applicable_courses: Optional[List[str]]
    description: Optional[str]
    status: CouponStatus
    is_valid: bool
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_coupon(cls, coupon: Coupon) -> "CouponResponse":
        """从Coupon模型创建响应对象"""
        return cls(
            coupon_id=coupon.coupon_id,
            coupon_code=coupon.coupon_code,
            coupon_name=coupon.coupon_name,
            coupon_type=coupon.coupon_type,
            discount_value=coupon.discount_value,
            min_order_amount=coupon.min_order_amount,
            max_discount=coupon.max_discount,
            valid_from=coupon.valid_from,
            valid_to=coupon.valid_to,
            usage_limit=coupon.usage_limit,
            usage_limit_per_user=coupon.usage_limit_per_user,
            used_count=coupon.used_count,
            applicable_courses=coupon.applicable_courses,
            description=coupon.description,
            status=coupon.status,
            is_valid=coupon.is_valid(),
            created_at=coupon.created_at,
            updated_at=coupon.updated_at
        )