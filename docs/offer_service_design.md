# 优惠服务设计文档

## 1. 核心设计原则

- **Service层直接暴露接口**：Agent直接调用Service方法，无需额外封装层
- **Agent决策模式**：系统提供折扣选项和范围，Agent根据对话内容判断并选择
- **简化架构**：减少抽象层，直接高效的调用链路

## 2. 数据模型设计

### 2.1 课程模型 (Course)
```python
- course_id: str           # 课程ID  
- course_name: str         # 课程名称
- category: str            # 分类(python/data_analysis/ai)
- original_price: Decimal  # 原价
- current_price: Decimal   # 现价
- description: str         # 描述
- duration_hours: int      # 时长
- difficulty_level: str    # 难度(beginner/intermediate/advanced)
- tags: List[str]         # 标签
- is_active: bool
```

### 2.2 折扣选项模型 (DiscountOption)
```python
- option_id: str           # 选项ID
- option_name: str         # 选项名称(新用户折扣/紧急转化/老用户回购)
- discount_type: str       # 类型(percentage/fixed_amount)
- min_discount: float      # 最小折扣
- max_discount: float      # 最大折扣
- applicable_courses: List[str] # 适用课程
- usage_conditions: Dict   # 使用条件
- description: str         # 描述信息
```

### 2.3 优惠券模型 (Coupon)
```python
- coupon_code: str         # 优惠券代码
- discount_value: Decimal  # 折扣值
- coupon_type: str         # 类型(percentage/fixed)
- min_order_amount: Decimal # 最小金额
- valid_from/to: datetime  # 有效期
- usage_limit: int         # 使用限制
- applicable_courses: List[str]
```

### 2.4 订单模型 (Order)
```python
- order_id: str
- user_id: str
- course_items: List[Dict]  # [{"course_id": "...", "price": ...}]
- applied_discount: Dict    # 应用的折扣信息
- original_amount: Decimal
- discount_amount: Decimal
- final_amount: Decimal
- order_status: str
```

## 3. Service接口设计

### 3.1 CourseService - 课程管理
```python
class CourseService:
    # Agent调用的核心方法
    async def get_courses_by_category(category: str) -> List[Course]
    async def get_course_details(course_id: str) -> Course
    async def search_courses(keywords: str) -> List[Course]
    async def get_recommended_courses(user_profile: Dict) -> List[Course]
```

### 3.2 DiscountService - 折扣服务  
```python
class DiscountService:
    # 获取可用的折扣选项 - Agent根据对话选择
    async def get_available_discount_options(user_id: str) -> List[DiscountOption]
    
    # Agent选定折扣后应用
    async def apply_discount_option(
        user_id: str, 
        option_id: str, 
        discount_amount: float,  # Agent决定的具体折扣额度
        course_ids: List[str]
    ) -> Dict
    
    # 获取折扣建议范围 - 供Agent参考
    async def get_discount_suggestion(
        user_profile: Dict, 
        course_ids: List[str]
    ) -> Dict[str, Any]  # 返回建议的折扣类型和范围
```

### 3.3 CouponService - 优惠券服务
```python
class CouponService:
    async def validate_coupon(coupon_code: str, course_ids: List[str]) -> Dict
    async def apply_coupon(user_id: str, coupon_code: str, course_ids: List[str]) -> Dict
    async def get_user_available_coupons(user_id: str) -> List[Coupon]
```

### 3.4 PriceCalculatorService - 价格计算
```python
class PriceCalculatorService:
    # 核心价格计算 - Agent调用
    async def calculate_order_price(
        course_ids: List[str],
        discount_info: Optional[Dict] = None,  # Agent应用的折扣
        coupon_code: Optional[str] = None
    ) -> Dict[str, Any]  # 返回详细价格明细
    
    # 获取价格预览 - 无折扣的基础价格
    async def get_price_preview(course_ids: List[str]) -> Dict
```

### 3.5 OrderService - 订单服务
```python
class OrderService:
    async def create_order(
        user_id: str,
        course_ids: List[str], 
        applied_discount: Dict,
        final_amount: Decimal
    ) -> Order
    
    async def get_user_orders(user_id: str) -> List[Order]
    async def update_order_status(order_id: str, status: str) -> bool
```

## 4. Agent使用流程

### 4.1 推荐课程场景
```python
# Agent获取用户画像后推荐课程
courses = await course_service.get_recommended_courses(user_profile)

# 获取基础价格
price_info = await price_calculator.get_price_preview([course.course_id])
```

### 4.2 应用折扣场景  
```python
# 1. Agent获取可用折扣选项
options = await discount_service.get_available_discount_options(user_id)

# 2. Agent根据对话判断选择哪个选项，以及具体折扣力度
# 例如：Agent判断用户很有购买意向，选择"紧急转化"选项，给8折
selected_option = "urgent_conversion" 
agent_decided_discount = 0.2  # Agent决定给20%折扣

# 3. 应用折扣
discount_result = await discount_service.apply_discount_option(
    user_id, selected_option, agent_decided_discount, course_ids
)

# 4. 计算最终价格
final_price = await price_calculator.calculate_order_price(
    course_ids, discount_result, coupon_code
)
```

### 4.3 折扣决策辅助
```python
# Agent可以获取折扣建议，但最终决策权在Agent
suggestion = await discount_service.get_discount_suggestion(
    user_profile, course_ids
)
# 返回: {"suggested_type": "new_user", "min_discount": 0.1, "max_discount": 0.3}

# Agent根据对话内容在建议范围内做决策
```

## 5. 折扣选项配置

### 5.1 预定义折扣选项
```python
DISCOUNT_OPTIONS = {
    "new_user": {
        "name": "新用户首购折扣",
        "min_discount": 0.1,  # 最小1折
        "max_discount": 0.3,  # 最大3折  
        "conditions": {"is_first_purchase": True}
    },
    "urgent_conversion": {
        "name": "紧急转化折扣", 
        "min_discount": 0.15,
        "max_discount": 0.4,
        "conditions": {"urgency_level": ">= 4"}
    },
    "returning_user": {
        "name": "老用户回购",
        "min_discount": 0.05,
        "max_discount": 0.2, 
        "conditions": {"has_previous_orders": True}
    },
    "bulk_purchase": {
        "name": "多课程优惠",
        "min_discount": 0.1,
        "max_discount": 0.25,
        "conditions": {"course_count": ">= 2"}
    }
}
```

## 6. 开发任务清单

### Phase 1: 基础模型和数据库
- [ ] 设计Course、Coupon、Order等Pydantic模型
- [ ] 创建数据库表结构和迁移脚本
- [ ] 实现Repository层数据访问

### Phase 2: 核心服务实现
- [ ] CourseService实现
- [ ] DiscountService实现(重点：选项配置和应用逻辑)
- [ ] CouponService实现
- [ ] PriceCalculatorService实现

### Phase 3: 业务逻辑和测试
- [ ] 折扣选项配置管理
- [ ] 价格计算引擎
- [ ] 订单管理服务
- [ ] 单元测试和集成测试

### Phase 4: 缓存和性能优化
- [ ] Redis缓存热门课程和折扣选项
- [ ] 价格计算结果缓存
- [ ] 数据库查询优化

## 7. 技术要点

- **无Agent层**：Service直接暴露方法给Agent调用
- **Agent决策**：系统只提供选项和范围，具体判断由Agent完成
- **灵活配置**：折扣选项可配置，易于调整策略
- **性能优先**：直接调用，减少中间层开销
- **清晰职责**：每个Service职责单一，易于维护