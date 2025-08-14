"""
课程Repository数据库操作测试 - 使用真实数据库
"""

import pytest
from decimal import Decimal
from datetime import datetime

from app.repositories.course_repository import CourseRepository
from app.models.database.course_db import CourseDB


@pytest.mark.asyncio
class TestCourseRepository:
    """课程Repository数据库操作测试类"""

    async def test_create_and_get_course(self, db_session):
        """测试创建和获取课程"""
        # 创建Repository实例
        course_repo = CourseRepository(db_session)
        
        # 准备测试数据
        course_data = {
            "course_id": f"TEST_COURSE_{int(datetime.now().timestamp())}",
            "course_name": "Python自动化测试课程",
            "category": "python",
            "original_price": Decimal("399.00"),
            "current_price": Decimal("299.00"),
            "description": "学习Python自动化测试技术",
            "duration_hours": 30,
            "difficulty_level": "intermediate",
            "instructor": "测试讲师",
            "tags": ["python", "testing", "automation"],
            "prerequisites": ["Python基础"],
            "learning_outcomes": ["掌握pytest框架", "编写自动化测试"],
            "status": "active",
            "rating": 4.7,
            "student_count": 150
        }
        
        # 创建课程
        course = CourseDB(**course_data)
        db_session.add(course)
        await db_session.commit()
        await db_session.refresh(course)
        
        # 通过ID获取课程
        retrieved_course = await course_repo.get_by_course_id(course.course_id)
        
        # 验证结果
        assert retrieved_course is not None
        assert retrieved_course.course_name == "Python自动化测试课程"
        assert retrieved_course.current_price == Decimal("299.00")
        assert retrieved_course.status == "active"

    async def test_get_nonexistent_course(self, db_session):
        """测试获取不存在的课程"""
        course_repo = CourseRepository(db_session)
        course = await course_repo.get_by_course_id("NONEXISTENT_COURSE_ID")
        assert course is None

    async def test_search_courses_basic(self, db_session):
        """测试基础课程搜索功能"""
        course_repo = CourseRepository(db_session)
        
        # 先创建一个测试课程
        course_data = {
            "course_id": f"SEARCH_TEST_{int(datetime.now().timestamp())}",
            "course_name": "JavaScript开发实战",
            "category": "web_development",
            "original_price": Decimal("299.00"),
            "current_price": Decimal("199.00"),
            "duration_hours": 25,
            "difficulty_level": "beginner",
            "instructor": "JS讲师",
            "status": "active"
        }
        
        course = CourseDB(**course_data)
        db_session.add(course)
        await db_session.commit()
        
        # 测试搜索
        courses = await course_repo.search_courses("JavaScript", limit=10)
        
        # 验证搜索结果
        assert isinstance(courses, list)
        found_course = next(
            (c for c in courses if c.course_id == course.course_id), 
            None
        )
        assert found_course is not None

    async def test_get_popular_courses(self, db_session):
        """测试获取热门课程"""
        course_repo = CourseRepository(db_session)
        courses = await course_repo.get_popular_courses(limit=3)
        
        # 验证返回结果
        assert isinstance(courses, list)
        assert len(courses) <= 3

    async def test_update_course_stats(self, db_session):
        """测试更新课程统计信息"""
        course_repo = CourseRepository(db_session)
        
        # 创建测试课程
        course_data = {
            "course_id": f"UPDATE_TEST_{int(datetime.now().timestamp())}",
            "course_name": "Vue.js框架学习",
            "category": "web_development",
            "original_price": Decimal("399.00"),
            "current_price": Decimal("299.00"),
            "duration_hours": 35,
            "difficulty_level": "intermediate",
            "instructor": "Vue讲师",
            "status": "active",
            "rating": 4.5,
            "student_count": 100
        }
        
        course = CourseDB(**course_data)
        db_session.add(course)
        await db_session.commit()
        await db_session.refresh(course)
        
        # 更新统计信息
        success = await course_repo.update_course_stats(
            course.course_id,
            new_rating=4.8,
            new_student_count=150
        )
        
        assert success is True
        
        # 验证更新结果
        updated_course = await course_repo.get_by_course_id(course.course_id)
        assert updated_course.rating == 4.8
        assert updated_course.student_count == 150

    async def test_pydantic_model_conversion(self, db_session):
        """测试数据库模型到Pydantic模型的转换"""
        course_repo = CourseRepository(db_session)
        
        # 创建测试课程
        course_data = {
            "course_id": f"CONVERT_TEST_{int(datetime.now().timestamp())}",
            "course_name": "React开发指南",
            "category": "web_development",
            "original_price": Decimal("499.00"),
            "current_price": Decimal("349.00"),
            "duration_hours": 40,
            "difficulty_level": "advanced",
            "instructor": "React专家",
            "tags": ["react", "frontend", "javascript"],
            "prerequisites": ["JavaScript基础", "HTML/CSS"],
            "learning_outcomes": ["掌握React核心概念", "构建复杂应用"],
            "status": "active",
            "rating": 4.9,
            "student_count": 200
        }
        
        db_course = CourseDB(**course_data)
        db_session.add(db_course)
        await db_session.commit()
        await db_session.refresh(db_course)
        
        # 测试转换
        pydantic_course = course_repo.to_model(db_course)
        
        # 验证基础字段转换
        assert pydantic_course.course_id == db_course.course_id
        assert pydantic_course.course_name == db_course.course_name
        assert pydantic_course.current_price == db_course.current_price
        
        # 验证列表字段转换
        assert isinstance(pydantic_course.tags, list)
        assert isinstance(pydantic_course.prerequisites, list)
        assert isinstance(pydantic_course.learning_outcomes, list)
        
        # 验证列表内容
        assert "react" in pydantic_course.tags
        assert "JavaScript基础" in pydantic_course.prerequisites