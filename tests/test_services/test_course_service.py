"""
CourseService业务逻辑测试
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.services.course_service import CourseService
from app.repositories.course_repository import CourseRepository
from app.models.course import Course, CourseCreate, CourseUpdate
from app.models.database.course_db import CourseDB


@pytest.mark.asyncio
class TestCourseService:
    """CourseService业务逻辑测试类"""

    @pytest.fixture
    def mock_course_repo(self):
        """模拟CourseRepository"""
        return AsyncMock(spec=CourseRepository)

    @pytest.fixture
    def mock_cache(self):
        """模拟缓存"""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.delete_pattern = AsyncMock()
        return cache

    @pytest.fixture
    def course_service(self, mock_course_repo, mock_cache):
        """创建CourseService实例"""
        service = CourseService(mock_course_repo)
        service.cache = mock_cache
        return service

    @pytest.fixture
    def sample_course_db(self):
        """示例CourseDB对象"""
        return CourseDB(
            course_id="course_001",
            course_name="Python基础课程",
            description="学习Python编程基础",
            category="python",
            difficulty_level="beginner",
            duration_hours=40,
            instructor="张老师",
            original_price=Decimal("399.00"),
            current_price=Decimal("299.00"),
            rating=4.5,
            student_count=1200,
            prerequisites=["基础计算机知识"],
            learning_outcomes=["掌握Python语法", "能够编写简单程序"],
            status="active"
        )

    @pytest.fixture
    def sample_course(self):
        """示例Course对象"""
        return Course(
            course_id="course_001",
            course_name="Python基础课程",
            description="学习Python编程基础",
            category="python",
            difficulty_level="beginner",
            duration_hours=40,
            instructor="张老师",
            original_price=Decimal("399.00"),
            current_price=Decimal("299.00"),
            rating=4.5,
            student_count=1200,
            prerequisites=["基础计算机知识"],
            learning_outcomes=["掌握Python语法", "能够编写简单程序"],
            status="active"
        )

    async def test_get_course_by_id_cache_hit(self, course_service, mock_cache, sample_course):
        """测试从缓存获取课程详情"""
        # 设置缓存返回数据
        mock_cache.get.return_value = sample_course.dict()
        
        # 调用方法
        result = await course_service.get_course_by_id("course_001")
        
        # 验证结果
        assert result is not None
        assert result.course_id == "course_001"
        assert result.course_name == "Python基础课程"
        
        # 验证缓存被调用
        mock_cache.get.assert_called_once_with("detail:course_001")
        
        # 验证Repository没有被调用
        course_service.course_repo.get_by_course_id.assert_not_called()

    async def test_get_course_by_id_cache_miss(self, course_service, mock_cache, mock_course_repo, sample_course_db, sample_course):
        """测试缓存未命中时获取课程详情"""
        # 设置缓存返回None
        mock_cache.get.return_value = None
        
        # 设置Repository返回数据
        mock_course_repo.get_by_course_id.return_value = sample_course_db
        mock_course_repo.to_model.return_value = sample_course
        
        # 调用方法
        result = await course_service.get_course_by_id("course_001")
        
        # 验证结果
        assert result is not None
        assert result.course_id == "course_001"
        
        # 验证Repository被调用
        mock_course_repo.get_by_course_id.assert_called_once_with("course_001")
        mock_course_repo.to_model.assert_called_once_with(sample_course_db)
        
        # 验证缓存被设置
        mock_cache.set.assert_called_once_with("detail:course_001", sample_course.dict(), ttl=3600)

    async def test_get_course_by_id_not_found(self, course_service, mock_cache, mock_course_repo):
        """测试获取不存在的课程"""
        # 设置缓存返回None
        mock_cache.get.return_value = None
        
        # 设置Repository返回None
        mock_course_repo.get_by_course_id.return_value = None
        
        # 调用方法
        result = await course_service.get_course_by_id("nonexistent")
        
        # 验证结果
        assert result is None
        
        # 验证Repository被调用
        mock_course_repo.get_by_course_id.assert_called_once_with("nonexistent")
        
        # 验证缓存没有被设置
        mock_cache.set.assert_not_called()

    async def test_search_courses_cache_hit(self, course_service, mock_cache, sample_course):
        """测试从缓存搜索课程"""
        # 设置缓存返回数据
        mock_cache.get.return_value = [sample_course.dict()]
        
        # 调用方法
        result = await course_service.search_courses(
            keywords="Python",
            category="python",
            limit=10
        )
        
        # 验证结果
        assert len(result) == 1
        assert result[0].course_id == "course_001"
        
        # 验证缓存被调用
        expected_cache_key = "search:keywords=Python:category=python:difficulty=:price_min=0:price_max=0:limit=10:offset=0"
        mock_cache.get.assert_called_once_with(expected_cache_key)

    async def test_search_courses_cache_miss(self, course_service, mock_cache, mock_course_repo, sample_course_db, sample_course):
        """测试缓存未命中时搜索课程"""
        # 设置缓存返回None
        mock_cache.get.return_value = None
        
        # 设置Repository返回数据
        mock_course_repo.search_courses.return_value = [sample_course_db]
        mock_course_repo.to_model.return_value = sample_course
        
        # 调用方法
        result = await course_service.search_courses(keywords="Python")
        
        # 验证结果
        assert len(result) == 1
        assert result[0].course_id == "course_001"
        
        # 验证Repository被调用
        mock_course_repo.search_courses.assert_called_once()
        
        # 验证缓存被设置
        mock_cache.set.assert_called_once()

    async def test_get_courses_by_category(self, course_service, mock_cache, mock_course_repo, sample_course_db, sample_course):
        """测试按分类获取课程"""
        # 设置缓存返回None
        mock_cache.get.return_value = None
        
        # 设置Repository返回数据
        mock_course_repo.get_courses_by_category.return_value = [sample_course_db]
        mock_course_repo.to_model.return_value = sample_course
        
        # 调用方法
        result = await course_service.get_courses_by_category("编程语言")
        
        # 验证结果
        assert len(result) == 1
        assert result[0].category == "编程语言"
        
        # 验证Repository被调用
        mock_course_repo.get_courses_by_category.assert_called_once_with(
            category="python",
            limit=20,
            offset=0
        )

    async def test_get_popular_courses(self, course_service, mock_cache, mock_course_repo, sample_course_db, sample_course):
        """测试获取热门课程"""
        # 设置缓存返回None
        mock_cache.get.return_value = None
        
        # 设置Repository返回数据
        mock_course_repo.get_popular_courses.return_value = [sample_course_db]
        mock_course_repo.to_model.return_value = sample_course
        
        # 调用方法
        result = await course_service.get_popular_courses(limit=5)
        
        # 验证结果
        assert len(result) == 1
        assert result[0].rating == 4.5
        
        # 验证Repository被调用
        mock_course_repo.get_popular_courses.assert_called_once_with(limit=5)

    async def test_get_course_categories(self, course_service, mock_cache, mock_course_repo):
        """测试获取课程分类"""
        # 设置缓存返回None
        mock_cache.get.return_value = None
        
        # 设置Repository返回数据
        categories_data = [
            {"category": "编程语言", "count": 25},
            {"category": "数据科学", "count": 15}
        ]
        mock_course_repo.get_course_categories.return_value = categories_data
        
        # 调用方法
        result = await course_service.get_course_categories()
        
        # 验证结果
        assert len(result) == 2
        assert result[0]["category"] == "编程语言"
        
        # 验证Repository被调用
        mock_course_repo.get_course_categories.assert_called_once()
        
        # 验证缓存被设置，TTL是正常的2倍
        mock_cache.set.assert_called_once_with("categories", categories_data, ttl=7200)

    async def test_get_price_range(self, course_service, mock_cache, mock_course_repo):
        """测试获取价格范围"""
        # 设置缓存返回None
        mock_cache.get.return_value = None
        
        # 设置Repository返回数据
        price_range = {
            "min_price": Decimal("99.00"),
            "max_price": Decimal("999.00"),
            "avg_price": Decimal("399.00")
        }
        mock_course_repo.get_price_range.return_value = price_range
        
        # 调用方法
        result = await course_service.get_price_range("编程语言")
        
        # 验证结果
        assert result["min_price"] == Decimal("99.00")
        assert result["max_price"] == Decimal("999.00")
        
        # 验证Repository被调用
        mock_course_repo.get_price_range.assert_called_once_with(category="编程语言")

    async def test_create_course(self, course_service, mock_course_repo, mock_cache, sample_course_db, sample_course):
        """测试创建课程"""
        # 准备创建数据
        course_create = CourseCreate(
            course_name="新课程",
            description="新课程描述",
            category="测试分类",
            difficulty_level="beginner",
            duration_hours=20,
            instructor="测试老师",
            original_price=Decimal("299.00"),
            current_price=Decimal("199.00")
        )
        
        # 设置Repository返回数据
        mock_course_repo.create.return_value = sample_course_db
        mock_course_repo.to_model.return_value = sample_course
        
        # 调用方法
        result = await course_service.create_course(course_create)
        
        # 验证结果
        assert result is not None
        assert result.course_id == "course_001"
        
        # 验证Repository被调用
        mock_course_repo.create.assert_called_once_with(course_create.dict())
        
        # 验证缓存被清除
        mock_cache.delete_pattern.assert_called()

    async def test_update_course(self, course_service, mock_course_repo, mock_cache, sample_course_db, sample_course):
        """测试更新课程"""
        # 准备更新数据
        course_update = CourseUpdate(
            course_name="更新后的课程名",
            current_price=Decimal("199.00")
        )
        
        # 设置Repository返回数据
        mock_course_repo.get_by_course_id.return_value = sample_course_db
        mock_course_repo.update.return_value = sample_course_db
        mock_course_repo.to_model.return_value = sample_course
        
        # 调用方法
        result = await course_service.update_course("course_001", course_update)
        
        # 验证结果
        assert result is not None
        assert result.course_id == "course_001"
        
        # 验证Repository被调用
        mock_course_repo.get_by_course_id.assert_called_once_with("course_001")
        mock_course_repo.update.assert_called_once()
        
        # 验证缓存被清除
        mock_cache.delete_pattern.assert_called()

    async def test_update_nonexistent_course(self, course_service, mock_course_repo):
        """测试更新不存在的课程"""
        # 准备更新数据
        course_update = CourseUpdate(course_name="更新后的课程名")
        
        # 设置Repository返回None
        mock_course_repo.get_by_course_id.return_value = None
        
        # 调用方法
        result = await course_service.update_course("nonexistent", course_update)
        
        # 验证结果
        assert result is None
        
        # 验证Repository被调用
        mock_course_repo.get_by_course_id.assert_called_once_with("nonexistent")
        mock_course_repo.update.assert_not_called()

    async def test_update_course_stats(self, course_service, mock_course_repo, mock_cache):
        """测试更新课程统计信息"""
        # 设置Repository返回成功
        mock_course_repo.update_course_stats.return_value = True
        
        # 调用方法
        result = await course_service.update_course_stats(
            "course_001",
            new_rating=4.8,
            new_student_count=1500
        )
        
        # 验证结果
        assert result is True
        
        # 验证Repository被调用
        mock_course_repo.update_course_stats.assert_called_once_with(
            course_id="course_001",
            new_rating=4.8,
            new_student_count=1500
        )
        
        # 验证缓存被清除
        mock_cache.delete_pattern.assert_called()

    async def test_get_course_for_agent(self, course_service, sample_course):
        """测试为Agent获取课程信息"""
        # 模拟get_course_by_id方法
        course_service.get_course_by_id = AsyncMock(return_value=sample_course)
        
        # 调用方法
        result = await course_service.get_course_for_agent("course_001")
        
        # 验证结果
        assert result is not None
        assert result.course_id == "course_001"
        assert result.agent_description is not None
        assert "课程名称：Python基础课程" in result.agent_description
        assert result.recommendation_score > 0

    async def test_get_course_for_agent_not_found(self, course_service):
        """测试为Agent获取不存在的课程"""
        # 模拟get_course_by_id方法返回None
        course_service.get_course_by_id = AsyncMock(return_value=None)
        
        # 调用方法
        result = await course_service.get_course_for_agent("nonexistent")
        
        # 验证结果
        assert result is None

    def test_generate_agent_course_description(self, course_service, sample_course):
        """测试生成Agent友好的课程描述"""
        # 调用私有方法
        description = course_service._generate_agent_course_description(sample_course)
        
        # 验证结果
        assert "课程名称：Python基础课程" in description
        assert "分类：编程语言" in description
        assert "难度：beginner" in description
        assert "时长：40小时" in description
        assert "讲师：张老师" in description
        assert "评分：4.5/5.0" in description
        assert "价格：原价399.00元，现价299.00元" in description

    def test_calculate_recommendation_score(self, course_service, sample_course):
        """测试计算推荐分数"""
        # 调用私有方法
        score = course_service._calculate_recommendation_score(sample_course)
        
        # 验证结果
        assert isinstance(score, float)
        assert 0 <= score <= 1
        
        # 验证分数计算逻辑
        expected_rating_score = 4.5 / 5.0 * 0.4  # 0.36
        expected_popularity_score = min(1200 / 1000, 1.0) * 0.3  # 0.3
        expected_price_score = max(0, (2000 - 299) / 2000) * 0.3  # 0.255
        expected_total = expected_rating_score + expected_popularity_score + expected_price_score
        
        assert abs(score - round(expected_total, 2)) < 0.01

    async def test_clear_course_caches(self, course_service, mock_cache):
        """测试清除课程缓存"""
        # 调用私有方法
        await course_service._clear_course_caches("course_001")
        
        # 验证缓存清除被调用
        expected_patterns = [
            "search:*",
            "category:*",
            "popular:*",
            "all_for_agent:*",
            "categories",
            "price_range:*",
            "detail:course_001"
        ]
        
        # 验证每个模式都被调用删除
        assert mock_cache.delete_pattern.call_count == len(expected_patterns)
        
        # 验证调用的参数
        call_args = [call[0][0] for call in mock_cache.delete_pattern.call_args_list]
        for pattern in expected_patterns:
            assert pattern in call_args

    async def test_cache_disabled(self, course_service, mock_cache, mock_course_repo, sample_course_db, sample_course):
        """测试禁用缓存的情况"""
        # 设置Repository返回数据
        mock_course_repo.get_by_course_id.return_value = sample_course_db
        mock_course_repo.to_model.return_value = sample_course
        
        # 调用方法，禁用缓存
        result = await course_service.get_course_by_id("course_001", use_cache=False)
        
        # 验证结果
        assert result is not None
        assert result.course_id == "course_001"
        
        # 验证缓存没有被调用
        mock_cache.get.assert_not_called()
        mock_cache.set.assert_not_called()
        
        # 验证Repository被调用
        mock_course_repo.get_by_course_id.assert_called_once_with("course_001")