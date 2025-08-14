"""
课程数据库操作层
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, update, and_, or_, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, CourseCreate, CourseUpdate
from app.models.database.course_db import CourseDB


class CourseRepository:
    """课程数据库操作类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_course_id(self, course_id: str) -> Optional[CourseDB]:
        """根据课程ID获取课程"""
        result = await self.db.execute(
            select(CourseDB).where(CourseDB.course_id == course_id)
        )
        return result.scalar_one_or_none()
    
    async def get_courses_by_category(
        self,
        category: str,
        limit: int = 20,
        offset: int = 0,
        status: str = "active"
    ) -> List[CourseDB]:
        """根据分类获取课程列表"""
        query = select(CourseDB).where(
            and_(
                CourseDB.category == category,
                CourseDB.status == status
            )
        ).order_by(desc(CourseDB.rating), CourseDB.current_price).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def search_courses(
        self,
        keywords: str,
        category: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[CourseDB]:
        """搜索课程"""
        conditions = [CourseDB.status == "active"]
        
        # 关键字搜索（课程名称、描述、标签）
        if keywords:
            search_condition = or_(
                CourseDB.course_name.ilike(f"%{keywords}%"),
                CourseDB.description.ilike(f"%{keywords}%"),
                func.array_to_string(CourseDB.tags, ',').ilike(f"%{keywords}%")
            )
            conditions.append(search_condition)
        
        # 分类过滤
        if category:
            conditions.append(CourseDB.category == category)
        
        # 难度过滤
        if difficulty_level:
            conditions.append(CourseDB.difficulty_level == difficulty_level)
        
        # 价格过滤
        if price_min is not None:
            conditions.append(CourseDB.current_price >= price_min)
        if price_max is not None:
            conditions.append(CourseDB.current_price <= price_max)
        
        query = select(CourseDB).where(
            and_(*conditions)
        ).order_by(desc(CourseDB.rating), CourseDB.current_price).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_all_courses_for_agent(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str = "active"
    ) -> List[CourseDB]:
        """获取所有课程供Agent分析推荐（移除推荐规则逻辑）"""
        query = select(CourseDB).where(
            CourseDB.status == status
        ).order_by(
            CourseDB.created_at.desc()
        ).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_popular_courses(self, limit: int = 10) -> List[CourseDB]:
        """获取热门课程"""
        query = select(CourseDB).where(
            CourseDB.status == "active"
        ).order_by(
            desc(CourseDB.student_count),
            desc(CourseDB.rating)
        ).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_course_stats(
        self,
        course_id: str,
        new_rating: Optional[float] = None,
        new_student_count: Optional[int] = None
    ) -> bool:
        """更新课程统计信息"""
        update_data = {"updated_at": datetime.now()}
        
        if new_rating is not None:
            update_data["rating"] = new_rating
        if new_student_count is not None:
            update_data["student_count"] = new_student_count
        
        result = await self.db.execute(
            update(CourseDB)
            .where(CourseDB.course_id == course_id)
            .values(**update_data)
        )
        
        return result.rowcount > 0
    
    async def get_course_categories(self) -> List[Dict[str, Any]]:
        """获取课程分类统计"""
        result = await self.db.execute(
            select(
                CourseDB.category,
                func.count(CourseDB.id).label("course_count"),
                func.avg(CourseDB.current_price).label("avg_price")
            ).where(
                CourseDB.status == "active"
            ).group_by(CourseDB.category)
        )
        
        return [
            {
                "category": row.category,
                "course_count": row.course_count,
                "avg_price": float(row.avg_price) if row.avg_price else 0.0
            }
            for row in result.fetchall()
        ]
    
    async def get_price_range(self, category: Optional[str] = None) -> Dict[str, Decimal]:
        """获取价格范围"""
        conditions = [CourseDB.status == "active"]
        if category:
            conditions.append(CourseDB.category == category)
        
        result = await self.db.execute(
            select(
                func.min(CourseDB.current_price).label("min_price"),
                func.max(CourseDB.current_price).label("max_price"),
                func.avg(CourseDB.current_price).label("avg_price")
            ).where(and_(*conditions))
        )
        
        row = result.fetchone()
        return {
            "min_price": row.min_price or Decimal("0"),
            "max_price": row.max_price or Decimal("0"),
            "avg_price": row.avg_price or Decimal("0")
        }
    
    def to_model(self, db_course: CourseDB) -> Course:
        """转换为Pydantic模型"""
        return Course(
            course_id=db_course.course_id,
            course_name=db_course.course_name,
            category=db_course.category,
            original_price=db_course.original_price,
            current_price=db_course.current_price,
            description=db_course.description,
            duration_hours=db_course.duration_hours,
            difficulty_level=db_course.difficulty_level,
            instructor=db_course.instructor,
            tags=db_course.tags or [],
            prerequisites=db_course.prerequisites or [],
            learning_outcomes=db_course.learning_outcomes or [],
            status=db_course.status,
            rating=db_course.rating,
            student_count=db_course.student_count,
            created_at=db_course.created_at,
            updated_at=db_course.updated_at
        )