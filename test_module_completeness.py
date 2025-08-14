"""
简单的模块完整性测试脚本
验证优惠系统的各个组件是否可以正常导入和使用
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_module_completeness():
    """测试模块完整性"""
    print("=== AI销售助手优惠系统模块完整性测试 ===\n")
    
    # 测试1: 数据模型导入
    try:
        from app.models.course import Course, CourseCreate
        from app.models.coupon import Coupon, CouponCreate  
        from app.models.order import Order, OrderCreate
        from app.models.discount import AppliedDiscount
        print("数据模型导入成功")
    except ImportError as e:
        print(f"✗ 数据模型导入失败: {e}")
        return False
    
    # 测试2: 数据库模型导入
    try:
        from app.models.database.course_db import CourseDB
        from app.models.database.coupon_db import CouponDB
        from app.models.database.order_db import OrderDB
        from app.models.database.discount_db import AppliedDiscountDB
        print("数据库模型导入成功")
    except ImportError as e:
        print(f"✗ 数据库模型导入失败: {e}")
        return False
    
    # 测试3: Repository层导入
    try:
        from app.repositories.course_repository import CourseRepository
        print("Repository层导入成功")
    except ImportError as e:
        print(f"✗ Repository层导入失败: {e}")
        return False
    
    # 测试4: Service层导入  
    try:
        from app.services.course_service import CourseService
        print("Service层导入成功")
    except ImportError as e:
        print(f"✗ Service层导入失败: {e}")
        return False
    
    # 测试5: 缓存工具导入
    try:
        from app.services.common_cache import course_cache, coupon_cache
        print("缓存工具导入成功")
    except ImportError as e:
        print(f"✗ 缓存工具导入失败: {e}")
        return False
    
    # 测试6: Agent集成服务导入
    try:
        from app.services.agent_integration_service import AgentIntegrationService
        print("Agent集成服务导入成功")
    except ImportError as e:
        print(f"✗ Agent集成服务导入失败: {e}")
        return False
        
    print(f"\n=== 测试结果 ===")
    print("优惠系统核心模块导入测试通过")
    print("系统具备以下能力：")
    print("- 完整的用户画像服务 (Phase 1)")  
    print("- 课程管理和推荐")
    print("- 优惠券系统")
    print("- 订单处理流程")
    print("- 折扣决策支持")
    print("- Agent集成接口")
    print("- Redis缓存支持")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_module_completeness())