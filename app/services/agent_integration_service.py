"""
Agent集成服务
为AI销售助手Agent提供统一的服务接口
"""

from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime

from app.services.course_service import CourseService
from app.services.coupon_service import CouponService  
from app.services.order_service import OrderService
from app.services.price_calculator_service import PriceCalculatorService
from app.services.user_profile_service import UserProfileService
from app.models.user_profile import UserProfile
from app.models.course import Course, CourseResponse
from app.models.order import Order, PriceCalculation
from app.models.coupon import CouponValidation


class AgentIntegrationService:
    """Agent集成服务 - 为AI销售助手提供统一接口"""
    
    def __init__(
        self,
        course_service: CourseService,
        coupon_service: CouponService,
        order_service: OrderService,
        price_calculator_service: PriceCalculatorService,
        user_profile_service: UserProfileService
    ):
        self.course_service = course_service
        self.coupon_service = coupon_service
        self.order_service = order_service
        self.price_calculator_service = price_calculator_service
        self.user_profile_service = user_profile_service
    
    # ========== 用户画像相关接口 ==========
    
    async def get_user_profile_for_agent(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """获取用户画像信息供Agent分析"""
        profile = await self.user_profile_service.get_user_profile(user_id, session_id)
        
        if not profile:
            return {
                "status": "no_profile",
                "message": "用户画像不存在",
                "recommendations": ["建议先进行用户需求调研"]
            }
        
        # 转换为Agent友好的格式
        return {
            "status": "found",
            "profile": profile.dict(),
            "key_insights": self._extract_key_insights(profile),
            "sales_guidance": self._generate_sales_guidance(profile),
            "recommendations": self._generate_profile_recommendations(profile)
        }
    
    async def update_user_profile_from_conversation(
        self,
        user_id: str,
        session_id: str,
        conversation_insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """根据对话内容更新用户画像"""
        try:
            profile = await self.user_profile_service.update_profile_from_conversation(
                user_id=user_id,
                session_id=session_id,
                insights=conversation_insights
            )
            
            return {
                "status": "updated",
                "profile": profile.dict() if profile else None,
                "message": "用户画像已更新"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"更新用户画像失败: {str(e)}"
            }
    
    # ========== 课程推荐相关接口 ==========
    
    async def get_course_recommendations_for_agent(
        self,
        user_id: str,
        session_id: str,
        search_keywords: Optional[str] = None,
        category_preference: Optional[str] = None,
        limit: int = 50  # 增加数量供Agent筛选
    ) -> Dict[str, Any]:
        """为Agent获取课程信息，由Agent决定推荐逻辑"""
        # 获取用户画像
        profile = await self.user_profile_service.get_user_profile(user_id, session_id)
        
        # 获取候选课程（不做规则过滤）
        if search_keywords:
            courses = await self.course_service.search_courses(
                keywords=search_keywords,
                category=category_preference,
                limit=limit
            )
        else:
            # 获取所有课程供Agent分析
            courses = await self.course_service.get_all_courses_for_agent(limit=limit)
        
        # 转换为Agent格式，提供完整信息但不做预筛选
        agent_courses = []
        for course in courses:
            course_response = await self.course_service.get_course_for_agent(course.course_id)
            if course_response:
                agent_courses.append({
                    "course": course_response.dict(),
                    "metadata": {
                        "category": course.category,
                        "difficulty": course.difficulty_level,
                        "price": float(course.current_price),
                        "rating": course.rating,
                        "student_count": course.student_count,
                        "tags": course.tags,
                        "prerequisites": course.prerequisites,
                        "learning_outcomes": course.learning_outcomes
                    }
                })
        
        return {
            "status": "success",
            "courses": agent_courses,
            "user_context": self._extract_key_insights(profile) if profile else None,
            "agent_guidance": {
                "instruction": "请根据用户画像和需求，从提供的课程中选择最适合的推荐给用户",
                "user_profile": profile.dict() if profile else None,
                "search_context": {
                    "keywords": search_keywords,
                    "category_preference": category_preference
                },
                "recommendation_factors": [
                    "用户学习目标匹配度",
                    "技能水平适应性", 
                    "价格预算匹配",
                    "课程质量和热度",
                    "个人兴趣偏好"
                ]
            }
        }
    
    async def get_course_details_for_agent(self, course_id: str) -> Dict[str, Any]:
        """获取课程详细信息供Agent介绍"""
        course_response = await self.course_service.get_course_for_agent(course_id)
        
        if not course_response:
            return {
                "status": "not_found",
                "message": "课程不存在"
            }
        
        return {
            "status": "found",
            "course": course_response.dict(),
            "selling_points": self._extract_selling_points(course_response),
            "target_audience": self._identify_target_audience(course_response)
        }
    
    # ========== 价格计算和优惠相关接口 ==========
    
    async def calculate_pricing_options_for_agent(
        self,
        user_id: str,
        session_id: str,
        course_ids: List[str],
        coupon_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """为Agent计算价格选项和优惠方案"""
        # 获取用户画像
        profile = await self.user_profile_service.get_user_profile(user_id, session_id)
        user_profile_dict = profile.dict() if profile else None
        
        # 计算价格选项
        pricing_result = await self.price_calculator_service.calculate_price_with_options(
            course_ids=course_ids,
            user_id=user_id,
            user_profile=user_profile_dict,
            coupon_code=coupon_code
        )
        
        # 获取可用优惠券推荐
        base_amount = pricing_result["base_calculation"]["original_total"]
        coupon_recommendations = await self.coupon_service.get_coupon_recommendations_for_agent(
            user_id=user_id,
            order_amount=Decimal(str(base_amount)),
            user_profile=user_profile_dict
        )
        
        return {
            "status": "success",
            "pricing_analysis": pricing_result,
            "available_coupons": coupon_recommendations,
            "agent_guidance": {
                "user_context": pricing_result.get("user_profile_factors", {}),
                "pricing_strategy": self._get_pricing_strategy(profile),
                "negotiation_tips": self._get_negotiation_tips(profile),
                "closing_suggestions": self._get_closing_suggestions(profile, base_amount)
            }
        }
    
    async def apply_agent_discount_decision(
        self,
        user_id: str,
        course_ids: List[str],
        selected_discount: Dict[str, Any],
        agent_reasoning: str,
        coupon_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """应用Agent的折扣决策"""
        try:
            final_calculation = await self.price_calculator_service.apply_agent_discount_decision(
                user_id=user_id,
                course_ids=course_ids,
                selected_discount=selected_discount,
                agent_reasoning=agent_reasoning,
                coupon_code=coupon_code
            )
            
            return {
                "status": "success",
                "final_pricing": final_calculation.dict(),
                "next_steps": [
                    "向用户展示最终价格",
                    "确认购买意向",
                    "引导至订单创建"
                ]
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"应用折扣失败: {str(e)}"
            }
    
    # ========== 订单管理相关接口 ==========
    
    async def create_order_for_agent(
        self,
        user_id: str,
        course_ids: List[str],
        selected_discount: Optional[Dict[str, Any]] = None,
        agent_reasoning: Optional[str] = None,
        coupon_code: Optional[str] = None,
        payment_method: str = "alipay"
    ) -> Dict[str, Any]:
        """为Agent创建订单"""
        try:
            # 如果有Agent折扣决策，先应用
            if selected_discount and agent_reasoning:
                await self.price_calculator_service.apply_agent_discount_decision(
                    user_id=user_id,
                    course_ids=course_ids,
                    selected_discount=selected_discount,
                    agent_reasoning=agent_reasoning,
                    coupon_code=coupon_code
                )
            
            # 创建订单
            order = await self.order_service.create_order(
                user_id=user_id,
                course_ids=course_ids,
                coupon_code=coupon_code,
                payment_method=payment_method,
                notes=f"Agent创建订单 - 推理: {agent_reasoning}" if agent_reasoning else None
            )
            
            # 获取Agent格式的订单信息
            agent_order_info = await self.order_service.get_order_for_agent(order.order_id)
            
            return {
                "status": "success",
                "order": agent_order_info,
                "next_steps": [
                    "引导用户完成支付",
                    "提供支付链接或二维码",
                    "跟进支付状态"
                ],
                "payment_guidance": self._get_payment_guidance(order)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"创建订单失败: {str(e)}"
            }
    
    async def get_order_status_for_agent(self, order_id: str) -> Dict[str, Any]:
        """获取订单状态供Agent查询"""
        agent_order_info = await self.order_service.get_order_for_agent(order_id)
        
        if not agent_order_info:
            return {
                "status": "not_found",
                "message": "订单不存在"
            }
        
        return {
            "status": "found",
            "order": agent_order_info,
            "status_explanation": self._explain_order_status(agent_order_info),
            "suggested_actions": self._suggest_order_actions(agent_order_info)
        }
    
    # ========== 对话支持相关接口 ==========
    
    async def get_conversation_context_for_agent(
        self,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """获取对话上下文信息"""
        # 获取用户画像
        profile = await self.user_profile_service.get_user_profile(user_id, session_id)
        
        # 获取用户最近订单
        recent_orders = await self.order_service.get_user_orders(user_id, limit=3)
        
        # 获取用户优惠券使用历史
        coupon_history = await self.coupon_service.get_user_coupon_usage_history(user_id, limit=5)
        
        return {
            "user_profile": profile.dict() if profile else None,
            "recent_orders": [order.dict() for order in recent_orders],
            "coupon_history": coupon_history,
            "conversation_tips": self._get_conversation_tips(profile),
            "personalization_suggestions": self._get_personalization_suggestions(profile)
        }
    
    # ========== 私有方法 - 辅助功能 ==========
    
    def _extract_key_insights(self, profile: Optional[UserProfile]) -> Dict[str, Any]:
        """提取用户关键洞察"""
        if not profile:
            return {}
        
        return {
            "price_sensitivity": profile.price_sensitivity,
            "urgency_level": profile.urgency_level,
            "learning_goals": profile.learning_goals,
            "budget_range": profile.budget_range,
            "communication_style": profile.communication_style,
            "decision_pattern": profile.decision_pattern
        }
    
    def _generate_sales_guidance(self, profile: UserProfile) -> List[str]:
        """生成销售指导"""
        guidance = []
        
        if profile.price_sensitivity == "high":
            guidance.append("用户价格敏感，重点强调性价比和优惠")
        elif profile.price_sensitivity == "low":
            guidance.append("用户价格不敏感，重点强调价值和品质")
        
        if profile.urgency_level and profile.urgency_level >= 4:
            guidance.append("用户学习意愿强烈，可适当催单")
        
        if profile.communication_style == "direct":
            guidance.append("用户喜欢直接沟通，避免过多铺垫")
        elif profile.communication_style == "consultative":
            guidance.append("用户喜欢咨询式沟通，提供详细建议")
        
        return guidance
    
    def _generate_profile_recommendations(self, profile: UserProfile) -> List[str]:
        """生成画像建议"""
        recommendations = []
        
        if profile.data_completeness < 0.7:
            recommendations.append("建议进一步了解用户需求以完善画像")
        
        if not profile.learning_goals:
            recommendations.append("建议询问用户具体学习目标")
        
        if not profile.budget_range:
            recommendations.append("建议了解用户预算范围")
        
        return recommendations
    
    def _build_course_preferences(
        self, 
        profile: Optional[UserProfile], 
        category_preference: Optional[str]
    ) -> Dict[str, Any]:
        """构建课程推荐参数"""
        preferences = {}
        
        if category_preference:
            preferences["categories"] = [category_preference]
        
        if profile:
            if profile.current_skill_level:
                preferences["skill_level"] = profile.current_skill_level
            
            if profile.budget_range:
                # 解析预算范围
                budget_map = {
                    "低预算": 500,
                    "中等预算": 1500, 
                    "高预算": 5000
                }
                preferences["budget_max"] = budget_map.get(profile.budget_range, 2000)
        
        return preferences
    
    def _generate_match_reasons(
        self, 
        course: Course, 
        profile: Optional[UserProfile]
    ) -> List[str]:
        """生成课程匹配原因"""
        reasons = []
        
        if not profile:
            return ["根据课程热度推荐"]
        
        if profile.learning_goals:
            for goal in profile.learning_goals:
                if goal.lower() in course.course_name.lower() or goal.lower() in course.description.lower():
                    reasons.append(f"匹配学习目标: {goal}")
        
        if profile.current_skill_level and course.difficulty_level:
            if (profile.current_skill_level == "beginner" and course.difficulty_level in ["beginner", "intermediate"]) or \
               (profile.current_skill_level == "intermediate" and course.difficulty_level in ["intermediate", "advanced"]) or \
               (profile.current_skill_level == "advanced" and course.difficulty_level == "advanced"):
                reasons.append(f"难度适合当前水平: {profile.current_skill_level}")
        
        return reasons if reasons else ["综合评分推荐"]
    
    def _get_recommendation_strategy(self, profile: Optional[UserProfile]) -> str:
        """获取推荐策略"""
        if not profile:
            return "通用推荐策略"
        
        if profile.price_sensitivity == "high":
            return "性价比导向推荐"
        elif profile.urgency_level and profile.urgency_level >= 4:
            return "快速转化导向推荐"
        else:
            return "价值匹配导向推荐"
    
    def _extract_selling_points(self, course: CourseResponse) -> List[str]:
        """提取课程卖点"""
        points = []
        
        if course.rating >= 4.5:
            points.append(f"高分好评课程 ({course.rating}/5.0)")
        
        if course.student_count >= 1000:
            points.append(f"热门课程 ({course.student_count}人已学)")
        
        if course.original_price > course.current_price:
            discount = course.original_price - course.current_price
            points.append(f"限时优惠，立省{discount}元")
        
        if course.instructor:
            points.append(f"资深讲师 {course.instructor} 授课")
        
        return points
    
    def _identify_target_audience(self, course: CourseResponse) -> List[str]:
        """识别目标受众"""
        audiences = []
        
        if course.difficulty_level == "beginner":
            audiences.append("编程零基础学员")
        elif course.difficulty_level == "intermediate":
            audiences.append("有一定基础的进阶学员")
        elif course.difficulty_level == "advanced":
            audiences.append("高级开发者")
        
        if course.prerequisites:
            audiences.append(f"具备{', '.join(course.prerequisites)}基础的学员")
        
        return audiences
    
    def _get_pricing_strategy(self, profile: Optional[UserProfile]) -> str:
        """获取定价策略"""
        if not profile:
            return "标准定价策略"
        
        if profile.price_sensitivity == "high":
            return "优惠导向策略 - 重点展示折扣和性价比"
        elif profile.price_sensitivity == "low":
            return "价值导向策略 - 重点展示课程价值和投资回报"
        else:
            return "平衡策略 - 价值与优惠并重"
    
    def _get_negotiation_tips(self, profile: Optional[UserProfile]) -> List[str]:
        """获取谈判技巧"""
        tips = []
        
        if not profile:
            return ["保持专业，突出课程价值"]
        
        if profile.decision_pattern == "analytical":
            tips.append("提供详细数据和对比分析")
        elif profile.decision_pattern == "intuitive":
            tips.append("重点描述学习体验和感受")
        
        if profile.communication_style == "direct":
            tips.append("直接了当，避免绕弯子")
        
        return tips
    
    def _get_closing_suggestions(
        self, 
        profile: Optional[UserProfile], 
        order_amount: float
    ) -> List[str]:
        """获取成交建议"""
        suggestions = []
        
        if profile and profile.urgency_level and profile.urgency_level >= 4:
            suggestions.append("用户意愿强烈，可适当施加时间压力")
        
        if order_amount > 1000:
            suggestions.append("大额订单，可考虑分期付款选项")
        
        suggestions.append("强调课程的长期价值和投资回报")
        suggestions.append("提供学习保障和售后支持承诺")
        
        return suggestions
    
    def _get_payment_guidance(self, order: Order) -> Dict[str, Any]:
        """获取支付指导"""
        return {
            "recommended_method": "支付宝",
            "security_assurance": "支持7天无理由退款",
            "payment_tips": [
                "支付完成后立即开通课程权限",
                "保存支付凭证以备查询",
                "如有支付问题可随时联系客服"
            ]
        }
    
    def _explain_order_status(self, order_info: Dict[str, Any]) -> str:
        """解释订单状态"""
        status = order_info.get("status", "unknown")
        
        explanations = {
            "pending": "订单已创建，等待支付",
            "paid": "支付成功，课程已开通",
            "cancelled": "订单已取消",
            "payment_failed": "支付失败，请重新支付"
        }
        
        return explanations.get(status, "未知状态")
    
    def _suggest_order_actions(self, order_info: Dict[str, Any]) -> List[str]:
        """建议订单操作"""
        status = order_info.get("status", "unknown")
        
        if status == "pending":
            return ["提醒用户尽快完成支付", "提供支付链接", "询问是否需要支付协助"]
        elif status == "paid":
            return ["恭喜用户购买成功", "介绍课程学习方式", "提供学习建议"]
        elif status == "cancelled":
            return ["了解取消原因", "推荐其他合适课程", "提供重新购买优惠"]
        elif status == "payment_failed":
            return ["协助解决支付问题", "提供其他支付方式", "确认订单信息"]
        else:
            return ["查询订单详细状态"]
    
    def _get_conversation_tips(self, profile: Optional[UserProfile]) -> List[str]:
        """获取对话技巧"""
        tips = []
        
        if not profile:
            return ["保持友好专业的语调", "主动了解用户需求"]
        
        if profile.communication_style == "friendly":
            tips.append("可以适当使用轻松幽默的语调")
        elif profile.communication_style == "formal":
            tips.append("保持正式专业的交流方式")
        
        if profile.response_speed == "fast":
            tips.append("用户回复较快，可以加快对话节奏")
        elif profile.response_speed == "slow":
            tips.append("用户需要思考时间，不要过于催促")
        
        return tips
    
    def _get_personalization_suggestions(self, profile: Optional[UserProfile]) -> List[str]:
        """获取个性化建议"""
        suggestions = []
        
        if not profile:
            return ["建议收集更多用户信息以提供个性化服务"]
        
        if profile.learning_goals:
            suggestions.append(f"可以经常提及用户的学习目标: {', '.join(profile.learning_goals[:2])}")
        
        if profile.motivation_type:
            suggestions.append(f"结合用户的学习动机({profile.motivation_type})制定话术")
        
        return suggestions