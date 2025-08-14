"""
订单业务服务层
提供订单相关的业务逻辑处理
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
import uuid

from app.models.order import Order, OrderCreate, OrderUpdate, OrderItem, PriceCalculation
from app.repositories.order_repository import OrderRepository
from app.repositories.course_repository import CourseRepository
from app.repositories.coupon_repository import CouponRepository
from app.repositories.discount_repository import DiscountRepository
from app.services.common_cache import order_cache


class OrderService:
    """订单业务服务"""
    
    def __init__(
        self, 
        order_repo: OrderRepository,
        course_repo: CourseRepository,
        coupon_repo: CouponRepository,
        discount_repo: DiscountRepository
    ):
        self.order_repo = order_repo
        self.course_repo = course_repo
        self.coupon_repo = coupon_repo
        self.discount_repo = discount_repo
        self.cache = order_cache
        self.cache_prefix = "order"
        self.cache_ttl = 1800  # 30分钟缓存
    
    async def get_order_by_id(self, order_id: str, use_cache: bool = True) -> Optional[Order]:
        """获取订单详情"""
        cache_key = f"{self.cache_prefix}:detail:{order_id}"
        
        if use_cache:
            cached_order = await self.cache.get(cache_key)
            if cached_order:
                return Order(**cached_order)
        
        db_order = await self.order_repo.get_by_order_id(order_id)
        if not db_order:
            return None
        
        order = self.order_repo.to_model(db_order)
        
        if use_cache:
            await self.cache.set(cache_key, order.dict(), ttl=self.cache_ttl)
        
        return order
    
    async def get_user_orders(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Order]:
        """获取用户订单列表"""
        cache_key = f"{self.cache_prefix}:user:{user_id}:{limit}:{offset}:{status_filter or 'all'}"
        
        if use_cache:
            cached_orders = await self.cache.get(cache_key)
            if cached_orders:
                return [Order(**order_data) for order_data in cached_orders]
        
        db_orders = await self.order_repo.get_user_orders(
            user_id=user_id,
            limit=limit,
            offset=offset,
            status_filter=status_filter
        )
        
        orders = [self.order_repo.to_model(db_order) for db_order in db_orders]
        
        if use_cache:
            await self.cache.set(
                cache_key, 
                [order.dict() for order in orders], 
                ttl=self.cache_ttl // 2
            )
        
        return orders
    
    async def calculate_order_price(
        self,
        course_ids: List[str],
        user_id: Optional[str] = None,
        coupon_code: Optional[str] = None,
        apply_auto_discount: bool = True
    ) -> PriceCalculation:
        """计算订单价格"""
        # 获取课程信息
        courses = []
        for course_id in course_ids:
            db_course = await self.course_repo.get_by_course_id(course_id)
            if db_course:
                courses.append(db_course)
        
        if not courses:
            return PriceCalculation(
                original_total=Decimal("0"),
                discount_total=Decimal("0"),
                final_total=Decimal("0"),
                coupon_discount=Decimal("0"),
                auto_discount=Decimal("0"),
                items=[]
            )
        
        # 计算原始总价
        original_total = sum(course.current_price for course in courses)
        
        # 计算优惠券折扣
        coupon_discount = Decimal("0")
        if coupon_code and user_id:
            validation = await self.coupon_repo.validate_coupon_for_user(
                coupon_code, user_id, original_total
            )
            if validation.is_valid:
                coupon_discount = validation.discount_amount
        
        # 计算自动折扣（来自Agent决策）
        auto_discount = Decimal("0")
        if apply_auto_discount and user_id:
            best_discount = await self.discount_repo.get_best_discount_for_user(
                user_id=user_id,
                order_amount=original_total
            )
            if best_discount:
                if best_discount.discount_type == "percentage":
                    auto_discount = original_total * (best_discount.discount_value / 100)
                elif best_discount.discount_type == "fixed_amount":
                    auto_discount = min(best_discount.discount_value, original_total)
        
        # 计算最终价格
        total_discount = coupon_discount + auto_discount
        final_total = max(original_total - total_discount, Decimal("0"))
        
        # 构建订单项
        items = [
            OrderItem(
                course_id=course.course_id,
                course_name=course.course_name,
                original_price=course.current_price,
                discount_price=course.current_price,  # 这里可以添加单个课程折扣逻辑
                quantity=1,
                subtotal=course.current_price
            )
            for course in courses
        ]
        
        return PriceCalculation(
            original_total=original_total,
            discount_total=total_discount,
            final_total=final_total,
            coupon_discount=coupon_discount,
            auto_discount=auto_discount,
            items=items
        )
    
    async def create_order(
        self,
        user_id: str,
        course_ids: List[str],
        coupon_code: Optional[str] = None,
        payment_method: str = "alipay",
        notes: Optional[str] = None
    ) -> Order:
        """创建订单"""
        # 计算价格
        price_calc = await self.calculate_order_price(
            course_ids=course_ids,
            user_id=user_id,
            coupon_code=coupon_code
        )
        
        # 生成订单ID
        order_id = f"ORDER_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8].upper()}"
        
        # 创建订单数据
        order_data = OrderCreate(
            order_id=order_id,
            items=price_calc.items,
            original_total=price_calc.original_total,
            discount_total=price_calc.discount_total,
            final_total=price_calc.final_total,
            coupon_discount=price_calc.coupon_discount,
            auto_discount=price_calc.auto_discount,
            coupon_code=coupon_code,
            payment_method=payment_method,
            notes=notes
        )
        
        # 创建订单
        db_order = await self.order_repo.create_order_with_items(order_data, user_id)
        order = self.order_repo.to_model(db_order)
        
        # 使用优惠券
        if coupon_code and price_calc.coupon_discount > 0:
            await self.coupon_repo.use_coupon(
                coupon_code=coupon_code,
                user_id=user_id,
                order_id=order_id,
                discount_amount=price_calc.coupon_discount
            )
        
        # 使用自动折扣
        if price_calc.auto_discount > 0:
            discount = await self.discount_repo.get_best_discount_for_user(user_id)
            if discount:
                await self.discount_repo.use_discount(
                    discount_id=discount.id,
                    order_id=order_id,
                    actual_discount_amount=price_calc.auto_discount
                )
        
        # 清除相关缓存
        await self._clear_user_order_caches(user_id)
        
        return order
    
    async def update_order_status(
        self,
        order_id: str,
        order_status: Optional[str] = None,
        payment_status: Optional[str] = None,
        payment_method: Optional[str] = None
    ) -> bool:
        """更新订单状态"""
        payment_time = None
        if payment_status == "paid":
            payment_time = datetime.now()
        
        success = await self.order_repo.update_order_status(
            order_id=order_id,
            order_status=order_status,
            payment_status=payment_status,
            payment_method=payment_method,
            payment_time=payment_time
        )
        
        if success:
            # 清除缓存
            await self.cache.delete(f"{self.cache_prefix}:detail:{order_id}")
        
        return success
    
    async def cancel_order(self, order_id: str, reason: str = "") -> bool:
        """取消订单"""
        # 获取订单信息
        order = await self.get_order_by_id(order_id, use_cache=False)
        if not order:
            return False
        
        # 取消订单
        success = await self.order_repo.cancel_order(order_id, reason)
        
        if success:
            # 清除缓存
            await self._clear_order_caches(order_id, order.user_id)
        
        return success
    
    async def get_order_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """获取订单统计信息"""
        cache_key = f"{self.cache_prefix}:stats:{start_date.date()}:{end_date.date()}:{user_id or 'all'}"
        
        if use_cache:
            cached_stats = await self.cache.get(cache_key)
            if cached_stats:
                return cached_stats
        
        stats = await self.order_repo.get_order_statistics(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id
        )
        
        if use_cache:
            await self.cache.set(cache_key, stats, ttl=self.cache_ttl * 2)
        
        return stats
    
    async def get_revenue_trend(
        self,
        days: int = 30,
        user_id: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """获取收入趋势"""
        cache_key = f"{self.cache_prefix}:revenue_trend:{days}:{user_id or 'all'}"
        
        if use_cache:
            cached_trend = await self.cache.get(cache_key)
            if cached_trend:
                return cached_trend
        
        trend = await self.order_repo.get_revenue_trend(days=days, user_id=user_id)
        
        if use_cache:
            await self.cache.set(cache_key, trend, ttl=self.cache_ttl)
        
        return trend
    
    async def get_popular_courses(
        self,
        days: int = 30,
        limit: int = 10,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """获取热门课程统计"""
        cache_key = f"{self.cache_prefix}:popular_courses:{days}:{limit}"
        
        if use_cache:
            cached_courses = await self.cache.get(cache_key)
            if cached_courses:
                return cached_courses
        
        courses = await self.order_repo.get_popular_courses(days=days, limit=limit)
        
        if use_cache:
            await self.cache.set(cache_key, courses, ttl=self.cache_ttl)
        
        return courses
    
    async def get_pending_payment_orders(
        self, 
        timeout_minutes: int = 30
    ) -> List[Order]:
        """获取待支付超时的订单"""
        db_orders = await self.order_repo.get_pending_payment_orders(timeout_minutes=timeout_minutes)
        return [self.order_repo.to_model(db_order) for db_order in db_orders]
    
    async def process_payment(
        self,
        order_id: str,
        payment_method: str,
        payment_result: Dict[str, Any]
    ) -> bool:
        """处理支付结果"""
        if payment_result.get("status") == "success":
            success = await self.update_order_status(
                order_id=order_id,
                order_status="paid",
                payment_status="paid",
                payment_method=payment_method
            )
            
            if success:
                # 可以在这里添加支付成功后的业务逻辑
                # 比如发送确认邮件、更新课程统计等
                await self._handle_payment_success(order_id)
            
            return success
        else:
            # 支付失败，更新订单状态
            return await self.update_order_status(
                order_id=order_id,
                order_status="payment_failed",
                payment_status="failed"
            )
    
    async def get_order_for_agent(self, order_id: str) -> Optional[Dict[str, Any]]:
        """为Agent提供订单信息"""
        order = await self.get_order_by_id(order_id)
        if not order:
            return None
        
        # 生成Agent友好的订单描述
        agent_description = self._generate_agent_order_description(order)
        
        return {
            "order_id": order.order_id,
            "user_id": order.user_id,
            "status": order.order_status,
            "payment_status": order.payment_status,
            "total_amount": float(order.final_total),
            "discount_amount": float(order.discount_total),
            "course_count": len(order.items),
            "courses": [
                {
                    "course_id": item.course_id,
                    "course_name": item.course_name,
                    "price": float(item.subtotal)
                }
                for item in order.items
            ],
            "agent_description": agent_description,
            "created_at": order.created_at.isoformat() if order.created_at else None
        }
    
    def _generate_agent_order_description(self, order: Order) -> str:
        """生成Agent友好的订单描述"""
        description_parts = [
            f"订单编号：{order.order_id}",
            f"订单状态：{order.order_status}",
            f"支付状态：{order.payment_status}",
            f"课程数量：{len(order.items)}门",
            f"订单总额：{order.final_total}元"
        ]
        
        if order.discount_total > 0:
            description_parts.append(f"优惠金额：{order.discount_total}元")
        
        if order.coupon_code:
            description_parts.append(f"使用优惠券：{order.coupon_code}")
        
        course_names = [item.course_name for item in order.items]
        description_parts.append(f"购买课程：{', '.join(course_names)}")
        
        return "\n".join(description_parts)
    
    async def _handle_payment_success(self, order_id: str):
        """处理支付成功后的业务逻辑"""
        order = await self.get_order_by_id(order_id)
        if not order:
            return
        
        # 更新课程统计
        for item in order.items:
            db_course = await self.course_repo.get_by_course_id(item.course_id)
            if db_course:
                await self.course_repo.update_course_stats(
                    course_id=item.course_id,
                    new_student_count=db_course.student_count + 1
                )
    
    async def _clear_order_caches(self, order_id: str, user_id: str):
        """清除订单相关缓存"""
        patterns = [
            f"{self.cache_prefix}:detail:{order_id}",
            f"{self.cache_prefix}:user:{user_id}:*",
            f"{self.cache_prefix}:stats:*",
            f"{self.cache_prefix}:revenue_trend:*",
            f"{self.cache_prefix}:popular_courses:*"
        ]
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)
    
    async def _clear_user_order_caches(self, user_id: str):
        """清除用户订单相关缓存"""
        patterns = [
            f"{self.cache_prefix}:user:{user_id}:*",
            f"{self.cache_prefix}:stats:*",
            f"{self.cache_prefix}:revenue_trend:*"
        ]
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)