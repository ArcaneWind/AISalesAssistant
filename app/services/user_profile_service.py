"""
用户画像业务服务类 - 业务逻辑处理
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.user_profile import (
    UserProfile, 
    UserProfileCreate, 
    UserProfileUpdate,
    UserProfileResponse,
    ProfileValidationRules
)
from app.repositories.user_profile_repository import (
    user_profile_repository,
    user_profile_history_repository
)
from app.services.profile_cache import UserProfileCache, profile_cache
from app.core.database import get_db_session

logger = logging.getLogger(__name__)


class UserProfileService:
    """用户画像业务服务类 - 处理业务逻辑"""
    
    def __init__(
        self, 
        cache: Optional[UserProfileCache] = None,
        repository = None,
        history_repository = None
    ):
        self.cache = cache or profile_cache
        self.repository = repository or user_profile_repository
        self.history_repository = history_repository or user_profile_history_repository
        self.validation_rules = ProfileValidationRules()
    
    async def init_service(self) -> None:
        """初始化服务"""
        try:
            # 初始化Redis缓存
            await self.cache.init_redis()
            logger.info("用户画像服务初始化成功")
        except Exception as e:
            logger.error(f"用户画像服务初始化失败: {e}")
            raise
    
    async def close_service(self) -> None:
        """关闭服务"""
        try:
            await self.cache.close_redis()
            logger.info("用户画像服务已关闭")
        except Exception as e:
            logger.error(f"关闭用户画像服务失败: {e}")
    
    async def create_profile(self, profile_create: UserProfileCreate) -> UserProfile:
        """创建用户画像，如果用户已存在则返回现有用户画像"""
        try:
            # 首先检查缓存中是否已存在
            cached_profile = await self.cache.get_profile(profile_create.user_id)
            if cached_profile:
                logger.info(f"用户画像已存在于缓存中: {profile_create.user_id}")
                return cached_profile
            
            # 创建UserProfile对象
            profile = UserProfile(
                user_id=profile_create.user_id,
                session_id=profile_create.session_id,
                channel_source=profile_create.channel_source,
                learning_goals=profile_create.learning_goals or [],
                pain_points=profile_create.pain_points or [],
                motivation_type=profile_create.motivation_type,
                urgency_level=profile_create.urgency_level,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 计算初始完整度
            profile.update_completeness()
            
            # 数据库操作
            async for session in get_db_session():
                # 创建数据库记录（如果已存在则返回现有记录）
                result_profile = await self.repository.create(profile, session)
                
                # 如果是新创建的用户，记录历史
                if result_profile.user_id == profile.user_id and result_profile.created_at == profile.created_at:
                    await self.history_repository.create_history(
                        session, 
                        profile.user_id, 
                        profile.session_id,
                        "create",
                        [],
                        {},
                        profile.model_dump(),
                        "system"
                    )
                    logger.info(f"新用户画像创建成功: {profile.user_id}")
                else:
                    logger.info(f"用户画像已存在，返回现有记录: {profile.user_id}")
                
                break
            
            # 设置缓存
            await self.cache.set_profile(result_profile.user_id, result_profile)
            
            return result_profile
            
        except Exception as e:
            logger.error(f"创建用户画像失败: {e}")
            raise
    
    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户画像"""
        try:
            # 先从缓存获取
            profile = await self.cache.get_profile(user_id)
            if profile:
                return profile
            
            # 缓存未命中，从数据库获取
            async for session in get_db_session():
                profile = await self.repository.get_by_user_id(user_id, session)
                
                if profile:
                    # 设置缓存
                    await self.cache.set_profile(user_id, profile)
                    logger.debug(f"用户画像数据库查询成功: {user_id}")
                    return profile
                
                logger.debug(f"用户画像不存在: {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"获取用户画像失败: {e}")
            return None
    
    async def get_profile_by_session(self, session_id: str) -> Optional[UserProfile]:
        """根据会话ID获取用户画像"""
        try:
            # 先从缓存获取
            profile = await self.cache.get_profile_by_session(session_id)
            if profile:
                return profile
            
            # 缓存未命中，从数据库获取
            async for session in get_db_session():
                profile = await self.repository.get_by_session_id(session_id, session)
                
                if profile:
                    # 设置缓存
                    await self.cache.set_profile(profile.user_id, profile)
                    logger.debug(f"根据会话ID查询用户画像成功: {session_id}")
                    return profile
                
                return None
                
        except Exception as e:
            logger.error(f"根据会话ID获取用户画像失败: {e}")
            return None
    
    async def update_profile(
        self, 
        user_id: str, 
        profile_update: UserProfileUpdate,
        confidence_scores: Optional[Dict[str, float]] = None,
        source: str = "system"
    ) -> Optional[UserProfile]:
        """更新用户画像"""
        try:
            # 获取现有画像
            current_profile = await self.get_profile(user_id)
            if not current_profile:
                logger.warning(f"用户画像不存在，无法更新: {user_id}")
                return None
            
            # 记录变更前的值
            old_values = {}
            new_values = {}
            changed_fields = []
            
            # 应用更新
            update_dict = profile_update.model_dump(exclude_unset=True)
            for field, value in update_dict.items():
                if field == "field_confidence":
                    continue  # 置信度单独处理
                    
                old_value = getattr(current_profile, field, None)
                if value is not None and value != old_value:
                    old_values[field] = old_value
                    new_values[field] = value
                    changed_fields.append(field)
                    setattr(current_profile, field, value)
            
            # 处理置信度更新
            if confidence_scores:
                current_profile.field_confidence.update(confidence_scores)
                changed_fields.append("field_confidence")
            
            if profile_update.field_confidence:
                current_profile.field_confidence.update(profile_update.field_confidence)
                if "field_confidence" not in changed_fields:
                    changed_fields.append("field_confidence")
            
            # 更新元信息
            current_profile.updated_at = datetime.now()
            current_profile.update_count += 1
            current_profile.update_completeness()
            
            # 数据库操作
            async for session in get_db_session():
                # 更新数据库
                await self.repository.update(user_id, current_profile, session)
                
                # 记录历史
                if changed_fields:
                    await self.history_repository.create_history(
                        session,
                        user_id,
                        current_profile.session_id,
                        "update",
                        changed_fields,
                        old_values,
                        new_values,
                        source,
                        confidence_scores
                    )
                
                break
            
            # 更新缓存
            await self.cache.set_profile(user_id, current_profile)
            
            logger.info(f"用户画像更新成功: {user_id}, 变更字段: {changed_fields}")
            return current_profile
            
        except Exception as e:
            logger.error(f"更新用户画像失败: {e}")
            raise
    
    async def delete_profile(self, user_id: str, soft_delete: bool = True) -> bool:
        """删除用户画像"""
        try:
            async for session in get_db_session():
                result = await self.repository.delete(user_id, session, soft_delete)
                
                if result:
                    # 删除缓存
                    await self.cache.delete_profile(user_id)
                    
                    logger.info(f"用户画像删除成功: {user_id}, 软删除: {soft_delete}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"删除用户画像失败: {e}")
            return False
    
    async def batch_get_profiles(self, user_ids: List[str]) -> Dict[str, Optional[UserProfile]]:
        """批量获取用户画像"""
        try:
            # 先从缓存批量获取
            cached_profiles = await self.cache.batch_get_profiles(user_ids)
            
            # 识别缓存未命中的用户
            missing_user_ids = [
                user_id for user_id, profile in cached_profiles.items() 
                if profile is None
            ]
            
            if missing_user_ids:
                # 从数据库获取未命中的用户画像
                async for session in get_db_session():
                    db_profiles = await self.repository.get_batch_by_user_ids(missing_user_ids, session)
                    
                    # 更新结果并设置缓存
                    db_profiles_list = []
                    for user_id, profile in db_profiles.items():
                        cached_profiles[user_id] = profile
                        db_profiles_list.append(profile)
                    
                    # 批量设置缓存
                    if db_profiles_list:
                        await self.cache.batch_set_profiles(db_profiles_list)
                    
                    break
            
            logger.debug(f"批量获取用户画像: {len(user_ids)}个, 命中: {sum(1 for p in cached_profiles.values() if p)}")
            return cached_profiles
            
        except Exception as e:
            logger.error(f"批量获取用户画像失败: {e}")
            return {user_id: None for user_id in user_ids}
    
    async def get_profiles_by_criteria(
        self,
        channel_source: Optional[str] = None,
        min_completeness: float = 0.0,
        motivation_type: Optional[str] = None,
        skill_level: Optional[str] = None,
        budget_range: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserProfile]:
        """根据条件查询用户画像"""
        try:
            async for session in get_db_session():
                profiles = await self.repository.get_by_criteria(
                    session,
                    channel_source=channel_source,
                    min_completeness=min_completeness,
                    motivation_type=motivation_type,
                    skill_level=skill_level,
                    budget_range=budget_range,
                    limit=limit,
                    offset=offset
                )
                
                logger.info(f"条件查询用户画像: 返回{len(profiles)}个结果")
                return profiles
                
        except Exception as e:
            logger.error(f"条件查询用户画像失败: {e}")
            return []
    
    async def get_profile_response(self, user_id: str) -> Optional[UserProfileResponse]:
        """获取完整的用户画像响应"""
        try:
            profile = await self.get_profile(user_id)
            if not profile:
                return None
            
            # 计算置信度摘要
            confidence_summary = {}
            if profile.field_confidence:
                confidence_summary = {
                    "average": sum(profile.field_confidence.values()) / len(profile.field_confidence),
                    "max": max(profile.field_confidence.values()),
                    "min": min(profile.field_confidence.values()),
                    "fields_with_high_confidence": len([c for c in profile.field_confidence.values() if c >= 0.8])
                }
            
            return UserProfileResponse(
                profile=profile,
                completeness_score=profile.data_completeness,
                last_updated=profile.updated_at,
                confidence_summary=confidence_summary
            )
            
        except Exception as e:
            logger.error(f"获取用户画像响应失败: {e}")
            return None
    
    async def get_user_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户画像变更历史"""
        try:
            async for session in get_db_session():
                history = await self.history_repository.get_user_history(user_id, session, limit)
                return history
                
        except Exception as e:
            logger.error(f"获取用户历史失败: {e}")
            return []
    
    async def validate_profile_update(self, profile_update: UserProfileUpdate) -> List[str]:
        """验证画像更新数据"""
        errors = []
        
        try:
            # 验证紧急程度
            if profile_update.urgency_level is not None:
                if not self.validation_rules.validate_urgency_level(profile_update.urgency_level):
                    errors.append(f"无效的紧急程度: {profile_update.urgency_level}")
            
            # 验证技能水平
            if profile_update.current_skill_level:
                if not self.validation_rules.validate_skill_level(profile_update.current_skill_level):
                    errors.append(f"无效的技能水平: {profile_update.current_skill_level}")
            
            # 验证预算范围
            if profile_update.budget_range:
                if not self.validation_rules.validate_budget_range(profile_update.budget_range):
                    errors.append(f"无效的预算范围: {profile_update.budget_range}")
            
            # 验证置信度分数
            if profile_update.field_confidence:
                for field, score in profile_update.field_confidence.items():
                    if not self.validation_rules.validate_confidence_score(score):
                        errors.append(f"无效的置信度分数 {field}: {score}")
        
        except Exception as e:
            logger.error(f"验证画像更新数据失败: {e}")
            errors.append(f"验证过程出错: {str(e)}")
        
        return errors
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查缓存状态
            cache_stats = await self.cache.get_cache_stats()
            
            # 检查数据库状态
            async for session in get_db_session():
                db_stats = await self.repository.get_stats(session)
                break
            
            return {
                "status": "healthy",
                "database": db_stats,
                "cache": cache_stats
            }
            
        except Exception as e:
            logger.error(f"用户画像服务健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# 全局服务实例
user_profile_service = UserProfileService()