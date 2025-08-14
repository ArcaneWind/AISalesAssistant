"""
折扣相关数据库模型
"""

from sqlalchemy import Column, String, Integer, Numeric, Text, Boolean, DateTime, JSON, ARRAY
from sqlalchemy.sql import func
from app.core.database import Base


class AppliedDiscountDB(Base):
    """应用折扣记录表"""
    
    __tablename__ = "applied_discounts"
    
    # 主键和关联信息
    discount_id = Column(String(50), primary_key=True, comment="折扣记录ID")
    user_id = Column(String(50), nullable=False, index=True, comment="用户ID")
    
    # 折扣信息
    option_type = Column(String(30), nullable=False, comment="折扣选项类型")
    discount_type = Column(String(20), nullable=False, comment="折扣计算类型")
    discount_value = Column(Numeric(5, 4), nullable=False, comment="折扣值(0-1)")
    
    # 应用范围
    applicable_course_ids = Column(ARRAY(String), nullable=False, comment="适用课程ID列表")
    
    # 金额信息
    original_amount = Column(Numeric(10, 2), nullable=False, comment="原始金额")
    discount_amount = Column(Numeric(10, 2), nullable=False, comment="折扣金额")
    final_amount = Column(Numeric(10, 2), nullable=False, comment="最终金额")
    
    # Agent信息
    agent_reasoning = Column(Text, comment="Agent决策理由")
    created_by = Column(String(20), default="agent", comment="创建者")
    
    # 有效期和使用状态
    valid_until = Column(DateTime(timezone=True), comment="有效期至")
    is_used = Column(Boolean, default=False, index=True, comment="是否已使用")
    used_at = Column(DateTime(timezone=True), comment="使用时间")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 索引
    __table_args__ = (
        {'comment': '应用折扣记录表'}
    )


class DiscountUsageHistoryDB(Base):
    """折扣使用历史表"""
    
    __tablename__ = "discount_usage_history"
    
    # 主键和关联信息
    history_id = Column(String(50), primary_key=True, comment="历史记录ID")
    user_id = Column(String(50), nullable=False, index=True, comment="用户ID")
    discount_id = Column(String(50), nullable=False, comment="折扣ID")
    order_id = Column(String(50), comment="关联订单ID")
    
    # 使用信息
    option_type = Column(String(30), nullable=False, comment="折扣类型")
    discount_amount = Column(Numeric(10, 2), nullable=False, comment="折扣金额")
    course_ids = Column(ARRAY(String), nullable=False, comment="应用课程ID")
    
    # 创建者和时间
    created_by = Column(String(20), nullable=False, comment="创建者")
    used_at = Column(DateTime(timezone=True), server_default=func.now(), comment="使用时间")
    
    # 索引
    __table_args__ = (
        {'comment': '折扣使用历史表'}
    )