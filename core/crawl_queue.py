"""
异步任务队列模块

实现生产者-消费者模式，用于并发爬取任务
"""
import asyncio
from typing import List, Dict, Any, Optional, Callable, Awaitable
from collections import deque
from loguru import logger


class CrawlQueue:
    """
    爬取任务队列
    
    使用 asyncio.Queue 实现生产者-消费者模式，支持：
    - 并发爬取多个任务
    - 动态调整并发数
    - 错误处理和重试
    - 进度统计
    
    Example:
        queue = CrawlQueue(max_workers=10)
        await queue.run(urls, spider.crawl_thread)
    """
    
    def __init__(
        self,
        max_workers: int = 10,
        queue_size: int = 1000,
        timeout: float = 1.0
    ):
        """
        初始化爬取队列
        
        Args:
            max_workers: 消费者（worker）的数量，即并发执行任务的线程数
                        注意：生产者只有一个，负责添加任务到队列
                        消费者有 max_workers 个，并发从队列取任务并执行
            queue_size: 队列最大容量
            timeout: 消费者超时时间（秒）
        """
        self.max_workers = max_workers
        self.queue = asyncio.Queue(maxsize=queue_size)
        self.timeout = timeout
        
        # 统计信息
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'active_workers': 0
        }
        
        # 错误记录
        self.errors = deque(maxlen=100)
        
        logger.info(f"🚀 初始化爬取队列: max_workers={max_workers}, queue_size={queue_size}")
    
    async def producer(self, items: List[Any]):
        """
        生产者：添加任务到队列
        
        Args:
            items: 任务列表（可以是URL、字典等）
        """
        self.stats['total_tasks'] = len(items)
        logger.info(f"📦 生产者开始添加 {len(items)} 个任务到队列")
        
        for item in items:
            await self.queue.put(item)
            logger.debug(f"   ✓ 添加任务: {item}")
        
        logger.success(f"✅ 生产者完成，共添加 {len(items)} 个任务")
    
    async def consumer(
        self,
        worker_func: Callable[[Any], Awaitable[Any]],
        worker_id: int
    ):
        """
        消费者：从队列取任务并执行
        
        Args:
            worker_func: 工作函数（异步）
            worker_id: 消费者ID（用于日志）
        """
        logger.debug(f"🔧 消费者 {worker_id} 启动")
        self.stats['active_workers'] += 1
        
        while True:
            try:
                # 从队列获取任务（带超时）
                item = await asyncio.wait_for(self.queue.get(), timeout=self.timeout)
                
                try:
                    # 执行任务
                    await worker_func(item)
                    self.stats['completed_tasks'] += 1
                    logger.debug(f"   ✓ 消费者 {worker_id} 完成任务")
                    
                except Exception as e:
                    # 任务执行失败
                    self.stats['failed_tasks'] += 1
                    self.errors.append({
                        'item': str(item)[:100],  # 限制长度
                        'error': str(e),
                        'worker_id': worker_id
                    })
                    logger.error(f"   ❌ 消费者 {worker_id} 任务失败: {e}")
                
                finally:
                    # 标记任务完成
                    self.queue.task_done()
                    
            except asyncio.TimeoutError:
                # 队列为空，等待超时
                logger.debug(f"   ⏸️  消费者 {worker_id} 等待超时，退出")
                break
            except Exception as e:
                logger.error(f"   ❌ 消费者 {worker_id} 发生错误: {e}")
                break
        
        self.stats['active_workers'] -= 1
        logger.debug(f"🔒 消费者 {worker_id} 退出")
    
    async def run(
        self,
        items: List[Any],
        worker_func: Callable[[Any], Awaitable[Any]],
        show_progress: bool = True
    ):
        """
        运行爬取任务
        
        Args:
            items: 任务列表
            worker_func: 工作函数（异步）
            show_progress: 是否显示进度
            
        Returns:
            统计信息字典
        """
        logger.info(f"🚀 开始运行爬取队列: {len(items)} 个任务, {self.max_workers} 个并发")
        
        # 重置统计
        self.stats = {
            'total_tasks': len(items),
            'completed_tasks': 0,
            'failed_tasks': 0,
            'active_workers': 0
        }
        self.errors.clear()
        
        # 启动生产者
        producer_task = asyncio.create_task(self.producer(items))
        
        # 启动多个消费者（并发）
        consumer_tasks = [
            asyncio.create_task(self.consumer(worker_func, worker_id=i))
            for i in range(self.max_workers)
        ]
        
        # 等待生产者完成
        await producer_task
        
        # 等待所有任务完成
        try:
            await self.queue.join()
        except Exception as e:
            logger.error(f"❌ 队列执行出错: {e}")
        
        # 取消消费者任务
        for task in consumer_tasks:
            if not task.done():
                task.cancel()
        
        # 等待所有消费者退出
        await asyncio.gather(*consumer_tasks, return_exceptions=True)
        
        # 输出统计信息
        logger.success(f"✅ 队列执行完成")
        logger.info(f"📊 统计: 总数={self.stats['total_tasks']}, "
                   f"成功={self.stats['completed_tasks']}, "
                   f"失败={self.stats['failed_tasks']}")
        
        if self.errors:
            logger.warning(f"⚠️  失败任务数: {len(self.errors)}")
            # 显示前5个错误
            for i, error in enumerate(list(self.errors)[:5]):
                logger.debug(f"   错误 {i+1}: {error['error']}")
        
        return self.stats.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """获取错误列表"""
        return list(self.errors)


class AdaptiveCrawlQueue(CrawlQueue):
    """
    自适应爬取队列
    
    根据错误率自动调整并发数，实现性能优化和错误处理平衡
    """
    
    def __init__(
        self,
        initial_workers: int = 5,
        max_workers: int = 20,
        min_workers: int = 1,
        queue_size: int = 1000,
        timeout: float = 1.0,
        error_threshold: float = 0.1,  # 错误率阈值（10%）
        check_interval: int = 50  # 每处理N个任务检查一次
    ):
        """
        初始化自适应爬取队列
        
        Args:
            initial_workers: 初始并发数
            max_workers: 最大并发数
            min_workers: 最小并发数
            queue_size: 队列最大容量
            timeout: 消费者超时时间（秒）
            error_threshold: 错误率阈值（超过此值会降低并发）
            check_interval: 检查间隔（每处理N个任务检查一次）
        """
        super().__init__(max_workers=initial_workers, queue_size=queue_size, timeout=timeout)
        
        self.initial_workers = initial_workers
        self.max_workers = max_workers
        self.min_workers = min_workers
        self.current_workers = initial_workers
        self.error_threshold = error_threshold
        self.check_interval = check_interval
        
        # 自适应统计
        self.adaptive_stats = {
            'adjustments': 0,
            'current_error_rate': 0.0,
            'last_adjustment': None
        }
        
        logger.info(f"🎯 初始化自适应队列: "
                   f"初始={initial_workers}, "
                   f"最大={max_workers}, "
                   f"最小={min_workers}, "
                   f"错误阈值={error_threshold:.1%}")
    
    def _calculate_error_rate(self) -> float:
        """计算当前错误率"""
        total = self.stats['completed_tasks'] + self.stats['failed_tasks']
        if total == 0:
            return 0.0
        return self.stats['failed_tasks'] / total
    
    def _adjust_workers(self):
        """根据错误率调整并发数"""
        error_rate = self._calculate_error_rate()
        self.adaptive_stats['current_error_rate'] = error_rate
        
        old_workers = self.current_workers
        
        if error_rate > self.error_threshold:
            # 错误率过高，降低并发
            self.current_workers = max(
                self.min_workers,
                int(self.current_workers * 0.8)
            )
            logger.warning(f"📉 错误率过高 ({error_rate:.1%}), 降低并发: {old_workers} -> {self.current_workers}")
        elif error_rate < 0.01 and self.current_workers < self.max_workers:
            # 错误率很低，提高并发
            self.current_workers = min(
                self.max_workers,
                int(self.current_workers * 1.2)
            )
            logger.info(f"📈 错误率很低 ({error_rate:.1%}), 提高并发: {old_workers} -> {self.current_workers}")
        
        if old_workers != self.current_workers:
            self.adaptive_stats['adjustments'] += 1
            self.adaptive_stats['last_adjustment'] = {
                'from': old_workers,
                'to': self.current_workers,
                'error_rate': error_rate
            }
    
    async def run(
        self,
        items: List[Any],
        worker_func: Callable[[Any], Awaitable[Any]],
        show_progress: bool = True
    ):
        """
        运行自适应爬取任务
        
        注意：自适应队列在运行过程中会动态调整并发数，
        但实际调整需要重新启动消费者，这里采用简化策略：
        在开始时根据历史错误率调整初始并发数
        """
        logger.info(f"🎯 开始运行自适应爬取队列")
        
        # 重置统计
        self.stats = {
            'total_tasks': len(items),
            'completed_tasks': 0,
            'failed_tasks': 0,
            'active_workers': 0
        }
        self.errors.clear()
        
        # 使用当前并发数
        self.max_workers = self.current_workers
        
        # 调用父类方法
        stats = await super().run(items, worker_func, show_progress)
        
        # 运行结束后，根据最终错误率调整并发数（用于下次运行）
        self._adjust_workers()
        
        # 输出自适应统计
        logger.info(f"📊 自适应统计: "
                   f"调整次数={self.adaptive_stats['adjustments']}, "
                   f"最终错误率={self.adaptive_stats['current_error_rate']:.1%}, "
                   f"当前并发数={self.current_workers}")
        
        return stats
    
    def get_adaptive_stats(self) -> Dict[str, Any]:
        """获取自适应统计信息"""
        return {
            **self.adaptive_stats,
            'current_workers': self.current_workers,
            'error_rate': self._calculate_error_rate()
        }
