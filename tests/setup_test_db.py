"""
创建测试数据库脚本
"""

import asyncio
import asyncpg
from app.core.config import settings


async def create_test_database():
    """创建测试数据库"""
    try:
        # 连接到默认数据库
        conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database="postgres"  # 连接默认数据库
        )
        
        test_db_name = f"{settings.db_name}_test"
        
        # 检查测试数据库是否存在
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", 
            test_db_name
        )
        
        if not result:
            # 创建测试数据库
            await conn.execute(f'CREATE DATABASE "{test_db_name}"')
            print(f"✓ 测试数据库 '{test_db_name}' 创建成功")
        else:
            print(f"✓ 测试数据库 '{test_db_name}' 已存在")
        
        await conn.close()
        
    except Exception as e:
        print(f"✗ 创建测试数据库失败: {e}")
        raise


async def drop_test_database():
    """删除测试数据库"""
    try:
        conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database="postgres"
        )
        
        test_db_name = f"{settings.db_name}_test"
        
        # 断开所有连接
        await conn.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{test_db_name}' AND pid <> pg_backend_pid()
        """)
        
        # 删除数据库
        await conn.execute(f'DROP DATABASE IF EXISTS "{test_db_name}"')
        print(f"✓ 测试数据库 '{test_db_name}' 删除成功")
        
        await conn.close()
        
    except Exception as e:
        print(f"✗ 删除测试数据库失败: {e}")


if __name__ == "__main__":
    print("设置测试数据库...")
    asyncio.run(create_test_database())