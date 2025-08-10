"""
仓库包初始化文件 - 数据库访问层
"""

from .user_profile_repository import (
    UserProfileRepository,
    UserProfileHistoryRepository,
    user_profile_repository,
    user_profile_history_repository
)

__all__ = [
    "UserProfileRepository",
    "UserProfileHistoryRepository", 
    "user_profile_repository",
    "user_profile_history_repository"
]