"""
用户画像业务服务层测试
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.services.user_profile_service import UserProfileService
from app.repositories.user_profile_repository import UserProfileRepository
from app.services.profile_cache import UserProfileCache
from app.models.user_profile import UserProfile, UserProfileCreate, UserProfileUpdate
from app.core.config import settings


class TestUserProfileService:
    """用户画像业务服务测试"""
    
    @pytest.fixture
    def sample_profile(self):
        """测试用户画像"""
        return UserProfile(
            user_id="service_test_user",
            session_id="service_test_session",
            channel_source="web",
            learning_goals=["Python编程"],
            motivation_type="career_advancement",
            urgency_level=4,
            data_completeness=0.7
        )
    
    @pytest.fixture
    def sample_create_data(self):
        """测试用户画像创建数据"""
        return UserProfileCreate(
            user_id="service_create_user",
            session_id="service_create_session",
            channel_source="mobile",
            learning_goals=["数据科学"],
            motivation_type="skill_upgrade"
        )
    
    @pytest_asyncio.fixture
    async def db_session(self):
        """数据库会话"""
        test_db_url = settings.database_url_computed.replace(
            settings.db_name, 
            f"{settings.db_name}_test"
        )
        
        engine = create_async_engine(
            test_db_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
        
        await engine.dispose()
    
    @pytest_asyncio.fixture
    async def redis_client(self):
        """Redis客户端"""
        import redis.asyncio as redis
        try:
            client = redis.from_url(
                "redis://localhost:6379/15",
                encoding='utf-8',
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            await client.ping()
            await client.flushdb()  # 清理测试数据
            
            yield client
            
            await client.flushdb()  # 清理测试数据
            await client.aclose()
        except Exception:
            pytest.skip("Redis not available")
    
    @pytest_asyncio.fixture
    async def profile_service(self, db_session, redis_client):
        """用户画像服务"""
        cache = UserProfileCache(redis_client)
        await cache.init_redis()
        
        repository = UserProfileRepository()
        
        service = UserProfileService(
            cache=cache,
            repository=repository
        )
        
        yield service
        
        await cache.close_redis()
    
    @pytest.mark.asyncio
    async def test_create_profile(self, profile_service, sample_create_data):
        """测试创建用户画像"""
        # 测试创建
        created_profile = await profile_service.create_profile(sample_create_data)
        
        assert created_profile.user_id == sample_create_data.user_id
        assert created_profile.session_id == sample_create_data.session_id
        assert created_profile.learning_goals == sample_create_data.learning_goals
        assert created_profile.data_completeness > 0  # 应该计算了完整度
        
        print(f"成功创建用户画像服务: {created_profile.user_id}")
    
    @pytest.mark.asyncio
    async def test_get_profile(self, profile_service, sample_profile):
        """测试获取用户画像"""
        # 先创建
        create_data = UserProfileCreate(
            user_id=sample_profile.user_id,
            session_id=sample_profile.session_id,
            channel_source=sample_profile.channel_source,
            learning_goals=sample_profile.learning_goals,
            motivation_type=sample_profile.motivation_type
        )
        await profile_service.create_profile(create_data)
        
        # 测试获取
        result = await profile_service.get_profile(sample_profile.user_id)
        
        assert result is not None
        assert result.user_id == sample_profile.user_id
        assert result.learning_goals == sample_profile.learning_goals
        
        print(f"成功获取用户画像: {result.user_id}")
    
    @pytest.mark.asyncio
    async def test_update_profile(self, profile_service, sample_profile):
        """测试更新用户画像"""
        # 先创建
        create_data = UserProfileCreate(
            user_id=sample_profile.user_id,
            session_id=sample_profile.session_id,
            channel_source=sample_profile.channel_source,
            learning_goals=sample_profile.learning_goals,
            motivation_type=sample_profile.motivation_type
        )
        await profile_service.create_profile(create_data)
        
        # 准备更新数据
        update_data = UserProfileUpdate(
            learning_goals=["Python编程", "机器学习"],
            urgency_level=5,
            budget_range="5000-10000"
        )
        
        # 测试更新
        updated_profile = await profile_service.update_profile(
            sample_profile.user_id, 
            update_data
        )
        
        assert updated_profile is not None
        assert updated_profile.learning_goals == ["Python编程", "机器学习"]
        assert updated_profile.urgency_level == 5
        assert updated_profile.budget_range == "5000-10000"
        
        print(f"成功更新用户画像: {updated_profile.user_id}")
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, profile_service, sample_profile):
        """测试缓存集成"""
        # 先创建
        create_data = UserProfileCreate(
            user_id=sample_profile.user_id,
            session_id=sample_profile.session_id,
            channel_source=sample_profile.channel_source,
            learning_goals=sample_profile.learning_goals,
            motivation_type=sample_profile.motivation_type
        )
        await profile_service.create_profile(create_data)
        
        # 第一次获取(从数据库)
        profile1 = await profile_service.get_profile(sample_profile.user_id)
        assert profile1 is not None
        
        # 第二次获取(应该从缓存)
        profile2 = await profile_service.get_profile(sample_profile.user_id)
        assert profile2 is not None
        assert profile1.user_id == profile2.user_id
        
        print("缓存集成测试通过")
    
    @pytest.mark.asyncio
    async def test_service_without_cache(self, sample_profile):
        """测试没有缓存的服务"""
        repository = UserProfileRepository()
        service = UserProfileService(cache=None, repository=repository)
        
        # 测试创建
        create_data = UserProfileCreate(
            user_id=sample_profile.user_id,
            session_id=sample_profile.session_id,
            channel_source=sample_profile.channel_source,
            learning_goals=sample_profile.learning_goals,
            motivation_type=sample_profile.motivation_type
        )
        created_profile = await service.create_profile(create_data)
        
        assert created_profile.user_id == sample_profile.user_id
        
        print("无缓存服务测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])