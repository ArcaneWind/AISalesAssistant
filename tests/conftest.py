"""
测试配置文件 - pytest fixtures和共用配置
"""

import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.user_profile import UserProfile, UserProfileCreate
from app.services.profile_cache import UserProfileCache
from app.repositories.user_profile_repository import UserProfileRepository
from app.services.user_profile_service import UserProfileService


# 配置pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """测试数据库引擎 - 使用真实PostgreSQL"""
    from app.core.config import settings
    
    # 使用真实的PostgreSQL数据库，但使用测试数据库名
    test_db_url = settings.database_url_computed.replace(
        settings.db_name, 
        f"{settings.db_name}_test"
    )
    
    engine = create_async_engine(
        test_db_url,
        echo=False,  # 设为True可以看到SQL语句
        pool_pre_ping=True,
        pool_recycle=3600
    )
    
    # 创建表结构
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 测试结束后清理数据（可选）
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_db_engine) -> AsyncSession:
    """测试数据库会话"""
    async_session_maker = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def redis_client():
    """测试Redis客户端"""
    try:
        client = redis.from_url(
            "redis://localhost:6379/15",  # 使用测试数据库15
            encoding='utf-8',
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        
        # 测试连接
        await client.ping()
        
        # 清理测试数据
        await client.flushdb()
        
        yield client
        
        # 测试结束后清理
        await client.flushdb()
        await client.close()
    except Exception:
        # 如果Redis不可用，跳过相关测试
        pytest.skip("Redis not available")


@pytest_asyncio.fixture
async def profile_cache(redis_client):
    """测试用户画像缓存"""
    cache = UserProfileCache(redis_client)
    await cache.init_redis()
    
    yield cache
    
    await cache.close_redis()


@pytest_asyncio.fixture
def profile_repository():
    """测试用户画像仓库"""
    return UserProfileRepository()


@pytest_asyncio.fixture
async def profile_service(profile_cache, profile_repository):
    """测试用户画像服务"""
    service = UserProfileService(
        cache=profile_cache,
        repository=profile_repository
    )
    
    yield service


@pytest_asyncio.fixture
def sample_user_profile():
    """示例用户画像数据 - 同步fixture"""
    return UserProfile(
        user_id="test_user_003",
        session_id="test_session_003",
        channel_source="web",
        learning_goals=["Python编程", "数据分析"],
        pain_points=["时间不够", "基础薄弱"],
        motivation_type="career_advancement",
        urgency_level=4,
        budget_range="1000-5000",
        time_availability="moderate",
        learning_duration="medium_term",
        current_skill_level="beginner",
        related_experience=["Excel使用"],
        learning_ability="fast",
        communication_style="direct",
        decision_pattern="careful_research",
        response_speed="quick",
        price_sensitivity="medium",
        payment_preference="installment",
        discount_response="moderately_motivated",
        field_confidence={
            "learning_goals": 0.9,
            "motivation_type": 0.8,
            "urgency_level": 0.7
        },
        update_count=1,
        data_completeness=0.75
    )


@pytest.fixture
def sample_profile_create():
    """示例用户画像创建数据 - 同步fixture"""
    return UserProfileCreate(
        user_id="test_user_002",
        session_id="test_session_002", 
        channel_source="mobile",
        learning_goals=["机器学习"],
        motivation_type="skill_upgrade",
        urgency_level=3
    )


@pytest.fixture
def multiple_test_users():
    """多个测试用户数据 - 同步fixture"""
    return [
        UserProfile(
            user_id=f"test_user_{i:03d}",
            session_id=f"test_session_{i:03d}",
            channel_source="web" if i % 2 == 0 else "mobile",
            learning_goals=[f"技能{i}"],
            motivation_type="career_advancement" if i % 3 == 0 else "skill_upgrade",
            current_skill_level="beginner" if i % 2 == 0 else "intermediate",
            data_completeness=0.5 + (i % 5) * 0.1
        )
        for i in range(1, 11)
    ]