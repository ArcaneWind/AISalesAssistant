"""
优惠券业务服务层
提供优惠券相关的业务逻辑处理
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta

from app.models.coupon import Coupon, CouponCreate, CouponUpdate, CouponValidation, CouponUsage
from app.repositories.coupon_repository import CouponRepository
from app.services.common_cache import coupon_cache


class CouponService:
    """优惠券业务服务"""
    
    def __init__(self, coupon_repo: CouponRepository):
        self.coupon_repo = coupon_repo
        self.cache = coupon_cache
        self.cache_prefix = "coupon"
        self.cache_ttl = 1800  # 30分钟缓存
    
    async def get_coupon_by_code(self, coupon_code: str, use_cache: bool = True) -> Optional[Coupon]:
        """根据优惠券代码获取优惠券"""
        cache_key = f"{self.cache_prefix}:code:{coupon_code}"
        
        if use_cache:
            cached_coupon = await self.cache.get(cache_key)
            if cached_coupon:
                return Coupon(**cached_coupon)
        
        db_coupon = await self.coupon_repo.get_by_coupon_code(coupon_code)
        if not db_coupon:
            return None
        
        coupon = self.coupon_repo.to_model(db_coupon)
        
        if use_cache:
            await self.cache.set(cache_key, coupon.dict(), ttl=self.cache_ttl)
        
        return coupon
    
    async def get_valid_coupons(self, use_cache: bool = True) -> List[Coupon]:
        """获取当前有效的优惠券"""
        cache_key = f"{self.cache_prefix}:valid:all"
        
        if use_cache:
            cached_coupons = await self.cache.get(cache_key)
            if cached_coupons:
                return [Coupon(**coupon_data) for coupon_data in cached_coupons]
        
        db_coupons = await self.coupon_repo.get_valid_coupons()
        coupons = [self.coupon_repo.to_model(db_coupon) for db_coupon in db_coupons]
        
        if use_cache:
            await self.cache.set(
                cache_key, 
                [coupon.dict() for coupon in coupons], 
                ttl=self.cache_ttl // 2  # 有效券缓存时间短一些
            )
        
        return coupons
    
    async def get_user_available_coupons(
        self,
        user_id: str,
        order_amount: Decimal,
        use_cache: bool = True
    ) -> List[Coupon]:
        """获取用户可用的优惠券"""
        cache_key = f"{self.cache_prefix}:user:{user_id}:amount:{order_amount}"
        
        if use_cache:
            cached_coupons = await self.cache.get(cache_key)
            if cached_coupons:
                return [Coupon(**coupon_data) for coupon_data in cached_coupons]
        
        db_coupons = await self.coupon_repo.get_user_available_coupons(
            user_id=user_id,
            order_amount=order_amount
        )
        
        coupons = [self.coupon_repo.to_model(db_coupon) for db_coupon in db_coupons]
        
        if use_cache:
            await self.cache.set(
                cache_key, 
                [coupon.dict() for coupon in coupons], 
                ttl=300  # 用户可用券缓存5分钟
            )
        
        return coupons
    
    async def validate_coupon_for_user(
        self,
        coupon_code: str,
        user_id: str,
        order_amount: Decimal
    ) -> CouponValidation:
        """验证用户是否可以使用优惠券"""
        # 优惠券验证不使用缓存，确保实时性
        return await self.coupon_repo.validate_coupon_for_user(
            coupon_code=coupon_code,
            user_id=user_id,
            order_amount=order_amount
        )
    
    async def use_coupon(
        self,
        coupon_code: str,
        user_id: str,
        order_id: str,
        discount_amount: Decimal
    ) -> bool:
        """使用优惠券"""
        # 先验证优惠券
        validation = await self.validate_coupon_for_user(coupon_code, user_id, discount_amount)
        if not validation.is_valid:
            return False
        
        # 使用优惠券
        success = await self.coupon_repo.use_coupon(
            coupon_id=validation.coupon_id,
            user_id=user_id,
            order_id=order_id,
            discount_amount=discount_amount
        )
        
        if success:
            # 清除相关缓存
            await self._clear_coupon_caches(coupon_code, user_id)
        
        return success
    
    async def get_user_coupon_usage_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """获取用户优惠券使用历史"""
        cache_key = f"{self.cache_prefix}:history:{user_id}:{limit}:{offset}"
        
        if use_cache:
            cached_history = await self.cache.get(cache_key)
            if cached_history:
                return cached_history
        
        history = await self.coupon_repo.get_user_coupon_usage_history(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        if use_cache:
            await self.cache.set(cache_key, history, ttl=self.cache_ttl)
        
        return history
    
    async def get_coupon_stats(
        self, 
        coupon_id: str, 
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """获取优惠券统计信息"""
        cache_key = f"{self.cache_prefix}:stats:{coupon_id}"
        
        if use_cache:
            cached_stats = await self.cache.get(cache_key)
            if cached_stats:
                return cached_stats
        
        stats = await self.coupon_repo.get_coupon_stats(coupon_id)
        
        if use_cache and stats:
            await self.cache.set(cache_key, stats, ttl=self.cache_ttl)
        
        return stats
    
    async def get_expiring_coupons(
        self, 
        days_ahead: int = 7,
        use_cache: bool = True
    ) -> List[Coupon]:
        """获取即将过期的优惠券"""
        cache_key = f"{self.cache_prefix}:expiring:{days_ahead}"
        
        if use_cache:
            cached_coupons = await self.cache.get(cache_key)
            if cached_coupons:
                return [Coupon(**coupon_data) for coupon_data in cached_coupons]
        
        db_coupons = await self.coupon_repo.get_expiring_coupons(days_ahead=days_ahead)
        coupons = [self.coupon_repo.to_model(db_coupon) for db_coupon in db_coupons]
        
        if use_cache:
            await self.cache.set(
                cache_key, 
                [coupon.dict() for coupon in coupons], 
                ttl=3600  # 即将过期券缓存1小时
            )
        
        return coupons
    
    async def create_coupon(self, coupon_data: CouponCreate) -> Coupon:
        """创建优惠券"""
        db_coupon = await self.coupon_repo.create(coupon_data.dict())
        coupon = self.coupon_repo.to_model(db_coupon)
        
        # 清除相关缓存
        await self._clear_all_coupon_caches()
        
        return coupon
    
    async def update_coupon(
        self, 
        coupon_id: str, 
        coupon_data: CouponUpdate
    ) -> Optional[Coupon]:
        """更新优惠券"""
        db_coupon = await self.coupon_repo.get_by_coupon_id(coupon_id)
        if not db_coupon:
            return None
        
        updated_coupon = await self.coupon_repo.update(
            db_coupon.id, 
            coupon_data.dict(exclude_unset=True)
        )
        coupon = self.coupon_repo.to_model(updated_coupon)
        
        # 清除相关缓存
        await self._clear_coupon_caches(db_coupon.coupon_code)
        
        return coupon
    
    async def get_best_coupon_for_user(
        self,
        user_id: str,
        order_amount: Decimal,
        course_ids: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """为用户推荐最佳优惠券"""
        available_coupons = await self.get_user_available_coupons(user_id, order_amount)
        
        if not available_coupons:
            return None
        
        best_coupon = None
        best_discount = Decimal("0")
        
        for coupon in available_coupons:
            # 验证优惠券
            validation = await self.validate_coupon_for_user(
                coupon.coupon_code, user_id, order_amount
            )
            
            if validation.is_valid and validation.discount_amount > best_discount:
                best_discount = validation.discount_amount
                best_coupon = {
                    "coupon": coupon,
                    "discount_amount": validation.discount_amount,
                    "final_amount": order_amount - validation.discount_amount
                }
        
        return best_coupon
    
    async def get_coupon_recommendations_for_agent(
        self,
        user_id: str,
        order_amount: Decimal,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """为Agent提供优惠券推荐"""
        available_coupons = await self.get_user_available_coupons(user_id, order_amount)
        
        recommendations = []
        for coupon in available_coupons:
            validation = await self.validate_coupon_for_user(
                coupon.coupon_code, user_id, order_amount
            )
            
            if validation.is_valid:
                # 生成推荐理由
                recommendation_reason = self._generate_recommendation_reason(
                    coupon, validation.discount_amount, order_amount, user_profile
                )
                
                recommendations.append({
                    "coupon_code": coupon.coupon_code,
                    "coupon_name": coupon.coupon_name,
                    "discount_amount": validation.discount_amount,
                    "final_amount": order_amount - validation.discount_amount,
                    "save_percentage": (validation.discount_amount / order_amount * 100),
                    "recommendation_reason": recommendation_reason,
                    "priority_score": self._calculate_coupon_priority(coupon, validation.discount_amount, order_amount)
                })
        
        # 按优先级排序
        recommendations.sort(key=lambda x: x["priority_score"], reverse=True)
        return recommendations
    
    def _generate_recommendation_reason(
        self,
        coupon: Coupon,
        discount_amount: Decimal,
        order_amount: Decimal,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成推荐理由"""
        save_percentage = discount_amount / order_amount * 100
        
        reasons = [f"使用 {coupon.coupon_name} 可节省 {discount_amount} 元"]
        
        if save_percentage >= 20:
            reasons.append("节省幅度较大")
        elif save_percentage >= 10:
            reasons.append("性价比不错")
        
        # 基于用户画像的推荐理由
        if user_profile and user_profile.get("price_sensitivity") == "high":
            reasons.append("适合价格敏感用户")
        
        if coupon.valid_to:
            days_left = (coupon.valid_to - datetime.now()).days
            if days_left <= 3:
                reasons.append("即将过期，建议尽快使用")
        
        return "，".join(reasons)
    
    def _calculate_coupon_priority(
        self,
        coupon: Coupon,
        discount_amount: Decimal,
        order_amount: Decimal
    ) -> float:
        """计算优惠券推荐优先级"""
        # 折扣金额权重 40%
        discount_score = float(discount_amount) / float(order_amount) * 0.4
        
        # 即将过期权重 30%
        expiry_score = 0
        if coupon.valid_to:
            days_left = (coupon.valid_to - datetime.now()).days
            if days_left <= 7:
                expiry_score = (7 - days_left) / 7 * 0.3
        
        # 使用限制权重 30%
        usage_score = 0.3
        if coupon.usage_limit > 0:
            remaining_ratio = (coupon.usage_limit - coupon.used_count) / coupon.usage_limit
            usage_score = remaining_ratio * 0.3
        
        return discount_score + expiry_score + usage_score
    
    async def _clear_coupon_caches(self, coupon_code: Optional[str] = None, user_id: Optional[str] = None):
        """清除优惠券相关缓存"""
        patterns = [
            f"{self.cache_prefix}:valid:*",
            f"{self.cache_prefix}:expiring:*"
        ]
        
        if coupon_code:
            patterns.append(f"{self.cache_prefix}:code:{coupon_code}")
        
        if user_id:
            patterns.extend([
                f"{self.cache_prefix}:user:{user_id}:*",
                f"{self.cache_prefix}:history:{user_id}:*"
            ])
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)
    
    async def _clear_all_coupon_caches(self):
        """清除所有优惠券缓存"""
        await self.cache.delete_pattern(f"{self.cache_prefix}:*")