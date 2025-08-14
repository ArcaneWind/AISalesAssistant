"""
优惠系统数据库表创建脚本
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings
from app.core.database import Base

# 导入所有数据库模型以确保表被注册
from app.models.database.user_profile_db import UserProfileDB, UserProfileHistory, UserProfileStats
from app.models.database.course_db import CourseDB
from app.models.database.coupon_db import CouponDB
from app.models.database.discount_db import AppliedDiscountDB, DiscountUsageHistoryDB
from app.models.database.order_db import OrderDB, OrderItemDB, CouponUsageDB


async def create_database_if_not_exists():
    """创建数据库（如果不存在）"""
    # 连接到PostgreSQL服务器（不指定数据库）
    server_url = settings.database_url_computed.replace(f"/{settings.db_name}", "/postgres")
    
    engine = create_async_engine(server_url)
    
    async with engine.begin() as conn:
        # 检查数据库是否存在
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": settings.db_name}
        )
        
        if not result.fetchone():
            # 创建数据库
            await conn.execute(text("COMMIT"))
            await conn.execute(text(f"CREATE DATABASE {settings.db_name}"))
            print(f"数据库 '{settings.db_name}' 创建成功")
        else:
            print(f"数据库 '{settings.db_name}' 已存在")
    
    await engine.dispose()


async def create_tables():
    """创建所有数据表"""
    # 连接到目标数据库
    engine = create_async_engine(settings.database_url_computed)
    
    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
        print("所有数据表创建成功")
    
    await engine.dispose()


async def create_indexes():
    """创建额外的索引"""
    engine = create_async_engine(settings.database_url_computed)
    
    indexes = [
        # 课程表索引
        "CREATE INDEX IF NOT EXISTS idx_courses_category_status ON courses(category, status);",
        "CREATE INDEX IF NOT EXISTS idx_courses_price_range ON courses(current_price);",
        "CREATE INDEX IF NOT EXISTS idx_courses_difficulty ON courses(difficulty_level);",
        
        # 优惠券表索引
        "CREATE INDEX IF NOT EXISTS idx_coupons_validity ON coupons(valid_from, valid_to);",
        "CREATE INDEX IF NOT EXISTS idx_coupons_status_code ON coupons(status, coupon_code);",
        
        # 折扣表索引
        "CREATE INDEX IF NOT EXISTS idx_applied_discounts_user_time ON applied_discounts(user_id, created_at);",
        "CREATE INDEX IF NOT EXISTS idx_applied_discounts_valid ON applied_discounts(valid_until, is_used);",
        
        # 订单表索引
        "CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, order_status);",
        "CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders(payment_status, created_at);",
        "CREATE INDEX IF NOT EXISTS idx_order_items_course ON order_items(course_id);",
        
        # 使用记录索引
        "CREATE INDEX IF NOT EXISTS idx_coupon_usage_user_time ON coupon_usage(user_id, used_at);",
        "CREATE INDEX IF NOT EXISTS idx_discount_history_user_time ON discount_usage_history(user_id, used_at);"
    ]
    
    async with engine.begin() as conn:
        for index_sql in indexes:
            await conn.execute(text(index_sql))
        print("所有索引创建成功")
    
    await engine.dispose()


async def insert_sample_courses():
    """插入示例课程数据"""
    engine = create_async_engine(settings.database_url_computed)
    
    sample_courses = [
        {
            "course_id": "python_basic_001",
            "course_name": "Python基础入门",
            "category": "python",
            "original_price": 899.00,
            "current_price": 699.00,
            "description": "零基础学习Python编程，掌握基础语法和编程思维",
            "duration_hours": 40,
            "difficulty_level": "beginner",
            "instructor": "张老师",
            "tags": ["Python", "编程基础", "零基础"],
            "prerequisites": [],
            "learning_outcomes": ["掌握Python基础语法", "能够编写简单程序", "理解编程思维"],
            "rating": 4.8,
            "student_count": 1250
        },
        {
            "course_id": "data_analysis_001",
            "course_name": "数据分析实战",
            "category": "data_analysis",
            "original_price": 1299.00,
            "current_price": 999.00,
            "description": "使用Python进行数据分析，掌握pandas、numpy等工具",
            "duration_hours": 60,
            "difficulty_level": "intermediate",
            "instructor": "李老师",
            "tags": ["数据分析", "pandas", "numpy", "可视化"],
            "prerequisites": ["Python基础"],
            "learning_outcomes": ["掌握数据分析流程", "熟练使用分析工具", "完成项目实战"],
            "rating": 4.9,
            "student_count": 890
        },
        {
            "course_id": "ml_intro_001",
            "course_name": "机器学习入门",
            "category": "machine_learning",
            "original_price": 1699.00,
            "current_price": 1299.00,
            "description": "机器学习算法原理与实践，scikit-learn实战",
            "duration_hours": 80,
            "difficulty_level": "advanced",
            "instructor": "王老师",
            "tags": ["机器学习", "算法", "scikit-learn", "AI"],
            "prerequisites": ["Python基础", "数据分析"],
            "learning_outcomes": ["理解ML算法原理", "能够选择合适算法", "完成ML项目"],
            "rating": 4.7,
            "student_count": 650
        }
    ]
    
    async with engine.begin() as conn:
        for course in sample_courses:
            # 检查课程是否已存在
            result = await conn.execute(
                text("SELECT 1 FROM courses WHERE course_id = :course_id"),
                {"course_id": course["course_id"]}
            )
            
            if not result.fetchone():
                # 插入课程数据
                await conn.execute(
                    text("""
                        INSERT INTO courses (
                            course_id, course_name, category, original_price, current_price,
                            description, duration_hours, difficulty_level, instructor,
                            tags, prerequisites, learning_outcomes, rating, student_count
                        ) VALUES (
                            :course_id, :course_name, :category, :original_price, :current_price,
                            :description, :duration_hours, :difficulty_level, :instructor,
                            :tags, :prerequisites, :learning_outcomes, :rating, :student_count
                        )
                    """),
                    course
                )
                print(f"插入课程: {course['course_name']}")
            else:
                print(f"课程已存在: {course['course_name']}")
    
    await engine.dispose()


async def insert_sample_coupons():
    """插入示例优惠券数据"""
    engine = create_async_engine(settings.database_url_computed)
    
    from datetime import datetime, timedelta
    
    now = datetime.now()
    sample_coupons = [
        {
            "coupon_id": "welcome_2024",
            "coupon_code": "WELCOME100",
            "coupon_name": "新用户欢迎券",
            "coupon_type": "fixed_amount",
            "discount_value": 100.00,
            "min_order_amount": 500.00,
            "max_discount": 100.00,
            "valid_from": now,
            "valid_to": now + timedelta(days=30),
            "usage_limit": 1000,
            "usage_limit_per_user": 1,
            "description": "新用户专享100元优惠券"
        },
        {
            "coupon_id": "spring_2024",
            "coupon_code": "SPRING20",
            "coupon_name": "春季促销券",
            "coupon_type": "percentage",
            "discount_value": 0.20,
            "min_order_amount": 800.00,
            "max_discount": 200.00,
            "valid_from": now,
            "valid_to": now + timedelta(days=60),
            "usage_limit": 500,
            "usage_limit_per_user": 2,
            "description": "春季促销8折优惠券，最高优惠200元"
        }
    ]
    
    async with engine.begin() as conn:
        for coupon in sample_coupons:
            # 检查优惠券是否已存在
            result = await conn.execute(
                text("SELECT 1 FROM coupons WHERE coupon_code = :coupon_code"),
                {"coupon_code": coupon["coupon_code"]}
            )
            
            if not result.fetchone():
                await conn.execute(
                    text("""
                        INSERT INTO coupons (
                            coupon_id, coupon_code, coupon_name, coupon_type, discount_value,
                            min_order_amount, max_discount, valid_from, valid_to,
                            usage_limit, usage_limit_per_user, description
                        ) VALUES (
                            :coupon_id, :coupon_code, :coupon_name, :coupon_type, :discount_value,
                            :min_order_amount, :max_discount, :valid_from, :valid_to,
                            :usage_limit, :usage_limit_per_user, :description
                        )
                    """),
                    coupon
                )
                print(f"插入优惠券: {coupon['coupon_name']}")
            else:
                print(f"优惠券已存在: {coupon['coupon_name']}")
    
    await engine.dispose()


async def main():
    """主函数"""
    print("开始创建优惠系统数据库表...")
    
    try:
        # 1. 创建数据库
        await create_database_if_not_exists()
        
        # 2. 创建表结构
        await create_tables()
        
        # 3. 创建索引
        await create_indexes()
        
        # 4. 插入示例数据
        await insert_sample_courses()
        await insert_sample_coupons()
        
        print("优惠系统数据库初始化完成！")
        
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())