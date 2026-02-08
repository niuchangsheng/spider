"""
CrawlQueue 单元测试
"""
import unittest
import asyncio
from core.crawl_queue import CrawlQueue, AdaptiveCrawlQueue


class TestCrawlQueue(unittest.TestCase):
    """CrawlQueue 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.queue = CrawlQueue(max_workers=3, queue_size=10, timeout=0.5)
    
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.queue.max_workers, 3)
        self.assertEqual(self.queue.queue.maxsize, 10)  # queue_size 存储在 queue.maxsize 中
        self.assertEqual(self.queue.timeout, 0.5)
        self.assertEqual(self.queue.stats['total_tasks'], 0)
    
    async def async_test_producer(self):
        """测试生产者"""
        items = [1, 2, 3, 4, 5]
        await self.queue.producer(items)
        
        self.assertEqual(self.queue.stats['total_tasks'], 5)
        self.assertEqual(self.queue.queue.qsize(), 5)
    
    def test_producer(self):
        """同步测试生产者"""
        asyncio.run(self.async_test_producer())
    
    async def async_test_consumer(self):
        """测试消费者"""
        results = []
        
        async def worker_func(item):
            results.append(item)
            await asyncio.sleep(0.01)
        
        # 添加任务
        await self.queue.queue.put(1)
        await self.queue.queue.put(2)
        await self.queue.queue.put(3)
        
        # 运行消费者
        await self.queue.consumer(worker_func, worker_id=0)
        
        # 等待一下确保处理完成
        await asyncio.sleep(0.1)
        
        self.assertEqual(len(results), 3)
        self.assertIn(1, results)
        self.assertIn(2, results)
        self.assertIn(3, results)
    
    def test_consumer(self):
        """同步测试消费者"""
        asyncio.run(self.async_test_consumer())
    
    async def async_test_run(self):
        """测试运行队列"""
        results = []
        
        async def worker_func(item):
            results.append(item)
            await asyncio.sleep(0.01)
        
        items = [1, 2, 3, 4, 5]
        stats = await self.queue.run(items, worker_func)
        
        self.assertEqual(len(results), 5)
        self.assertEqual(stats['completed_tasks'], 5)
        self.assertEqual(stats['failed_tasks'], 0)
    
    def test_run(self):
        """同步测试运行队列"""
        asyncio.run(self.async_test_run())
    
    async def async_test_error_handling(self):
        """测试错误处理"""
        async def failing_worker(item):
            if item == 3:
                raise ValueError(f"Error processing {item}")
            await asyncio.sleep(0.01)
        
        items = [1, 2, 3, 4, 5]
        stats = await self.queue.run(items, failing_worker)
        
        # 应该有4个成功，1个失败
        self.assertEqual(stats['completed_tasks'], 4)
        self.assertEqual(stats['failed_tasks'], 1)
        self.assertEqual(len(self.queue.errors), 1)
    
    def test_error_handling(self):
        """同步测试错误处理"""
        asyncio.run(self.async_test_error_handling())
    
    def test_get_stats(self):
        """测试获取统计信息"""
        stats = self.queue.get_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('total_tasks', stats)
        self.assertIn('completed_tasks', stats)
        self.assertIn('failed_tasks', stats)


class TestAdaptiveCrawlQueue(unittest.TestCase):
    """AdaptiveCrawlQueue 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.queue = AdaptiveCrawlQueue(
            initial_workers=5,
            max_workers=10,
            min_workers=1,
            error_threshold=0.1
        )
    
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.queue.initial_workers, 5)
        self.assertEqual(self.queue.max_workers, 10)
        self.assertEqual(self.queue.min_workers, 1)
        self.assertEqual(self.queue.current_workers, 5)
        self.assertEqual(self.queue.error_threshold, 0.1)
    
    def test_calculate_error_rate(self):
        """测试计算错误率"""
        self.queue.stats['completed_tasks'] = 8
        self.queue.stats['failed_tasks'] = 2
        
        error_rate = self.queue._calculate_error_rate()
        self.assertEqual(error_rate, 0.2)  # 2/10 = 0.2
    
    def test_adjust_workers_high_error(self):
        """测试高错误率时降低并发"""
        self.queue.stats['completed_tasks'] = 5
        self.queue.stats['failed_tasks'] = 10  # 错误率 66%
        self.queue.current_workers = 10
        
        old_workers = self.queue.current_workers
        self.queue._adjust_workers()
        
        # 应该降低并发
        self.assertLess(self.queue.current_workers, old_workers)
        self.assertGreaterEqual(self.queue.current_workers, self.queue.min_workers)
    
    def test_adjust_workers_low_error(self):
        """测试低错误率时提高并发"""
        self.queue.stats['completed_tasks'] = 100
        self.queue.stats['failed_tasks'] = 0  # 错误率 0%
        self.queue.current_workers = 5
        
        old_workers = self.queue.current_workers
        self.queue._adjust_workers()
        
        # 应该提高并发（如果还没达到最大值）
        if old_workers < self.queue.max_workers:
            self.assertGreaterEqual(self.queue.current_workers, old_workers)
    
    def test_get_adaptive_stats(self):
        """测试获取自适应统计信息"""
        stats = self.queue.get_adaptive_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('current_workers', stats)
        self.assertIn('error_rate', stats)
        self.assertIn('adjustments', stats)

    async def async_test_adaptive_run(self):
        """AdaptiveCrawlQueue.run 覆盖父类 run 及调整逻辑"""
        results = []
        async def worker_func(item):
            results.append(item)
            await asyncio.sleep(0.01)
        items = [1, 2, 3]
        stats = await self.queue.run(items, worker_func, show_progress=False)
        self.assertEqual(stats['completed_tasks'], 3)
        self.assertEqual(len(results), 3)

    def test_adaptive_run(self):
        asyncio.run(self.async_test_adaptive_run())


if __name__ == '__main__':
    unittest.main()
