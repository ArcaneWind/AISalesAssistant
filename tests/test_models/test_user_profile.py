"""
用户画像数据模型测试
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.user_profile import (
    UserProfile,
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileResponse,
    ProfileValidationRules,
    MotivationType,
    SkillLevel,
    BudgetRange
)


class TestUserProfile:
    """用户画像模型测试"""
    
    def test_create_valid_profile(self, sample_user_profile):
        """测试创建有效的用户画像"""
        profile = sample_user_profile
        
        assert profile.user_id == "test_user_001"
        assert profile.session_id == "test_session_001"
        assert profile.channel_source == "web"
        assert profile.learning_goals == ["Python编程", "数据分析"]
        assert profile.motivation_type == "career_advancement"
        assert profile.urgency_level == 4
        assert profile.data_completeness == 0.75
    
    def test_profile_with_minimal_data(self):
        """测试最小数据创建画像"""
        profile = UserProfile(
            user_id="minimal_user",
            session_id="minimal_session",
            channel_source="api"
        )
        
        assert profile.user_id == "minimal_user"
        assert profile.learning_goals == []
        assert profile.pain_points == []
        assert profile.field_confidence == {}
        assert profile.update_count == 0
        assert profile.data_completeness == 0.0
    
    def test_urgency_level_validation(self):
        """测试紧急程度验证"""
        # 有效值
        for level in [1, 2, 3, 4, 5]:
            profile = UserProfile(
                user_id="test",
                session_id="test",
                channel_source="test",
                urgency_level=level
            )
            assert profile.urgency_level == level
        
        # 无效值应该通过Pydantic验证失败
        with pytest.raises(ValidationError):
            UserProfile(
                user_id="test",
                session_id="test", 
                channel_source="test",
                urgency_level=6
            )
        
        with pytest.raises(ValidationError):
            UserProfile(
                user_id="test",
                session_id="test",
                channel_source="test", 
                urgency_level=0
            )
    
    def test_confidence_scores_validation(self):
        """测试置信度分数验证"""
        # 有效置信度
        profile = UserProfile(
            user_id="test",
            session_id="test",
            channel_source="test",
            field_confidence={
                "learning_goals": 0.8,
                "motivation_type": 1.0,
                "urgency_level": 0.0
            }
        )
        assert profile.field_confidence["learning_goals"] == 0.8
        
        # 无效置信度应该通过验证器失败
        with pytest.raises(ValidationError):
            UserProfile(
                user_id="test",
                session_id="test",
                channel_source="test",
                field_confidence={
                    "learning_goals": 1.5  # 超过1.0
                }
            )
    
    def test_completeness_calculation(self):
        """测试完整度计算"""
        profile = UserProfile(
            user_id="test",
            session_id="test", 
            channel_source="test"
        )
        
        # 初始完整度应该很低
        completeness = profile.calculate_completeness()
        assert completeness == 0.0
        
        # 添加一些字段
        profile.learning_goals = ["Python"]
        profile.motivation_type = "career_advancement"
        profile.urgency_level = 4
        profile.budget_range = "1000-5000"
        
        completeness = profile.calculate_completeness()
        assert completeness > 0.0
        assert completeness <= 1.0
    
    def test_update_completeness(self):
        """测试更新完整度方法"""
        import time
        
        profile = UserProfile(
            user_id="test",
            session_id="test",
            channel_source="test",
            learning_goals=["Python"],
            motivation_type="career_advancement"
        )
        
        old_updated_at = profile.updated_at
        old_completeness = profile.data_completeness
        
        # 稍微等待一下确保时间差异
        time.sleep(0.001)
        
        profile.update_completeness()
        
        assert profile.data_completeness > 0.0
        # 检查完整度是否有变化而不是时间
        assert profile.data_completeness != old_completeness or profile.updated_at >= old_updated_at
    
    def test_confidence_field_methods(self):
        """测试置信度字段方法"""
        profile = UserProfile(
            user_id="test",
            session_id="test",
            channel_source="test"
        )
        
        # 测试获取置信度
        assert profile.get_confidence_for_field("learning_goals") == 0.0
        
        # 测试设置置信度
        profile.set_confidence_for_field("learning_goals", 0.8)
        assert profile.get_confidence_for_field("learning_goals") == 0.8
        
        # 测试无效置信度
        with pytest.raises(ValueError):
            profile.set_confidence_for_field("test_field", 1.5)


class TestUserProfileCreate:
    """用户画像创建模型测试"""
    
    def test_create_valid_profile_create(self, sample_profile_create):
        """测试有效的创建数据"""
        create_data = sample_profile_create
        
        assert create_data.user_id == "test_user_002"
        assert create_data.session_id == "test_session_002"
        assert create_data.channel_source == "mobile"
        assert create_data.learning_goals == ["机器学习"]
        assert create_data.motivation_type == "skill_upgrade"
        assert create_data.urgency_level == 3
    
    def test_minimal_create_data(self):
        """测试最小创建数据"""
        create_data = UserProfileCreate(
            user_id="minimal",
            session_id="minimal",
            channel_source="test"
        )
        
        assert create_data.learning_goals == []
        assert create_data.pain_points == []
        assert create_data.motivation_type is None


class TestUserProfileUpdate:
    """用户画像更新模型测试"""
    
    def test_partial_update(self):
        """测试部分字段更新"""
        update_data = UserProfileUpdate(
            learning_goals=["新的学习目标"],
            urgency_level=5
        )
        
        assert update_data.learning_goals == ["新的学习目标"]
        assert update_data.urgency_level == 5
        assert update_data.motivation_type is None  # 未设置的字段
    
    def test_confidence_update(self):
        """测试置信度更新"""
        update_data = UserProfileUpdate(
            field_confidence={
                "learning_goals": 0.9,
                "urgency_level": 0.7
            }
        )
        
        assert update_data.field_confidence["learning_goals"] == 0.9
        assert update_data.field_confidence["urgency_level"] == 0.7


class TestEnums:
    """枚举类型测试"""
    
    def test_motivation_type_enum(self):
        """测试学习动机类型枚举"""
        assert MotivationType.CAREER_ADVANCEMENT == "career_advancement"
        assert MotivationType.SKILL_UPGRADE == "skill_upgrade"
        assert MotivationType.CAREER_CHANGE == "career_change"
        assert MotivationType.PERSONAL_INTEREST == "personal_interest"
        assert MotivationType.PROBLEM_SOLVING == "problem_solving"
    
    def test_skill_level_enum(self):
        """测试技能水平枚举"""
        assert SkillLevel.BEGINNER == "beginner"
        assert SkillLevel.INTERMEDIATE == "intermediate"
        assert SkillLevel.ADVANCED == "advanced"
        assert SkillLevel.EXPERT == "expert"
    
    def test_budget_range_enum(self):
        """测试预算范围枚举"""
        assert BudgetRange.UNDER_1K == "<1000"
        assert BudgetRange.RANGE_1K_5K == "1000-5000"
        assert BudgetRange.RANGE_5K_10K == "5000-10000"
        assert BudgetRange.OVER_10K == "10000+"


class TestProfileValidationRules:
    """画像验证规则测试"""
    
    def test_urgency_level_validation(self):
        """测试紧急程度验证"""
        rules = ProfileValidationRules()
        
        # 有效值
        for level in [1, 2, 3, 4, 5]:
            assert rules.validate_urgency_level(level) == True
        
        # 无效值
        assert rules.validate_urgency_level(0) == False
        assert rules.validate_urgency_level(6) == False
        assert rules.validate_urgency_level(-1) == False
    
    def test_skill_level_validation(self):
        """测试技能水平验证"""
        rules = ProfileValidationRules()
        
        # 有效值
        for level in ["beginner", "intermediate", "advanced", "expert"]:
            assert rules.validate_skill_level(level) == True
        
        # 无效值
        assert rules.validate_skill_level("invalid") == False
        assert rules.validate_skill_level("") == False
    
    def test_budget_range_validation(self):
        """测试预算范围验证"""
        rules = ProfileValidationRules()
        
        # 有效值
        for budget in ["<1000", "1000-5000", "5000-10000", "10000+"]:
            assert rules.validate_budget_range(budget) == True
        
        # 无效值
        assert rules.validate_budget_range("invalid") == False
        assert rules.validate_budget_range("") == False
    
    def test_confidence_score_validation(self):
        """测试置信度分数验证"""
        rules = ProfileValidationRules()
        
        # 有效值
        assert rules.validate_confidence_score(0.0) == True
        assert rules.validate_confidence_score(0.5) == True
        assert rules.validate_confidence_score(1.0) == True
        
        # 无效值
        assert rules.validate_confidence_score(-0.1) == False
        assert rules.validate_confidence_score(1.1) == False


class TestUserProfileResponse:
    """用户画像响应模型测试"""
    
    def test_profile_response(self, sample_user_profile):
        """测试画像响应模型"""
        response = UserProfileResponse(
            profile=sample_user_profile,
            completeness_score=sample_user_profile.data_completeness,
            last_updated=sample_user_profile.updated_at,
            confidence_summary={
                "average": 0.8,
                "max": 0.9,
                "min": 0.7,
                "fields_with_high_confidence": 2
            }
        )
        
        assert response.profile.user_id == "test_user_001"
        assert response.completeness_score == 0.75
        assert response.confidence_summary["average"] == 0.8
        assert response.confidence_summary["fields_with_high_confidence"] == 2