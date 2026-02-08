"""
检查点管理器 - 基于 Storage 实现（v2.4 整合）

进度统一存 SQLite（Storage.checkpoints 表），不再使用本地 JSON 文件。
使用前需先调用 storage.connect()。
"""
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from loguru import logger
from urllib.parse import urlparse

from core.storage import storage


class CheckpointManager:
    """
    检查点管理器（基于 Storage 实现）

    进度持久化在 Storage 的 checkpoints 表中，以 (site, board) 唯一标识。
    使用前需确保已调用 storage.connect()。
    """

    def __init__(self, site: str, board: str = "all", checkpoint_dir: Optional[Path] = None):
        """
        初始化检查点管理器

        Args:
            site: 网站域名（如 "sxd.xd.com"）
            board: 板块名称（默认 "all"）
            checkpoint_dir: 已废弃，保留参数兼容；进度现存 SQLite
        """
        parsed = urlparse(site if site.startswith("http") else f"https://{site}")
        self.site = parsed.netloc or site
        self.board = board or "all"
        self.checkpoint_file = f"SQLite:{self.site}_{self.board}"

    def save_checkpoint(
        self,
        current_page: int,
        last_thread_id: Optional[str] = None,
        last_thread_url: Optional[str] = None,
        status: str = "running",
        stats: Optional[Dict[str, Any]] = None,
        seen_article_ids: Optional[List[str]] = None,
        min_article_id: Optional[str] = None,
        max_article_id: Optional[str] = None,
    ) -> bool:
        """保存检查点（委托 Storage）"""
        try:
            checkpoint = {
                "site": self.site,
                "board": self.board,
                "current_page": current_page,
                "last_thread_id": last_thread_id,
                "last_thread_url": last_thread_url,
                "status": status,
                "last_update_time": datetime.now().isoformat(),
                "stats": stats or {},
            }
            if seen_article_ids is not None:
                checkpoint["seen_article_ids"] = seen_article_ids
            if min_article_id is not None:
                checkpoint["min_article_id"] = min_article_id
            if max_article_id is not None:
                checkpoint["max_article_id"] = max_article_id

            old = storage.load_checkpoint(self.site, self.board)
            if old:
                checkpoint["created_at"] = old.get("created_at", datetime.now().isoformat())
            else:
                checkpoint["created_at"] = datetime.now().isoformat()

            ok = storage.save_checkpoint(self.site, self.board, checkpoint)
            if ok:
                logger.debug("Checkpoint saved: page {}", current_page)
            return ok
        except Exception as e:
            logger.error("Save checkpoint failed: {}", e)
            return False

    def load_checkpoint(self, *, silent: bool = False) -> Optional[Dict[str, Any]]:
        """加载检查点（委托 Storage）。silent=True 时不打「Checkpoint loaded」日志（用于 mark_completed 等仅读取再更新）。"""
        data = storage.load_checkpoint(self.site, self.board)
        if data and not silent:
            logger.info("Checkpoint loaded: page {}", data.get("current_page", 0))
        return data

    def get_current_page(self) -> int:
        """获取当前页码"""
        data = self.load_checkpoint()
        return data.get("current_page", 1) if data else 1

    def get_last_thread_id(self) -> Optional[str]:
        """获取最后爬取的帖子 ID"""
        data = self.load_checkpoint()
        return data.get("last_thread_id") if data else None

    def mark_completed(self, final_stats: Optional[Dict[str, Any]] = None) -> bool:
        """标记任务完成"""
        data = self.load_checkpoint(silent=True)
        if not data:
            logger.warning("No checkpoint to mark completed")
            return False
        return self.save_checkpoint(
            current_page=data.get("current_page", 0),
            last_thread_id=data.get("last_thread_id"),
            last_thread_url=data.get("last_thread_url"),
            status="completed",
            stats=final_stats or data.get("stats", {}),
            seen_article_ids=data.get("seen_article_ids"),
            min_article_id=data.get("min_article_id"),
            max_article_id=data.get("max_article_id"),
        )

    def mark_error(self, error_message: str) -> bool:
        """标记任务错误"""
        data = self.load_checkpoint(silent=True)
        if not data:
            return False
        stats = data.get("stats", {})
        stats["last_error"] = error_message
        stats["error_count"] = stats.get("error_count", 0) + 1
        return self.save_checkpoint(
            current_page=data.get("current_page", 0),
            last_thread_id=data.get("last_thread_id"),
            last_thread_url=data.get("last_thread_url"),
            status="error",
            stats=stats,
            seen_article_ids=data.get("seen_article_ids"),
            min_article_id=data.get("min_article_id"),
            max_article_id=data.get("max_article_id"),
        )

    def clear_checkpoint(self) -> bool:
        """清除检查点（委托 Storage）"""
        ok = storage.delete_checkpoint(self.site, self.board)
        if ok:
            logger.info("Checkpoint cleared: {} / {}", self.site, self.board)
        return ok

    def exists(self) -> bool:
        """检查点是否存在"""
        return storage.checkpoint_exists(self.site, self.board)

    def get_status(self) -> Optional[str]:
        """获取检查点状态"""
        data = self.load_checkpoint()
        return data.get("status") if data else None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        data = self.load_checkpoint()
        return data.get("stats", {}) if data else {}

    def get_seen_article_ids(self) -> set:
        """获取已爬取的文章 ID 集合（用于动态新闻去重）"""
        data = self.load_checkpoint()
        if not data:
            return set()
        seen = data.get("seen_article_ids") or []
        return set(seen) if isinstance(seen, list) else set()

    def get_min_article_id(self) -> Optional[str]:
        """获取已爬取的最小文章 ID"""
        data = self.load_checkpoint()
        return data.get("min_article_id") if data else None

    def get_max_article_id(self) -> Optional[str]:
        """获取已爬取的最大文章 ID"""
        data = self.load_checkpoint()
        return data.get("max_article_id") if data else None


def get_checkpoint_manager(site: str, board: str = "all") -> CheckpointManager:
    """获取检查点管理器实例（便捷函数）"""
    return CheckpointManager(site, board)
