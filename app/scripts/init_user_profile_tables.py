"""
用户画像数据库表初始化迁移脚本

运行方式:
python -m app.scripts.init_user_profile_tables
"""

import asyncio
import logging
from sqlalchemy import text

from app.core.database import init_database, engine, close_database
from app.models.database.user_profile_db import UserProfileDB, UserProfileHistory, UserProfileStats
from app.core.database import Base

logger = logging.getLogger(__name__)


async def create_user_profile_tables():
    """创建用户画像相关数据表"""
    try:
        # 初始化数据库连接
        await init_database()
        
        # 导入全局engine
        from app.core.database import engine as db_engine
        
        if not db_engine:
            raise RuntimeError("数据库引擎未初始化")
        
        logger.info("开始创建用户画像数据表...")
        
        # 创建所有表
        async with db_engine.begin() as conn:
            # 创建用户画像相关表
            await conn.run_sync(Base.metadata.create_all)
            logger.info("用户画像数据表创建成功")
            
            # 创建额外的约束和索引
            await _create_additional_constraints(conn)
            
            # 插入初始化数据
            await _insert_initial_data(conn)
            
        logger.info("用户画像数据库初始化完成")
        
    except Exception as e:
        logger.error(f"创建用户画像数据表失败: {e}")
        raise
    finally:
        await close_database()


async def _create_additional_constraints(conn):
    """创建额外的约束和索引"""
    try:
        # 创建检查约束
        constraints_sql = [
            # 紧急程度约束
            """
            ALTER TABLE user_profiles 
            ADD CONSTRAINT chk_urgency_level 
            CHECK (urgency_level IS NULL OR urgency_level BETWEEN 1 AND 5)
            """,
            
            # 数据完整度约束
            """
            ALTER TABLE user_profiles 
            ADD CONSTRAINT chk_data_completeness 
            CHECK (data_completeness >= 0.0 AND data_completeness <= 1.0)
            """,
            
            # 更新次数约束
            """
            ALTER TABLE user_profiles 
            ADD CONSTRAINT chk_update_count 
            CHECK (update_count >= 0)
            """
        ]
        
        for constraint_sql in constraints_sql:
            try:
                await conn.execute(text(constraint_sql))
                logger.info(f"约束创建成功")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"约束已存在，跳过")
                else:
                    logger.warning(f"创建约束失败: {e}")
        
    except Exception as e:
        logger.error(f"创建额外约束失败: {e}")


async def _insert_initial_data(conn):
    """插入初始化数据"""
    try:
        # 创建初始统计记录
        from datetime import datetime
        
        initial_stats_sql = """
        INSERT INTO user_profile_stats 
        (stat_date, total_profiles, complete_profiles, avg_completeness, avg_confidence, created_at)
        VALUES (:stat_date, 0, 0, 0.0, 0.0, :created_at)
        ON CONFLICT DO NOTHING
        """
        
        await conn.execute(
            text(initial_stats_sql),
            {
                "stat_date": datetime.now(),
                "created_at": datetime.now()
            }
        )
        
        logger.info("初始化数据插入成功")
        
    except Exception as e:
        logger.error(f"插入初始化数据失败: {e}")


async def drop_user_profile_tables():
    """删除用户画像相关数据表（谨慎使用）"""
    try:
        await init_database()
        
        # 导入全局engine
        from app.core.database import engine as db_engine
        
        if not db_engine:
            raise RuntimeError("数据库引擎未初始化")
            
        logger.warning("开始删除用户画像数据表...")
        
        async with db_engine.begin() as conn:
            # 删除表的顺序很重要，先删除依赖表
            drop_tables_sql = [
                "DROP TABLE IF EXISTS user_profile_history CASCADE",
                "DROP TABLE IF EXISTS user_profile_stats CASCADE", 
                "DROP TABLE IF EXISTS user_profiles CASCADE"
            ]
            
            for drop_sql in drop_tables_sql:
                await conn.execute(text(drop_sql))
                logger.warning(f"表删除成功: {drop_sql}")
        
        logger.warning("用户画像数据表删除完成")
        
    except Exception as e:
        logger.error(f"删除用户画像数据表失败: {e}")
        raise
    finally:
        await close_database()


async def check_tables_exist():
    """检查表是否存在"""
    try:
        await init_database()
        
        # 导入全局engine
        from app.core.database import engine as db_engine
        
        if not db_engine:
            raise RuntimeError("数据库引擎未初始化")
            
        async with db_engine.begin() as conn:
            check_sql = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('user_profiles', 'user_profile_history', 'user_profile_stats')
            ORDER BY table_name
            """
            
            result = await conn.execute(text(check_sql))
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = ['user_profiles', 'user_profile_history', 'user_profile_stats']
            
            logger.info(f"现有表: {tables}")
            logger.info(f"期望表: {expected_tables}")
            
            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                logger.warning(f"缺少表: {missing_tables}")
                return False
            else:
                logger.info("所有用户画像表都存在")
                return True
                
    except Exception as e:
        logger.error(f"检查表存在性失败: {e}")
        return False
    finally:
        await close_database()


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行初始化
    asyncio.run(create_user_profile_tables())