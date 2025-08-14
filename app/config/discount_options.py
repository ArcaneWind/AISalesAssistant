"""
折扣选项静态配置 - Agent通过提示词引导选择
"""

from typing import Dict, Any
from app.models.discount import DiscountOption, DiscountOptionType, DiscountType

# 折扣选项配置字典
DISCOUNT_OPTIONS_CONFIG: Dict[str, Dict[str, Any]] = {
    "new_user": {
        "option_name": "新用户首购折扣",
        "discount_type": DiscountType.PERCENTAGE,
        "min_discount": 0.1,  # 最小10%折扣
        "max_discount": 0.3,  # 最大30%折扣
        "description": "针对新用户的首次购买优惠，可根据用户意向强度调整",
        "prompt_guidance": "新用户且学习意向强烈时使用，通常给15-25%折扣"
    },
    "urgent_conversion": {
        "option_name": "紧急转化折扣",
        "discount_type": DiscountType.PERCENTAGE,
        "min_discount": 0.15,  # 最小15%折扣
        "max_discount": 0.4,   # 最大40%折扣
        "description": "针对高紧迫度用户的转化优惠，力度可较大",
        "prompt_guidance": "用户紧迫度>=4且预算充足时使用，可给20-35%折扣"
    },
    "returning_user": {
        "option_name": "老用户回购折扣",
        "discount_type": DiscountType.PERCENTAGE,
        "min_discount": 0.05,  # 最小5%折扣
        "max_discount": 0.2,   # 最大20%折扣
        "description": "针对已购买过课程用户的复购优惠",
        "prompt_guidance": "老用户复购时使用，根据历史购买金额调整5-15%折扣"
    },
    "bulk_purchase": {
        "option_name": "批量购买折扣",
        "discount_type": DiscountType.PERCENTAGE,
        "min_discount": 0.1,   # 最小10%折扣
        "max_discount": 0.25,  # 最大25%折扣
        "description": "购买多门课程时的批量优惠",
        "prompt_guidance": "购买2门以上课程时使用，课程越多折扣越大"
    },
    "vip_discount": {
        "option_name": "VIP专享折扣",
        "discount_type": DiscountType.PERCENTAGE,
        "min_discount": 0.2,   # 最小20%折扣
        "max_discount": 0.5,   # 最大50%折扣
        "description": "针对高价值用户的专享优惠，折扣力度最大",
        "prompt_guidance": "识别为高价值用户或特殊情况时使用，需谨慎"
    }
}


def get_discount_options() -> Dict[DiscountOptionType, DiscountOption]:
    """
    获取所有折扣选项配置
    
    Returns:
        折扣选项字典，供Agent选择使用
    """
    options = {}
    
    for option_key, config in DISCOUNT_OPTIONS_CONFIG.items():
        option_type = DiscountOptionType(option_key)
        options[option_type] = DiscountOption(
            option_type=option_type,
            option_name=config["option_name"],
            discount_type=config["discount_type"],
            min_discount=config["min_discount"],
            max_discount=config["max_discount"],
            description=config["description"],
            is_active=True
        )
    
    return options


def get_discount_option(option_type: DiscountOptionType) -> DiscountOption:
    """
    获取指定类型的折扣选项
    
    Args:
        option_type: 折扣选项类型
        
    Returns:
        折扣选项配置
    """
    options = get_discount_options()
    return options.get(option_type)


def validate_discount_in_range(option_type: DiscountOptionType, discount_value: float) -> bool:
    """
    验证折扣值是否在允许范围内
    
    Args:
        option_type: 折扣选项类型
        discount_value: Agent选择的折扣值
        
    Returns:
        是否在有效范围内
    """
    option = get_discount_option(option_type)
    if not option:
        return False
    
    return option.min_discount <= discount_value <= option.max_discount


def get_prompt_guidance() -> str:
    """
    获取Agent使用的提示词指导
    
    Returns:
        格式化的提示词指导内容
    """
    guidance_lines = [
        "=== 折扣选择指导 ===",
        "根据用户画像和对话内容选择合适的折扣类型和力度：",
        ""
    ]
    
    for option_key, config in DISCOUNT_OPTIONS_CONFIG.items():
        guidance_lines.extend([
            f"【{config['option_name']}】",
            f"- 范围: {config['min_discount']*100:.0f}% - {config['max_discount']*100:.0f}%",
            f"- 使用场景: {config['prompt_guidance']}",
            f"- 说明: {config['description']}",
            ""
        ])
    
    guidance_lines.extend([
        "=== 使用原则 ===",
        "1. 优先考虑用户画像中的紧迫度、预算范围、动机类型",
        "2. 新用户可给予较大优惠促进首购转化",
        "3. 老用户以维护关系为主，折扣适中",
        "4. 批量购买鼓励多课程学习",
        "5. VIP折扣需谨慎使用，仅限高价值场景",
        ""
    ])
    
    return "\n".join(guidance_lines)


# Agent可以使用的示例代码
AGENT_USAGE_EXAMPLE = """
# Agent使用示例：

# 1. 获取可用折扣选项
from app.config.discount_options import get_discount_options, validate_discount_in_range

options = get_discount_options()

# 2. 根据对话判断选择折扣
# 假设Agent分析用户为新用户，意向强烈
selected_type = DiscountOptionType.NEW_USER
agent_decided_discount = 0.2  # Agent决定给20%折扣

# 3. 验证折扣在范围内
if validate_discount_in_range(selected_type, agent_decided_discount):
    # 应用折扣
    await discount_service.apply_discount_option(
        user_id, selected_type, agent_decided_discount, course_ids
    )
"""