"""
课程数据库模型
"""

from sqlalchemy import Column, String, Integer, Numeric, Text, Boolean, DateTime, ARRAY
from sqlalchemy.sql import func
from app.core.database import Base


class CourseDB(Base):
    """课程数据库表"""
    
    __tablename__ = "courses"
    
    # 主键和基本信息
    course_id = Column(String(50), primary_key=True, comment="课程ID")
    course_name = Column(String(200), nullable=False, comment="课程名称")
    category = Column(String(50), nullable=False, index=True, comment="课程分类")
    
    # 价格信息
    original_price = Column(Numeric(10, 2), nullable=False, comment="原价")
    current_price = Column(Numeric(10, 2), nullable=False, comment="当前价格")
    
    # 课程详情
    description = Column(Text, comment="课程描述")
    duration_hours = Column(Integer, nullable=False, comment="课程时长(小时)")
    difficulty_level = Column(String(20), nullable=False, comment="难度等级")
    instructor = Column(String(100), comment="讲师")
    
    # 数组字段
    tags = Column(ARRAY(String), default=[], comment="课程标签")
    prerequisites = Column(ARRAY(String), default=[], comment="前置要求")
    learning_outcomes = Column(ARRAY(String), default=[], comment="学习成果")
    
    # 统计信息
    rating = Column(Numeric(3, 2), comment="课程评分")
    student_count = Column(Integer, default=0, comment="学员数量")
    
    # 状态和时间
    status = Column(String(20), default="active", index=True, comment="课程状态")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 索引
    __table_args__ = (
        {'comment': '课程信息表'}
    )