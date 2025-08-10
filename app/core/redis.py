import redis.asyncio as aioredis
import json
from typing import Any, Optional, Union
from app.core.config import settings
import structlog

"redis连接管理器以及会话缓存管理器"

logger = structlog.get_logger()


class RedisManager:
    """Redis连接管理器"""

    def __init__(self):
        self.redis_pool: Optional[aioredis.Redis] = None

    async def init_redis(self) -> None:
        """初始化Redis连接池"""
        try:
            self.redis_pool = await aioredis.from_url(
                settings.redis_url_computed,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True
            )
            # 测试连接
            await self.redis_pool.ping()
            logger.info("Redis连接初始化成功")
        except Exception as e:
            logger.error("Redis连接初始化失败", error=str(e))
            raise

    async def close_redis(self) -> None:
        """关闭Redis连接"""
        if self.redis_pool:
            await self.redis_pool.close()
            logger.info("Redis连接已关闭")

    async def get(self, key: str) -> Optional[str]:
        """获取缓存值"""
        try:
            return await self.redis_pool.get(key)
        except Exception as e:
            logger.error("Redis获取数据失败", key=key, error=str(e))
            return None

    async def set(
            self,
            key: str,
            value: Union[str, dict, list],
            expire: Optional[int] = None
    ) -> bool:
        """设置缓存值"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)

            result = await self.redis_pool.set(key, value, ex=expire)
            return result
        except Exception as e:
            logger.error("Redis设置数据失败", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            result = await self.redis_pool.delete(key)
            return bool(result)
        except Exception as e:
            logger.error("Redis删除数据失败", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """检查key是否存在"""
        try:
            result = await self.redis_pool.exists(key)
            return bool(result)
        except Exception as e:
            logger.error("Redis检查key存在性失败", key=key, error=str(e))
            return False

    async def hget(self, name: str, key: str) -> Optional[str]:
        """获取hash字段值"""
        try:
            return await self.redis_pool.hget(name, key)
        except Exception as e:
            logger.error("Redis获取hash数据失败", hash_name=name, key=key, error=str(e))
            return None

    async def hset(self, name: str, key: str, value: Any) -> bool:
        """设置hash字段值"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            result = await self.redis_pool.hset(name, key, value)
            return bool(result)
        except Exception as e:
            logger.error("Redis设置hash数据失败", hash_name=name, key=key, error=str(e))
            return False

    async def hgetall(self, name: str) -> dict:
        """获取hash所有字段"""
        try:
            return await self.redis_pool.hgetall(name)
        except Exception as e:
            logger.error("Redis获取hash所有数据失败", hash_name=name, error=str(e))
            return {}

    async def expire(self, key: str, time: int) -> bool:
        """设置key过期时间"""
        try:
            result = await self.redis_pool.expire(key, time)
            return bool(result)
        except Exception as e:
            logger.error("Redis设置过期时间失败", key=key, error=str(e))
            return False


# 全局Redis管理器实例
redis_manager = RedisManager()


def get_redis_client():
    """获取Redis客户端实例"""
    return redis_manager.redis_pool


class SessionCache:
    """会话缓存管理类"""

    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager
        self.session_prefix = "session:"
        self.user_prefix = "user:"
        self.default_expire = 3600  # 1小时过期

    async def get_session(self, session_id: str) -> Optional[dict]:
        """获取会话数据"""
        key = f"{self.session_prefix}{session_id}"
        data = await self.redis.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    async def set_session(self, session_id: str, session_data: dict, expire: Optional[int] = None) -> bool:
        """设置会话数据"""
        key = f"{self.session_prefix}{session_id}"
        expire = expire or self.default_expire
        return await self.redis.set(key, session_data, expire)

    async def update_session(self, session_id: str, updates: dict) -> bool:
        """更新会话数据"""
        session_data = await self.get_session(session_id)
        if session_data is None:
            session_data = {}

        session_data.update(updates)
        return await self.set_session(session_id, session_data)

    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        key = f"{self.session_prefix}{session_id}"
        return await self.redis.delete(key)

    async def get_user_context(self, user_id: str) -> Optional[dict]:
        """获取用户上下文"""
        key = f"{self.user_prefix}{user_id}"
        data = await self.redis.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    async def set_user_context(self, user_id: str, context: dict, expire: Optional[int] = None) -> bool:
        """设置用户上下文"""
        key = f"{self.user_prefix}{user_id}"
        expire = expire or self.default_expire * 24  # 24小时过期
        return await self.redis.set(key, context, expire)


# 全局会话缓存实例
session_cache = SessionCache(redis_manager)