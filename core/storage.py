"""
数据存储模块（v2.4：SQLite + 内存结构）

定位（见 ARCHITECTURE.md 2.3 / docs/designs/2026-02-07-storage-checkpoint-queue-positioning.md）：
- 爬取结果持久化（threads / images）及基于其的统计。
- 进度持久化（checkpoints 表），供 CheckpointManager 基于 Storage 实现。
- 不负责任务队列（由 CrawlQueue 负责）。
"""
from typing import Dict, Any, List, Optional
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from collections import deque
from threading import Lock
from loguru import logger

from config import config


def _serialize(obj: Any) -> str:
    """序列化为 JSON 字符串"""
    if obj is None:
        return "null"
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, ensure_ascii=False)
    return str(obj)


def _deserialize_json(s: Optional[str]) -> Any:
    """从 JSON 字符串反序列化"""
    if s is None or s == "null":
        return None
    try:
        return json.loads(s)
    except (TypeError, json.JSONDecodeError):
        return None


class Storage:
    """数据存储管理器（SQLite 持久化 + 可选内存 Set）"""

    def __init__(self):
        self.db_config = config.database
        self._conn: Optional[sqlite3.Connection] = None
        self._visited_urls: set = set()
        self._memory_queues: Dict[str, deque] = {}
        self._queue_lock = Lock()

    def connect(self):
        """连接数据库（创建 SQLite 文件及表结构）"""
        path = Path(self.db_config.sqlite_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._conn = sqlite3.connect(str(path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
            logger.success("Connected to SQLite: {}", path)
        except sqlite3.Error as e:
            logger.error("Failed to connect to SQLite: {}", e)
            self._conn = None

    def _init_schema(self):
        """初始化表结构"""
        if self._conn is None:
            return
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT UNIQUE NOT NULL,
                title TEXT,
                url TEXT,
                board TEXT,
                images TEXT,
                image_count INTEGER,
                metadata TEXT,
                content TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_threads_board ON threads(board);
            CREATE INDEX IF NOT EXISTS idx_threads_thread_id ON threads(thread_id);

            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                save_path TEXT,
                file_size INTEGER,
                success INTEGER,
                metadata TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS checkpoints (
                site TEXT NOT NULL,
                board TEXT NOT NULL,
                current_page INTEGER DEFAULT 1,
                last_thread_id TEXT,
                last_thread_url TEXT,
                status TEXT DEFAULT 'running',
                stats TEXT,
                seen_article_ids TEXT,
                min_article_id TEXT,
                max_article_id TEXT,
                created_at TEXT,
                updated_at TEXT,
                PRIMARY KEY (site, board)
            );

            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id TEXT UNIQUE NOT NULL,
                url TEXT,
                title TEXT,
                site TEXT,
                board TEXT,
                metadata TEXT,
                created_at TEXT,
                images_downloaded INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_articles_article_id ON articles(article_id);
        """)
        self._conn.commit()
        try:
            self._conn.execute(
                "ALTER TABLE articles ADD COLUMN images_downloaded INTEGER DEFAULT 0"
            )
            self._conn.commit()
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("SQLite connection closed")
        self._visited_urls.clear()
        with self._queue_lock:
            self._memory_queues.clear()

    # ==================== SQLite 持久化（threads / images） ====================

    def save_thread(self, thread_data: Dict[str, Any]) -> bool:
        """保存帖子数据"""
        if self._conn is None:
            logger.warning("SQLite not connected")
            return False
        try:
            now = datetime.now().isoformat()
            thread_id = thread_data.get("thread_id")
            images_json = _serialize(thread_data.get("images"))
            metadata_json = _serialize(thread_data.get("metadata"))
            created = thread_data.get("created_at")
            if isinstance(created, datetime):
                created = created.isoformat()
            elif not created:
                created = now
            else:
                created = str(created)
            self._conn.execute(
                """
                INSERT INTO threads (thread_id, title, url, board, images, image_count, metadata, content, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET
                    title=excluded.title, url=excluded.url, board=excluded.board,
                    images=excluded.images, image_count=excluded.image_count,
                    metadata=excluded.metadata, content=excluded.content,
                    updated_at=excluded.updated_at
                """,
                (
                    thread_id,
                    thread_data.get("title"),
                    thread_data.get("url"),
                    thread_data.get("board"),
                    images_json,
                    thread_data.get("image_count", 0) or len(thread_data.get("images") or []),
                    metadata_json,
                    thread_data.get("content"),
                    created,
                    now,
                ),
            )
            self._conn.commit()
            logger.info("Saved thread: {}", thread_id)
            return True
        except sqlite3.Error as e:
            logger.error("Failed to save thread: {}", e)
            return False

    def save_image_record(self, image_data: Dict[str, Any]) -> bool:
        """保存图片记录"""
        if self._conn is None:
            logger.warning("SQLite not connected")
            return False
        try:
            now = datetime.now().isoformat()
            created = image_data.get("created_at")
            if isinstance(created, datetime):
                created = created.isoformat()
            elif created is None:
                created = now
            else:
                created = str(created)
            save_path = image_data.get("save_path")
            if save_path is not None and not isinstance(save_path, str):
                save_path = str(save_path)
            self._conn.execute(
                """
                INSERT INTO images (url, save_path, file_size, success, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    image_data.get("url"),
                    save_path,
                    image_data.get("file_size", 0),
                    1 if image_data.get("success", True) else 0,
                    _serialize(image_data.get("metadata")),
                    created,
                ),
            )
            self._conn.commit()
            logger.debug("Saved image record: {}", image_data.get("url"))
            return True
        except sqlite3.Error as e:
            logger.error("Failed to save image record: {}", e)
            return False

    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """获取帖子数据"""
        if self._conn is None:
            return None
        try:
            row = self._conn.execute("SELECT * FROM threads WHERE thread_id = ?", (thread_id,)).fetchone()
            return self._row_to_thread(row) if row else None
        except sqlite3.Error as e:
            logger.error("Failed to get thread: {}", e)
            return None

    def thread_exists(self, thread_id: str) -> bool:
        """检查帖子是否已存在（权威去重依据）"""
        if self._conn is None:
            return False
        try:
            cur = self._conn.execute("SELECT 1 FROM threads WHERE thread_id = ? LIMIT 1", (thread_id,))
            return cur.fetchone() is not None
        except sqlite3.Error as e:
            logger.error("Failed to check thread existence: {}", e)
            return False

    def get_all_threads(self, board: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有帖子"""
        if self._conn is None:
            return []
        try:
            if board:
                rows = self._conn.execute("SELECT * FROM threads WHERE board = ?", (board,)).fetchall()
            else:
                rows = self._conn.execute("SELECT * FROM threads").fetchall()
            return [self._row_to_thread(row) for row in rows]
        except sqlite3.Error as e:
            logger.error("Failed to get threads: {}", e)
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if self._conn is None:
            return {}
        try:
            stats = {
                "total_threads": self._conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0],
                "total_images": self._conn.execute("SELECT COUNT(*) FROM images").fetchone()[0],
                "successful_downloads": self._conn.execute("SELECT COUNT(*) FROM images WHERE success = 1").fetchone()[0],
                "failed_downloads": self._conn.execute("SELECT COUNT(*) FROM images WHERE success = 0").fetchone()[0],
            }
            rows = self._conn.execute(
                "SELECT board, COUNT(*) as cnt FROM threads WHERE board IS NOT NULL AND board != '' GROUP BY board"
            ).fetchall()
            stats["boards"] = {row[0]: row[1] for row in rows}
            return stats
        except sqlite3.Error as e:
            logger.error("Failed to get statistics: {}", e)
            return {}

    def _row_to_thread(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将 SQLite Row 转为 thread 字典"""
        return {
            "thread_id": row["thread_id"],
            "title": row["title"],
            "url": row["url"],
            "board": row["board"],
            "images": _deserialize_json(row["images"]),
            "image_count": row["image_count"],
            "metadata": _deserialize_json(row["metadata"]),
            "content": row["content"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ==================== 文章（动态新闻，与 thread_exists 对称） ====================

    def article_exists(self, article_id: str) -> bool:
        """检查文章是否已爬过且已下载图片（未下载图片不算爬过）"""
        if self._conn is None:
            return False
        try:
            cur = self._conn.execute(
                "SELECT 1 FROM articles WHERE article_id = ? AND COALESCE(images_downloaded, 1) = 1 LIMIT 1",
                (article_id,),
            )
            return cur.fetchone() is not None
        except sqlite3.Error as e:
            logger.error("Failed to check article existence: {}", e)
            return False

    def save_article(self, article_data: Dict[str, Any]) -> bool:
        """保存文章记录（与 save_thread 对称，用于动态新闻）"""
        if self._conn is None:
            logger.warning("SQLite not connected")
            return False
        try:
            now = datetime.now().isoformat()
            article_id = article_data.get("article_id")
            created = article_data.get("created_at")
            if isinstance(created, datetime):
                created = created.isoformat()
            elif not created:
                created = now
            else:
                created = str(created)
            images_downloaded = 1 if article_data.get("images_downloaded") else 0
            self._conn.execute(
                """
                INSERT INTO articles (article_id, url, title, site, board, metadata, created_at, images_downloaded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(article_id) DO UPDATE SET
                    url=excluded.url,
                    title=excluded.title,
                    site=excluded.site,
                    board=excluded.board,
                    metadata=excluded.metadata,
                    images_downloaded=excluded.images_downloaded
                """,
                (
                    article_id,
                    article_data.get("url"),
                    article_data.get("title"),
                    article_data.get("site"),
                    article_data.get("board"),
                    _serialize(article_data.get("metadata")),
                    created,
                    images_downloaded,
                ),
            )
            self._conn.commit()
            logger.debug("Saved article: {}", article_id)
            return True
        except sqlite3.Error as e:
            logger.error("Failed to save article: {}", e)
            return False

    # ==================== 检查点（供 CheckpointManager 薄封装） ====================

    def save_checkpoint(self, site: str, board: str, data: Dict[str, Any]) -> bool:
        """保存检查点（site + board 唯一）"""
        if self._conn is None:
            return False
        try:
            now = datetime.now().isoformat()
            created = data.get("created_at", now)
            self._conn.execute(
                """
                INSERT INTO checkpoints (site, board, current_page, last_thread_id, last_thread_url, status, stats,
                    seen_article_ids, min_article_id, max_article_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(site, board) DO UPDATE SET
                    current_page=excluded.current_page,
                    last_thread_id=excluded.last_thread_id,
                    last_thread_url=excluded.last_thread_url,
                    status=excluded.status,
                    stats=excluded.stats,
                    seen_article_ids=excluded.seen_article_ids,
                    min_article_id=excluded.min_article_id,
                    max_article_id=excluded.max_article_id,
                    updated_at=excluded.updated_at
                """,
                (
                    site,
                    board,
                    data.get("current_page", 1),
                    data.get("last_thread_id"),
                    data.get("last_thread_url"),
                    data.get("status", "running"),
                    _serialize(data.get("stats")),
                    _serialize(data.get("seen_article_ids")),
                    data.get("min_article_id"),
                    data.get("max_article_id"),
                    created,
                    now,
                ),
            )
            self._conn.commit()
            logger.debug("Checkpoint saved: {} / {}", site, board)
            return True
        except sqlite3.Error as e:
            logger.error("Failed to save checkpoint: {}", e)
            return False

    def load_checkpoint(self, site: str, board: str) -> Optional[Dict[str, Any]]:
        """加载检查点"""
        if self._conn is None:
            return None
        try:
            row = self._conn.execute(
                "SELECT * FROM checkpoints WHERE site = ? AND board = ?", (site, board)
            ).fetchone()
            if not row:
                return None
            return {
                "site": row["site"],
                "board": row["board"],
                "current_page": row["current_page"] or 1,
                "last_thread_id": row["last_thread_id"],
                "last_thread_url": row["last_thread_url"],
                "status": row["status"] or "running",
                "last_update_time": row["updated_at"],
                "stats": _deserialize_json(row["stats"]) or {},
                "seen_article_ids": _deserialize_json(row["seen_article_ids"]),
                "min_article_id": row["min_article_id"],
                "max_article_id": row["max_article_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        except sqlite3.Error as e:
            logger.error("Failed to load checkpoint: {}", e)
            return None

    def delete_checkpoint(self, site: str, board: str) -> bool:
        """删除检查点"""
        if self._conn is None:
            return False
        try:
            self._conn.execute("DELETE FROM checkpoints WHERE site = ? AND board = ?", (site, board))
            self._conn.commit()
            logger.info("Checkpoint deleted: {} / {}", site, board)
            return True
        except sqlite3.Error as e:
            logger.error("Failed to delete checkpoint: {}", e)
            return False

    def checkpoint_exists(self, site: str, board: str) -> bool:
        """检查点是否存在"""
        if self._conn is None:
            return False
        try:
            row = self._conn.execute(
                "SELECT 1 FROM checkpoints WHERE site = ? AND board = ? LIMIT 1", (site, board)
            ).fetchone()
            return row is not None
        except sqlite3.Error as e:
            logger.error("Failed to check checkpoint existence: {}", e)
            return False

    # ==================== 内存结构（仅本次运行，非持久化） ====================

    def is_url_visited(self, url: str) -> bool:
        """检查 URL 是否已访问（仅本次运行）"""
        return url in self._visited_urls

    def mark_url_visited(self, url: str) -> bool:
        """标记 URL 已访问（仅本次运行）"""
        self._visited_urls.add(url)
        return True

    def add_to_queue(self, queue_name: str, item: Any) -> bool:
        """添加到队列（兼容保留，仅内存、仅本次运行）"""
        with self._queue_lock:
            if queue_name not in self._memory_queues:
                self._memory_queues[queue_name] = deque()
            q = self._memory_queues[queue_name]
        try:
            q.append(item if not isinstance(item, dict) else json.dumps(item, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error("Failed to add to queue: {}", e)
            return False

    def get_from_queue(self, queue_name: str, timeout: int = 0) -> Optional[Any]:
        """从队列获取（兼容保留，仅内存；timeout 在此实现中忽略）"""
        with self._queue_lock:
            q = self._memory_queues.get(queue_name)
        if not q:
            return None
        try:
            val = q.popleft() if q else None
            if val is None:
                return None
            try:
                return json.loads(val)
            except (TypeError, json.JSONDecodeError):
                return val
        except IndexError:
            return None

    def get_queue_size(self, queue_name: str) -> int:
        """获取队列大小（兼容保留）"""
        with self._queue_lock:
            q = self._memory_queues.get(queue_name)
        return len(q) if q else 0

    def clear_queue(self, queue_name: str) -> bool:
        """清空队列（兼容保留）"""
        with self._queue_lock:
            if queue_name in self._memory_queues:
                self._memory_queues[queue_name].clear()
        return True


# 全局存储实例
storage = Storage()
