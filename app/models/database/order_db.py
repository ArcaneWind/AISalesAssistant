"""
订单相关数据库模型
"""

from sqlalchemy import Column, String, Integer, Numeric, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class OrderDB(Base):
    """订单数据库表"""
    
    __tablename__ = "orders"
    
    # 主键和用户信息
    order_id = Column(String(50), primary_key=True, comment="订单ID")
    user_id = Column(String(50), nullable=False, index=True, comment="用户ID")
    
    # 金额信息
    original_amount = Column(Numeric(12, 2), nullable=False, comment="原始总金额")
    discount_amount = Column(Numeric(12, 2), default=0, comment="折扣金额")
    coupon_discount = Column(Numeric(12, 2), default=0, comment="优惠券折扣")
    final_amount = Column(Numeric(12, 2), nullable=False, comment="最终金额")
    
    # 应用的优惠信息
    applied_discount_id = Column(String(50), comment="应用的折扣ID")
    applied_coupon_code = Column(String(50), comment="使用的优惠券代码")
    
    # 订单状态
    order_status = Column(String(20), default="pending", index=True, comment="订单状态")
    payment_status = Column(String(20), default="pending", index=True, comment="支付状态")
    payment_method = Column(String(50), comment="支付方式")
    
    # 备注
    notes = Column(Text, comment="订单备注")
    cancel_reason = Column(Text, comment="取消原因")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    paid_at = Column(DateTime(timezone=True), comment="支付时间")
    cancelled_at = Column(DateTime(timezone=True), comment="取消时间")
    
    # 关系映射
    order_items = relationship("OrderItemDB", back_populates="order", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        {'comment': '订单主表'}
    )


class OrderItemDB(Base):
    """订单项目数据库表"""
    
    __tablename__ = "order_items"
    
    # 主键和关联信息
    item_id = Column(String(50), primary_key=True, comment="项目ID")
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False, index=True, comment="订单ID")
    
    # 课程信息
    course_id = Column(String(50), nullable=False, comment="课程ID")
    course_name = Column(String(200), nullable=False, comment="课程名称")
    
    # 价格信息
    original_price = Column(Numeric(10, 2), nullable=False, comment="课程原价")
    discounted_price = Column(Numeric(10, 2), nullable=False, comment="折后价格")
    quantity = Column(Integer, default=1, comment="数量")
    
    # 关系映射
    order = relationship("OrderDB", back_populates="order_items")
    
    # 索引
    __table_args__ = (
        {'comment': '订单项目表'}
    )


class CouponUsageDB(Base):
    """优惠券使用记录表"""
    
    __tablename__ = "coupon_usage"
    
    # 主键和关联信息
    usage_id = Column(String(50), primary_key=True, comment="使用记录ID")
    coupon_id = Column(String(50), nullable=False, index=True, comment="优惠券ID")
    coupon_code = Column(String(50), nullable=False, comment="优惠券代码")
    user_id = Column(String(50), nullable=False, index=True, comment="使用用户ID")
    order_id = Column(String(50), comment="关联订单ID")
    
    # 使用详情
    course_ids = Column(JSON, nullable=False, comment="应用课程ID列表")
    original_amount = Column(Numeric(10, 2), nullable=False, comment="原始金额")
    discount_amount = Column(Numeric(10, 2), nullable=False, comment="折扣金额")
    final_amount = Column(Numeric(10, 2), nullable=False, comment="最终金额")
    
    # 使用时间
    used_at = Column(DateTime(timezone=True), server_default=func.now(), comment="使用时间")
    
    # 索引
    __table_args__ = (
        {'comment': '优惠券使用记录表'}
    )