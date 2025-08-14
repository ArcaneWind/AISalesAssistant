"""
优惠券数据库操作层
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, update, and_, or_, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coupon import Coupon, CouponCreate, CouponUpdate, CouponValidation
from app.models.database.coupon_db import CouponDB
from app.models.database.order_db import CouponUsageDB
class CouponRepository:
    """优惠券数据库操作类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_coupon_code(self, coupon_code: str) -> Optional[CouponDB]:
        """根据优惠券代码获取优惠券"""
        result = await self.db.execute(
            select(CouponDB).where(CouponDB.coupon_code == coupon_code)
        )
        return result.scalar_one_or_none()
    
    async def get_by_coupon_id(self, coupon_id: str) -> Optional[CouponDB]:
        """根据优惠券ID获取优惠券"""
        result = await self.db.execute(
            select(CouponDB).where(CouponDB.coupon_id == coupon_id)
        )
        return result.scalar_one_or_none()
    
    async def get_valid_coupons(
        self,
        current_time: Optional[datetime] = None
    ) -> List[CouponDB]:
        """获取当前有效的优惠券"""
        if current_time is None:
            current_time = datetime.now()
        
        query = select(CouponDB).where(
            and_(
                CouponDB.status == "active",
                CouponDB.valid_from <= current_time,
                CouponDB.valid_to >= current_time,
                CouponDB.used_count < CouponDB.usage_limit
            )
        ).order_by(desc(CouponDB.discount_value))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_user_available_coupons(
        self,
        user_id: str,
        order_amount: Decimal,
        current_time: Optional[datetime] = None
    ) -> List[CouponDB]:
        """获取用户可用的优惠券"""
        if current_time is None:
            current_time = datetime.now()
        
        # 子查询：获取用户已使用的优惠券及使用次数
        user_usage_subquery = select(
            CouponUsageDB.coupon_id,
            func.count(CouponUsageDB.usage_id).label("user_used_count")
        ).where(CouponUsageDB.user_id == user_id).group_by(CouponUsageDB.coupon_id).subquery()
        
        # 主查询：获取可用优惠券
        query = select(CouponDB).outerjoin(
            user_usage_subquery,
            CouponDB.coupon_id == user_usage_subquery.c.coupon_id
        ).where(
            and_(
                CouponDB.status == "active",
                CouponDB.valid_from <= current_time,
                CouponDB.valid_to >= current_time,
                CouponDB.used_count < CouponDB.usage_limit,
                CouponDB.min_order_amount <= order_amount,
                or_(
                    user_usage_subquery.c.user_used_count.is_(None),
                    user_usage_subquery.c.user_used_count < CouponDB.usage_limit_per_user
                )
            )
        ).order_by(desc(CouponDB.discount_value))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def validate_coupon_for_user(
        self,
        coupon_code: str,
        user_id: str,
        order_amount: Decimal,
        current_time: Optional[datetime] = None
    ) -> CouponValidation:
        """验证用户是否可以使用优惠券"""
        if current_time is None:
            current_time = datetime.now()
        
        # 获取优惠券信息
        coupon = await self.get_by_coupon_code(coupon_code)
        if not coupon:
            return CouponValidation(
                is_valid=False,
                validation_errors=["优惠券不存在"],
                coupon=None,
                estimated_discount=Decimal("0")
            )
        
        # 转换为Pydantic模型
        coupon_model = self.to_model(coupon)
        
        # 检查优惠券状态
        if coupon.status != "active":
            return CouponValidation(
                is_valid=False,
                validation_errors=["优惠券已停用"],
                coupon=coupon_model,
                estimated_discount=Decimal("0")
            )
        
        # 检查有效期
        if current_time < coupon.valid_from:
            return CouponValidation(
                is_valid=False,
                validation_errors=["优惠券尚未开始使用"],
                coupon=coupon_model,
                estimated_discount=Decimal("0")
            )
        
        if current_time > coupon.valid_to:
            return CouponValidation(
                is_valid=False,
                validation_errors=["优惠券已过期"],
                coupon=coupon_model,
                estimated_discount=Decimal("0")
            )
        
        # 检查总使用次数
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            return CouponValidation(
                is_valid=False,
                validation_errors=["优惠券使用次数已达上限"],
                coupon=coupon_model,
                estimated_discount=Decimal("0")
            )
        
        # 检查最小订单金额
        if order_amount < coupon.min_order_amount:
            return CouponValidation(
                is_valid=False,
                validation_errors=[f"订单金额不满足最低要求 {coupon.min_order_amount} 元"],
                coupon=coupon_model,
                estimated_discount=Decimal("0"),
                min_order_required=coupon.min_order_amount
            )
        
        # 检查用户使用次数
        if coupon.usage_limit_per_user:
            user_used_count = await self.get_user_coupon_usage_count(user_id, coupon.coupon_id)
            if user_used_count >= coupon.usage_limit_per_user:
                return CouponValidation(
                    is_valid=False,
                    validation_errors=["您已达到该优惠券的使用上限"],
                    coupon=coupon_model,
                    estimated_discount=Decimal("0")
                )
        
        # 计算优惠金额
        if coupon.coupon_type == "fixed_amount":
            discount_amount = min(coupon.discount_value, order_amount)
        else:  # percentage
            discount_amount = order_amount * coupon.discount_value
            if coupon.max_discount:
                discount_amount = min(discount_amount, coupon.max_discount)
            discount_amount = min(discount_amount, order_amount)
        
        return CouponValidation(
            is_valid=True,
            validation_errors=[],
            coupon=coupon_model,
            estimated_discount=discount_amount,
            applicable_courses=coupon.applicable_courses or []
        )
    
    async def get_user_coupon_usage_count(self, user_id: str, coupon_id: str) -> int:
        """获取用户对特定优惠券的使用次数"""
        result = await self.db.execute(
            select(func.count(CouponUsageDB.usage_id)).where(
                and_(
                    CouponUsageDB.user_id == user_id,
                    CouponUsageDB.coupon_id == coupon_id
                )
            )
        )
        return result.scalar() or 0
    
    async def get_user_coupon_usage_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取用户优惠券使用历史"""
        query = select(
            CouponUsageDB,
            CouponDB.coupon_name,
            CouponDB.coupon_code,
            CouponDB.coupon_type
        ).join(
            CouponDB, CouponUsageDB.coupon_id == CouponDB.coupon_id
        ).where(
            CouponUsageDB.user_id == user_id
        ).order_by(desc(CouponUsageDB.used_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return [
            {
                "usage_id": row.CouponUsageDB.usage_id,
                "coupon_id": row.CouponUsageDB.coupon_id,
                "coupon_name": row.coupon_name,
                "coupon_code": row.coupon_code,
                "coupon_type": row.coupon_type,
                "order_id": row.CouponUsageDB.order_id,
                "discount_amount": row.CouponUsageDB.discount_amount,
                "used_at": row.CouponUsageDB.used_at
            }
            for row in result.fetchall()
        ]
    
    async def use_coupon(
        self,
        coupon_id: str,
        user_id: str,
        order_id: str,
        discount_amount: Decimal
    ) -> bool:
        """使用优惠券（记录使用并更新统计）"""
        try:
            # 获取优惠券信息
            coupon = await self.get_by_coupon_id(coupon_id)
            if not coupon:
                return False
            
            # 记录使用
            import uuid
            usage = CouponUsageDB(
                usage_id=str(uuid.uuid4()),
                coupon_id=coupon_id,
                coupon_code=coupon.coupon_code,
                user_id=user_id,
                order_id=order_id,
                course_ids=[],  # 简化处理，实际应该传入课程列表
                original_amount=discount_amount,  # 简化处理
                discount_amount=discount_amount,
                final_amount=Decimal("0"),  # 简化处理
                used_at=datetime.now()
            )
            self.db.add(usage)
            
            # 更新优惠券使用次数
            await self.db.execute(
                update(CouponDB)
                .where(CouponDB.coupon_id == coupon_id)
                .values(
                    used_count=CouponDB.used_count + 1,
                    updated_at=datetime.now()
                )
            )
            
            return True
        except Exception:
            return False
    
    async def get_coupon_stats(self, coupon_id: str) -> Dict[str, Any]:
        """获取优惠券统计信息"""
        # 基本信息
        coupon = await self.get_by_coupon_id(coupon_id)
        if not coupon:
            return {}
        
        # 使用统计
        usage_stats = await self.db.execute(
            select(
                func.count(CouponUsageDB.usage_id).label("total_usage"),
                func.sum(CouponUsageDB.discount_amount).label("total_discount"),
                func.count(func.distinct(CouponUsageDB.user_id)).label("unique_users")
            ).where(CouponUsageDB.coupon_id == coupon_id)
        )
        
        stats_row = usage_stats.fetchone()
        
        return {
            "coupon_id": coupon.coupon_id,
            "coupon_name": coupon.coupon_name,
            "coupon_code": coupon.coupon_code,
            "status": coupon.status,
            "usage_limit": coupon.usage_limit,
            "used_count": coupon.used_count,
            "remaining_count": coupon.usage_limit - coupon.used_count,
            "total_usage": stats_row.total_usage or 0,
            "total_discount": float(stats_row.total_discount or 0),
            "unique_users": stats_row.unique_users or 0,
            "usage_rate": (coupon.used_count / coupon.usage_limit * 100) if coupon.usage_limit > 0 else 0
        }
    
    async def get_expiring_coupons(
        self,
        days_ahead: int = 7
    ) -> List[CouponDB]:
        """获取即将过期的优惠券"""
        expiry_date = datetime.now() + timedelta(days=days_ahead)
        
        query = select(CouponDB).where(
            and_(
                CouponDB.status == "active",
                CouponDB.valid_to <= expiry_date,
                CouponDB.valid_to >= datetime.now(),
                CouponDB.used_count < CouponDB.usage_limit
            )
        ).order_by(CouponDB.valid_to)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    def to_model(self, db_coupon: CouponDB) -> Coupon:
        """转换为Pydantic模型"""
        return Coupon(
            coupon_id=db_coupon.coupon_id,
            coupon_code=db_coupon.coupon_code,
            coupon_name=db_coupon.coupon_name,
            coupon_type=db_coupon.coupon_type,
            discount_value=db_coupon.discount_value,
            min_order_amount=db_coupon.min_order_amount,
            max_discount=db_coupon.max_discount,
            valid_from=db_coupon.valid_from,
            valid_to=db_coupon.valid_to,
            usage_limit=db_coupon.usage_limit,
            used_count=db_coupon.used_count,
            usage_limit_per_user=db_coupon.usage_limit_per_user,
            applicable_courses=db_coupon.applicable_courses or [],
            description=db_coupon.description,
            status=db_coupon.status,
            created_at=db_coupon.created_at,
            updated_at=db_coupon.updated_at
        )