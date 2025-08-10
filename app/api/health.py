from fastapi import APIRouter, HTTPException
import logging

from app.core.config import settings
from app.core.redis import redis_manager
from app.core.qdrant import qdrant_manager
from app.core.database import database_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("")
async def health_check():
    """基础健康检查接口"""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }


@router.get("/database")
async def database_health():
    """数据库连接健康检查"""
    health_status = {
        "postgresql": False,
        "redis": False,
        "qdrant": False,
        "overall": False,
        "details": {}
    }
    
    try:
        # 测试PostgreSQL连接
        pg_status = await database_service.health_check()
        health_status["postgresql"] = pg_status["status"] == "healthy"
        health_status["details"]["postgresql"] = pg_status["message"]
        
        # 测试Redis连接
        if redis_manager.redis_pool:
            try:
                await redis_manager.redis_pool.ping()
                health_status["redis"] = True
                health_status["details"]["redis"] = "连接正常"
            except Exception as e:
                health_status["details"]["redis"] = f"连接失败: {str(e)}"
        else:
            health_status["details"]["redis"] = "连接池未初始化"
        
        # 测试Qdrant连接
        if qdrant_manager.client:
            try:
                collections = qdrant_manager.client.get_collections()
                health_status["qdrant"] = True
                health_status["details"]["qdrant"] = f"连接正常, 集合数量: {len(collections.collections)}"
            except Exception as e:
                health_status["details"]["qdrant"] = f"连接失败: {str(e)}"
        else:
            health_status["details"]["qdrant"] = "客户端未初始化"
        
        # 整体状态
        health_status["overall"] = all([
            health_status["postgresql"],
            health_status["redis"],
            health_status["qdrant"]
        ])
        
        if not health_status["overall"]:
            logger.warning("数据库连接检查部分失败", extra=health_status)
            return health_status
            
        logger.info("数据库连接检查全部通过")
        return health_status
        
    except Exception as e:
        logger.error(f"数据库健康检查异常: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail={
                "error": "数据库连接失败",
                "message": str(e),
                "status": health_status
            }
        )


@router.get("/detailed")
async def detailed_health():
    """详细健康检查，包括各组件状态"""
    status = {
        "app": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "debug": settings.debug
        },
        "databases": {},
        "overall": True
    }
    
    # Redis状态
    try:
        if redis_manager.redis_pool:
            ping_result = await redis_manager.redis_pool.ping()
            info = await redis_manager.redis_pool.info()
            status["databases"]["redis"] = {
                "status": "healthy",
                "ping": ping_result,
                "version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory_human")
            }
        else:
            status["databases"]["redis"] = {"status": "not_initialized"}
            status["overall"] = False
    except Exception as e:
        status["databases"]["redis"] = {"status": "error", "error": str(e)}
        status["overall"] = False
    
    # Qdrant状态
    try:
        if qdrant_manager.client:
            collections = qdrant_manager.client.get_collections()
            collection_info = {}
            for collection in collections.collections:
                try:
                    info = qdrant_manager.get_collection_info(collection.name)
                    if info:
                        collection_info[collection.name] = info
                except:
                    collection_info[collection.name] = {"status": "error"}
                    
            status["databases"]["qdrant"] = {
                "status": "healthy",
                "collections_count": len(collections.collections),
                "collections": collection_info
            }
        else:
            status["databases"]["qdrant"] = {"status": "not_initialized"}
            status["overall"] = False
    except Exception as e:
        status["databases"]["qdrant"] = {"status": "error", "error": str(e)}
        status["overall"] = False
    
    return status