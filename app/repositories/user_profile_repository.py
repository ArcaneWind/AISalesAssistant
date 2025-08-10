"""
用户画像数据库访问层 - 数据库交互专用类
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func, text
from sqlalchemy.exc import IntegrityError

from app.models.user_profile import UserProfile, UserProfileCreate, UserProfileUpdate
from app.models.database.user_profile_db import UserProfileDB, UserProfileHistory, UserProfileStats
from app.core.database import get_db_session

logger = logging.getLogger(__name__)


class UserProfileRepository:
    """用户画像数据库访问层"""
    
    def _db_to_profile(self, db_profile: UserProfileDB) -> UserProfile:
        """数据库模型转换为Pydantic模型"""
        try:
            return UserProfile(
                user_id=db_profile.user_id,
                session_id=db_profile.session_id,
                channel_source=db_profile.channel_source,
                created_at=db_profile.created_at,
                updated_at=db_profile.updated_at,
                learning_goals=db_profile.learning_goals or [],
                pain_points=db_profile.pain_points or [],
                motivation_type=db_profile.motivation_type,
                urgency_level=db_profile.urgency_level,
                budget_range=db_profile.budget_range,
                time_availability=db_profile.time_availability,
                learning_duration=db_profile.learning_duration,
                current_skill_level=db_profile.current_skill_level,
                related_experience=db_profile.related_experience or [],
                learning_ability=db_profile.learning_ability,
                communication_style=db_profile.communication_style,
                decision_pattern=db_profile.decision_pattern,
                response_speed=db_profile.response_speed,
                price_sensitivity=db_profile.price_sensitivity,
                payment_preference=db_profile.payment_preference,
                discount_response=db_profile.discount_response,
                field_confidence=db_profile.field_confidence or {},
                update_count=db_profile.update_count or 0,
                data_completeness=db_profile.data_completeness or 0.0
            )
        except Exception as e:
            logger.error(f"数据库模型转换失败: {e}")
            raise
    
    def _profile_to_db(self, profile: UserProfile) -> Dict[str, Any]:
        """Pydantic模型转换为数据库字段"""
        return {
            "user_id": profile.user_id,
            "session_id": profile.session_id,
            "channel_source": profile.channel_source,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
            "learning_goals": profile.learning_goals,
            "pain_points": profile.pain_points,
            "motivation_type": profile.motivation_type,
            "urgency_level": profile.urgency_level,
            "budget_range": profile.budget_range,
            "time_availability": profile.time_availability,
            "learning_duration": profile.learning_duration,
            "current_skill_level": profile.current_skill_level,
            "related_experience": profile.related_experience,
            "learning_ability": profile.learning_ability,
            "communication_style": profile.communication_style,
            "decision_pattern": profile.decision_pattern,
            "response_speed": profile.response_speed,
            "price_sensitivity": profile.price_sensitivity,
            "payment_preference": profile.payment_preference,
            "discount_response": profile.discount_response,
            "field_confidence": profile.field_confidence,
            "update_count": profile.update_count,
            "data_completeness": profile.data_completeness,
            "is_active": True,
            "last_interaction_at": datetime.now()
        }
    
    async def create(self, profile: UserProfile, session: AsyncSession) -> UserProfile:
        """创建用户画像记录，如果已存在则返回现有记录"""
        try:
            # 检查用户是否已存在
            existing = await session.execute(
                select(UserProfileDB).where(UserProfileDB.user_id == profile.user_id)
            )
            existing_profile = existing.scalar_one_or_none()
            
            if existing_profile:
                # 如果用户已存在，返回现有的用户画像
                logger.info(f"用户画像已存在，返回现有记录: {profile.user_id}")
                return self._db_to_profile(existing_profile)
            
            # 创建新的数据库记录
            db_profile = UserProfileDB(**self._profile_to_db(profile))
            session.add(db_profile)
            await session.flush()
            
            logger.info(f"用户画像创建成功: {profile.user_id}")
            return profile
            
        except Exception as e:
            logger.error(f"创建用户画像数据库记录失败: {e}")
            raise
    
    async def get_by_user_id(self, user_id: str, session: AsyncSession) -> Optional[UserProfile]:
        """根据用户ID获取画像"""
        try:
            result = await session.execute(
                select(UserProfileDB).where(
                    and_(
                        UserProfileDB.user_id == user_id,
                        UserProfileDB.is_active == True
                    )
                )
            )
            db_profile = result.scalar_one_or_none()
            
            if db_profile:
                return self._db_to_profile(db_profile)
            
            return None
            
        except Exception as e:
            logger.error(f"根据用户ID获取画像失败: {e}")
            return None
    
    async def get_by_session_id(self, session_id: str, session: AsyncSession) -> Optional[UserProfile]:
        """根据会话ID获取画像"""
        try:
            result = await session.execute(
                select(UserProfileDB).where(
                    and_(
                        UserProfileDB.session_id == session_id,
                        UserProfileDB.is_active == True
                    )
                )
            )
            db_profile = result.scalar_one_or_none()
            
            if db_profile:
                return self._db_to_profile(db_profile)
            
            return None
            
        except Exception as e:
            logger.error(f"根据会话ID获取画像失败: {e}")
            return None
    
    async def update(self, user_id: str, profile: UserProfile, session: AsyncSession) -> bool:
        """更新用户画像"""
        try:
            db_data = self._profile_to_db(profile)
            result = await session.execute(
                update(UserProfileDB)
                .where(UserProfileDB.user_id == user_id)
                .values(**db_data)
            )
            
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"更新用户画像失败: {e}")
            raise
    
    async def delete(self, user_id: str, session: AsyncSession, soft_delete: bool = True) -> bool:
        """删除用户画像"""
        try:
            if soft_delete:
                result = await session.execute(
                    update(UserProfileDB)
                    .where(UserProfileDB.user_id == user_id)
                    .values(is_active=False, updated_at=datetime.now())
                )
            else:
                result = await session.execute(
                    delete(UserProfileDB)
                    .where(UserProfileDB.user_id == user_id)
                )
            
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"删除用户画像失败: {e}")
            return False
    
    async def get_by_criteria(
        self,
        session: AsyncSession,
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
            query = select(UserProfileDB).where(UserProfileDB.is_active == True)
            
            # 添加筛选条件
            if channel_source:
                query = query.where(UserProfileDB.channel_source == channel_source)
            
            if min_completeness > 0:
                query = query.where(UserProfileDB.data_completeness >= min_completeness)
            
            if motivation_type:
                query = query.where(UserProfileDB.motivation_type == motivation_type)
            
            if skill_level:
                query = query.where(UserProfileDB.current_skill_level == skill_level)
            
            if budget_range:
                query = query.where(UserProfileDB.budget_range == budget_range)
            
            # 分页
            query = query.offset(offset).limit(limit)
            query = query.order_by(UserProfileDB.updated_at.desc())
            
            result = await session.execute(query)
            db_profiles = result.scalars().all()
            
            return [self._db_to_profile(db_profile) for db_profile in db_profiles]
            
        except Exception as e:
            logger.error(f"条件查询用户画像失败: {e}")
            return []
    
    async def get_batch_by_user_ids(self, user_ids: List[str], session: AsyncSession) -> Dict[str, UserProfile]:
        """批量获取用户画像"""
        try:
            result = await session.execute(
                select(UserProfileDB).where(
                    and_(
                        UserProfileDB.user_id.in_(user_ids),
                        UserProfileDB.is_active == True
                    )
                )
            )
            db_profiles = result.scalars().all()
            
            return {
                db_profile.user_id: self._db_to_profile(db_profile) 
                for db_profile in db_profiles
            }
            
        except Exception as e:
            logger.error(f"批量获取用户画像失败: {e}")
            return {}
    
    async def get_stats(self, session: AsyncSession) -> Dict[str, Any]:
        """获取画像统计信息"""
        try:
            # 总画像数
            result = await session.execute(
                text("SELECT COUNT(*) FROM user_profiles WHERE is_active = true")
            )
            total_profiles = result.scalar()
            
            # 完整画像数
            result = await session.execute(
                text("SELECT COUNT(*) FROM user_profiles WHERE is_active = true AND data_completeness > 0.7")
            )
            complete_profiles = result.scalar()
            
            return {
                "total_profiles": total_profiles,
                "complete_profiles": complete_profiles,
                "completion_rate": complete_profiles / total_profiles if total_profiles > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"获取画像统计信息失败: {e}")
            return {}


class UserProfileHistoryRepository:
    """用户画像历史记录数据库访问层"""
    
    async def create_history(
        self,
        session: AsyncSession,
        user_id: str,
        session_id: str,
        change_type: str,
        changed_fields: List[str],
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        source: str,
        confidence_scores: Optional[Dict[str, float]] = None
    ) -> None:
        """创建历史记录"""
        try:
            history = UserProfileHistory(
                user_id=user_id,
                session_id=session_id,
                change_type=change_type,
                changed_fields=changed_fields,
                old_values=old_values,
                new_values=new_values,
                change_source=source,
                confidence_scores=confidence_scores or {},
                created_at=datetime.now()
            )
            
            session.add(history)
            
        except Exception as e:
            logger.error(f"创建画像历史记录失败: {e}")
            raise
    
    async def get_user_history(
        self, 
        user_id: str, 
        session: AsyncSession,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取用户的历史变更记录"""
        try:
            result = await session.execute(
                select(UserProfileHistory)
                .where(UserProfileHistory.user_id == user_id)
                .order_by(UserProfileHistory.created_at.desc())
                .limit(limit)
            )
            
            history_records = result.scalars().all()
            
            return [
                {
                    "id": record.id,
                    "change_type": record.change_type,
                    "changed_fields": record.changed_fields,
                    "old_values": record.old_values,
                    "new_values": record.new_values,
                    "change_source": record.change_source,
                    "confidence_scores": record.confidence_scores,
                    "created_at": record.created_at
                }
                for record in history_records
            ]
            
        except Exception as e:
            logger.error(f"获取用户历史记录失败: {e}")
            return []


# 全局仓库实例
user_profile_repository = UserProfileRepository()
user_profile_history_repository = UserProfileHistoryRepository()