"""
课程相关数据模型
"""

from decimal import Decimal
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class CourseCategory(str, Enum):
    """课程分类枚举"""
    PYTHON = "python"
    DATA_ANALYSIS = "data_analysis"
    MACHINE_LEARNING = "machine_learning"
    WEB_DEVELOPMENT = "web_development"
    DATABASE = "database"
    AI = "artificial_intelligence"
    BUSINESS = "business_skills"


class DifficultyLevel(str, Enum):
    """难度等级枚举"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class CourseStatus(str, Enum):
    """课程状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive" 
    DRAFT = "draft"
    ARCHIVED = "archived"


class Course(BaseModel):
    """课程基础模型"""
    
    course_id: str = Field(..., description="课程唯一标识")
    course_name: str = Field(..., min_length=1, max_length=200, description="课程名称")
    category: CourseCategory = Field(..., description="课程分类")
    original_price: Decimal = Field(..., ge=0, description="课程原价")
    current_price: Decimal = Field(..., ge=0, description="当前价格")
    description: Optional[str] = Field(None, max_length=2000, description="课程描述")
    duration_hours: int = Field(..., ge=1, le=1000, description="课程总时长(小时)")
    difficulty_level: DifficultyLevel = Field(..., description="难度等级")
    tags: List[str] = Field(default_factory=list, description="课程标签")
    prerequisites: List[str] = Field(default_factory=list, description="前置要求")
    learning_outcomes: List[str] = Field(default_factory=list, description="学习成果")
    instructor: Optional[str] = Field(None, description="讲师")
    rating: Optional[float] = Field(None, ge=0, le=5, description="课程评分")
    student_count: int = Field(default=0, ge=0, description="学员数量")
    status: CourseStatus = Field(default=CourseStatus.ACTIVE, description="课程状态")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @validator('current_price')
    def validate_current_price(cls, v, values):
        """验证当前价格不能超过原价"""
        if 'original_price' in values and v > values['original_price']:
            raise ValueError('当前价格不能超过原价')
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        """验证标签数量和格式"""
        if len(v) > 10:
            raise ValueError('标签数量不能超过10个')
        for tag in v:
            if len(tag.strip()) == 0:
                raise ValueError('标签不能为空')
        return [tag.strip() for tag in v]

    def is_available(self) -> bool:
        """检查课程是否可用"""
        return self.status == CourseStatus.ACTIVE
    
    def get_discount_percentage(self) -> float:
        """计算折扣百分比"""
        if self.original_price == 0:
            return 0.0
        return float((self.original_price - self.current_price) / self.original_price)


class CourseCreate(BaseModel):
    """创建课程数据模型"""
    
    course_name: str = Field(..., min_length=1, max_length=200)
    category: CourseCategory = Field(...)
    original_price: Decimal = Field(..., ge=0)
    current_price: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=2000)
    duration_hours: int = Field(..., ge=1, le=1000)
    difficulty_level: DifficultyLevel = Field(...)
    tags: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    learning_outcomes: List[str] = Field(default_factory=list)
    instructor: Optional[str] = Field(None)

    @validator('current_price')
    def set_current_price_default(cls, v, values):
        """如果未设置当前价格，默认等于原价"""
        if v is None and 'original_price' in values:
            return values['original_price']
        return v


class CourseUpdate(BaseModel):
    """更新课程数据模型"""
    
    course_name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[CourseCategory] = None
    original_price: Optional[Decimal] = Field(None, ge=0)
    current_price: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=2000)
    duration_hours: Optional[int] = Field(None, ge=1, le=1000)
    difficulty_level: Optional[DifficultyLevel] = None
    tags: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    learning_outcomes: Optional[List[str]] = None
    instructor: Optional[str] = None
    status: Optional[CourseStatus] = None


class CourseResponse(BaseModel):
    """课程响应模型 - 用于API返回"""
    
    course_id: str
    course_name: str
    category: CourseCategory
    original_price: Decimal
    current_price: Decimal
    description: Optional[str]
    duration_hours: int
    difficulty_level: DifficultyLevel
    tags: List[str]
    prerequisites: List[str]
    learning_outcomes: List[str]
    instructor: Optional[str]
    rating: Optional[float]
    student_count: int
    status: CourseStatus
    discount_percentage: float
    is_available: bool
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_course(cls, course: Course) -> "CourseResponse":
        """从Course模型创建响应对象"""
        return cls(
            course_id=course.course_id,
            course_name=course.course_name,
            category=course.category,
            original_price=course.original_price,
            current_price=course.current_price,
            description=course.description,
            duration_hours=course.duration_hours,
            difficulty_level=course.difficulty_level,
            tags=course.tags,
            prerequisites=course.prerequisites,
            learning_outcomes=course.learning_outcomes,
            instructor=course.instructor,
            rating=course.rating,
            student_count=course.student_count,
            status=course.status,
            discount_percentage=course.get_discount_percentage(),
            is_available=course.is_available(),
            created_at=course.created_at,
            updated_at=course.updated_at
        )


class CourseSearchQuery(BaseModel):
    """课程搜索查询模型"""
    
    keywords: Optional[str] = Field(None, description="关键词搜索")
    category: Optional[CourseCategory] = Field(None, description="按分类筛选")
    difficulty_level: Optional[DifficultyLevel] = Field(None, description="按难度筛选")
    min_price: Optional[Decimal] = Field(None, ge=0, description="最低价格")
    max_price: Optional[Decimal] = Field(None, ge=0, description="最高价格")
    tags: Optional[List[str]] = Field(None, description="标签筛选")
    min_duration: Optional[int] = Field(None, ge=1, description="最少时长")
    max_duration: Optional[int] = Field(None, ge=1, description="最多时长")
    only_available: bool = Field(default=True, description="只显示可用课程")
    
    @validator('max_price')
    def validate_price_range(cls, v, values):
        """验证价格范围"""
        if v is not None and 'min_price' in values and values['min_price'] is not None:
            if v < values['min_price']:
                raise ValueError('最高价格不能低于最低价格')
        return v
    
    @validator('max_duration')
    def validate_duration_range(cls, v, values):
        """验证时长范围"""
        if v is not None and 'min_duration' in values and values['min_duration'] is not None:
            if v < values['min_duration']:
                raise ValueError('最多时长不能少于最少时长')
        return v


class CourseRecommendation(BaseModel):
    """课程推荐结果模型"""
    
    course: CourseResponse
    recommendation_score: float = Field(..., ge=0, le=1, description="推荐分数")
    recommendation_reasons: List[str] = Field(..., description="推荐理由")
    match_tags: List[str] = Field(default_factory=list, description="匹配的标签")
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }