"""
CouponService业务逻辑测试
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.services.coupon_service import CouponService
from app.repositories.coupon_repository import CouponRepository
from app.models.coupon import Coupon, CouponCreate, CouponUpdate, CouponType, CouponStatus
from app.models.database.coupon_db import CouponDB


@pytest.mark.asyncio
class TestCouponService:
    """CouponService业务逻辑测试类"""

    @pytest.fixture
    def mock_coupon_repo(self):
        """模拟CouponRepository"""
        return AsyncMock(spec=CouponRepository)

    @pytest.fixture
    def mock_cache(self):
        """模拟缓存"""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.delete_pattern = AsyncMock()
        return cache

    @pytest.fixture
    def coupon_service(self, mock_coupon_repo, mock_cache):
        """创建CouponService实例"""
        service = CouponService(mock_coupon_repo)
        service.cache = mock_cache
        return service

    @pytest.fixture
    def sample_coupon_db(self):
        """示例CouponDB对象"""
        return CouponDB(
            coupon_id="coupon_001",
            coupon_code="PYTHON50",
            coupon_name="Python课程50元优惠券",
            description="Python相关课程专享50元优惠",
            coupon_type="fixed_amount",
            discount_value=Decimal("50.00"),
            min_order_amount=Decimal("200.00"),
            usage_limit=100,
            used_count=10,
            valid_from=datetime.now() - timedelta(days=1),
            valid_to=datetime.now() + timedelta(days=30),
            status="active"
        )

    @pytest.fixture
    def sample_coupon(self):
        """示例Coupon对象"""
        return Coupon(
            coupon_id="coupon_001",
            coupon_code="PYTHON50",
            coupon_name="Python课程50元优惠券",
            description="Python相关课程专享50元优惠",
            coupon_type=CouponType.FIXED_AMOUNT,
            discount_value=Decimal("50.00"),
            min_order_amount=Decimal("200.00"),
            usage_limit=100,
            used_count=10,
            valid_from=datetime.now() - timedelta(days=1),
            valid_to=datetime.now() + timedelta(days=30),
            status=CouponStatus.ACTIVE
        )

    async def test_get_coupon_by_code_cache_hit(self, coupon_service, mock_cache, sample_coupon):
        """测试从缓存获取优惠券详情"""
        # 设置缓存返回数据
        mock_cache.get.return_value = sample_coupon.model_dump()
        
        # 调用方法
        result = await coupon_service.get_coupon_by_code("PYTHON50")
        
        # 验证结果
        assert result is not None
        assert result.coupon_code == "PYTHON50"
        assert result.coupon_name == "Python课程50元优惠券"
        
        # 验证缓存被调用
        mock_cache.get.assert_called_once_with("coupon:code:PYTHON50")

    async def test_get_coupon_by_code_cache_miss(self, coupon_service, mock_cache, mock_coupon_repo, sample_coupon_db, sample_coupon):
        """测试缓存未命中时获取优惠券详情"""
        # 设置缓存返回None
        mock_cache.get.return_value = None
        
        # 设置Repository返回数据
        mock_coupon_repo.get_by_code.return_value = sample_coupon_db
        mock_coupon_repo.to_model.return_value = sample_coupon
        
        # 调用方法
        result = await coupon_service.get_coupon_by_code("PYTHON50")
        
        # 验证结果
        assert result is not None
        assert result.coupon_code == "PYTHON50"
        
        # 验证Repository被调用
        mock_coupon_repo.get_by_code.assert_called_once_with("PYTHON50")
        mock_coupon_repo.to_model.assert_called_once_with(sample_coupon_db)
        
        # 验证缓存被设置
        mock_cache.set.assert_called_once_with("coupon:code:PYTHON50", sample_coupon.model_dump(), ttl=3600)

    async def test_validate_coupon_success(self, coupon_service, sample_coupon):
        """测试优惠券验证成功"""
        # 模拟get_coupon_by_code方法
        coupon_service.get_coupon_by_code = AsyncMock(return_value=sample_coupon)
        
        # 调用方法
        result = await coupon_service.validate_coupon("PYTHON50", Decimal("300.00"), "test_user")
        
        # 验证结果
        assert result.is_valid is True
        assert result.discount_amount == Decimal("50.00")
        assert result.coupon == sample_coupon

    async def test_validate_coupon_not_found(self, coupon_service):
        """测试优惠券不存在"""
        # 模拟get_coupon_by_code方法返回None
        coupon_service.get_coupon_by_code = AsyncMock(return_value=None)
        
        # 调用方法
        result = await coupon_service.validate_coupon("NONEXISTENT", Decimal("300.00"), "test_user")
        
        # 验证结果
        assert result.is_valid is False
        assert result.error_message == "优惠券不存在"

    async def test_validate_coupon_insufficient_amount(self, coupon_service, sample_coupon):
        """测试订单金额不足"""
        # 模拟get_coupon_by_code方法
        coupon_service.get_coupon_by_code = AsyncMock(return_value=sample_coupon)
        
        # 调用方法 - 订单金额低于最低要求
        result = await coupon_service.validate_coupon("PYTHON50", Decimal("100.00"), "test_user")
        
        # 验证结果
        assert result.is_valid is False
        assert result.error_message == "订单金额不满足优惠券使用要求"

    async def test_create_coupon(self, coupon_service, mock_coupon_repo, mock_cache, sample_coupon_db, sample_coupon):
        """测试创建优惠券"""
        # 准备创建数据
        coupon_create = CouponCreate(
            code="NEWCOUPON",
            name="新优惠券",
            description="测试创建的优惠券",
            coupon_type=CouponType.FIXED_AMOUNT,
            discount_value=Decimal("30.00"),
            minimum_order_amount=Decimal("150.00"),
            max_usage_count=50
        )
        
        # 设置Repository返回数据
        mock_coupon_repo.create.return_value = sample_coupon_db
        mock_coupon_repo.to_model.return_value = sample_coupon
        
        # 调用方法
        result = await coupon_service.create_coupon(coupon_create)
        
        # 验证结果
        assert result is not None
        assert result.coupon_id == "coupon_001"
        
        # 验证Repository被调用
        mock_coupon_repo.create.assert_called_once()
        
        # 验证缓存被清除
        mock_cache.delete_pattern.assert_called()

    async def test_update_coupon(self, coupon_service, mock_coupon_repo, mock_cache, sample_coupon_db, sample_coupon):
        """测试更新优惠券"""
        # 准备更新数据
        coupon_update = CouponUpdate(
            name="更新后的优惠券名称",
            discount_value=Decimal("60.00")
        )
        
        # 设置Repository返回数据
        mock_coupon_repo.get_by_coupon_id.return_value = sample_coupon_db
        mock_coupon_repo.update.return_value = sample_coupon_db
        mock_coupon_repo.to_model.return_value = sample_coupon
        
        # 调用方法
        result = await coupon_service.update_coupon("coupon_001", coupon_update)
        
        # 验证结果
        assert result is not None
        assert result.coupon_id == "coupon_001"
        
        # 验证Repository被调用
        mock_coupon_repo.get_by_coupon_id.assert_called_once_with("coupon_001")
        mock_coupon_repo.update.assert_called_once()
        
        # 验证缓存被清除
        mock_cache.delete_pattern.assert_called()

    async def test_get_available_coupons(self, coupon_service, mock_cache, mock_coupon_repo, sample_coupon_db, sample_coupon):
        """测试获取可用优惠券列表"""
        # 设置缓存返回None
        mock_cache.get.return_value = None
        
        # 设置Repository返回数据
        mock_coupon_repo.get_available_coupons.return_value = [sample_coupon_db]
        mock_coupon_repo.to_model.return_value = sample_coupon
        
        # 调用方法
        result = await coupon_service.get_available_coupons("test_user")
        
        # 验证结果
        assert len(result) == 1
        assert result[0].coupon_id == "coupon_001"
        
        # 验证Repository被调用
        mock_coupon_repo.get_available_coupons.assert_called_once_with("test_user")

    async def test_use_coupon_success(self, coupon_service, mock_coupon_repo):
        """测试使用优惠券成功"""
        # 设置Repository返回成功
        mock_coupon_repo.use_coupon.return_value = True
        
        # 调用方法
        result = await coupon_service.use_coupon("PYTHON50", "test_user", "order_001")
        
        # 验证结果
        assert result is True
        
        # 验证Repository被调用
        mock_coupon_repo.use_coupon.assert_called_once_with("PYTHON50", "test_user", "order_001")

    async def test_get_coupon_usage_stats(self, coupon_service, mock_coupon_repo):
        """测试获取优惠券使用统计"""
        # 设置Repository返回数据
        stats_data = {
            "total_coupons": 10,
            "active_coupons": 8,
            "total_used": 150,
            "total_discount": Decimal("7500.00")
        }
        mock_coupon_repo.get_coupon_usage_stats.return_value = stats_data
        
        # 调用方法
        result = await coupon_service.get_coupon_usage_stats()
        
        # 验证结果
        assert result["total_coupons"] == 10
        assert result["total_discount"] == Decimal("7500.00")
        
        # 验证Repository被调用
        mock_coupon_repo.get_coupon_usage_stats.assert_called_once()