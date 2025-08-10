from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from typing import AsyncGenerator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# 创建基础模型类
Base = declarative_base()

# 全局数据库引擎
engine: AsyncEngine = None
async_session_maker: sessionmaker = None


async def init_database() -> None:
    """初始化数据库连接"""
    global engine, async_session_maker
    
    try:
        # 创建异步数据库引擎
        engine = create_async_engine(
            settings.database_url_computed,
            echo=settings.debug,  # 调试模式下打印SQL
            poolclass=NullPool if settings.environment == "testing" else None,
            pool_pre_ping=True,  # 连接前ping检查
            pool_recycle=3600,   # 连接回收时间1小时
        )
        
        # 创建异步session工厂
        async_session_maker = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("数据库连接初始化成功")
        
    except Exception as e:
        logger.error(f"数据库连接初始化失败: {e}")
        raise


async def close_database() -> None:
    """关闭数据库连接"""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("数据库连接已关闭")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话依赖注入函数"""
    if not async_session_maker:
        raise RuntimeError("数据库未初始化，请先调用 init_database()")
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class DatabaseService:
    """数据库服务类"""
    
    @property
    def engine(self):
        return engine
    
    @property 
    def session_maker(self):
        return async_session_maker
    
    async def health_check(self) -> dict:
        """数据库健康检查"""
        try:
            if not self.engine:
                return {"status": "error", "message": "数据库引擎未初始化"}
            
            # 执行简单查询测试连接
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                row = result.fetchone()
            
            return {
                "status": "healthy",
                "message": "数据库连接正常",
                "test_query_result": row[0] if row else None
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"数据库连接失败: {str(e)}"
            }
    
    async def get_connection_info(self) -> dict:
        """获取数据库连接信息"""
        if not self.engine:
            return {"status": "not_initialized"}
        
        return {
            "url": str(self.engine.url).replace(self.engine.url.password or '', '***'),
            "driver": self.engine.url.drivername,
            "database": self.engine.url.database,
            "host": self.engine.url.host,
            "port": self.engine.url.port,
            "pool_size": self.engine.pool.size() if hasattr(self.engine.pool, 'size') else None,
            "checked_out_connections": self.engine.pool.checkedout() if hasattr(self.engine.pool, 'checkedout') else None,
        }


# 全局数据库服务实例
database_service = DatabaseService()