"""
创建测试数据库表结构脚本
"""

import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.core.database import Base

# 导入所有数据库模型，确保表被注册到Base.metadata
from app.models.database.user_profile_db import UserProfileDB, UserProfileHistory, UserProfileStats

logger = logging.getLogger(__name__)


async def create_test_tables():
    """在测试数据库中创建所有表"""
    try:
        # 使用测试数据库连接
        test_db_url = settings.database_url_computed.replace(
            settings.db_name, 
            f"{settings.db_name}_test"
        )
        
        print(f"连接测试数据库: {test_db_url}")
        
        engine = create_async_engine(
            test_db_url,
            echo=True,  # 显示SQL语句
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        print("开始创建表结构...")
        
        # 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("所有表创建成功!")
        
        # 验证表是否创建成功
        async with engine.begin() as conn:
            from sqlalchemy import text
            # 查询所有表
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            print(f"\n创建的表:")
            for table in tables:
                print(f"  - {table}")
        
        await engine.dispose()
        
    except Exception as e:
        print(f"创建表失败: {e}")
        raise


async def drop_test_tables():
    """删除测试数据库中的所有表"""
    try:
        test_db_url = settings.database_url_computed.replace(
            settings.db_name, 
            f"{settings.db_name}_test"
        )
        
        engine = create_async_engine(test_db_url, echo=True)
        
        print("开始删除所有表...")
        
        # 删除所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        print("所有表删除成功!")
        
        await engine.dispose()
        
    except Exception as e:
        print(f"删除表失败: {e}")
        raise


async def check_tables():
    """检查测试数据库中的表"""
    try:
        test_db_url = settings.database_url_computed.replace(
            settings.db_name, 
            f"{settings.db_name}_test"
        )
        
        engine = create_async_engine(test_db_url)
        
        async with engine.begin() as conn:
            from sqlalchemy import text
            # 查询所有表
            result = await conn.execute(text("""
                SELECT 
                    table_name,
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                ORDER BY table_name, ordinal_position
            """))
            
            columns = result.fetchall()
            
            if not columns:
                print("没有找到任何表")
                return
            
            print("\n数据库表结构:")
            current_table = None
            for row in columns:
                table_name, column_name, data_type, is_nullable = row
                if table_name != current_table:
                    print(f"\n表: {table_name}")
                    current_table = table_name
                nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
                print(f"   {column_name:25} {data_type:20} {nullable}")
        
        await engine.dispose()
        
    except Exception as e:
        print(f"检查表失败: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create":
            print("创建测试数据库表...")
            asyncio.run(create_test_tables())
            
        elif command == "drop":
            print("删除测试数据库表...")
            asyncio.run(drop_test_tables())
            
        elif command == "check":
            print("检查测试数据库表...")
            asyncio.run(check_tables())
            
        else:
            print("使用方法:")
            print("  python tests/create_test_tables.py create  # 创建表")
            print("  python tests/create_test_tables.py drop    # 删除表")
            print("  python tests/create_test_tables.py check   # 检查表")
    else:
        print("默认创建测试数据库表...")
        asyncio.run(create_test_tables())