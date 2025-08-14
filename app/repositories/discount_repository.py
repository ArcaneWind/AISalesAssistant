"""
折扣记录数据库操作层
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, update, and_, or_, desc, func, text, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discount import AppliedDiscount, DiscountOption, DiscountApplication
from app.models.database.discount_db import AppliedDiscountDB, DiscountUsageHistoryDB
class DiscountRepository:
    """折扣记录数据库操作层"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_applied_discount(
        self,
        user_id: str,
        discount_type: str,
        discount_value: Decimal,
        course_id: Optional[str] = None,
        order_id: Optional[str] = None,
        agent_reasoning: Optional[str] = None,
        valid_until: Optional[datetime] = None
    ) -> AppliedDiscountDB:
        """创建已应用折扣记录"""
        if valid_until is None:
            valid_until = datetime.now() + timedelta(hours=24)  # 默认24小时有效
        
        db_discount = AppliedDiscountDB(
            user_id=user_id,
            discount_type=discount_type,
            discount_value=discount_value,
            course_id=course_id,
            order_id=order_id,
            agent_reasoning=agent_reasoning,
            valid_until=valid_until,
            is_used=False
        )
        
        self.db.add(db_discount)
        await self.db.flush()
        return db_discount
    
    async def get_user_active_discounts(
        self,
        user_id: str,
        course_id: Optional[str] = None
    ) -> List[AppliedDiscountDB]:
        """获取用户当前有效的折扣"""
        conditions = [
            AppliedDiscountDB.user_id == user_id,
            AppliedDiscountDB.is_used == False,
            AppliedDiscountDB.valid_until > datetime.now()
        ]
        
        if course_id:
            conditions.append(
                or_(
                    AppliedDiscountDB.course_id == course_id,
                    AppliedDiscountDB.course_id.is_(None)  # 通用折扣
                )
            )
        
        query = select(AppliedDiscountDB).where(
            and_(*conditions)
        ).order_by(desc(AppliedDiscountDB.discount_value))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_best_discount_for_user(
        self,
        user_id: str,
        course_id: Optional[str] = None,
        order_amount: Optional[Decimal] = None
    ) -> Optional[AppliedDiscountDB]:
        """获取用户最佳可用折扣"""
        discounts = await self.get_user_active_discounts(user_id, course_id)
        
        if not discounts:
            return None
        
        # 选择最佳折扣（这里可以添加更复杂的逻辑）
        if order_amount:
            # 考虑订单金额选择最优折扣
            best_discount = max(discounts, key=lambda d: self._calculate_discount_amount(d, order_amount))
        else:
            # 直接选择折扣值最大的
            best_discount = max(discounts, key=lambda d: d.discount_value)
        
        return best_discount
    
    def _calculate_discount_amount(self, discount: AppliedDiscountDB, order_amount: Decimal) -> Decimal:
        """计算实际折扣金额"""
        if discount.discount_type == "percentage":
            return order_amount * (discount.discount_value / 100)
        elif discount.discount_type == "fixed_amount":
            return min(discount.discount_value, order_amount)
        else:
            return Decimal("0")
    
    async def use_discount(
        self,
        discount_id: int,
        order_id: str,
        actual_discount_amount: Decimal
    ) -> bool:
        """使用折扣"""
        try:
            # 更新折扣状态
            result = await self.db.execute(
                update(AppliedDiscountDB)
                .where(
                    and_(
                        AppliedDiscountDB.id == discount_id,
                        AppliedDiscountDB.is_used == False
                    )
                )
                .values(
                    is_used=True,
                    used_at=datetime.now(),
                    order_id=order_id,
                    updated_at=datetime.now()
                )
            )
            
            if result.rowcount == 0:
                return False
            
            # 记录使用历史
            usage_history = DiscountUsageHistoryDB(
                applied_discount_id=discount_id,
                user_id=(await self.get(discount_id)).user_id,
                order_id=order_id,
                discount_amount=actual_discount_amount,
                used_at=datetime.now()
            )
            self.db.add(usage_history)
            
            return True
        except Exception:
            return False
    
    async def get_user_discount_history(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取用户折扣使用历史"""
        query = select(
            DiscountUsageHistoryDB,
            AppliedDiscountDB.discount_type,
            AppliedDiscountDB.discount_value,
            AppliedDiscountDB.course_id,
            AppliedDiscountDB.agent_reasoning
        ).join(
            AppliedDiscountDB,
            DiscountUsageHistoryDB.applied_discount_id == AppliedDiscountDB.id
        ).where(
            DiscountUsageHistoryDB.user_id == user_id
        ).order_by(desc(DiscountUsageHistoryDB.used_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        
        return [
            {
                "usage_id": row.DiscountUsageHistoryDB.id,
                "discount_id": row.DiscountUsageHistoryDB.applied_discount_id,
                "discount_type": row.discount_type,
                "discount_value": float(row.discount_value),
                "discount_amount": float(row.DiscountUsageHistoryDB.discount_amount),
                "course_id": row.course_id,
                "order_id": row.DiscountUsageHistoryDB.order_id,
                "agent_reasoning": row.agent_reasoning,
                "used_at": row.DiscountUsageHistoryDB.used_at
            }
            for row in result.fetchall()
        ]
    
    async def get_discount_effectiveness_stats(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """获取折扣效果统计"""
        # 基础统计
        basic_stats = await self.db.execute(
            select(
                func.count(AppliedDiscountDB.id).label("total_applied"),
                func.count(
                    func.distinct(AppliedDiscountDB.user_id)
                ).label("unique_users"),
                func.sum(
                    case(
                        (AppliedDiscountDB.is_used == True, 1),
                        else_=0
                    )
                ).label("total_used")
            ).where(
                AppliedDiscountDB.created_at.between(start_date, end_date)
            )
        )
        
        basic_row = basic_stats.fetchone()
        
        # 类型统计
        type_stats = await self.db.execute(
            select(
                AppliedDiscountDB.discount_type,
                func.count(AppliedDiscountDB.id).label("applied_count"),
                func.sum(
                    case(
                        (AppliedDiscountDB.is_used == True, 1),
                        else_=0
                    )
                ).label("used_count")
            ).where(
                AppliedDiscountDB.created_at.between(start_date, end_date)
            ).group_by(AppliedDiscountDB.discount_type)
        )
        
        # 使用金额统计
        amount_stats = await self.db.execute(
            select(
                func.sum(DiscountUsageHistoryDB.discount_amount).label("total_discount_amount"),
                func.avg(DiscountUsageHistoryDB.discount_amount).label("avg_discount_amount")
            ).where(
                DiscountUsageHistoryDB.used_at.between(start_date, end_date)
            )
        )
        
        amount_row = amount_stats.fetchone()
        
        return {
            "total_applied": basic_row.total_applied or 0,
            "total_used": basic_row.total_used or 0,
            "unique_users": basic_row.unique_users or 0,
            "usage_rate": (basic_row.total_used / basic_row.total_applied * 100) if basic_row.total_applied > 0 else 0,
            "total_discount_amount": float(amount_row.total_discount_amount or 0),
            "avg_discount_amount": float(amount_row.avg_discount_amount or 0),
            "type_breakdown": {
                row.discount_type: {
                    "applied": row.applied_count,
                    "used": row.used_count,
                    "usage_rate": (row.used_count / row.applied_count * 100) if row.applied_count > 0 else 0
                }
                for row in type_stats.fetchall()
            }
        }
    
    async def clean_expired_discounts(self) -> int:
        """清理过期的未使用折扣"""
        result = await self.db.execute(
            update(AppliedDiscountDB)
            .where(
                and_(
                    AppliedDiscountDB.is_used == False,
                    AppliedDiscountDB.valid_until < datetime.now()
                )
            )
            .values(is_expired=True, updated_at=datetime.now())
        )
        
        return result.rowcount
    
    async def get_agent_discount_patterns(
        self,
        user_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """分析Agent折扣决策模式"""
        start_date = datetime.now() - timedelta(days=days)
        conditions = [AppliedDiscountDB.created_at >= start_date]
        
        if user_id:
            conditions.append(AppliedDiscountDB.user_id == user_id)
        
        # 折扣类型分布
        type_distribution = await self.db.execute(
            select(
                AppliedDiscountDB.discount_type,
                func.count(AppliedDiscountDB.id).label("count"),
                func.avg(AppliedDiscountDB.discount_value).label("avg_value")
            ).where(and_(*conditions))
            .group_by(AppliedDiscountDB.discount_type)
        )
        
        # Agent推理关键词分析（简单词频统计）
        reasoning_stats = await self.db.execute(
            select(AppliedDiscountDB.agent_reasoning)
            .where(
                and_(
                    *conditions,
                    AppliedDiscountDB.agent_reasoning.is_not(None)
                )
            )
        )
        
        # 提取推理关键词
        reasoning_keywords = {}
        for row in reasoning_stats.fetchall():
            if row.agent_reasoning:
                words = row.agent_reasoning.lower().split()
                for word in words:
                    if len(word) > 3:  # 过滤短词
                        reasoning_keywords[word] = reasoning_keywords.get(word, 0) + 1
        
        # 获取最常见的推理关键词
        top_keywords = sorted(reasoning_keywords.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "type_distribution": {
                row.discount_type: {
                    "count": row.count,
                    "avg_value": float(row.avg_value)
                }
                for row in type_distribution.fetchall()
            },
            "top_reasoning_keywords": [
                {"keyword": word, "frequency": freq}
                for word, freq in top_keywords
            ]
        }
    
    def to_model(self, db_discount: AppliedDiscountDB) -> AppliedDiscount:
        """转换为Pydantic模型"""
        return AppliedDiscount(
            discount_id=str(db_discount.id),
            user_id=db_discount.user_id,
            discount_type=db_discount.discount_type,
            discount_value=db_discount.discount_value,
            course_id=db_discount.course_id,
            order_id=db_discount.order_id,
            is_used=db_discount.is_used,
            agent_reasoning=db_discount.agent_reasoning,
            valid_until=db_discount.valid_until,
            used_at=db_discount.used_at,
            created_at=db_discount.created_at
        )