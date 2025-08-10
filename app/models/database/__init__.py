"""
数据库模型包初始化文件
"""

from .user_profile_db import UserProfileDB, UserProfileHistory, UserProfileStats

__all__ = [
    "UserProfileDB",
    "UserProfileHistory", 
    "UserProfileStats"
]