"""
优惠券Repository数据库操作测试 - 使用真实数据库
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from app.repositories.coupon_repository import CouponRepository
from app.models.database.coupon_db import CouponDB


@pytest.mark.asyncio
class TestCouponRepository:
    """优惠券Repository数据库操作测试类"""

    async def test_create_and_get_coupon(self, db_session):
        """测试创建和获取优惠券"""
        # 创建Repository实例
        coupon_repo = CouponRepository(db_session)
        
        # 准备测试数据
        coupon_data = {
            "coupon_id": f"ID_{int(datetime.now().timestamp())}",
            "coupon_code": f"TEST_COUPON_{int(datetime.now().timestamp())}",
            "coupon_name": "新年优惠券",
            "coupon_type": "percentage",
            "discount_value": Decimal("20.00"),
            "min_order_amount": Decimal("100.00"),
            "max_discount": Decimal("50.00"),
            "valid_from": datetime.now(),
            "valid_to": datetime.now() + timedelta(days=30),
            "usage_limit": 100,
            "used_count": 0,
            "status": "active",
            "applicable_courses": ["course1", "course2"]
        }
        
        # 创建优惠券
        coupon = CouponDB(**coupon_data)
        db_session.add(coupon)
        await db_session.commit()
        await db_session.refresh(coupon)
        
        # 通过code获取优惠券
        retrieved_coupon = await coupon_repo.get_by_coupon_code(coupon.coupon_code)
        
        # 验证结果
        assert retrieved_coupon is not None
        assert retrieved_coupon.coupon_name == "新年优惠券"
        assert retrieved_coupon.coupon_type == "percentage"
        assert retrieved_coupon.discount_value == Decimal("20.00")
        assert retrieved_coupon.status == "active"

    async def test_get_nonexistent_coupon(self, db_session):
        """测试获取不存在的优惠券"""
        coupon_repo = CouponRepository(db_session)
        coupon = await coupon_repo.get_by_coupon_code("NONEXISTENT_COUPON")
        assert coupon is None

    async def test_get_valid_coupons(self, db_session):
        """测试获取有效优惠券列表"""
        coupon_repo = CouponRepository(db_session)
        
        # 先创建测试优惠券
        now = datetime.now()
        coupon_data = {
            "coupon_id": f"VALID_ID_{int(now.timestamp())}",
            "coupon_code": f"VALID_TEST_{int(now.timestamp())}",
            "coupon_name": "有效测试优惠券",
            "coupon_type": "fixed",
            "discount_value": Decimal("10.00"),
            "valid_from": now - timedelta(days=1),
            "valid_to": now + timedelta(days=30),
            "usage_limit": 50,
            "used_count": 0,
            "status": "active"
        }
        
        coupon = CouponDB(**coupon_data)
        db_session.add(coupon)
        await db_session.commit()
        
        # 测试获取有效优惠券
        coupons = await coupon_repo.get_valid_coupons()
        
        # 验证搜索结果
        assert isinstance(coupons, list)
        found_coupon = next(
            (c for c in coupons if c.coupon_code == coupon.coupon_code), 
            None
        )
        assert found_coupon is not None
        assert found_coupon.status == "active"

    async def test_use_coupon(self, db_session):
        """测试使用优惠券功能"""
        coupon_repo = CouponRepository(db_session)
        
        # 创建测试优惠券
        coupon_data = {
            "coupon_id": f"USE_ID_{int(datetime.now().timestamp())}",
            "coupon_code": f"USE_TEST_{int(datetime.now().timestamp())}",
            "coupon_name": "使用测试券",
            "coupon_type": "percentage",
            "discount_value": Decimal("15.00"),
            "valid_from": datetime.now(),
            "valid_to": datetime.now() + timedelta(days=30),
            "usage_limit": 100,
            "used_count": 5,
            "status": "active"
        }
        
        coupon = CouponDB(**coupon_data)
        db_session.add(coupon)
        await db_session.commit()
        await db_session.refresh(coupon)
        
        # 使用优惠券
        success = await coupon_repo.use_coupon(
            coupon.coupon_id, 
            "test_user", 
            "test_order", 
            Decimal("10.00")
        )
        
        assert success is True
        
        # 验证更新结果
        updated_coupon = await coupon_repo.get_by_coupon_code(coupon.coupon_code)
        assert updated_coupon.used_count == 6

    async def test_validate_coupon_valid(self, db_session):
        """测试验证有效优惠券"""
        coupon_repo = CouponRepository(db_session)
        
        # 创建有效的测试优惠券
        now = datetime.now()
        coupon_data = {
            "coupon_id": f"VALIDATE_ID_{int(now.timestamp())}",
            "coupon_code": f"VALIDATE_TEST_{int(now.timestamp())}",
            "coupon_name": "验证测试优惠券",
            "coupon_type": "fixed_amount",
            "discount_value": Decimal("25.00"),
            "min_order_amount": Decimal("50.00"),
            "max_discount": Decimal("25.00"),
            "valid_from": now - timedelta(days=1),
            "valid_to": now + timedelta(days=30),
            "usage_limit": 100,
            "used_count": 10,
            "usage_limit_per_user": 5,
            "status": "active"
        }
        
        coupon = CouponDB(**coupon_data)
        db_session.add(coupon)
        await db_session.commit()
        
        # 验证优惠券 - 应该有效
        validation_result = await coupon_repo.validate_coupon_for_user(
            coupon.coupon_code, 
            "test_user",
            order_amount=Decimal("100.00")
        )
        
        assert validation_result.is_valid is True
        assert validation_result.coupon is not None
        assert len(validation_result.validation_errors) == 0

    async def test_validate_coupon_invalid_expired(self, db_session):
        """测试验证过期优惠券"""
        coupon_repo = CouponRepository(db_session)
        
        # 创建过期的测试优惠券
        now = datetime.now()
        coupon_data = {
            "coupon_id": f"EXPIRED_ID_{int(now.timestamp())}",
            "coupon_code": f"EXPIRED_TEST_{int(now.timestamp())}",
            "coupon_name": "过期测试优惠券",
            "coupon_type": "fixed_amount",
            "discount_value": Decimal("25.00"),
            "valid_from": now - timedelta(days=30),
            "valid_to": now - timedelta(days=1),  # 昨天过期
            "usage_limit": 100,
            "used_count": 0,
            "usage_limit_per_user": 10,
            "status": "active"
        }
        
        coupon = CouponDB(**coupon_data)
        db_session.add(coupon)
        await db_session.commit()
        
        # 验证优惠券 - 应该无效（过期）
        validation_result = await coupon_repo.validate_coupon_for_user(
            coupon.coupon_code,
            "test_user",
            order_amount=Decimal("100.00")
        )
        
        assert validation_result.is_valid is False
        assert "已过期" in validation_result.validation_errors[0]

    async def test_validate_coupon_invalid_min_amount(self, db_session):
        """测试验证不满足最小金额的优惠券"""
        coupon_repo = CouponRepository(db_session)
        
        # 创建有最小金额要求的测试优惠券
        now = datetime.now()
        coupon_data = {
            "coupon_id": f"MIN_AMOUNT_ID_{int(now.timestamp())}",
            "coupon_code": f"MIN_AMOUNT_TEST_{int(now.timestamp())}",
            "coupon_name": "最小金额测试券",
            "coupon_type": "fixed_amount",
            "discount_value": Decimal("25.00"),
            "min_order_amount": Decimal("200.00"),  # 要求最小200元
            "valid_from": now - timedelta(days=1),
            "valid_to": now + timedelta(days=30),
            "usage_limit": 100,
            "used_count": 0,
            "usage_limit_per_user": 10,
            "status": "active"
        }
        
        coupon = CouponDB(**coupon_data)
        db_session.add(coupon)
        await db_session.commit()
        
        # 验证优惠券 - 订单金额不足
        validation_result = await coupon_repo.validate_coupon_for_user(
            coupon.coupon_code,
            "test_user",
            order_amount=Decimal("100.00")  # 只有100元，不满足200元要求
        )
        
        assert validation_result.is_valid is False
        assert "最低要求" in validation_result.validation_errors[0]

    async def test_get_user_available_coupons(self, db_session):
        """测试获取用户可用优惠券"""
        coupon_repo = CouponRepository(db_session)
        
        # 创建测试优惠券
        now = datetime.now()
        coupon_data = {
            "coupon_id": f"USER_ID_{int(now.timestamp())}",
            "coupon_code": f"USER_TEST_{int(now.timestamp())}",
            "coupon_name": "用户可用优惠券",
            "coupon_type": "percentage",
            "discount_value": Decimal("0.30"),  # 30% 折扣需要用 0.30 而不是 30.00
            "min_order_amount": Decimal("50.00"),
            "valid_from": now - timedelta(days=1),
            "valid_to": now + timedelta(days=30),
            "usage_limit": 50,
            "used_count": 0,
            "usage_limit_per_user": 1,
            "status": "active",
            "applicable_courses": ["python_course1", "data_science_course1"]
        }
        
        coupon = CouponDB(**coupon_data)
        db_session.add(coupon)
        await db_session.commit()
        
        # 测试获取用户可用优惠券
        coupons = await coupon_repo.get_user_available_coupons(
            "test_user", 
            order_amount=Decimal("100.00")
        )
        
        # 验证结果
        assert isinstance(coupons, list)
        found_coupon = next(
            (c for c in coupons if c.coupon_code == coupon.coupon_code), 
            None
        )
        assert found_coupon is not None
        assert "python_course1" in (found_coupon.applicable_courses or [])

    async def test_get_expiring_coupons(self, db_session):
        """测试获取即将过期的优惠券"""
        coupon_repo = CouponRepository(db_session)
        
        # 创建即将过期的测试优惠券
        now = datetime.now()
        coupon_data = {
            "coupon_id": f"EXPIRING_ID_{int(now.timestamp())}",
            "coupon_code": f"EXPIRING_TEST_{int(now.timestamp())}",
            "coupon_name": "即将过期优惠券",
            "coupon_type": "percentage",
            "discount_value": Decimal("20.00"),
            "valid_from": now - timedelta(days=1),
            "valid_to": now + timedelta(days=3),  # 3天后过期
            "usage_limit": 100,
            "used_count": 0,
            "status": "active"
        }
        
        coupon = CouponDB(**coupon_data)
        db_session.add(coupon)
        await db_session.commit()
        
        # 测试获取即将过期的优惠券
        expiring_coupons = await coupon_repo.get_expiring_coupons(days_ahead=7)
        
        # 验证结果
        assert isinstance(expiring_coupons, list)
        found_coupon = next(
            (c for c in expiring_coupons if c.coupon_code == coupon.coupon_code), 
            None
        )
        assert found_coupon is not None

    async def test_pydantic_model_conversion(self, db_session):
        """测试数据库模型到Pydantic模型的转换"""
        coupon_repo = CouponRepository(db_session)
        
        # 创建测试优惠券
        now = datetime.now()
        coupon_data = {
            "coupon_id": f"CONVERT_ID_{int(now.timestamp())}",
            "coupon_code": f"CONVERT_TEST_{int(now.timestamp())}",
            "coupon_name": "转换测试优惠券",
            "coupon_type": "percentage",
            "discount_value": Decimal("0.25"),  # 25% 折扣用 0.25 而不是 25.00
            "min_order_amount": Decimal("150.00"),
            "max_discount": Decimal("75.00"),
            "valid_from": now,
            "valid_to": now + timedelta(days=30),
            "usage_limit": 200,
            "used_count": 15,
            "status": "active",
            "applicable_courses": ["web_course1", "mobile_course1"],
            "description": "仅限新用户使用"
        }
        
        db_coupon = CouponDB(**coupon_data)
        db_session.add(db_coupon)
        await db_session.commit()
        await db_session.refresh(db_coupon)
        
        # 测试转换
        pydantic_coupon = coupon_repo.to_model(db_coupon)
        
        # 验证基础字段转换
        assert pydantic_coupon.coupon_code == db_coupon.coupon_code
        assert pydantic_coupon.coupon_name == db_coupon.coupon_name
        assert pydantic_coupon.discount_value == db_coupon.discount_value
        
        # 验证列表字段转换
        assert isinstance(pydantic_coupon.applicable_courses, list)
        
        # 验证列表内容
        assert "web_course1" in (pydantic_coupon.applicable_courses or [])