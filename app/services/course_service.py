"""
课程业务服务层
提供课程相关的业务逻辑处理
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from app.models.course import Course, CourseCreate, CourseUpdate, CourseResponse
from app.repositories.course_repository import CourseRepository
from app.services.common_cache import course_cache


class CourseService:
    """课程业务服务"""
    
    def __init__(self, course_repo: CourseRepository):
        self.course_repo = course_repo
        self.cache = course_cache
        self.cache_ttl = 3600  # 1小时缓存
    
    async def get_course_by_id(self, course_id: str, use_cache: bool = True) -> Optional[Course]:
        """获取课程详情"""
        cache_key = f"detail:{course_id}"
        
        if use_cache:
            cached_course = await self.cache.get(cache_key)
            if cached_course:
                return Course(**cached_course)
        
        db_course = await self.course_repo.get_by_course_id(course_id)
        if not db_course:
            return None
        
        course = self.course_repo.to_model(db_course)
        
        if use_cache:
            await self.cache.set(cache_key, course.dict(), ttl=self.cache_ttl)
        
        return course
    
    async def search_courses(
        self,
        keywords: Optional[str] = None,
        category: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        limit: int = 20,
        offset: int = 0,
        use_cache: bool = True
    ) -> List[Course]:
        """搜索课程"""
        # 构建缓存键
        cache_params = {
            "keywords": keywords or "",
            "category": category or "",
            "difficulty": difficulty_level or "",
            "price_min": str(price_min or 0),
            "price_max": str(price_max or 0),
            "limit": limit,
            "offset": offset
        }
        cache_key = f"search:" + ":".join(f"{k}={v}" for k, v in cache_params.items())
        
        if use_cache:
            cached_courses = await self.cache.get(cache_key)
            if cached_courses:
                return [Course(**course_data) for course_data in cached_courses]
        
        db_courses = await self.course_repo.search_courses(
            keywords=keywords,
            category=category,
            difficulty_level=difficulty_level,
            price_min=price_min,
            price_max=price_max,
            limit=limit,
            offset=offset
        )
        
        courses = [self.course_repo.to_model(db_course) for db_course in db_courses]
        
        if use_cache:
            await self.cache.set(
                cache_key, 
                [course.dict() for course in courses], 
                ttl=self.cache_ttl // 2  # 搜索结果缓存时间短一些
            )
        
        return courses
    
    async def get_courses_by_category(
        self,
        category: str,
        limit: int = 20,
        offset: int = 0,
        use_cache: bool = True
    ) -> List[Course]:
        """根据分类获取课程"""
        cache_key = f"category:{category}:{limit}:{offset}"
        
        if use_cache:
            cached_courses = await self.cache.get(cache_key)
            if cached_courses:
                return [Course(**course_data) for course_data in cached_courses]
        
        db_courses = await self.course_repo.get_courses_by_category(
            category=category,
            limit=limit,
            offset=offset
        )
        
        courses = [self.course_repo.to_model(db_course) for db_course in db_courses]
        
        if use_cache:
            await self.cache.set(cache_key, [course.dict() for course in courses], ttl=self.cache_ttl)
        
        return courses
    
    async def get_all_courses_for_agent(
        self,
        limit: int = 100,
        offset: int = 0,
        use_cache: bool = True
    ) -> List[Course]:
        """获取所有课程供Agent分析推荐"""
        cache_key = f"all_for_agent:{limit}:{offset}"
        
        if use_cache:
            cached_courses = await self.cache.get(cache_key)
            if cached_courses:
                return [Course(**course_data) for course_data in cached_courses]
        
        db_courses = await self.course_repo.get_all_courses_for_agent(
            limit=limit,
            offset=offset
        )
        
        courses = [self.course_repo.to_model(db_course) for db_course in db_courses]
        
        if use_cache:
            await self.cache.set(
                cache_key, 
                [course.dict() for course in courses], 
                ttl=self.cache_ttl
            )
        
        return courses
    
    async def get_popular_courses(
        self,
        limit: int = 10,
        use_cache: bool = True
    ) -> List[Course]:
        """获取热门课程"""
        cache_key = f"popular:{limit}"
        
        if use_cache:
            cached_courses = await self.cache.get(cache_key)
            if cached_courses:
                return [Course(**course_data) for course_data in cached_courses]
        
        db_courses = await self.course_repo.get_popular_courses(limit=limit)
        courses = [self.course_repo.to_model(db_course) for db_course in db_courses]
        
        if use_cache:
            await self.cache.set(cache_key, [course.dict() for course in courses], ttl=self.cache_ttl)
        
        return courses
    
    async def get_course_categories(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """获取课程分类统计"""
        cache_key = "categories"
        
        if use_cache:
            cached_categories = await self.cache.get(cache_key)
            if cached_categories:
                return cached_categories
        
        categories = await self.course_repo.get_course_categories()
        
        if use_cache:
            await self.cache.set(cache_key, categories, ttl=self.cache_ttl * 2)  # 分类信息缓存时间长一些
        
        return categories
    
    async def get_price_range(
        self, 
        category: Optional[str] = None, 
        use_cache: bool = True
    ) -> Dict[str, Decimal]:
        """获取价格范围"""
        cache_key = f"price_range:{category or 'all'}"
        
        if use_cache:
            cached_range = await self.cache.get(cache_key)
            if cached_range:
                return {
                    k: Decimal(str(v)) for k, v in cached_range.items()
                }
        
        price_range = await self.course_repo.get_price_range(category=category)
        
        if use_cache:
            # 将Decimal转换为字符串存储
            cache_data = {k: str(v) for k, v in price_range.items()}
            await self.cache.set(cache_key, cache_data, ttl=self.cache_ttl * 2)
        
        return price_range
    
    async def create_course(self, course_data: CourseCreate) -> Course:
        """创建课程"""
        db_course = await self.course_repo.create(course_data.dict())
        course = self.course_repo.to_model(db_course)
        
        # 清除相关缓存
        await self._clear_course_caches()
        
        return course
    
    async def update_course(
        self, 
        course_id: str, 
        course_data: CourseUpdate
    ) -> Optional[Course]:
        """更新课程"""
        db_course = await self.course_repo.get_by_course_id(course_id)
        if not db_course:
            return None
        
        updated_course = await self.course_repo.update(db_course.id, course_data.dict(exclude_unset=True))
        course = self.course_repo.to_model(updated_course)
        
        # 清除相关缓存
        await self._clear_course_caches(course_id)
        
        return course
    
    async def update_course_stats(
        self,
        course_id: str,
        new_rating: Optional[float] = None,
        new_student_count: Optional[int] = None
    ) -> bool:
        """更新课程统计信息"""
        success = await self.course_repo.update_course_stats(
            course_id=course_id,
            new_rating=new_rating,
            new_student_count=new_student_count
        )
        
        if success:
            # 清除相关缓存
            await self._clear_course_caches(course_id)
        
        return success
    
    async def get_course_for_agent(self, course_id: str) -> Optional[CourseResponse]:
        """为Agent提供课程信息（包含推荐说明）"""
        course = await self.get_course_by_id(course_id)
        if not course:
            return None
        
        # 生成Agent友好的课程描述
        agent_description = self._generate_agent_course_description(course)
        
        return CourseResponse(
            **course.dict(),
            agent_description=agent_description,
            recommendation_score=self._calculate_recommendation_score(course)
        )
    
    def _generate_agent_course_description(self, course: Course) -> str:
        """生成Agent友好的课程描述"""
        description_parts = [
            f"课程名称：{course.course_name}",
            f"分类：{course.category}",
            f"难度：{course.difficulty_level}",
            f"时长：{course.duration_hours}小时",
            f"讲师：{course.instructor}",
            f"评分：{course.rating}/5.0 ({course.student_count}人学习)",
            f"价格：原价{course.original_price}元，现价{course.current_price}元"
        ]
        
        if course.prerequisites:
            description_parts.append(f"前置要求：{', '.join(course.prerequisites)}")
        
        if course.learning_outcomes:
            description_parts.append(f"学习收获：{', '.join(course.learning_outcomes)}")
        
        return "\n".join(description_parts)
    
    def _calculate_recommendation_score(self, course: Course) -> float:
        """计算推荐分数"""
        # 综合评分、学员数量、价格等因素
        rating_score = course.rating / 5.0 * 0.4
        popularity_score = min(course.student_count / 1000, 1.0) * 0.3
        price_score = max(0, (2000 - float(course.current_price)) / 2000) * 0.3
        
        return round(rating_score + popularity_score + price_score, 2)
    
    async def _clear_course_caches(self, course_id: Optional[str] = None):
        """清除课程相关缓存"""
        patterns = [
            "search:*",
            "category:*",
            "popular:*",
            "all_for_agent:*", 
            "categories",
            "price_range:*"
        ]
        
        if course_id:
            patterns.append(f"detail:{course_id}")
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)