"""
通用缓存工具
参考用户画像模块的缓存实现，为优惠系统提供简单的Redis缓存功能
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class SimpleCache:
    """简单缓存管理器"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None, key_prefix: str = ""):
        self.redis_client = redis_client
        self.key_prefix = key_prefix
        
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
            logger.info(f"{self.key_prefix}缓存Redis连接初始化成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise
    
    async def close_redis(self) -> None:
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
    
    def _get_key(self, key: str) -> str:
        """获取完整的缓存key"""
        return f"{self.key_prefix}{key}" if self.key_prefix else key
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            full_key = self._get_key(key)
            data = await self.redis_client.get(full_key)
            
            if data:
                return json.loads(data)
            
            return None
            
        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存值"""
        try:
            full_key = self._get_key(key)
            data = json.dumps(value, default=str, ensure_ascii=False)
            
            await self.redis_client.setex(full_key, ttl, data)
            return True
            
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            full_key = self._get_key(key)
            result = await self.redis_client.delete(full_key)
            return result > 0
            
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有缓存"""
        try:
            full_pattern = self._get_key(pattern)
            keys = []
            
            async for key in self.redis_client.scan_iter(match=full_pattern):
                keys.append(key)
            
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
            
        except Exception as e:
            logger.error(f"删除模式缓存失败 {pattern}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            full_key = self._get_key(key)
            return await self.redis_client.exists(full_key) > 0
        except Exception as e:
            logger.error(f"检查缓存存在失败 {key}: {e}")
            return False


# 各个模块的缓存实例
course_cache = SimpleCache(key_prefix="course:")
coupon_cache = SimpleCache(key_prefix="coupon:")
order_cache = SimpleCache(key_prefix="order:")
price_cache = SimpleCache(key_prefix="price:")