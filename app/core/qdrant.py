from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, Range, MatchValue
)
from typing import List, Dict, Any, Optional, Union
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class QdrantManager:
    """
    向量数据库管理器
    核心功能：
    - 连接管理和健康检查
    - 集合创建和配置
    - 向量数据的CRUD操作
    - 语义检索和过滤搜索
    """

    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.collections = {
            "courses": "课程知识库",
            "user_profiles": "用户画像",
            "chat_history": "对话历史"
        }

    async def init_qdrant(self) -> None:
        """
        初始化Qdrant连接

        - 采用grpc内部连接
        """
        max_retries = 3
        retry_delay = 2  # 秒

        for attempt in range(max_retries):
            try:
                logger.info(f"尝试连接Qdrant (第{attempt + 1}次)",
                            host=settings.qdrant_host,
                            port=settings.qdrant_port)

                # 创建Qdrant客户端连接
                self.client = QdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port,
                    grpc_port=settings.qdrant_grpc_port,
                    prefer_grpc=True,
                    timeout=15,  # 增加超时时间
                    api_key=None,
                    https=False,
                )

                # 测试连接 - 使用正确的API方法
                collections = self.client.get_collections()
                logger.info("Qdrant连接成功",
                            collections_count=len(collections.collections),
                            attempt=attempt + 1)

                # 初始化必要的集合
                await self._init_collections()
                return  # 连接成功，退出重试循环

            except Exception as e:
                logger.error(f"Qdrant连接失败 (第{attempt + 1}次)",
                             error=str(e),
                             error_type=type(e).__name__)

                # 如果不是最后一次尝试，等待后重试
                if attempt < max_retries - 1:
                    logger.info(f"等待{retry_delay}秒后重试...")
                    import asyncio
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    # 最后一次失败，设置客户端为None但不抛出异常
                    logger.error("所有Qdrant连接尝试均失败，但继续启动应用")
                    self.client = None

    async def _init_collections(self) -> None:
        """
        初始化向量集合

        - 向量维度需要与embedding模型输出维度一致
        - Distance.COSINE适合文本相似度计算
        - 可以为向量添加payload（元数据）用于过滤
        """
        try:
            # 课程知识库集合配置
            courses_config = VectorParams(
                size=384,  # sentence-transformers模型输出维度
                distance=Distance.COSINE  # 余弦相似度，适合文本
            )

            # 检查并创建courses集合
            try:
                # 尝试获取集合信息来检查是否存在
                self.client.get_collection("courses")
                logger.info("courses集合已存在")
            except Exception:
                # 集合不存在，创建新集合
                self.client.create_collection(
                    collection_name="courses",
                    vectors_config=courses_config
                )
                logger.info("创建courses集合成功")

            # 用户画像集合（用于个性化推荐）
            user_profiles_config = VectorParams(
                size=384,
                distance=Distance.COSINE
            )

            try:
                # 尝试获取集合信息来检查是否存在
                self.client.get_collection("user_profiles")
                logger.info("user_profiles集合已存在")
            except Exception:
                # 集合不存在，创建新集合
                self.client.create_collection(
                    collection_name="user_profiles",
                    vectors_config=user_profiles_config
                )
                logger.info("创建user_profiles集合成功")

        except Exception as e:
            logger.error("初始化集合失败", error=str(e))
            raise

    def close_qdrant(self) -> None:
        """关闭Qdrant连接"""
        if self.client:
            self.client.close()
            logger.info("Qdrant连接已关闭")

    def upsert_vectors(
            self,
            collection_name: str,
            points: List[PointStruct]
    ) -> bool:
        """
        插入或更新向量数据

        Args:
            collection_name: 集合名称
            points: 向量点数据列表

        - upsert操作：如果ID存在则更新，否则插入
        - PointStruct包含：id, vector, payload
        - payload用于存储元数据，支持过滤查询
        """
        try:
            result = self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(
                "向量数据upsert成功",
                collection=collection_name,
                count=len(points),
                operation_id=result.operation_id
            )
            return True

        except Exception as e:
            logger.error(
                "向量数据upsert失败",
                collection=collection_name,
                error=str(e)
            )
            return False

    def search_vectors(
            self,
            collection_name: str,
            query_vector: List[float],
            limit: int = 5,
            score_threshold: float = 0.0,
            filter_conditions: Optional[Filter] = None
    ) -> List[Dict[str, Any]]:
        """
        向量相似度搜索

        Args:
            collection_name: 集合名称
            query_vector: 查询向量
            limit: 返回结果数量
            score_threshold: 相似度阈值
            filter_conditions: 过滤条件

        - 向量搜索基于余弦相似度计算
        - score_threshold用于过滤低相似度结果
        - filter_conditions支持复杂的元数据过滤
        """
        try:
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=filter_conditions,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,  # 返回元数据
                with_vectors=False  # 不返回向量数据（节省带宽）
            )

            # 格式化搜索结果
            results = []
            for result in search_results:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                })

            logger.info(
                "向量搜索完成",
                collection=collection_name,
                query_size=len(query_vector),
                results_count=len(results)
            )

            return results

        except Exception as e:
            logger.error(
                "向量搜索失败",
                collection=collection_name,
                error=str(e)
            )
            return []

    def delete_vectors(
            self,
            collection_name: str,
            point_ids: List[Union[int, str]]
    ) -> bool:
        """删除向量数据"""
        try:
            result = self.client.delete(
                collection_name=collection_name,
                points_selector=point_ids
            )
            logger.info(
                "向量数据删除成功",
                collection=collection_name,
                count=len(point_ids)
            )
            return True

        except Exception as e:
            logger.error(
                "向量数据删除失败",
                collection=collection_name,
                error=str(e)
            )
            return False

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """获取集合信息"""
        try:
            info = self.client.get_collection(collection_name)
            return {
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "config": {
                    "params": info.config.params.dict(),
                    "hnsw_config": info.config.hnsw_config.dict() if info.config.hnsw_config else None
                }
            }
        except Exception as e:
            logger.error("获取集合信息失败", collection=collection_name, error=str(e))
            return None


# 全局Qdrant管理器实例
qdrant_manager = QdrantManager()