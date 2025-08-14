"""
订单数据库操作层
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, update, and_, or_, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderCreate, OrderUpdate, OrderItem, PriceCalculation
from app.models.database.order_db import OrderDB, OrderItemDB, CouponUsageDB
class OrderRepository:
    """订单数据库操作层"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_order_id(self, order_id: str) -> Optional[OrderDB]:
        """根据订单ID获取订单（包含订单项）"""
        result = await self.db.execute(
            select(OrderDB)
            .options(selectinload(OrderDB.order_items))
            .where(OrderDB.order_id == order_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_orders(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[OrderDB]:
        """获取用户订单列表"""
        conditions = [OrderDB.user_id == user_id]
        
        if status_filter:
            conditions.append(OrderDB.order_status == status_filter)
        
        query = select(OrderDB).options(
            selectinload(OrderDB.order_items)
        ).where(
            and_(*conditions)
        ).order_by(desc(OrderDB.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_order_with_items(
        self,
        order_data: OrderCreate,
        user_id: str
    ) -> OrderDB:
        """创建订单及订单项"""
        # 创建订单
        db_order = OrderDB(
            order_id=order_data.order_id,
            user_id=user_id,
            original_amount=order_data.original_total,
            discount_amount=order_data.discount_total,
            final_amount=order_data.final_total,
            coupon_discount=order_data.coupon_discount,
            applied_coupon_code=order_data.coupon_code,
            order_status="pending",
            payment_status="pending",
            payment_method=order_data.payment_method,
            notes=order_data.notes
        )
        
        self.db.add(db_order)
        await self.db.flush()  # 获取生成的ID
        
        # 创建订单项
        for item in order_data.items:
            import uuid
            db_item = OrderItemDB(
                item_id=str(uuid.uuid4()),
                order_id=db_order.order_id,
                course_id=item.course_id,
                course_name=item.course_name,
                original_price=item.original_price,
                discounted_price=item.discounted_price,
                quantity=item.quantity
            )
            self.db.add(db_item)
        
        return db_order
    
    async def update_order_status(
        self,
        order_id: str,
        order_status: Optional[str] = None,
        payment_status: Optional[str] = None,
        payment_method: Optional[str] = None,
        paid_at: Optional[datetime] = None
    ) -> bool:
        """更新订单状态"""
        update_data = {"updated_at": datetime.now()}
        
        if order_status:
            update_data["order_status"] = order_status
        if payment_status:
            update_data["payment_status"] = payment_status
        if payment_method:
            update_data["payment_method"] = payment_method
        if paid_at:
            update_data["paid_at"] = paid_at
        
        result = await self.db.execute(
            update(OrderDB)
            .where(OrderDB.order_id == order_id)
            .values(**update_data)
        )
        
        return result.rowcount > 0
    
    async def cancel_order(self, order_id: str, reason: str = "") -> bool:
        """取消订单"""
        update_data = {
            "order_status": "cancelled",
            "cancel_reason": reason,
            "cancelled_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = await self.db.execute(
            update(OrderDB)
            .where(
                and_(
                    OrderDB.order_id == order_id,
                    OrderDB.order_status.in_(["pending", "confirmed"])
                )
            )
            .values(**update_data)
        )
        
        return result.rowcount > 0
    
    async def get_orders_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[OrderDB]:
        """根据状态获取订单"""
        query = select(OrderDB).options(
            selectinload(OrderDB.order_items)
        ).where(
            OrderDB.order_status == status
        ).order_by(desc(OrderDB.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_pending_payment_orders(
        self,
        timeout_minutes: int = 30
    ) -> List[OrderDB]:
        """获取待支付超时的订单"""
        timeout_time = datetime.now() - timedelta(minutes=timeout_minutes)
        
        query = select(OrderDB).where(
            and_(
                OrderDB.order_status == "pending",
                OrderDB.payment_status == "pending",
                OrderDB.created_at <= timeout_time
            )
        ).order_by(OrderDB.created_at)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_order_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取订单统计信息"""
        conditions = [
            OrderDB.created_at >= start_date,
            OrderDB.created_at <= end_date
        ]
        
        if user_id:
            conditions.append(OrderDB.user_id == user_id)
        
        # 基础统计
        basic_stats = await self.db.execute(
            select(
                func.count(OrderDB.order_id).label("total_orders"),
                func.sum(OrderDB.final_amount).label("total_amount"),
                func.avg(OrderDB.final_amount).label("avg_amount"),
                func.count(
                    func.distinct(OrderDB.user_id)
                ).label("unique_customers")
            ).where(and_(*conditions))
        )
        
        basic_row = basic_stats.fetchone()
        
        # 状态统计
        status_stats = await self.db.execute(
            select(
                OrderDB.order_status,
                func.count(OrderDB.order_id).label("count"),
                func.sum(OrderDB.final_amount).label("amount")
            ).where(and_(*conditions))
            .group_by(OrderDB.order_status)
        )
        
        # 支付方式统计
        payment_stats = await self.db.execute(
            select(
                OrderDB.payment_method,
                func.count(OrderDB.order_id).label("count"),
                func.sum(OrderDB.final_amount).label("amount")
            ).where(
                and_(
                    *conditions,
                    OrderDB.payment_status == "paid"
                )
            ).group_by(OrderDB.payment_method)
        )
        
        return {
            "total_orders": basic_row.total_orders or 0,
            "total_amount": float(basic_row.total_amount or 0),
            "avg_amount": float(basic_row.avg_amount or 0),
            "unique_customers": basic_row.unique_customers or 0,
            "status_breakdown": {
                row.order_status: {
                    "count": row.count,
                    "amount": float(row.amount or 0)
                }
                for row in status_stats.fetchall()
            },
            "payment_method_breakdown": {
                row.payment_method: {
                    "count": row.count,
                    "amount": float(row.amount or 0)
                }
                for row in payment_stats.fetchall()
                if row.payment_method
            }
        }
    
    async def get_revenue_trend(
        self,
        days: int = 30,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取收入趋势"""
        start_date = datetime.now() - timedelta(days=days)
        conditions = [
            OrderDB.payment_status == "paid",
            OrderDB.paid_at >= start_date
        ]
        
        if user_id:
            conditions.append(OrderDB.user_id == user_id)
        
        query = select(
            func.date(OrderDB.paid_at).label("date"),
            func.count(OrderDB.order_id).label("orders"),
            func.sum(OrderDB.final_amount).label("revenue")
        ).where(and_(*conditions)).group_by(
            func.date(OrderDB.paid_at)
        ).order_by(func.date(OrderDB.paid_at))
        
        result = await self.db.execute(query)
        
        return [
            {
                "date": row.date.isoformat(),
                "orders": row.orders,
                "revenue": float(row.revenue)
            }
            for row in result.fetchall()
        ]
    
    async def get_popular_courses(
        self,
        days: int = 30,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取热门课程统计"""
        start_date = datetime.now() - timedelta(days=days)
        
        query = select(
            OrderItemDB.course_id,
            OrderItemDB.course_name,
            func.sum(OrderItemDB.quantity).label("total_sold"),
            func.sum(OrderItemDB.discounted_price * OrderItemDB.quantity).label("total_revenue"),
            func.count(func.distinct(OrderDB.user_id)).label("unique_buyers")
        ).join(
            OrderDB, OrderItemDB.order_id == OrderDB.order_id
        ).where(
            and_(
                OrderDB.payment_status == "paid",
                OrderDB.paid_at >= start_date
            )
        ).group_by(
            OrderItemDB.course_id, OrderItemDB.course_name
        ).order_by(desc("total_sold")).limit(limit)
        
        result = await self.db.execute(query)
        
        return [
            {
                "course_id": row.course_id,
                "course_name": row.course_name,
                "total_sold": row.total_sold,
                "total_revenue": float(row.total_revenue),
                "unique_buyers": row.unique_buyers
            }
            for row in result.fetchall()
        ]
    
    async def calculate_order_price(
        self,
        course_ids: List[str],
        coupon_code: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> PriceCalculation:
        """计算订单价格（不创建订单）"""
        from app.repositories.course_repository import CourseRepository
        from app.repositories.coupon_repository import CouponRepository
        
        course_repo = CourseRepository(self.db)
        coupon_repo = CouponRepository(self.db)
        
        # 获取课程信息
        courses = []
        for course_id in course_ids:
            course = await course_repo.get_by_course_id(course_id)
            if course:
                courses.append(course)
        
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
            validation = await coupon_repo.validate_coupon_for_user(
                coupon_code, user_id, original_total
            )
            if validation.is_valid:
                coupon_discount = validation.discount_amount
        
        # 自动折扣（这里可以添加业务逻辑）
        auto_discount = Decimal("0")
        
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
    
    def to_model(self, db_order: OrderDB) -> Order:
        """转换为Pydantic模型"""
        # 转换订单项 - 安全处理关系加载
        items = []
        try:
            # 尝试访问order_items，如果失败则使用空列表
            if hasattr(db_order, 'order_items') and db_order.order_items is not None:
                for db_item in db_order.order_items:
                    items.append(OrderItem(
                        item_id=db_item.item_id,
                        course_id=db_item.course_id,
                        course_name=db_item.course_name,
                        original_price=db_item.original_price,
                        discounted_price=db_item.discounted_price,
                        quantity=db_item.quantity
                    ))
        except Exception:
            # 如果关系加载失败，使用空列表
            items = []
        
        return Order(
            order_id=db_order.order_id,
            user_id=db_order.user_id,
            order_items=items,
            original_amount=db_order.original_amount,
            discount_amount=db_order.discount_amount,
            final_amount=db_order.final_amount,
            coupon_discount=db_order.coupon_discount,
            applied_coupon_code=db_order.applied_coupon_code,
            order_status=db_order.order_status,
            payment_status=db_order.payment_status,
            payment_method=db_order.payment_method,
            paid_at=db_order.paid_at,
            notes=db_order.notes,
            created_at=db_order.created_at,
            updated_at=db_order.updated_at
        )