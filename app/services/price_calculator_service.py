"""
价格计算服务
集成优惠券、折扣等因素的价格计算逻辑，为Agent提供决策支持
"""

from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime

from app.models.order import PriceCalculation, OrderItem
from app.models.discount import DiscountOption, DiscountApplication
from app.repositories.course_repository import CourseRepository
from app.repositories.coupon_repository import CouponRepository
from app.repositories.discount_repository import DiscountRepository
from app.services.common_cache import price_cache
from app.config.discount_options import DISCOUNT_OPTIONS_CONFIG


class PriceCalculatorService:
    """价格计算服务 - 为Agent提供折扣决策支持"""
    
    def __init__(
        self,
        course_repo: CourseRepository,
        coupon_repo: CouponRepository,
        discount_repo: DiscountRepository
    ):
        self.course_repo = course_repo
        self.coupon_repo = coupon_repo
        self.discount_repo = discount_repo
        self.cache = price_cache
        self.cache_prefix = "price_calc"
        self.cache_ttl = 300  # 5分钟缓存，价格计算缓存时间较短
    
    async def calculate_price_with_options(
        self,
        course_ids: List[str],
        user_id: str,
        user_profile: Optional[Dict[str, Any]] = None,
        coupon_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        计算价格并提供Agent可选的折扣方案
        返回完整的价格分析和推荐
        """
        # 获取课程基础信息
        courses = await self._get_courses(course_ids)
        if not courses:
            return self._empty_price_result()
        
        # 计算基础价格
        base_calculation = await self._calculate_base_price(courses, user_id, coupon_code)
        
        # 获取Agent可选的折扣方案
        discount_options = await self._get_discount_options_for_agent(
            user_id=user_id,
            courses=courses,
            base_amount=base_calculation.original_total,
            user_profile=user_profile
        )
        
        # 获取最佳推荐方案
        recommended_option = self._select_recommended_option(
            discount_options, user_profile, base_calculation.original_total
        )
        
        return {
            "base_calculation": base_calculation.dict(),
            "discount_options": discount_options,
            "recommended_option": recommended_option,
            "agent_guidance": self._generate_agent_guidance(
                base_calculation, discount_options, user_profile
            ),
            "user_profile_factors": self._extract_pricing_factors(user_profile)
        }
    
    async def apply_agent_discount_decision(
        self,
        user_id: str,
        course_ids: List[str],
        selected_discount: Dict[str, Any],
        agent_reasoning: str,
        coupon_code: Optional[str] = None
    ) -> PriceCalculation:
        """
        应用Agent选择的折扣方案
        """
        courses = await self._get_courses(course_ids)
        if not courses:
            return self._empty_price_calculation()
        
        # 计算基础价格
        base_calculation = await self._calculate_base_price(courses, user_id, coupon_code)
        
        # 应用Agent选择的折扣
        agent_discount = Decimal("0")
        if selected_discount and selected_discount.get("type") != "none":
            # 创建折扣记录
            discount_db = await self.discount_repo.create_applied_discount(
                user_id=user_id,
                discount_type=selected_discount["type"],
                discount_value=Decimal(str(selected_discount["value"])),
                agent_reasoning=agent_reasoning
            )
            
            # 计算实际折扣金额
            if selected_discount["type"] == "percentage":
                agent_discount = base_calculation.original_total * (Decimal(str(selected_discount["value"])) / 100)
            elif selected_discount["type"] == "fixed_amount":
                agent_discount = min(
                    Decimal(str(selected_discount["value"])), 
                    base_calculation.original_total
                )
        
        # 返回最终计算结果
        total_discount = base_calculation.coupon_discount + agent_discount
        final_total = max(base_calculation.original_total - total_discount, Decimal("0"))
        
        return PriceCalculation(
            original_total=base_calculation.original_total,
            discount_total=total_discount,
            final_total=final_total,
            coupon_discount=base_calculation.coupon_discount,
            auto_discount=agent_discount,
            items=base_calculation.items
        )
    
    async def get_price_comparison(
        self,
        course_ids: List[str],
        user_id: str,
        comparison_scenarios: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        比较不同价格方案
        """
        courses = await self._get_courses(course_ids)
        if not courses:
            return []
        
        results = []
        for scenario in comparison_scenarios:
            calculation = await self.apply_agent_discount_decision(
                user_id=user_id,
                course_ids=course_ids,
                selected_discount=scenario.get("discount", {}),
                agent_reasoning=scenario.get("reasoning", "比较方案"),
                coupon_code=scenario.get("coupon_code")
            )
            
            results.append({
                "scenario_name": scenario.get("name", "未命名方案"),
                "calculation": calculation.dict(),
                "savings": float(calculation.original_total - calculation.final_total),
                "savings_percentage": float(
                    (calculation.original_total - calculation.final_total) / calculation.original_total * 100
                ) if calculation.original_total > 0 else 0
            })
        
        # 按节省金额排序
        results.sort(key=lambda x: x["savings"], reverse=True)
        return results
    
    async def _get_courses(self, course_ids: List[str]):
        """获取课程信息"""
        courses = []
        for course_id in course_ids:
            course = await self.course_repo.get_by_course_id(course_id)
            if course:
                courses.append(course)
        return courses
    
    async def _calculate_base_price(
        self, 
        courses: List,
        user_id: str, 
        coupon_code: Optional[str]
    ) -> PriceCalculation:
        """计算基础价格（不含Agent折扣）"""
        original_total = sum(course.current_price for course in courses)
        
        # 计算优惠券折扣
        coupon_discount = Decimal("0")
        if coupon_code:
            validation = await self.coupon_repo.validate_coupon_for_user(
                coupon_code, user_id, original_total
            )
            if validation.is_valid:
                coupon_discount = validation.discount_amount
        
        # 构建订单项
        items = [
            OrderItem(
                course_id=course.course_id,
                course_name=course.course_name,
                original_price=course.current_price,
                discount_price=course.current_price,
                quantity=1,
                subtotal=course.current_price
            )
            for course in courses
        ]
        
        final_total = original_total - coupon_discount
        
        return PriceCalculation(
            original_total=original_total,
            discount_total=coupon_discount,
            final_total=final_total,
            coupon_discount=coupon_discount,
            auto_discount=Decimal("0"),
            items=items
        )
    
    async def _get_discount_options_for_agent(
        self,
        user_id: str,
        courses: List,
        base_amount: Decimal,
        user_profile: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """获取Agent可选的折扣方案"""
        options = []
        
        # 添加不打折选项
        options.append({
            "type": "none",
            "value": 0,
            "description": "不提供额外折扣",
            "estimated_discount": 0,
            "final_amount": float(base_amount),
            "recommendation_score": self._calculate_no_discount_score(user_profile),
            "reasoning": "保持原价，适用于价格不敏感或高价值感知的用户"
        })
        
        # 从配置中获取折扣选项
        for category, config in DISCOUNT_OPTIONS_CONFIG.items():
            if self._should_offer_category(category, user_profile, courses):
                for option in config["options"]:
                    discount_amount = self._calculate_discount_amount(
                        option, base_amount
                    )
                    
                    if discount_amount > 0:
                        options.append({
                            "type": option["type"],
                            "value": option["value"],
                            "description": option["description"],
                            "estimated_discount": float(discount_amount),
                            "final_amount": float(base_amount - discount_amount),
                            "recommendation_score": self._calculate_option_score(
                                option, user_profile, base_amount
                            ),
                            "reasoning": self._generate_option_reasoning(
                                option, user_profile, discount_amount
                            ),
                            "category": category
                        })
        
        # 按推荐分数排序
        options.sort(key=lambda x: x["recommendation_score"], reverse=True)
        return options
    
    def _should_offer_category(
        self, 
        category: str, 
        user_profile: Optional[Dict[str, Any]], 
        courses: List
    ) -> bool:
        """判断是否应该提供某类折扣"""
        if not user_profile:
            return True
        
        # 根据用户画像和课程特征决定
        if category == "new_user" and user_profile.get("is_new_user", True):
            return True
        elif category == "price_sensitive" and user_profile.get("price_sensitivity") == "high":
            return True
        elif category == "loyalty" and user_profile.get("purchase_history_count", 0) > 2:
            return True
        elif category == "bulk_purchase" and len(courses) >= 2:
            return True
        elif category == "general":
            return True
        
        return False
    
    def _calculate_discount_amount(self, option: Dict, base_amount: Decimal) -> Decimal:
        """计算折扣金额"""
        if option["type"] == "percentage":
            return base_amount * (Decimal(str(option["value"])) / 100)
        elif option["type"] == "fixed_amount":
            return min(Decimal(str(option["value"])), base_amount)
        return Decimal("0")
    
    def _calculate_option_score(
        self, 
        option: Dict, 
        user_profile: Optional[Dict[str, Any]], 
        base_amount: Decimal
    ) -> float:
        """计算折扣选项推荐分数"""
        base_score = 0.5
        
        if not user_profile:
            return base_score
        
        # 价格敏感度权重
        price_sensitivity = user_profile.get("price_sensitivity", "medium")
        if price_sensitivity == "high":
            base_score += 0.3
        elif price_sensitivity == "low":
            base_score -= 0.2
        
        # 折扣幅度适中性
        discount_amount = self._calculate_discount_amount(option, base_amount)
        discount_percentage = discount_amount / base_amount * 100 if base_amount > 0 else 0
        
        if 10 <= discount_percentage <= 25:  # 适中折扣
            base_score += 0.2
        elif discount_percentage > 30:  # 过大折扣可能降低信任
            base_score -= 0.1
        
        return max(0, min(1, base_score))
    
    def _calculate_no_discount_score(self, user_profile: Optional[Dict[str, Any]]) -> float:
        """计算不打折选项的推荐分数"""
        if not user_profile:
            return 0.3
        
        base_score = 0.3
        
        # 价格敏感度低的用户更适合不打折
        if user_profile.get("price_sensitivity") == "low":
            base_score += 0.4
        elif user_profile.get("price_sensitivity") == "high":
            base_score -= 0.2
        
        # 高价值感知用户
        if user_profile.get("value_perception") == "high":
            base_score += 0.2
        
        return max(0, min(1, base_score))
    
    def _select_recommended_option(
        self, 
        options: List[Dict[str, Any]], 
        user_profile: Optional[Dict[str, Any]],
        base_amount: Decimal
    ) -> Optional[Dict[str, Any]]:
        """选择推荐的折扣选项"""
        if not options:
            return None
        
        # 返回得分最高的选项
        return max(options, key=lambda x: x["recommendation_score"])
    
    def _generate_option_reasoning(
        self, 
        option: Dict, 
        user_profile: Optional[Dict[str, Any]], 
        discount_amount: Decimal
    ) -> str:
        """生成折扣选项推理"""
        reasoning_parts = [f"提供{option['description']}"]
        
        if user_profile:
            if user_profile.get("price_sensitivity") == "high":
                reasoning_parts.append("用户对价格敏感")
            
            if user_profile.get("urgency_level", 0) >= 4:
                reasoning_parts.append("用户购买意愿较强")
        
        reasoning_parts.append(f"可节省{discount_amount}元")
        
        return "，".join(reasoning_parts)
    
    def _generate_agent_guidance(
        self, 
        base_calculation: PriceCalculation,
        options: List[Dict[str, Any]], 
        user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成Agent决策指导"""
        guidance = {
            "user_context": self._extract_pricing_factors(user_profile),
            "recommendation": "根据用户画像分析，建议选择得分最高的折扣方案",
            "considerations": [
                "考虑用户价格敏感度",
                "平衡优惠力度与利润",
                "注意用户体验和满意度"
            ]
        }
        
        if user_profile:
            if user_profile.get("price_sensitivity") == "high":
                guidance["considerations"].append("该用户价格敏感，适当优惠有助于成交")
            elif user_profile.get("price_sensitivity") == "low":
                guidance["considerations"].append("该用户价格不敏感，可适当减少折扣保持利润")
        
        return guidance
    
    def _extract_pricing_factors(self, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """提取影响定价的用户因素"""
        if not user_profile:
            return {"status": "无用户画像数据"}
        
        return {
            "price_sensitivity": user_profile.get("price_sensitivity", "unknown"),
            "budget_range": user_profile.get("budget_range", "unknown"),
            "urgency_level": user_profile.get("urgency_level", 0),
            "purchase_history": user_profile.get("purchase_history_count", 0),
            "discount_response": user_profile.get("discount_response", "unknown")
        }
    
    def _empty_price_result(self) -> Dict[str, Any]:
        """空的价格计算结果"""
        return {
            "base_calculation": self._empty_price_calculation().dict(),
            "discount_options": [],
            "recommended_option": None,
            "agent_guidance": {"error": "未找到有效课程"},
            "user_profile_factors": {}
        }
    
    def _empty_price_calculation(self) -> PriceCalculation:
        """空的价格计算"""
        return PriceCalculation(
            original_total=Decimal("0"),
            discount_total=Decimal("0"),
            final_total=Decimal("0"),
            coupon_discount=Decimal("0"),
            auto_discount=Decimal("0"),
            items=[]
        )