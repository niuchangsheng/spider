"""
数据存储模块
"""
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import redis
from loguru import logger
from datetime import datetime
import json

from config import config


class Storage:
    """数据存储管理器"""
    
    def __init__(self):
        self.db_config = config.database
        self.mongo_client: Optional[MongoClient] = None
        self.mongo_db = None
        self.redis_client: Optional[redis.Redis] = None
    
    def connect(self):
        """连接数据库"""
        try:
            # 连接MongoDB
            self.mongo_client = MongoClient(
                self.db_config.mongodb_uri,
                serverSelectionTimeoutMS=5000
            )
            self.mongo_db = self.mongo_client[self.db_config.mongodb_db]
            # 测试连接
            self.mongo_client.server_info()
            logger.success("Connected to MongoDB")
        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.mongo_client = None
        
        try:
            # 连接Redis
            self.redis_client = redis.Redis(
                host=self.db_config.redis_host,
                port=self.db_config.redis_port,
                db=self.db_config.redis_db,
                password=self.db_config.redis_password,
                decode_responses=True
            )
            # 测试连接
            self.redis_client.ping()
            logger.success("Connected to Redis")
        except redis.RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    def close(self):
        """关闭数据库连接"""
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB connection closed")
        
        if self.redis_client:
            self.redis_client.close()
            logger.info("Redis connection closed")
    
    # ==================== MongoDB操作 ====================
    
    def save_thread(self, thread_data: Dict[str, Any]) -> bool:
        """保存帖子数据"""
        if self.mongo_db is None:
            logger.warning("MongoDB not connected")
            return False
        
        try:
            collection = self.mongo_db['threads']
            thread_data['created_at'] = datetime.now()
            thread_data['updated_at'] = datetime.now()
            
            # 使用thread_id作为唯一标识，存在则更新
            result = collection.update_one(
                {'thread_id': thread_data['thread_id']},
                {'$set': thread_data},
                upsert=True
            )
            
            logger.info(f"Saved thread: {thread_data['thread_id']}")
            return True
        
        except PyMongoError as e:
            logger.error(f"Failed to save thread: {e}")
            return False
    
    def save_image_record(self, image_data: Dict[str, Any]) -> bool:
        """保存图片记录"""
        if self.mongo_db is None:
            logger.warning("MongoDB not connected")
            return False
        
        try:
            collection = self.mongo_db['images']
            image_data['created_at'] = datetime.now()
            
            result = collection.insert_one(image_data)
            logger.debug(f"Saved image record: {image_data.get('url')}")
            return True
        
        except PyMongoError as e:
            logger.error(f"Failed to save image record: {e}")
            return False
    
    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """获取帖子数据"""
        if self.mongo_db is None:
            return None
        
        try:
            collection = self.mongo_db['threads']
            return collection.find_one({'thread_id': thread_id})
        except PyMongoError as e:
            logger.error(f"Failed to get thread: {e}")
            return None
    
    def thread_exists(self, thread_id: str) -> bool:
        """检查帖子是否已存在"""
        if self.mongo_db is None:
            return False
        
        try:
            collection = self.mongo_db['threads']
            return collection.count_documents({'thread_id': thread_id}) > 0
        except PyMongoError as e:
            logger.error(f"Failed to check thread existence: {e}")
            return False
    
    def get_all_threads(self, board: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有帖子"""
        if self.mongo_db is None:
            return []
        
        try:
            collection = self.mongo_db['threads']
            query = {'metadata.board': board} if board else {}
            return list(collection.find(query))
        except PyMongoError as e:
            logger.error(f"Failed to get threads: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if self.mongo_db is None:
            return {}
        
        try:
            stats = {
                'total_threads': self.mongo_db['threads'].count_documents({}),
                'total_images': self.mongo_db['images'].count_documents({}),
                'successful_downloads': self.mongo_db['images'].count_documents({'success': True}),
                'failed_downloads': self.mongo_db['images'].count_documents({'success': False}),
            }
            
            # 按板块统计
            pipeline = [
                {'$group': {
                    '_id': '$metadata.board',
                    'count': {'$sum': 1}
                }}
            ]
            board_stats = list(self.mongo_db['threads'].aggregate(pipeline))
            stats['boards'] = {item['_id']: item['count'] for item in board_stats if item['_id']}
            
            return stats
        
        except PyMongoError as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    # ==================== Redis操作 ====================
    
    def add_to_queue(self, queue_name: str, item: Any) -> bool:
        """添加到队列"""
        if not self.redis_client:
            return False
        
        try:
            if isinstance(item, dict):
                item = json.dumps(item)
            self.redis_client.rpush(queue_name, item)
            return True
        except redis.RedisError as e:
            logger.error(f"Failed to add to queue: {e}")
            return False
    
    def get_from_queue(self, queue_name: str, timeout: int = 0) -> Optional[Any]:
        """从队列获取"""
        if not self.redis_client:
            return None
        
        try:
            if timeout > 0:
                result = self.redis_client.blpop(queue_name, timeout=timeout)
                if result:
                    _, value = result
                    try:
                        return json.loads(value)
                    except:
                        return value
            else:
                value = self.redis_client.lpop(queue_name)
                if value:
                    try:
                        return json.loads(value)
                    except:
                        return value
            return None
        except redis.RedisError as e:
            logger.error(f"Failed to get from queue: {e}")
            return None
    
    def is_url_visited(self, url: str) -> bool:
        """检查URL是否已访问"""
        if not self.redis_client:
            return False
        
        try:
            return self.redis_client.sismember('visited_urls', url)
        except redis.RedisError as e:
            logger.error(f"Failed to check URL: {e}")
            return False
    
    def mark_url_visited(self, url: str) -> bool:
        """标记URL已访问"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.sadd('visited_urls', url)
            return True
        except redis.RedisError as e:
            logger.error(f"Failed to mark URL: {e}")
            return False
    
    def get_queue_size(self, queue_name: str) -> int:
        """获取队列大小"""
        if not self.redis_client:
            return 0
        
        try:
            return self.redis_client.llen(queue_name)
        except redis.RedisError as e:
            logger.error(f"Failed to get queue size: {e}")
            return 0
    
    def clear_queue(self, queue_name: str) -> bool:
        """清空队列"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.delete(queue_name)
            return True
        except redis.RedisError as e:
            logger.error(f"Failed to clear queue: {e}")
            return False


# 全局存储实例
storage = Storage()
