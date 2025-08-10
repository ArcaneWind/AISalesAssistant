"""
用户画像缓存层测试
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from app.services.profile_cache import UserProfileCache
from app.models.user_profile import UserProfile, UserProfileUpdate


@pytest.mark.asyncio
class TestUserProfileCache:
    """用户画像缓存测试"""
    
    async def test_init_and_close_redis(self, redis_client):
        """测试Redis连接初始化和关闭"""
        cache = UserProfileCache(redis_client)
        
        # 测试初始化
        await cache.init_redis()
        
        # 测试连接是否正常
        await cache.redis_client.ping()
        
        # 测试关闭
        await cache.close_redis()
    
    async def test_set_and_get_profile(self, profile_cache, sample_user_profile):
        """测试设置和获取用户画像缓存"""
        profile = sample_user_profile
        
        # 测试设置缓存
        result = await profile_cache.set_profile(profile.user_id, profile)
        assert result == True
        
        # 测试获取缓存
        cached_profile = await profile_cache.get_profile(profile.user_id)
        assert cached_profile is not None
        assert cached_profile.user_id == profile.user_id
        assert cached_profile.session_id == profile.session_id
        assert cached_profile.learning_goals == profile.learning_goals
        assert cached_profile.data_completeness == profile.data_completeness
    
    async def test_get_nonexistent_profile(self, profile_cache):
        """测试获取不存在的用户画像"""
        result = await profile_cache.get_profile("nonexistent_user")
        assert result is None
    
    async def test_update_profile(self, profile_cache, sample_user_profile):
        """测试增量更新用户画像缓存"""
        profile = sample_user_profile
        
        # 先设置缓存
        await profile_cache.set_profile(profile.user_id, profile)
        
        # 创建更新数据
        update_data = UserProfileUpdate(
            learning_goals=["新的学习目标", "数据科学"],
            urgency_level=5,
            field_confidence={"learning_goals": 0.95}
        )
        
        # 测试增量更新
        result = await profile_cache.update_profile(profile.user_id, update_data)
        assert result == True
        
        # 验证更新结果
        updated_profile = await profile_cache.get_profile(profile.user_id)
        assert updated_profile.learning_goals == ["新的学习目标", "数据科学"]
        assert updated_profile.urgency_level == 5
        assert updated_profile.update_count == profile.update_count + 1
        assert updated_profile.field_confidence["learning_goals"] == 0.95
    
    async def test_update_nonexistent_profile(self, profile_cache):
        """测试更新不存在的用户画像"""
        update_data = UserProfileUpdate(learning_goals=["测试"])
        
        result = await profile_cache.update_profile("nonexistent_user", update_data)
        assert result == False
    
    async def test_delete_profile(self, profile_cache, sample_user_profile):
        """测试删除用户画像缓存"""
        profile = sample_user_profile
        
        # 先设置缓存
        await profile_cache.set_profile(profile.user_id, profile)
        
        # 验证存在
        cached_profile = await profile_cache.get_profile(profile.user_id)
        assert cached_profile is not None
        
        # 测试删除
        result = await profile_cache.delete_profile(profile.user_id)
        assert result == True
        
        # 验证已删除
        cached_profile = await profile_cache.get_profile(profile.user_id)
        assert cached_profile is None
    
    async def test_get_profile_by_session(self, profile_cache, sample_user_profile):
        """测试根据会话ID获取用户画像"""
        profile = sample_user_profile
        
        # 先设置缓存
        await profile_cache.set_profile(profile.user_id, profile)
        
        # 测试根据会话ID获取
        cached_profile = await profile_cache.get_profile_by_session(profile.session_id)
        assert cached_profile is not None
        assert cached_profile.user_id == profile.user_id
        assert cached_profile.session_id == profile.session_id
    
    async def test_batch_get_profiles(self, profile_cache, multiple_test_users):
        """测试批量获取用户画像"""
        # 先批量设置缓存
        for profile in multiple_test_users[:5]:  # 只设置前5个
            await profile_cache.set_profile(profile.user_id, profile)
        
        # 测试批量获取（包含存在和不存在的）
        user_ids = [profile.user_id for profile in multiple_test_users]
        results = await profile_cache.batch_get_profiles(user_ids)
        
        assert len(results) == len(user_ids)
        
        # 验证前5个存在
        for i in range(5):
            user_id = multiple_test_users[i].user_id
            assert user_id in results
            assert results[user_id] is not None
            assert results[user_id].user_id == user_id
        
        # 验证后5个不存在
        for i in range(5, 10):
            user_id = multiple_test_users[i].user_id
            assert user_id in results
            assert results[user_id] is None
    
    async def test_batch_set_profiles(self, profile_cache, multiple_test_users):
        """测试批量设置用户画像"""
        profiles = multiple_test_users[:3]
        
        # 测试批量设置
        success_count = await profile_cache.batch_set_profiles(profiles)
        assert success_count >= 0  # 应该成功设置一些
        
        # 验证设置结果
        for profile in profiles:
            cached_profile = await profile_cache.get_profile(profile.user_id)
            assert cached_profile is not None
            assert cached_profile.user_id == profile.user_id
    
    async def test_get_profiles_by_completeness(self, profile_cache, multiple_test_users):
        """测试按完整度获取用户画像"""
        # 设置一些用户画像
        for profile in multiple_test_users:
            await profile_cache.set_profile(profile.user_id, profile)
        
        # 等待索引更新
        await asyncio.sleep(0.1)
        
        # 测试按完整度获取
        high_completeness_users = await profile_cache.get_profiles_by_completeness(
            min_completeness=0.7,
            limit=5
        )
        
        assert isinstance(high_completeness_users, list)
        # 由于测试数据的完整度设置，应该有一些结果
        for user_id in high_completeness_users:
            assert isinstance(user_id, str)
    
    async def test_cache_expiry(self, profile_cache, sample_user_profile):
        """测试缓存过期"""
        profile = sample_user_profile
        
        # 设置短过期时间的缓存
        await profile_cache.set_profile(profile.user_id, profile, expiry=1)
        
        # 立即获取应该存在
        cached_profile = await profile_cache.get_profile(profile.user_id)
        assert cached_profile is not None
        
        # 等待过期
        await asyncio.sleep(2)
        
        # 过期后应该获取不到
        cached_profile = await profile_cache.get_profile(profile.user_id)
        assert cached_profile is None
    
    async def test_hot_user_detection(self, profile_cache, sample_user_profile):
        """测试热点用户检测"""
        profile = sample_user_profile
        
        # 设置缓存
        await profile_cache.set_profile(profile.user_id, profile)
        
        # 多次访问触发热点用户检测
        for _ in range(6):  # 超过阈值
            await profile_cache.get_profile(profile.user_id)
        
        # 验证命中统计
        assert profile_cache._hit_stats.get(profile.user_id, 0) >= 6
    
    async def test_get_cache_stats(self, profile_cache, sample_user_profile):
        """测试获取缓存统计信息"""
        profile = sample_user_profile
        
        # 设置一些缓存数据
        await profile_cache.set_profile(profile.user_id, profile)
        
        # 获取统计信息
        stats = await profile_cache.get_cache_stats()
        
        assert "redis_info" in stats
        assert "cache_counts" in stats
        assert "hit_stats" in stats
        assert "config" in stats
        
        assert isinstance(stats["redis_info"], dict)
        assert isinstance(stats["cache_counts"], dict)
        assert isinstance(stats["hit_stats"], dict)
    
    async def test_clear_cache(self, profile_cache, multiple_test_users):
        """测试清理缓存"""
        # 设置一些缓存数据
        for profile in multiple_test_users[:3]:
            await profile_cache.set_profile(profile.user_id, profile)
        
        # 验证数据存在
        for profile in multiple_test_users[:3]:
            cached_profile = await profile_cache.get_profile(profile.user_id)
            assert cached_profile is not None
        
        # 清理缓存
        deleted_count = await profile_cache.clear_cache()
        assert deleted_count >= 0
        
        # 验证数据已清理
        for profile in multiple_test_users[:3]:
            cached_profile = await profile_cache.get_profile(profile.user_id)
            assert cached_profile is None
    
    async def test_serialization_error_handling(self, profile_cache):
        """测试序列化错误处理"""
        # 创建一个包含不可序列化对象的画像（模拟错误情况）
        profile = UserProfile(
            user_id="error_test",
            session_id="error_session",
            channel_source="test"
        )
        
        # 正常情况应该可以序列化
        serialized = profile_cache._serialize_profile(profile)
        assert isinstance(serialized, str)
        
        # 反序列化
        deserialized = profile_cache._deserialize_profile(serialized)
        assert deserialized.user_id == "error_test"
    
    async def test_redis_connection_error_handling(self):
        """测试Redis连接错误处理"""
        # 使用无效的Redis配置
        invalid_cache = UserProfileCache()
        
        # 模拟连接失败
        with pytest.raises(Exception):
            await invalid_cache.init_redis()


class TestProfileCacheConfig:
    """缓存配置测试"""
    
    def test_cache_config_defaults(self, profile_cache):
        """测试缓存配置默认值"""
        config = profile_cache.config
        
        assert config.PROFILE_KEY_PREFIX == "user_profile:"
        assert config.SESSION_KEY_PREFIX == "user_session:"
        assert config.PROFILE_EXPIRY == 3600 * 24  # 24小时
        assert config.SESSION_EXPIRY == 3600 * 2   # 2小时
        assert config.MAX_CACHE_SIZE == 10000
        assert config.CACHE_HIT_THRESHOLD == 5
    
    def test_key_generation(self, profile_cache):
        """测试缓存key生成"""
        user_id = "test_user_123"
        session_id = "test_session_456"
        
        profile_key = profile_cache._get_profile_key(user_id)
        session_key = profile_cache._get_session_key(session_id)
        stats_key = profile_cache._get_stats_key("2024-01-01")
        completeness_key = profile_cache._get_completeness_key("high")
        
        assert profile_key == "user_profile:test_user_123"
        assert session_key == "user_session:test_session_456"
        assert stats_key == "profile_stats:2024-01-01"
        assert completeness_key == "profile_completeness:high"