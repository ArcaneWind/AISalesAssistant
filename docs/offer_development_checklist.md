# 优惠服务开发任务清单

## Phase 1: 数据模型和数据库设计 (1-2天)

### 1.1 Pydantic数据模型
- [ ] **Course模型** (`app/models/course.py`)
  - [ ] Course基础模型
  - [ ] CourseCreate/CourseUpdate模型
  - [ ] CourseResponse模型
  
- [ ] **Discount模型** (`app/models/discount.py`)  
  - [ ] DiscountOption模型
  - [ ] AppliedDiscount模型
  - [ ] DiscountSuggestion模型

- [ ] **Coupon模型** (`app/models/coupon.py`)
  - [ ] Coupon基础模型
  - [ ] CouponValidation模型
  - [ ] CouponUsage模型

- [ ] **Order模型** (`app/models/order.py`)
  - [ ] Order基础模型
  - [ ] OrderItem模型
  - [ ] OrderCreate/OrderUpdate模型
  - [ ] PriceCalculation模型

### 1.2 数据库表设计
- [ ] **数据库模型** (`app/models/database/`)
  - [ ] `course_db.py` - 课程表
  - [ ] `coupon_db.py` - 优惠券表  
  - [ ] `discount_option_db.py` - 折扣选项表
  - [ ] `order_db.py` - 订单表
  - [ ] `order_item_db.py` - 订单项目表
  - [ ] `applied_discount_db.py` - 应用折扣记录表

- [ ] **数据库迁移脚本**
  - [ ] 创建表结构脚本
  - [ ] 索引创建脚本
  - [ ] 初始数据插入脚本

### 1.3 Repository层
- [ ] **数据访问层** (`app/repositories/`)
  - [ ] `course_repository.py` - 课程数据访问
  - [ ] `coupon_repository.py` - 优惠券数据访问
  - [ ] `discount_repository.py` - 折扣数据访问
  - [ ] `order_repository.py` - 订单数据访问

## Phase 2: 核心服务实现 (2-3天)

### 2.1 CourseService
- [ ] **课程管理服务** (`app/services/course_service.py`)
  - [ ] `get_courses_by_category()` - 按分类获取课程
  - [ ] `get_course_details()` - 获取课程详情
  - [ ] `search_courses()` - 搜索课程
  - [ ] `get_recommended_courses()` - 基于用户画像推荐
  - [ ] 缓存层集成

### 2.2 DiscountService  
- [ ] **折扣服务** (`app/services/discount_service.py`)
  - [ ] 折扣选项配置管理
  - [ ] `get_available_discount_options()` - 获取可用选项
  - [ ] `apply_discount_option()` - 应用Agent选择的折扣
  - [ ] `get_discount_suggestion()` - 获取折扣建议
  - [ ] 折扣规则引擎
  - [ ] 权限和条件验证

### 2.3 CouponService
- [ ] **优惠券服务** (`app/services/coupon_service.py`)
  - [ ] `validate_coupon()` - 验证优惠券
  - [ ] `apply_coupon()` - 应用优惠券
  - [ ] `get_user_available_coupons()` - 获取用户可用券
  - [ ] 优惠券使用记录

### 2.4 PriceCalculatorService
- [ ] **价格计算服务** (`app/services/price_calculator.py`)
  - [ ] `calculate_order_price()` - 核心价格计算
  - [ ] `get_price_preview()` - 价格预览
  - [ ] 折扣叠加逻辑
  - [ ] 价格明细生成
  - [ ] 计算结果缓存

### 2.5 OrderService
- [ ] **订单服务** (`app/services/order_service.py`)
  - [ ] `create_order()` - 创建订单
  - [ ] `get_user_orders()` - 获取用户订单
  - [ ] `update_order_status()` - 更新订单状态
  - [ ] 订单状态管理

## Phase 3: 配置和业务逻辑 (1天)

### 3.1 折扣选项配置
- [ ] **配置管理** (`app/config/discount_options.py`)
  - [ ] 预定义折扣选项配置
  - [ ] 动态配置加载
  - [ ] 配置验证逻辑

### 3.2 业务规则引擎
- [ ] **规则引擎** (`app/services/business_rules.py`)
  - [ ] 折扣适用性判断
  - [ ] 用户权限验证
  - [ ] 课程适用性检查
  - [ ] 订单金额限制

### 3.3 缓存层
- [ ] **缓存服务** (`app/services/offer_cache.py`)
  - [ ] 课程信息缓存
  - [ ] 折扣选项缓存
  - [ ] 价格计算缓存
  - [ ] 用户权益缓存

## Phase 4: 测试和优化 (1-2天)

### 4.1 单元测试
- [ ] **模型测试** (`tests/test_models/`)
  - [ ] `test_course.py`
  - [ ] `test_discount.py` 
  - [ ] `test_coupon.py`
  - [ ] `test_order.py`

- [ ] **服务测试** (`tests/test_services/`)
  - [ ] `test_course_service.py`
  - [ ] `test_discount_service.py`
  - [ ] `test_coupon_service.py`
  - [ ] `test_price_calculator.py`
  - [ ] `test_order_service.py`

### 4.2 集成测试  
- [ ] **端到端测试** (`tests/test_integration/`)
  - [ ] Agent调用流程测试
  - [ ] 价格计算准确性测试
  - [ ] 折扣叠加逻辑测试
  - [ ] 订单创建流程测试

### 4.3 性能优化
- [ ] 数据库查询优化
- [ ] 缓存命中率优化
- [ ] 服务响应时间优化
- [ ] 并发性能测试

## Phase 5: Agent集成和文档 (0.5天)

### 5.1 Agent集成示例
- [ ] **集成示例** (`docs/examples/`)
  - [ ] Agent调用课程服务示例
  - [ ] Agent应用折扣示例
  - [ ] Agent价格计算示例
  - [ ] Agent订单创建示例

### 5.2 接口文档
- [ ] **API文档**
  - [ ] Service方法详细说明
  - [ ] 参数和返回值文档
  - [ ] 使用示例和最佳实践
  - [ ] 错误处理指南

## 开发优先级建议

### 🚀 高优先级 (核心功能)
1. Course模型和CourseService - Agent需要推荐课程
2. 基础价格计算 - 核心商业逻辑
3. DiscountService折扣选项 - Agent决策的基础

### ⭐ 中优先级 (完善功能)  
1. CouponService - 优惠券功能
2. OrderService - 订单管理
3. 缓存层优化

### 📝 低优先级 (增强功能)
1. 复杂业务规则
2. 高级缓存策略
3. 详细监控和分析

## 预估工作量

- **Phase 1 (数据层)**: 1-2天
- **Phase 2 (服务层)**: 2-3天  
- **Phase 3 (配置业务)**: 1天
- **Phase 4 (测试优化)**: 1-2天
- **Phase 5 (集成文档)**: 0.5天

**总计**: 5.5-8.5天

## 技术栈和依赖

- **数据模型**: Pydantic v2
- **数据库**: PostgreSQL + SQLAlchemy (async)
- **缓存**: Redis
- **测试**: pytest + pytest-asyncio  
- **配置**: Python dataclass/dict
- **日志**: Python logging

## 关键设计决策

1. **简化架构**: 无额外Agent层，Service直接暴露接口
2. **Agent决策**: 系统提供选项和范围，Agent做最终决策
3. **灵活配置**: 折扣选项可配置，易于业务调整
4. **性能优先**: 直接调用链路，减少中间层
5. **职责清晰**: 每个Service单一职责，便于维护