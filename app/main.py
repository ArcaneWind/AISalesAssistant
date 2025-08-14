from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError
import uvicorn

from app.core.config import settings
from app.core.redis import redis_manager
from app.core.qdrant import qdrant_manager
from app.core.database import init_database, close_database
from app.api.health import router as health_router
from app.api.profiles import router as profiles_router
from app.api.courses import router as courses_router
from app.api.coupons import router as coupons_router
from app.api.orders import router as orders_router
from app.api.agent import router as agent_router
from app.api.exceptions import (
    validation_exception_handler,
    http_exception_handler,
    database_exception_handler,
    general_exception_handler,
    business_exception_handler,
    BusinessException
)

# 简化日志配置
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("正在启动AI销售助手应用")
    
    try:
        # 初始化数据库连接
        await init_database()
        logger.info("PostgreSQL数据库初始化成功")
        
        await redis_manager.init_redis()
        logger.info("Redis初始化成功")

        await qdrant_manager.init_qdrant()
        logger.info("Qdrant初始化成功")
        
        logger.info("应用启动完成")
        
    except Exception as e:
        logger.error("应用启动失败", error=str(e))
        raise
    
    yield
    
    logger.info("正在关闭应用")
    await close_database()
    await redis_manager.close_redis()
    qdrant_manager.close_qdrant()
    logger.info("应用关闭完成")


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI销售助手 - 基于LangGraph + DSPy + LlamaIndex的多Agent销售对话系统",
    debug=settings.debug,
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(health_router)
app.include_router(profiles_router)
app.include_router(courses_router)
app.include_router(coupons_router)
app.include_router(orders_router)
app.include_router(agent_router)

# 注册异常处理器
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用 {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,  # 换个端口测试
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )