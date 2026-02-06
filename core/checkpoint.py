"""
检查点管理器 - 本地文件存储

用于保存和恢复爬取进度，支持断点续传。
"""
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json
from loguru import logger
from urllib.parse import urlparse


class CheckpointManager:
    """
    检查点管理器（本地文件存储）
    
    检查点文件格式: checkpoints/{site}_{board}.json
    例如: checkpoints/sxd.xd.com_all.json
    """
    
    def __init__(self, site: str, board: str = "all", checkpoint_dir: Optional[Path] = None):
        """
        初始化检查点管理器
        
        Args:
            site: 网站域名（如 "sxd.xd.com"）
            board: 板块名称（默认 "all"）
            checkpoint_dir: 检查点目录（默认项目根目录/checkpoints）
        """
        # 规范化site（提取域名）
        parsed = urlparse(site if site.startswith('http') else f'https://{site}')
        self.site = parsed.netloc or site
        
        self.board = board or "all"
        
        # 检查点目录
        if checkpoint_dir is None:
            checkpoint_dir = Path(__file__).parent.parent / "checkpoints"
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查点文件路径
        safe_site = self.site.replace('.', '_').replace('/', '_')
        safe_board = self.board.replace('/', '_').replace('\\', '_')
        self.checkpoint_file = self.checkpoint_dir / f"{safe_site}_{safe_board}.json"
        
        logger.debug(f"📁 检查点文件: {self.checkpoint_file}")
    
    def save_checkpoint(
        self,
        current_page: int,
        last_thread_id: Optional[str] = None,
        last_thread_url: Optional[str] = None,
        status: str = "running",
        stats: Optional[Dict[str, Any]] = None,
        seen_article_ids: Optional[List[str]] = None,
        min_article_id: Optional[str] = None,
        max_article_id: Optional[str] = None
    ) -> bool:
        """
        保存检查点
        
        Args:
            current_page: 当前页码
            last_thread_id: 最后爬取的帖子ID
            last_thread_url: 最后爬取的帖子URL
            status: 状态 (running/paused/completed/error)
            stats: 统计信息字典
            seen_article_ids: 已爬取的文章ID列表（用于动态新闻去重）
            min_article_id: 已爬取的最小文章ID（用于倒序排列）
            max_article_id: 已爬取的最大文章ID（用于正序排列）
        
        Returns:
            是否保存成功
        """
        try:
            checkpoint = {
                "site": self.site,
                "board": self.board,
                "current_page": current_page,
                "last_thread_id": last_thread_id,
                "last_thread_url": last_thread_url,
                "status": status,
                "last_update_time": datetime.now().isoformat(),
                "stats": stats or {}
            }
            
            # 添加 article_id 相关字段（用于动态新闻）
            if seen_article_ids is not None:
                checkpoint["seen_article_ids"] = seen_article_ids
            if min_article_id is not None:
                checkpoint["min_article_id"] = min_article_id
            if max_article_id is not None:
                checkpoint["max_article_id"] = max_article_id
            
            # 如果存在旧检查点，保留创建时间
            old_checkpoint = self.load_checkpoint()
            if old_checkpoint:
                checkpoint["created_at"] = old_checkpoint.get("created_at", datetime.now().isoformat())
            else:
                checkpoint["created_at"] = datetime.now().isoformat()
            
            # 保存到文件
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"💾 检查点已保存: 第 {current_page} 页")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存检查点失败: {e}")
            return False
    
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        加载检查点
        
        Returns:
            检查点字典，如果不存在返回 None
        """
        if not self.checkpoint_file.exists():
            return None
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            
            logger.info(f"📂 加载检查点: 第 {checkpoint.get('current_page', 0)} 页")
            return checkpoint
            
        except Exception as e:
            logger.error(f"❌ 加载检查点失败: {e}")
            return None
    
    def get_current_page(self) -> int:
        """
        获取当前页码
        
        Returns:
            当前页码，如果不存在返回 1
        """
        checkpoint = self.load_checkpoint()
        if checkpoint:
            return checkpoint.get('current_page', 1)
        return 1
    
    def get_last_thread_id(self) -> Optional[str]:
        """获取最后爬取的帖子ID"""
        checkpoint = self.load_checkpoint()
        if checkpoint:
            return checkpoint.get('last_thread_id')
        return None
    
    def mark_completed(self, final_stats: Optional[Dict[str, Any]] = None) -> bool:
        """
        标记任务完成
        
        Args:
            final_stats: 最终统计信息
        
        Returns:
            是否保存成功
        """
        checkpoint = self.load_checkpoint()
        if not checkpoint:
            logger.warning("⚠️  没有检查点可标记为完成")
            return False
        
        return self.save_checkpoint(
            current_page=checkpoint.get('current_page', 0),
            last_thread_id=checkpoint.get('last_thread_id'),
            last_thread_url=checkpoint.get('last_thread_url'),
            status="completed",
            stats=final_stats or checkpoint.get('stats', {}),
            seen_article_ids=checkpoint.get('seen_article_ids'),
            min_article_id=checkpoint.get('min_article_id'),
            max_article_id=checkpoint.get('max_article_id')
        )
    
    def mark_error(self, error_message: str) -> bool:
        """
        标记任务错误
        
        Args:
            error_message: 错误信息
        
        Returns:
            是否保存成功
        """
        checkpoint = self.load_checkpoint()
        if not checkpoint:
            return False
        
        stats = checkpoint.get('stats', {})
        stats['last_error'] = error_message
        stats['error_count'] = stats.get('error_count', 0) + 1
        
        return self.save_checkpoint(
            current_page=checkpoint.get('current_page', 0),
            last_thread_id=checkpoint.get('last_thread_id'),
            last_thread_url=checkpoint.get('last_thread_url'),
            status="error",
            stats=stats,
            seen_article_ids=checkpoint.get('seen_article_ids'),
            min_article_id=checkpoint.get('min_article_id'),
            max_article_id=checkpoint.get('max_article_id')
        )
    
    def clear_checkpoint(self) -> bool:
        """
        清除检查点
        
        Returns:
            是否清除成功
        """
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                logger.info(f"🗑️  检查点已清除: {self.checkpoint_file}")
            return True
        except Exception as e:
            logger.error(f"❌ 清除检查点失败: {e}")
            return False
    
    def exists(self) -> bool:
        """检查检查点是否存在"""
        return self.checkpoint_file.exists()
    
    def get_status(self) -> Optional[str]:
        """获取检查点状态"""
        checkpoint = self.load_checkpoint()
        if checkpoint:
            return checkpoint.get('status')
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        checkpoint = self.load_checkpoint()
        if checkpoint:
            return checkpoint.get('stats', {})
        return {}
    
    def get_seen_article_ids(self) -> set:
        """
        获取已爬取的文章ID集合（用于动态新闻去重）
        
        Returns:
            文章ID集合
        """
        checkpoint = self.load_checkpoint()
        if checkpoint:
            seen_ids = checkpoint.get('seen_article_ids', [])
            return set(seen_ids)
        return set()
    
    def get_min_article_id(self) -> Optional[str]:
        """获取已爬取的最小文章ID（用于倒序排列）"""
        checkpoint = self.load_checkpoint()
        if checkpoint:
            return checkpoint.get('min_article_id')
        return None
    
    def get_max_article_id(self) -> Optional[str]:
        """获取已爬取的最大文章ID（用于正序排列）"""
        checkpoint = self.load_checkpoint()
        if checkpoint:
            return checkpoint.get('max_article_id')
        return None


def get_checkpoint_manager(site: str, board: str = "all") -> CheckpointManager:
    """
    获取检查点管理器实例（便捷函数）
    
    Args:
        site: 网站URL或域名
        board: 板块名称
    
    Returns:
        CheckpointManager 实例
    """
    return CheckpointManager(site, board)
