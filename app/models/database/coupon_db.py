"""
优惠券数据库模型
"""

from sqlalchemy import Column, String, Integer, Numeric, Text, Boolean, DateTime, ARRAY
from sqlalchemy.sql import func
from app.core.database import Base


class CouponDB(Base):
    """优惠券数据库表"""
    
    __tablename__ = "coupons"
    
    # 主键和基本信息
    coupon_id = Column(String(50), primary_key=True, comment="优惠券ID")
    coupon_code = Column(String(50), nullable=False, unique=True, index=True, comment="优惠券代码")
    coupon_name = Column(String(200), nullable=False, comment="优惠券名称")
    coupon_type = Column(String(20), nullable=False, comment="优惠券类型")
    
    # 折扣信息
    discount_value = Column(Numeric(10, 2), nullable=False, comment="折扣值")
    min_order_amount = Column(Numeric(10, 2), default=0, comment="最小订单金额")
    max_discount = Column(Numeric(10, 2), comment="最大折扣金额")
    
    # 有效期
    valid_from = Column(DateTime(timezone=True), nullable=False, index=True, comment="有效开始时间")
    valid_to = Column(DateTime(timezone=True), nullable=False, index=True, comment="有效结束时间")
    
    # 使用限制
    usage_limit = Column(Integer, comment="总使用次数限制")
    usage_limit_per_user = Column(Integer, comment="单用户使用次数限制")
    used_count = Column(Integer, default=0, comment="已使用次数")
    
    # 适用范围
    applicable_courses = Column(ARRAY(String), comment="适用课程ID列表")
    
    # 其他信息
    description = Column(Text, comment="优惠券描述")
    status = Column(String(20), default="active", index=True, comment="优惠券状态")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 索引
    __table_args__ = (
        {'comment': '优惠券信息表'}
    )