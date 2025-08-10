from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, Boolean, Index
from sqlalchemy.sql import func
from app.core.database import Base


class UserProfileDB(Base):
    """用户画像数据库模型"""
    
    __tablename__ = "user_profiles"
    
    # 基础信息
    user_id = Column(String(255), primary_key=True, index=True, comment="用户唯一标识")
    session_id = Column(String(255), nullable=False, index=True, comment="会话唯一标识")
    channel_source = Column(String(100), nullable=False, comment="渠道来源")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 学习需求维度 (JSON存储)
    learning_goals = Column(JSON, comment="学习目标列表")
    pain_points = Column(JSON, comment="痛点问题列表")
    motivation_type = Column(String(50), comment="学习动机类型")
    urgency_level = Column(Integer, comment="紧急程度 1-5")
    
    # 预算时间维度
    budget_range = Column(String(20), comment="预算范围")
    time_availability = Column(String(20), comment="时间可用性")
    learning_duration = Column(String(20), comment="期望学习周期")
    
    # 技能背景维度
    current_skill_level = Column(String(20), comment="当前技能水平")
    related_experience = Column(JSON, comment="相关经验列表")
    learning_ability = Column(String(20), comment="学习能力评估")
    
    # 行为特征维度
    communication_style = Column(String(30), comment="沟通风格")
    decision_pattern = Column(String(30), comment="决策模式")
    response_speed = Column(String(20), comment="响应速度特征")
    
    # 价格敏感度维度
    price_sensitivity = Column(String(20), comment="价格敏感度")
    payment_preference = Column(String(30), comment="支付偏好")
    discount_response = Column(String(30), comment="优惠反应")
    
    # 置信度和元信息 
    field_confidence = Column(JSON, comment="各字段置信度JSON")
    update_count = Column(Integer, default=0, comment="更新次数")
    data_completeness = Column(Float, default=0.0, comment="数据完整度")
    
    # 业务状态
    is_active = Column(Boolean, default=True, comment="是否激活")
    last_interaction_at = Column(DateTime(timezone=True), comment="最后交互时间")
    
    # 创建索引
    __table_args__ = (
        Index('idx_user_session', 'user_id', 'session_id'),
        Index('idx_channel_source', 'channel_source'),
        Index('idx_updated_at', 'updated_at'),
        Index('idx_motivation_type', 'motivation_type'),
        Index('idx_skill_level', 'current_skill_level'),
        Index('idx_budget_range', 'budget_range'),
        Index('idx_price_sensitivity', 'price_sensitivity'),
        Index('idx_completeness', 'data_completeness'),
        Index('idx_interaction_time', 'last_interaction_at'),
        {'comment': '用户画像表'}
    )


class UserProfileHistory(Base):
    """用户画像历史版本表"""
    
    __tablename__ = "user_profile_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="历史记录ID")
    user_id = Column(String(255), nullable=False, index=True, comment="用户唯一标识")
    session_id = Column(String(255), nullable=False, comment="会话标识")
    
    # 变更信息
    change_type = Column(String(20), nullable=False, comment="变更类型: create, update, merge")
    changed_fields = Column(JSON, comment="变更字段列表")
    old_values = Column(JSON, comment="变更前的值")
    new_values = Column(JSON, comment="变更后的值")
    
    # 变更元信息
    change_source = Column(String(50), comment="变更来源: llm, manual, system")
    confidence_scores = Column(JSON, comment="变更时的置信度")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="变更时间")
    
    # 创建索引
    __table_args__ = (
        Index('idx_history_user_id', 'user_id'),
        Index('idx_history_change_type', 'change_type'),
        Index('idx_history_created_at', 'created_at'),
        {'comment': '用户画像变更历史表'}
    )


class UserProfileStats(Base):
    """用户画像统计表"""
    
    __tablename__ = "user_profile_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="统计记录ID")
    
    # 统计维度
    stat_date = Column(DateTime(timezone=True), nullable=False, comment="统计日期")
    channel_source = Column(String(100), comment="渠道来源")
    
    # 画像质量统计
    total_profiles = Column(Integer, default=0, comment="总画像数")
    complete_profiles = Column(Integer, default=0, comment="完整画像数(完整度>70%)")
    avg_completeness = Column(Float, default=0.0, comment="平均完整度")
    avg_confidence = Column(Float, default=0.0, comment="平均置信度")
    
    # 字段填充统计
    learning_goals_filled = Column(Integer, default=0, comment="学习目标填充数")
    pain_points_filled = Column(Integer, default=0, comment="痛点问题填充数")
    motivation_filled = Column(Integer, default=0, comment="动机类型填充数")
    budget_filled = Column(Integer, default=0, comment="预算信息填充数")
    skill_level_filled = Column(Integer, default=0, comment="技能水平填充数")
    
    # 更新统计
    total_updates = Column(Integer, default=0, comment="总更新次数")
    avg_updates_per_profile = Column(Float, default=0.0, comment="平均每个画像更新次数")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 创建索引
    __table_args__ = (
        Index('idx_stats_date', 'stat_date'),
        Index('idx_stats_channel', 'channel_source'),
        Index('idx_stats_created_at', 'created_at'),
        {'comment': '用户画像统计表'}
    )