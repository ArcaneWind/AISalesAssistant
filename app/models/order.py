"""
订单相关数据模型
"""

from decimal import Decimal
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING = "pending"  # 待处理
    CONFIRMED = "confirmed"  # 已确认
    PAID = "paid"  # 已支付
    CANCELLED = "cancelled"  # 已取消
    REFUNDED = "refunded"  # 已退款


class PaymentStatus(str, Enum):
    """支付状态枚举"""
    PENDING = "pending"  # 待支付
    PAID = "paid"  # 已支付
    FAILED = "failed"  # 支付失败
    REFUNDED = "refunded"  # 已退款
    PARTIAL_REFUNDED = "partial_refunded"  # 部分退款


class OrderItem(BaseModel):
    """订单项目模型"""
    
    item_id: str = Field(..., description="项目ID")
    course_id: str = Field(..., description="课程ID")
    course_name: str = Field(..., description="课程名称")
    original_price: Decimal = Field(..., ge=0, description="课程原价")
    discounted_price: Decimal = Field(..., ge=0, description="折后价格")
    quantity: int = Field(default=1, ge=1, description="数量")
    
    @validator('discounted_price')
    def validate_discounted_price(cls, v, values):
        """验证折后价格不能超过原价"""
        if 'original_price' in values and v > values['original_price']:
            raise ValueError('折后价格不能超过原价')
        return v
    
    @property
    def subtotal_original(self) -> Decimal:
        """原价小计"""
        return self.original_price * self.quantity
    
    @property
    def subtotal_discounted(self) -> Decimal:
        """折后价小计"""
        return self.discounted_price * self.quantity
    
    @property
    def discount_amount(self) -> Decimal:
        """折扣金额"""
        return self.subtotal_original - self.subtotal_discounted


class Order(BaseModel):
    """订单基础模型"""
    
    order_id: str = Field(..., description="订单ID")
    user_id: str = Field(..., description="用户ID")
    order_items: List[OrderItem] = Field(..., min_items=1, description="订单项目列表")
    original_amount: Decimal = Field(..., ge=0, description="原始总金额")
    discount_amount: Decimal = Field(default=Decimal('0'), ge=0, description="折扣金额")
    coupon_discount: Decimal = Field(default=Decimal('0'), ge=0, description="优惠券折扣")
    final_amount: Decimal = Field(..., ge=0, description="最终金额")
    applied_discount_id: Optional[str] = Field(None, description="应用的折扣ID")
    applied_coupon_code: Optional[str] = Field(None, description="使用的优惠券代码")
    order_status: OrderStatus = Field(default=OrderStatus.PENDING, description="订单状态")
    payment_status: PaymentStatus = Field(default=PaymentStatus.PENDING, description="支付状态")
    payment_method: Optional[str] = Field(None, description="支付方式")
    notes: Optional[str] = Field(None, max_length=1000, description="订单备注")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    paid_at: Optional[datetime] = Field(None, description="支付时间")
    
    @validator('final_amount')
    def validate_final_amount(cls, v, values):
        """验证最终金额计算"""
        if all(k in values for k in ['original_amount', 'discount_amount', 'coupon_discount']):
            expected = values['original_amount'] - values['discount_amount'] - values['coupon_discount']
            if abs(v - expected) > Decimal('0.01'):  # 允许1分钱误差
                raise ValueError('最终金额计算错误')
        return v
    
    @validator('order_items')
    def validate_order_items(cls, v):
        """验证订单项目不能为空"""
        if not v:
            raise ValueError('订单必须包含至少一个项目')
        return v
    
    @property
    def total_courses(self) -> int:
        """订单中的课程总数"""
        return sum(item.quantity for item in self.order_items)
    
    @property
    def course_ids(self) -> List[str]:
        """获取所有课程ID"""
        return [item.course_id for item in self.order_items]
    
    @property
    def total_discount(self) -> Decimal:
        """总折扣金额"""
        return self.discount_amount + self.coupon_discount
    
    @property
    def discount_percentage(self) -> float:
        """总折扣百分比"""
        if self.original_amount == 0:
            return 0.0
        return float(self.total_discount / self.original_amount)
    
    def is_paid(self) -> bool:
        """检查是否已支付"""
        return self.payment_status == PaymentStatus.PAID
    
    def is_cancelled(self) -> bool:
        """检查是否已取消"""
        return self.order_status == OrderStatus.CANCELLED
    
    def mark_as_paid(self, payment_method: str = None):
        """标记为已支付"""
        self.payment_status = PaymentStatus.PAID
        self.order_status = OrderStatus.PAID
        self.paid_at = datetime.now()
        self.updated_at = datetime.now()
        if payment_method:
            self.payment_method = payment_method


class OrderCreate(BaseModel):
    """创建订单请求模型"""
    
    user_id: str = Field(..., description="用户ID")
    course_ids: List[str] = Field(..., min_items=1, description="课程ID列表")
    applied_discount_id: Optional[str] = Field(None, description="应用的折扣ID")
    applied_coupon_code: Optional[str] = Field(None, description="使用的优惠券代码")
    notes: Optional[str] = Field(None, max_length=1000, description="订单备注")


class OrderUpdate(BaseModel):
    """更新订单模型"""
    
    order_status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)


class PriceCalculation(BaseModel):
    """价格计算结果模型"""
    
    course_items: List[OrderItem] = Field(..., description="课程项目详情")
    original_amount: Decimal = Field(..., ge=0, description="原始总金额")
    discount_amount: Decimal = Field(default=Decimal('0'), ge=0, description="折扣金额")
    coupon_discount: Decimal = Field(default=Decimal('0'), ge=0, description="优惠券折扣")
    final_amount: Decimal = Field(..., ge=0, description="最终金额")
    discount_details: Dict[str, Any] = Field(default_factory=dict, description="折扣详情")
    coupon_details: Optional[Dict[str, Any]] = Field(None, description="优惠券详情")
    savings: Decimal = Field(..., ge=0, description="总节省金额")
    savings_percentage: float = Field(..., ge=0, le=1, description="节省百分比")
    
    @property
    def total_discount(self) -> Decimal:
        """总折扣金额"""
        return self.discount_amount + self.coupon_discount
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class OrderResponse(BaseModel):
    """订单响应模型"""
    
    order_id: str
    user_id: str
    order_items: List[OrderItem]
    original_amount: Decimal
    discount_amount: Decimal
    coupon_discount: Decimal
    final_amount: Decimal
    applied_discount_id: Optional[str]
    applied_coupon_code: Optional[str]
    order_status: OrderStatus
    payment_status: PaymentStatus
    payment_method: Optional[str]
    notes: Optional[str]
    total_courses: int
    total_discount: Decimal
    discount_percentage: float
    is_paid: bool
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime]
    
    @classmethod
    def from_order(cls, order: Order) -> "OrderResponse":
        """从Order模型创建响应对象"""
        return cls(
            order_id=order.order_id,
            user_id=order.user_id,
            order_items=order.order_items,
            original_amount=order.original_amount,
            discount_amount=order.discount_amount,
            coupon_discount=order.coupon_discount,
            final_amount=order.final_amount,
            applied_discount_id=order.applied_discount_id,
            applied_coupon_code=order.applied_coupon_code,
            order_status=order.order_status,
            payment_status=order.payment_status,
            payment_method=order.payment_method,
            notes=order.notes,
            total_courses=order.total_courses,
            total_discount=order.total_discount,
            discount_percentage=order.discount_percentage,
            is_paid=order.is_paid(),
            created_at=order.created_at,
            updated_at=order.updated_at,
            paid_at=order.paid_at
        )


class OrderSearchQuery(BaseModel):
    """订单搜索查询模型"""
    
    user_id: Optional[str] = None
    order_status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    course_id: Optional[str] = None
    has_discount: Optional[bool] = None
    has_coupon: Optional[bool] = None