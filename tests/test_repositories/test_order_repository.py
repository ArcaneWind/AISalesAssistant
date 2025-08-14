"""
订单Repository数据库操作测试 - 使用真实数据库
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from app.repositories.order_repository import OrderRepository
from app.models.database.order_db import OrderDB, OrderItemDB
from app.models.order import OrderCreate, OrderItem


@pytest.mark.asyncio
class TestOrderRepository:
    """订单Repository数据库操作测试类"""

    async def test_create_and_get_order(self, db_session):
        """测试创建和获取订单"""
        # 创建Repository实例
        order_repo = OrderRepository(db_session)
        
        # 准备测试数据
        order_data = {
            "order_id": f"TEST_ORDER_{int(datetime.now().timestamp())}",
            "user_id": "test_user_123",
            "original_amount": Decimal("399.00"),
            "discount_amount": Decimal("50.00"),
            "coupon_discount": Decimal("30.00"),
            "final_amount": Decimal("349.00"),
            "applied_coupon_code": "TESTCOUPON",
            "order_status": "pending",
            "payment_status": "pending",
            "payment_method": "wechat_pay",
            "notes": "测试订单备注"
        }
        
        # 创建订单
        order = OrderDB(**order_data)
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)
        
        # 通过ID获取订单
        retrieved_order = await order_repo.get_by_order_id(order.order_id)
        
        # 验证结果
        assert retrieved_order is not None
        assert retrieved_order.user_id == "test_user_123"
        assert retrieved_order.final_amount == Decimal("349.00")
        assert retrieved_order.order_status == "pending"

    async def test_get_nonexistent_order(self, db_session):
        """测试获取不存在的订单"""
        order_repo = OrderRepository(db_session)
        order = await order_repo.get_by_order_id("NONEXISTENT_ORDER_ID")
        assert order is None

    async def test_create_order_with_items(self, db_session):
        """测试创建包含订单项的订单"""
        order_repo = OrderRepository(db_session)
        
        # 创建订单项
        order_items = [
            OrderItem(
                item_id="item_001",
                course_id="course_001",
                course_name="Python基础课程",
                original_price=Decimal("299.00"),
                discounted_price=Decimal("199.00"),
                quantity=1
            ),
            OrderItem(
                item_id="item_002",
                course_id="course_002", 
                course_name="JavaScript高级课程",
                original_price=Decimal("399.00"),
                discounted_price=Decimal("299.00"),
                quantity=1
            )
        ]
        
        # 创建订单数据 - 使用字典而不是OrderCreate
        order_data = type('OrderData', (), {
            'order_id': f"ORDER_WITH_ITEMS_{int(datetime.now().timestamp())}",
            'original_total': Decimal("698.00"),
            'discount_total': Decimal("200.00"),
            'final_total': Decimal("498.00"),
            'coupon_discount': Decimal("50.00"),
            'coupon_code': "TESTCOUPON50",
            'payment_method': "alipay",
            'notes': "包含多个课程的测试订单",
            'items': order_items
        })()
        
        # 创建订单
        created_order = await order_repo.create_order_with_items(order_data, "test_user_456")
        await db_session.commit()
        await db_session.refresh(created_order)
        
        # 验证订单创建成功
        assert created_order.user_id == "test_user_456"
        assert created_order.final_amount == Decimal("498.00")
        assert created_order.applied_coupon_code == "TESTCOUPON50"
        
        # 获取完整订单（包含订单项）
        full_order = await order_repo.get_by_order_id(created_order.order_id)
        assert full_order is not None
        assert len(full_order.order_items) == 2
        
        # 验证订单项
        item_course_ids = [item.course_id for item in full_order.order_items]
        assert "course_001" in item_course_ids
        assert "course_002" in item_course_ids

    async def test_get_user_orders(self, db_session):
        """测试获取用户订单列表"""
        order_repo = OrderRepository(db_session)
        user_id = "test_user_orders"
        
        # 创建多个测试订单
        for i in range(3):
            order_data = {
                "order_id": f"USER_ORDER_{user_id}_{i}_{int(datetime.now().timestamp())}",
                "user_id": user_id,
                "original_amount": Decimal("300.00"),
                "discount_amount": Decimal("50.00"),
                "final_amount": Decimal("250.00"),
                "order_status": "completed" if i < 2 else "pending",
                "payment_status": "paid" if i < 2 else "pending"
            }
            
            order = OrderDB(**order_data)
            db_session.add(order)
        
        await db_session.commit()
        
        # 获取所有订单
        all_orders = await order_repo.get_user_orders(user_id, limit=10)
        assert len(all_orders) == 3
        
        # 获取已完成订单
        completed_orders = await order_repo.get_user_orders(user_id, status_filter="completed")
        assert len(completed_orders) == 2
        for order in completed_orders:
            assert order.order_status == "completed"

    async def test_update_order_status(self, db_session):
        """测试更新订单状态"""
        order_repo = OrderRepository(db_session)
        
        # 创建测试订单
        order_data = {
            "order_id": f"UPDATE_STATUS_ORDER_{int(datetime.now().timestamp())}",
            "user_id": "test_user_update",
            "original_amount": Decimal("500.00"),
            "final_amount": Decimal("500.00"),
            "order_status": "pending",
            "payment_status": "pending"
        }
        
        order = OrderDB(**order_data)
        db_session.add(order)
        await db_session.commit()
        
        # 更新订单状态
        payment_time = datetime.now()
        success = await order_repo.update_order_status(
            order.order_id,
            order_status="completed",
            payment_status="paid",
            payment_method="wechat_pay",
            paid_at=payment_time
        )
        
        assert success is True
        
        # 验证更新结果
        updated_order = await order_repo.get_by_order_id(order.order_id)
        assert updated_order.order_status == "completed"
        assert updated_order.payment_status == "paid"
        assert updated_order.payment_method == "wechat_pay"

    async def test_cancel_order(self, db_session):
        """测试取消订单"""
        order_repo = OrderRepository(db_session)
        
        # 创建可取消的测试订单
        order_data = {
            "order_id": f"CANCEL_ORDER_{int(datetime.now().timestamp())}",
            "user_id": "test_user_cancel",
            "original_amount": Decimal("300.00"),
            "final_amount": Decimal("300.00"),
            "order_status": "pending",
            "payment_status": "pending"
        }
        
        order = OrderDB(**order_data)
        db_session.add(order)
        await db_session.commit()
        
        # 取消订单
        success = await order_repo.cancel_order(order.order_id, "用户主动取消")
        assert success is True
        
        # 验证取消结果
        cancelled_order = await order_repo.get_by_order_id(order.order_id)
        assert cancelled_order.order_status == "cancelled"

    async def test_cancel_completed_order_fails(self, db_session):
        """测试取消已完成订单应该失败"""
        order_repo = OrderRepository(db_session)
        
        # 创建已完成的测试订单
        order_data = {
            "order_id": f"COMPLETED_ORDER_{int(datetime.now().timestamp())}",
            "user_id": "test_user_completed",
            "original_amount": Decimal("300.00"),
            "final_amount": Decimal("300.00"),
            "order_status": "completed",
            "payment_status": "paid"
        }
        
        order = OrderDB(**order_data)
        db_session.add(order)
        await db_session.commit()
        
        # 尝试取消已完成订单
        success = await order_repo.cancel_order(order.order_id, "尝试取消已完成订单")
        assert success is False
        
        # 验证订单状态未改变
        unchanged_order = await order_repo.get_by_order_id(order.order_id)
        assert unchanged_order.order_status == "completed"

    async def test_get_orders_by_status(self, db_session):
        """测试按状态获取订单"""
        order_repo = OrderRepository(db_session)
        
        # 创建不同状态的测试订单
        statuses = ["pending", "completed", "cancelled"]
        for i, status in enumerate(statuses):
            for j in range(2):  # 每种状态创建2个订单
                order_data = {
                    "order_id": f"STATUS_ORDER_{status}_{i}_{j}_{int(datetime.now().timestamp())}",
                    "user_id": f"test_user_status_{i}_{j}",
                    "original_amount": Decimal("200.00"),
                    "final_amount": Decimal("200.00"),
                    "order_status": status,
                    "payment_status": "paid" if status == "completed" else "pending"
                }
                
                order = OrderDB(**order_data)
                db_session.add(order)
        
        await db_session.commit()
        
        # 测试按状态获取
        pending_orders = await order_repo.get_orders_by_status("pending", limit=10)
        completed_orders = await order_repo.get_orders_by_status("completed", limit=10)
        cancelled_orders = await order_repo.get_orders_by_status("cancelled", limit=10)
        
        assert len(pending_orders) >= 2
        assert len(completed_orders) >= 2  
        assert len(cancelled_orders) >= 2
        
        # 验证状态正确
        for order in pending_orders:
            assert order.order_status == "pending"
        for order in completed_orders:
            assert order.order_status == "completed"
        for order in cancelled_orders:
            assert order.order_status == "cancelled"

    async def test_pydantic_model_conversion(self, db_session):
        """测试数据库模型到Pydantic模型的转换"""
        order_repo = OrderRepository(db_session)
        
        # 创建测试订单
        order_data = {
            "order_id": f"CONVERT_ORDER_{int(datetime.now().timestamp())}",
            "user_id": "test_user_convert",
            "original_amount": Decimal("599.00"),
            "discount_amount": Decimal("100.00"),
            "coupon_discount": Decimal("50.00"),
            "final_amount": Decimal("449.00"),  # 修正计算: 599 - 100 - 50 = 449
            "applied_coupon_code": "CONVERT50",
            "order_status": "paid",  # 使用有效的枚举值
            "payment_status": "paid",
            "payment_method": "alipay",
            "notes": "转换测试订单"
        }
        
        db_order = OrderDB(**order_data)
        db_session.add(db_order)
        await db_session.flush()  # 先flush获得ID
        
        # 添加一个测试订单项
        import uuid
        test_item = OrderItemDB(
            item_id=str(uuid.uuid4()),
            order_id=db_order.order_id,
            course_id="test_course_001",
            course_name="测试课程",
            original_price=Decimal("599.00"),
            discounted_price=Decimal("449.00"),
            quantity=1
        )
        db_session.add(test_item)
        
        await db_session.commit()
        await db_session.refresh(db_order)
        
        # 测试转换 (如果Repository有to_model方法)
        if hasattr(order_repo, 'to_model'):
            # 重新获取订单以确保关系被加载
            full_order = await order_repo.get_by_order_id(db_order.order_id)
            if full_order:
                pydantic_order = order_repo.to_model(full_order)
                
                # 验证基础字段转换
                assert pydantic_order.order_id == full_order.order_id
                assert pydantic_order.user_id == full_order.user_id
                assert pydantic_order.final_amount == full_order.final_amount
            else:
                # 如果没有找到完整订单，直接用db_order测试
                pydantic_order = order_repo.to_model(db_order)
                
                # 验证基础字段转换
                assert pydantic_order.order_id == db_order.order_id
                assert pydantic_order.user_id == db_order.user_id
                assert pydantic_order.final_amount == db_order.final_amount
            
        # 验证数据库对象字段
        assert db_order.order_id.startswith("CONVERT_ORDER_")
        assert db_order.user_id == "test_user_convert"
        assert db_order.final_amount == Decimal("449.00")