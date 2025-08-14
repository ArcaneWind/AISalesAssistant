# RAG模块架构设计文档

## 项目概述

本RAG模块专为AI销售助手设计，旨在处理PDF和图片文档，提供智能检索和问答功能。系统采用中文优化的模型，分为三个核心模块：离线数据录入、在线检索和评测系统。

## 整体架构

```
AI销售助手RAG系统
├── A模块：离线数据录入 (Offline Data Ingestion)
│   ├── PDF处理服务
│   ├── 图片OCR服务  
│   ├── 中文向量化服务
│   ├── 文档分块策略
│   └── 数据质量管理
├── B模块：在线检索 (Online Retrieval)
│   ├── 语义搜索引擎
│   ├── 个性化重排序
│   ├── 混合检索策略
│   ├── 缓存优化
│   └── RAG统一接口
└── C模块：评测系统 (Evaluation System)
    ├── 检索相关性评估
    ├── 排序质量评估
    ├── 测试数据管理
    ├── 自动化评测
    └── 回归测试
```

## 技术选型

### 中文优化模型选择
- **文本向量化**: BGE-M3 或 M3E-base (中文语义理解优秀)
- **OCR识别**: PaddleOCR (中文识别准确率高)
- **重排序**: BGE-reranker-large (中文重排序效果好)
- **向量数据库**: Qdrant (支持混合检索和高性能)

### 核心依赖包
```python
# 中文NLP和向量化
sentence-transformers>=2.2.0
FlagEmbedding>=1.2.0  # BGE模型
qdrant-client>=1.7.0

# 文档处理
PyPDF2>=3.0.0
pdfplumber>=0.9.0
Pillow>=9.5.0
paddleocr>=2.7.0
paddlepaddle>=2.5.0

# 检索和评测
rank-bm25>=0.2.2
scikit-learn>=1.3.0
numpy>=1.24.0
```

## A模块：离线数据录入

### 核心功能
1. **多格式文档处理**
   - PDF文档内容提取和结构化
   - 图片OCR文字识别
   - 文档元数据提取和管理

2. **中文文本向量化**
   - 基于BGE-M3的高质量中文向量化
   - 支持长文本分块处理
   - 向量维度：1024维

3. **数据质量控制**
   - 文档内容去重
   - 低质量文本过滤
   - 向量质量验证

### 技术架构
```
文档输入 → 格式识别 → 内容提取 → 文本预处理 → 分块策略 → 向量化 → 质量检查 → 存储
```

### 存储设计
- **原始文档**: 文件系统存储
- **文本内容**: PostgreSQL存储元数据
- **向量数据**: Qdrant向量数据库

## B模块：在线检索

### 核心功能
1. **混合检索策略**
   - 语义检索：基于向量相似度
   - 关键词检索：基于BM25算法
   - 混合权重：动态调整检索权重

2. **个性化重排序**
   - 基于用户画像的相关性调整
   - 基于历史行为的偏好学习
   - BGE-reranker二次排序优化

3. **性能优化**
   - 多级缓存策略
   - 异步检索处理
   - 批量向量查询优化

### API接口设计
```python
class RAGService:
    async def search(
        self, 
        query: str, 
        user_profile: dict = None,
        top_k: int = 10,
        search_type: str = "hybrid"
    ) -> List[SearchResult]
    
    async def get_context_for_question(
        self,
        question: str,
        user_id: str = None,
        max_context_length: int = 4000
    ) -> ContextResult
```

## C模块：评测系统

### 评估指标
1. **检索质量指标**
   - Precision@K：前K个结果的精确率
   - Recall@K：前K个结果的召回率
   - NDCG@K：归一化折扣累积增益
   - MRR：平均倒数排名

2. **用户体验指标**
   - 响应时间：平均检索延迟
   - 相关性评分：人工标注相关性
   - 答案准确性：基于标准答案的匹配度

### 测试框架
```python
class RAGEvaluator:
    def evaluate_retrieval_quality(self, test_queries: List[TestQuery]) -> EvalResult
    def evaluate_response_time(self, query_batch: List[str]) -> PerformanceReport  
    def run_regression_test(self, baseline_version: str) -> RegressionReport
```

## 数据流程设计

### 离线数据录入流程
```
1. 文档上传 → 文档解析 → 内容提取
2. 文本预处理 → 分块处理 → 向量化
3. 质量检查 → 数据存储 → 索引构建
```

### 在线检索流程  
```
1. 用户查询 → 查询理解 → 向量化
2. 混合检索 → 结果合并 → 个性化重排序  
3. 缓存更新 → 结果返回
```

## 部署架构

### 服务组件
- **RAG API服务**: FastAPI + Uvicorn
- **向量数据库**: Qdrant集群
- **缓存服务**: Redis集群  
- **文档存储**: 本地文件系统/对象存储

### 监控和日志
- 检索请求日志记录
- 性能指标监控
- 错误异常告警
- 数据质量监控

## 开发里程碑

### Phase 1: 基础设施 (A模块)
- A1: 安装中文优化RAG依赖包
- A2: PDF文档处理服务实现
- A3: 图片OCR识别服务实现  
- A4: 中文向量化服务实现
- A5: 文档分块和向量化流程
- A6: 数据质量管理工具

### Phase 2: 检索引擎 (B模块)  
- B1: 语义搜索核心服务
- B2: 个性化重排序算法
- B3: 混合检索策略实现
- B4: RAG主服务和统一接口
- B5: 缓存和性能优化

### Phase 3: 评测优化 (C模块)
- C1: 检索相关性评估指标
- C2: 排序质量评估指标  
- C3: 测试数据集管理
- C4: 自动化评测报告
- C5: 回归测试框架

## 质量保证

### 代码规范
- 统一的Python代码风格
- 完整的类型提示
- 全面的单元测试覆盖
- 详细的API文档

### 性能要求
- 单次检索响应时间 < 500ms
- 批量处理吞吐量 > 100 QPS
- 向量检索精度 > 0.85
- 系统可用性 > 99.9%

## 风险评估

### 技术风险
- 中文模型效果不达预期
- 向量数据库性能瓶颈
- OCR识别准确率问题

### 缓解策略  
- 多模型对比测试
- 性能基准测试
- 渐进式部署验证

---

*文档版本: v1.0*  
*最后更新: 2025-01-14*
*负责人: Claude AI Assistant*