"""
用户画像Redis缓存数据结构和管理
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from pydantic import BaseModel

from app.models.user_profile import UserProfile, UserProfileUpdate
from app.core.config import settings

logger = logging.getLogger(__name__)


class ProfileCacheConfig(BaseModel):
    """画像缓存配置"""
    
    # 缓存key前缀
    PROFILE_KEY_PREFIX: str = "user_profile:"
    SESSION_KEY_PREFIX: str = "user_session:"
    STATS_KEY_PREFIX: str = "profile_stats:"
    COMPLETENESS_KEY_PREFIX: str = "profile_completeness:"
    
    # 缓存过期时间(秒)
    PROFILE_EXPIRY: int = 3600 * 24  # 24小时
    SESSION_EXPIRY: int = 3600 * 2   # 2小时
    STATS_EXPIRY: int = 3600 * 6     # 6小时
    HOT_USER_EXPIRY: int = 3600 * 48 # 热点用户48小时
    
    # 缓存策略
    MAX_CACHE_SIZE: int = 10000      # 最大缓存条数
    CACHE_HIT_THRESHOLD: int = 5     # 热点用户判定阈值
    BATCH_SIZE: int = 100            # 批量操作大小


class UserProfileCache:
    """用户画像缓存管理器"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.config = ProfileCacheConfig()
        self._hit_stats = {}  # 缓存命中统计
        
    async def init_redis(self) -> None:
        """初始化Redis连接"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                settings.redis_url_computed,
                encoding='utf-8',
                decode_responses=True,
                socket_timeout=30,
                socket_connect_timeout=30,
                retry_on_timeout=True,
                max_connections=20
            )
        
        # 测试连接
        try:
            await self.redis_client.ping()
            logger.info("用户画像缓存Redis连接初始化成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise
    
    async def close_redis(self) -> None:
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
    
    def _get_profile_key(self, user_id: str) -> str:
        """获取用户画像缓存key"""
        return f"{self.config.PROFILE_KEY_PREFIX}{user_id}"
    
    def _get_session_key(self, session_id: str) -> str:
        """获取会话缓存key"""
        return f"{self.config.SESSION_KEY_PREFIX}{session_id}"
    
    def _get_stats_key(self, date: str = None) -> str:
        """获取统计缓存key"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        return f"{self.config.STATS_KEY_PREFIX}{date}"
    
    def _get_completeness_key(self, completeness_range: str) -> str:
        """获取完整度范围缓存key"""
        return f"{self.config.COMPLETENESS_KEY_PREFIX}{completeness_range}"
    
    def _serialize_profile(self, profile: UserProfile) -> str:
        """序列化用户画像为JSON"""
        try:
            return profile.model_dump_json()
        except Exception as e:
            logger.error(f"序列化用户画像失败: {e}")
            raise
    
    def _deserialize_profile(self, data: str) -> UserProfile:
        """反序列化JSON为用户画像"""
        try:
            profile_dict = json.loads(data)
            return UserProfile.model_validate(profile_dict)
        except Exception as e:
            logger.error(f"反序列化用户画像失败: {e}")
            raise
    
    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户画像缓存"""
        try:
            key = self._get_profile_key(user_id)
            data = await self.redis_client.get(key)
            
            if data:
                # 更新命中统计
                self._hit_stats[user_id] = self._hit_stats.get(user_id, 0) + 1
                
                # 如果是热点用户，延长过期时间
                if self._hit_stats[user_id] >= self.config.CACHE_HIT_THRESHOLD:
                    await self.redis_client.expire(key, self.config.HOT_USER_EXPIRY)
                
                logger.debug(f"缓存命中: {user_id}")
                return self._deserialize_profile(data)
            
            logger.debug(f"缓存未命中: {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"获取用户画像缓存失败: {e}")
            return None
    
    async def set_profile(
        self, 
        user_id: str, 
        profile: UserProfile, 
        expiry: Optional[int] = None
    ) -> bool:
        """设置用户画像缓存"""
        try:
            key = self._get_profile_key(user_id)
            data = self._serialize_profile(profile)
            
            expiry = expiry or self.config.PROFILE_EXPIRY
            
            # 设置缓存
            await self.redis_client.setex(key, expiry, data)
            
            # 更新会话映射
            await self._update_session_mapping(profile.session_id, user_id)
            
            # 更新完整度索引
            await self._update_completeness_index(profile)
            
            logger.debug(f"用户画像缓存设置成功: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"设置用户画像缓存失败: {e}")
            return False
    
    async def update_profile(
        self, 
        user_id: str, 
        profile_update: UserProfileUpdate
    ) -> bool:
        """增量更新用户画像缓存"""
        try:
            # 先获取现有画像
            current_profile = await self.get_profile(user_id)
            if not current_profile:
                logger.warning(f"用户画像缓存不存在，无法增量更新: {user_id}")
                return False
            
            # 应用增量更新
            update_dict = profile_update.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                if value is not None:
                    setattr(current_profile, field, value)
            
            # 更新元信息
            current_profile.updated_at = datetime.now()
            current_profile.update_count += 1
            current_profile.update_completeness()
            
            # 保存更新后的画像
            return await self.set_profile(user_id, current_profile)
            
        except Exception as e:
            logger.error(f"增量更新用户画像缓存失败: {e}")
            return False
    
    async def delete_profile(self, user_id: str) -> bool:
        """删除用户画像缓存"""
        try:
            key = self._get_profile_key(user_id)
            result = await self.redis_client.delete(key)
            
            # 清理会话映射
            profile = await self.get_profile(user_id)
            if profile:
                await self._remove_session_mapping(profile.session_id)
            
            # 清理命中统计
            if user_id in self._hit_stats:
                del self._hit_stats[user_id]
            
            logger.debug(f"用户画像缓存删除: {user_id}, 结果: {result}")
            return result > 0
            
        except Exception as e:
            logger.error(f"删除用户画像缓存失败: {e}")
            return False
    
    async def get_profile_by_session(self, session_id: str) -> Optional[UserProfile]:
        """根据会话ID获取用户画像"""
        try:
            session_key = self._get_session_key(session_id)
            user_id = await self.redis_client.get(session_key)
            
            if user_id:
                return await self.get_profile(user_id)
            
            return None
            
        except Exception as e:
            logger.error(f"根据会话ID获取画像失败: {e}")
            return None
    
    async def _update_session_mapping(self, session_id: str, user_id: str) -> None:
        """更新会话到用户ID的映射"""
        try:
            session_key = self._get_session_key(session_id)
            await self.redis_client.setex(
                session_key, 
                self.config.SESSION_EXPIRY, 
                user_id
            )
        except Exception as e:
            logger.error(f"更新会话映射失败: {e}")
    
    async def _remove_session_mapping(self, session_id: str) -> None:
        """删除会话映射"""
        try:
            session_key = self._get_session_key(session_id)
            await self.redis_client.delete(session_key)
        except Exception as e:
            logger.error(f"删除会话映射失败: {e}")
    
    async def _update_completeness_index(self, profile: UserProfile) -> None:
        """更新完整度索引"""
        try:
            completeness = profile.data_completeness
            
            # 根据完整度分段
            if completeness >= 0.8:
                range_key = "high"  # 80%+
            elif completeness >= 0.5:
                range_key = "medium"  # 50-80%
            elif completeness >= 0.3:
                range_key = "low"  # 30-50%
            else:
                range_key = "minimal"  # <30%
            
            completeness_key = self._get_completeness_key(range_key)
            
            # 使用有序集合存储，分数为完整度
            await self.redis_client.zadd(
                completeness_key, 
                {profile.user_id: completeness}
            )
            
            # 设置过期时间
            await self.redis_client.expire(completeness_key, self.config.STATS_EXPIRY)
            
        except Exception as e:
            logger.error(f"更新完整度索引失败: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            # 获取Redis基础信息
            info = await self.redis_client.info()
            
            # 统计各类型key数量
            profile_count = 0
            session_count = 0
            
            # 获取所有相关key
            profile_pattern = f"{self.config.PROFILE_KEY_PREFIX}*"
            session_pattern = f"{self.config.SESSION_KEY_PREFIX}*"
            
            async for key in self.redis_client.scan_iter(match=profile_pattern, count=100):
                profile_count += 1
            
            async for key in self.redis_client.scan_iter(match=session_pattern, count=100):
                session_count += 1
            
            return {
                "redis_info": {
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                },
                "cache_counts": {
                    "user_profiles": profile_count,
                    "user_sessions": session_count,
                },
                "hit_stats": self._hit_stats.copy(),
                "config": self.config.model_dump()
            }
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {"error": str(e)}


# 全局缓存管理器实例
profile_cache = UserProfileCache()