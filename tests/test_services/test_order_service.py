"""
OrderService业务逻辑测试
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.services.order_service import OrderService
from app.repositories.order_repository import OrderRepository
from app.models.order import Order, OrderCreate, OrderItem, OrderStatus, PaymentStatus
from app.models.database.order_db import OrderDB


@pytest.mark.asyncio
class TestOrderService:
    """OrderService业务逻辑测试类"""

    @pytest.fixture
    def mock_order_repo(self):
        """模拟OrderRepository"""
        return AsyncMock(spec=OrderRepository)

    @pytest.fixture
    def mock_cache(self):
        """模拟缓存"""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.delete_pattern = AsyncMock()
        return cache

    @pytest.fixture
    def order_service(self, mock_order_repo, mock_cache):
        """创建OrderService实例"""
        service = OrderService(mock_order_repo)
        service.cache = mock_cache
        return service

    @pytest.fixture
    def sample_order_db(self):
        """示例OrderDB对象"""
        return OrderDB(
            order_id="order_001",
            user_id="test_user_001",
            original_amount=Decimal("599.00"),
            discount_amount=Decimal("100.00"),
            final_amount=Decimal("499.00"),
            coupon_discount=Decimal("50.00"),
            applied_coupon_code="PYTHON50",
            order_status="pending",
            payment_status="pending",
            payment_method="alipay",
            notes="测试订单"
        )

    @pytest.fixture
    def sample_order(self):
        """示例Order对象"""
        return Order(
            order_id="order_001",
            user_id="test_user_001",
            order_items=[],
            original_amount=Decimal("599.00"),
            discount_amount=Decimal("100.00"),
            final_amount=Decimal("499.00"),
            coupon_discount=Decimal("50.00"),
            applied_coupon_code="PYTHON50",
            order_status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            payment_method="alipay",
            notes="测试订单"
        )

    @pytest.fixture
    def sample_order_items(self):
        """示例订单项"""
        return [
            OrderItem(
                item_id="item_001",
                course_id="course_001",
                course_name="Python基础课程",
                original_price=Decimal("399.00"),
                discounted_price=Decimal("299.00"),
                quantity=1
            ),
            OrderItem(
                item_id="item_002", 
                course_id="course_002",
                course_name="Python进阶课程",
                original_price=Decimal("499.00"),
                discounted_price=Decimal("399.00"),
                quantity=1
            )
        ]

    async def test_get_order_by_id_cache_hit(self, order_service, mock_cache, sample_order):
        """测试从缓存获取订单详情"""
        # 设置缓存返回数据
        mock_cache.get.return_value = sample_order.model_dump()
        
        # 调用方法
        result = await order_service.get_order_by_id("order_001")
        
        # 验证结果
        assert result is not None
        assert result.order_id == "order_001"
        assert result.user_id == "test_user_001"
        
        # 验证缓存被调用
        mock_cache.get.assert_called_once_with("order:order_001")

    async def test_get_order_by_id_cache_miss(self, order_service, mock_cache, mock_order_repo, sample_order_db, sample_order):
        """测试缓存未命中时获取订单详情"""
        # 设置缓存返回None
        mock_cache.get.return_value = None
        
        # 设置Repository返回数据
        mock_order_repo.get_by_order_id.return_value = sample_order_db
        mock_order_repo.to_model.return_value = sample_order
        
        # 调用方法
        result = await order_service.get_order_by_id("order_001")
        
        # 验证结果
        assert result is not None
        assert result.order_id == "order_001"
        
        # 验证Repository被调用
        mock_order_repo.get_by_order_id.assert_called_once_with("order_001")
        mock_order_repo.to_model.assert_called_once_with(sample_order_db)
        
        # 验证缓存被设置
        mock_cache.set.assert_called_once_with("order:order_001", sample_order.model_dump(), ttl=3600)

    async def test_create_order_success(self, order_service, mock_order_repo, mock_cache, sample_order_db, sample_order, sample_order_items):
        """测试创建订单成功"""
        # 准备创建数据
        order_create_data = type('OrderData', (), {
            'order_id': 'new_order_001',
            'original_total': Decimal("898.00"),
            'discount_total': Decimal("200.00"),
            'final_total': Decimal("698.00"),
            'coupon_discount': Decimal("100.00"),
            'coupon_code': "SAVE100",
            'payment_method': "wechat_pay",
            'notes': "新创建的订单",
            'items': sample_order_items
        })()
        
        # 设置Repository返回数据
        mock_order_repo.create_order_with_items.return_value = sample_order_db
        mock_order_repo.to_model.return_value = sample_order
        
        # 调用方法
        result = await order_service.create_order(order_create_data, "test_user_001")
        
        # 验证结果
        assert result is not None
        assert result.order_id == "order_001"
        
        # 验证Repository被调用
        mock_order_repo.create_order_with_items.assert_called_once_with(order_create_data, "test_user_001")
        
        # 验证缓存被清除
        mock_cache.delete_pattern.assert_called()

    async def test_update_order_status(self, order_service, mock_order_repo, mock_cache):
        """测试更新订单状态"""
        # 设置Repository返回成功
        mock_order_repo.update_order_status.return_value = True
        
        # 调用方法
        result = await order_service.update_order_status(
            "order_001",
            order_status="completed",
            payment_status="paid"
        )
        
        # 验证结果
        assert result is True
        
        # 验证Repository被调用
        mock_order_repo.update_order_status.assert_called_once_with(
            "order_001",
            order_status="completed",
            payment_status="paid",
            payment_method=None,
            paid_at=None
        )
        
        # 验证缓存被清除
        mock_cache.delete_pattern.assert_called()

    async def test_cancel_order_success(self, order_service, mock_order_repo, mock_cache):
        """测试取消订单成功"""
        # 设置Repository返回成功
        mock_order_repo.cancel_order.return_value = True
        
        # 调用方法
        result = await order_service.cancel_order("order_001", "用户主动取消")
        
        # 验证结果
        assert result is True
        
        # 验证Repository被调用
        mock_order_repo.cancel_order.assert_called_once_with("order_001", "用户主动取消")
        
        # 验证缓存被清除
        mock_cache.delete_pattern.assert_called()

    async def test_get_user_orders(self, order_service, mock_cache, mock_order_repo, sample_order_db, sample_order):
        """测试获取用户订单列表"""
        # 设置缓存返回None
        mock_cache.get.return_value = None
        
        # 设置Repository返回数据
        mock_order_repo.get_user_orders.return_value = [sample_order_db]
        mock_order_repo.to_model.return_value = sample_order
        
        # 调用方法
        result = await order_service.get_user_orders("test_user_001", limit=10)
        
        # 验证结果
        assert len(result) == 1
        assert result[0].order_id == "order_001"
        
        # 验证Repository被调用
        mock_order_repo.get_user_orders.assert_called_once_with("test_user_001", limit=10, offset=0, status_filter=None)

    async def test_get_orders_by_status(self, order_service, mock_cache, mock_order_repo, sample_order_db, sample_order):
        """测试按状态获取订单"""
        # 设置缓存返回None
        mock_cache.get.return_value = None
        
        # 设置Repository返回数据
        mock_order_repo.get_orders_by_status.return_value = [sample_order_db]
        mock_order_repo.to_model.return_value = sample_order
        
        # 调用方法
        result = await order_service.get_orders_by_status("pending", limit=20)
        
        # 验证结果
        assert len(result) == 1
        assert result[0].order_status == OrderStatus.PENDING
        
        # 验证Repository被调用
        mock_order_repo.get_orders_by_status.assert_called_once_with("pending", limit=20, offset=0)

    async def test_get_order_statistics(self, order_service, mock_order_repo):
        """测试获取订单统计"""
        # 设置Repository返回数据
        stats_data = {
            "total_orders": 100,
            "total_amount": 50000.0,
            "avg_amount": 500.0,
            "unique_customers": 75,
            "status_breakdown": {
                "completed": {"count": 80, "amount": 40000.0},
                "pending": {"count": 15, "amount": 7500.0},
                "cancelled": {"count": 5, "amount": 2500.0}
            }
        }
        mock_order_repo.get_order_statistics.return_value = stats_data
        
        # 调用方法
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        result = await order_service.get_order_statistics(start_date, end_date)
        
        # 验证结果
        assert result["total_orders"] == 100
        assert result["total_amount"] == 50000.0
        assert len(result["status_breakdown"]) == 3
        
        # 验证Repository被调用
        mock_order_repo.get_order_statistics.assert_called_once_with(start_date, end_date, user_id=None)

    async def test_calculate_order_price(self, order_service, mock_order_repo):
        """测试计算订单价格"""
        # 设置Repository返回价格计算结果
        from app.models.order import PriceCalculation, OrderItem
        
        price_calc = PriceCalculation(
            original_total=Decimal("898.00"),
            discount_total=Decimal("200.00"),
            final_total=Decimal("698.00"),
            coupon_discount=Decimal("100.00"),
            auto_discount=Decimal("100.00"),
            items=[
                OrderItem(
                    item_id="item_001",
                    course_id="course_001", 
                    course_name="Python基础课程",
                    original_price=Decimal("399.00"),
                    discounted_price=Decimal("349.00"),
                    quantity=1
                )
            ]
        )
        
        mock_order_repo.calculate_order_price.return_value = price_calc
        
        # 调用方法
        result = await order_service.calculate_order_price(
            ["course_001", "course_002"],
            coupon_code="SAVE100",
            user_id="test_user_001"
        )
        
        # 验证结果
        assert result.final_total == Decimal("698.00")
        assert result.coupon_discount == Decimal("100.00")
        assert len(result.items) == 1
        
        # 验证Repository被调用
        mock_order_repo.calculate_order_price.assert_called_once_with(
            ["course_001", "course_002"],
            coupon_code="SAVE100",
            user_id="test_user_001"
        )

    async def test_get_pending_payment_orders(self, order_service, mock_order_repo, sample_order_db, sample_order):
        """测试获取待支付超时订单"""
        # 设置Repository返回数据
        mock_order_repo.get_pending_payment_orders.return_value = [sample_order_db]
        mock_order_repo.to_model.return_value = sample_order
        
        # 调用方法
        result = await order_service.get_pending_payment_orders(timeout_minutes=30)
        
        # 验证结果
        assert len(result) == 1
        assert result[0].payment_status == PaymentStatus.PENDING
        
        # 验证Repository被调用
        mock_order_repo.get_pending_payment_orders.assert_called_once_with(timeout_minutes=30)

    async def test_get_revenue_trend(self, order_service, mock_order_repo):
        """测试获取收入趋势"""
        # 设置Repository返回数据
        trend_data = [
            {"date": "2024-01-01", "orders": 10, "revenue": 5000.0},
            {"date": "2024-01-02", "orders": 8, "revenue": 4000.0},
            {"date": "2024-01-03", "orders": 12, "revenue": 6000.0}
        ]
        mock_order_repo.get_revenue_trend.return_value = trend_data
        
        # 调用方法
        result = await order_service.get_revenue_trend(days=30)
        
        # 验证结果
        assert len(result) == 3
        assert result[0]["date"] == "2024-01-01"
        assert result[0]["revenue"] == 5000.0
        
        # 验证Repository被调用
        mock_order_repo.get_revenue_trend.assert_called_once_with(days=30, user_id=None)

    async def test_get_popular_courses_from_orders(self, order_service, mock_order_repo):
        """测试从订单中获取热门课程统计"""
        # 设置Repository返回数据
        popular_courses = [
            {
                "course_id": "course_001",
                "course_name": "Python基础课程",
                "total_sold": 50,
                "total_revenue": 15000.0,
                "unique_buyers": 45
            },
            {
                "course_id": "course_002", 
                "course_name": "JavaScript高级课程",
                "total_sold": 30,
                "total_revenue": 12000.0,
                "unique_buyers": 28
            }
        ]
        mock_order_repo.get_popular_courses.return_value = popular_courses
        
        # 调用方法
        result = await order_service.get_popular_courses_from_orders(days=30, limit=10)
        
        # 验证结果
        assert len(result) == 2
        assert result[0]["course_name"] == "Python基础课程"
        assert result[0]["total_sold"] == 50
        
        # 验证Repository被调用
        mock_order_repo.get_popular_courses.assert_called_once_with(days=30, limit=10)