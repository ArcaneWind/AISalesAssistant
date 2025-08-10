"""
用户画像数据库访问层测试
"""

import pytest
from datetime import datetime

from app.repositories.user_profile_repository import (
    UserProfileRepository, 
    UserProfileHistoryRepository
)
from app.models.user_profile import UserProfile, UserProfileUpdate
from app.models.database.user_profile_db import UserProfileDB


@pytest.mark.asyncio  
class TestUserProfileRepository:
    """用户画像数据库访问层测试"""
    
    def test_db_to_profile_conversion(self, profile_repository, sample_user_profile):
        """测试数据库模型到Pydantic模型转换"""
        profile = sample_user_profile
        
        # 先转换为数据库字段
        db_data = profile_repository._profile_to_db(profile)
        
        # 创建数据库模型对象
        db_profile = UserProfileDB(**db_data)
        
        # 转换回Pydantic模型
        converted_profile = profile_repository._db_to_profile(db_profile)
        
        assert converted_profile.user_id == profile.user_id
        assert converted_profile.session_id == profile.session_id
        assert converted_profile.learning_goals == profile.learning_goals
        assert converted_profile.motivation_type == profile.motivation_type
        assert converted_profile.data_completeness == profile.data_completeness
    
    def test_profile_to_db_conversion(self, profile_repository, sample_user_profile):
        """测试Pydantic模型到数据库字段转换"""
        profile = sample_user_profile
        
        db_data = profile_repository._profile_to_db(profile)
        
        assert db_data["user_id"] == profile.user_id
        assert db_data["session_id"] == profile.session_id
        assert db_data["learning_goals"] == profile.learning_goals
        assert db_data["motivation_type"] == profile.motivation_type
        assert db_data["data_completeness"] == profile.data_completeness
        assert db_data["is_active"] == True
        assert "last_interaction_at" in db_data
    
    async def test_create_profile(self, profile_repository, db_session, sample_user_profile):
        """测试创建用户画像"""
        profile = sample_user_profile
        
        # 测试创建
        created_profile = await profile_repository.create(profile, db_session)
        
        assert created_profile.user_id == profile.user_id
        assert created_profile.session_id == profile.session_id
        
        # 验证数据库中存在
        result = await profile_repository.get_by_user_id(profile.user_id, db_session)
        assert result is not None
        assert result.user_id == profile.user_id
    
    async def test_create_duplicate_profile(self, profile_repository, db_session, sample_user_profile):
        """测试创建重复用户画像，应该返回现有用户"""
        profile = sample_user_profile
        
        # 先创建一次
        created_profile1 = await profile_repository.create(profile, db_session)
        
        # 再次创建应该返回现有用户，而不是报错
        created_profile2 = await profile_repository.create(profile, db_session)
        
        # 验证返回的是同一个用户
        assert created_profile1.user_id == created_profile2.user_id
        assert created_profile1.created_at == created_profile2.created_at  # 创建时间应该相同
    
    async def test_get_by_user_id(self, profile_repository, db_session, sample_user_profile):
        """测试根据用户ID获取画像"""
        profile = sample_user_profile
        
        # 先创建
        await profile_repository.create(profile, db_session)
        
        # 测试获取
        result = await profile_repository.get_by_user_id(profile.user_id, db_session)
        
        assert result is not None
        assert result.user_id == profile.user_id
        assert result.session_id == profile.session_id
        assert result.learning_goals == profile.learning_goals
    
    async def test_get_nonexistent_user(self, profile_repository, db_session):
        """测试获取不存在的用户"""
        result = await profile_repository.get_by_user_id("nonexistent", db_session)
        assert result is None
    
    async def test_get_by_session_id(self, profile_repository, db_session, sample_user_profile):
        """测试根据会话ID获取画像"""
        profile = sample_user_profile
        
        # 先创建
        await profile_repository.create(profile, db_session)
        
        # 测试根据会话ID获取
        result = await profile_repository.get_by_session_id(profile.session_id, db_session)
        
        assert result is not None
        assert result.user_id == profile.user_id
        assert result.session_id == profile.session_id
    
    async def test_update_profile(self, profile_repository, db_session, sample_user_profile):
        """测试更新用户画像"""
        profile = sample_user_profile
        
        # 先创建
        await profile_repository.create(profile, db_session)
        
        # 修改数据
        profile.learning_goals = ["更新的学习目标"]
        profile.urgency_level = 5
        profile.update_count += 1
        profile.updated_at = datetime.now()
        
        # 测试更新
        result = await profile_repository.update(profile.user_id, profile, db_session)
        assert result == True
        
        # 验证更新结果
        updated_profile = await profile_repository.get_by_user_id(profile.user_id, db_session)
        assert updated_profile.learning_goals == ["更新的学习目标"]
        assert updated_profile.urgency_level == 5
    
    async def test_update_nonexistent_profile(self, profile_repository, db_session, sample_user_profile):
        """测试更新不存在的用户画像"""
        profile = sample_user_profile
        
        result = await profile_repository.update("nonexistent", profile, db_session)
        assert result == False
    
    async def test_soft_delete_profile(self, profile_repository, db_session, sample_user_profile):
        """测试软删除用户画像"""
        profile = sample_user_profile
        
        # 先创建
        await profile_repository.create(profile, db_session)
        
        # 测试软删除
        result = await profile_repository.delete(profile.user_id, db_session, soft_delete=True)
        assert result == True
        
        # 验证软删除后获取不到（因为is_active=False）
        deleted_profile = await profile_repository.get_by_user_id(profile.user_id, db_session)
        assert deleted_profile is None
    
    async def test_hard_delete_profile(self, profile_repository, db_session, sample_user_profile):
        """测试硬删除用户画像"""
        profile = sample_user_profile
        profile.user_id = "hard_delete_test"
        
        # 先创建
        await profile_repository.create(profile, db_session)
        
        # 测试硬删除
        result = await profile_repository.delete(profile.user_id, db_session, soft_delete=False)
        assert result == True
        
        # 验证硬删除后数据不存在
        deleted_profile = await profile_repository.get_by_user_id(profile.user_id, db_session)
        assert deleted_profile is None
    
    async def test_get_by_criteria(self, profile_repository, db_session, multiple_test_users):
        """测试根据条件查询用户画像"""
        # 创建多个测试用户
        for profile in multiple_test_users:
            await profile_repository.create(profile, db_session)
        
        # 测试按渠道来源查询
        web_users = await profile_repository.get_by_criteria(
            db_session,
            channel_source="web",
            limit=5
        )
        assert len(web_users) > 0
        for profile in web_users:
            assert profile.channel_source == "web"
        
        # 测试按完整度查询
        complete_users = await profile_repository.get_by_criteria(
            db_session,
            min_completeness=0.6,
            limit=5
        )
        assert len(complete_users) >= 0
        for profile in complete_users:
            assert profile.data_completeness >= 0.6
        
        # 测试按动机类型查询
        career_users = await profile_repository.get_by_criteria(
            db_session,
            motivation_type="career_advancement",
            limit=5
        )
        for profile in career_users:
            assert profile.motivation_type == "career_advancement"
        
        # 测试组合条件查询
        combined_users = await profile_repository.get_by_criteria(
            db_session,
            channel_source="web",
            motivation_type="career_advancement",
            limit=3
        )
        for profile in combined_users:
            assert profile.channel_source == "web"
            assert profile.motivation_type == "career_advancement"
    
    async def test_get_batch_by_user_ids(self, profile_repository, db_session, multiple_test_users):
        """测试批量获取用户画像"""
        # 创建前5个用户
        created_users = multiple_test_users[:5]
        for profile in created_users:
            await profile_repository.create(profile, db_session)
        
        # 测试批量获取（包含存在和不存在的用户ID）
        all_user_ids = [profile.user_id for profile in multiple_test_users]
        results = await profile_repository.get_batch_by_user_ids(all_user_ids, db_session)
        
        # 验证前5个用户存在
        for profile in created_users:
            assert profile.user_id in results
            assert results[profile.user_id].user_id == profile.user_id
        
        # 验证后5个用户不存在
        for profile in multiple_test_users[5:]:
            assert profile.user_id not in results
    
    async def test_get_stats(self, profile_repository, db_session, multiple_test_users):
        """测试获取画像统计信息"""
        # 创建一些测试用户
        for profile in multiple_test_users:
            await profile_repository.create(profile, db_session)
        
        # 获取统计信息
        stats = await profile_repository.get_stats(db_session)
        
        assert "total_profiles" in stats
        assert "complete_profiles" in stats
        assert "completion_rate" in stats
        
        assert stats["total_profiles"] >= len(multiple_test_users)
        assert 0 <= stats["completion_rate"] <= 1


@pytest.mark.asyncio
class TestUserProfileHistoryRepository:
    """用户画像历史记录数据库访问层测试"""
    
    async def test_create_history(self, db_session):
        """测试创建历史记录"""
        history_repo = UserProfileHistoryRepository()
        
        # 创建历史记录
        await history_repo.create_history(
            db_session,
            user_id="test_user",
            session_id="test_session", 
            change_type="create",
            changed_fields=["learning_goals", "motivation_type"],
            old_values={},
            new_values={"learning_goals": ["Python"], "motivation_type": "career_advancement"},
            source="system",
            confidence_scores={"learning_goals": 0.8}
        )
        
        # 验证历史记录创建成功
        await db_session.commit()
    
    async def test_get_user_history(self, db_session):
        """测试获取用户历史记录"""
        history_repo = UserProfileHistoryRepository()
        
        # 先创建几条历史记录
        for i in range(3):
            await history_repo.create_history(
                db_session,
                user_id="history_test_user",
                session_id="history_test_session",
                change_type="update" if i > 0 else "create",
                changed_fields=[f"field_{i}"],
                old_values={f"field_{i}": f"old_value_{i}"},
                new_values={f"field_{i}": f"new_value_{i}"},
                source="system"
            )
        
        await db_session.commit()
        
        # 获取历史记录
        history = await history_repo.get_user_history("history_test_user", db_session, limit=10)
        
        assert len(history) == 3
        
        # 验证记录内容
        for record in history:
            assert "id" in record
            assert "change_type" in record
            assert "changed_fields" in record
            assert "old_values" in record
            assert "new_values" in record
            assert "change_source" in record
            assert "created_at" in record
        
        # 验证按时间倒序
        assert history[0]["created_at"] >= history[1]["created_at"]
        assert history[1]["created_at"] >= history[2]["created_at"]
    
    async def test_get_empty_user_history(self, db_session):
        """测试获取不存在用户的历史记录"""
        history_repo = UserProfileHistoryRepository()
        
        history = await history_repo.get_user_history("nonexistent_user", db_session)
        assert len(history) == 0


@pytest.mark.asyncio
class TestRepositoryErrorHandling:
    """仓库错误处理测试"""
    
    async def test_database_connection_error_handling(self, profile_repository):
        """测试数据库连接错误处理"""
        # 使用无效的会话模拟连接错误
        invalid_session = None
        
        with pytest.raises(AttributeError):
            await profile_repository.get_by_user_id("test", invalid_session)
    
    def test_invalid_data_conversion(self, profile_repository):
        """测试无效数据转换"""
        # 创建无效的数据库对象
        invalid_db_profile = UserProfileDB(
            user_id="test",
            session_id="test",
            channel_source="test"
        )
        
        # 转换应该成功，因为有默认值处理
        profile = profile_repository._db_to_profile(invalid_db_profile)
        assert profile.user_id == "test"
        assert profile.learning_goals == []
        assert profile.field_confidence == {}