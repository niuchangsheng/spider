"""
图片去重模块
"""
from typing import Set, Optional
from pathlib import Path
import hashlib
from loguru import logger
from PIL import Image
import imagehash

from config import config


class ImageDeduplicator:
    """图片去重器"""
    
    def __init__(self, use_perceptual_hash: bool = True):
        """
        初始化去重器
        
        Args:
            use_perceptual_hash: 是否使用感知哈希（用于检测相似图片）
        """
        self.use_perceptual_hash = use_perceptual_hash
        self.url_hashes: Set[str] = set()  # URL哈希集合
        self.file_hashes: Set[str] = set()  # 文件内容哈希集合
        self.perceptual_hashes: Set[str] = set()  # 感知哈希集合
        self.stats = {
            "total_checked": 0,
            "duplicates_found": 0,
            "unique_images": 0
        }
    
    def is_duplicate_url(self, url: str) -> bool:
        """
        检查URL是否重复
        
        Args:
            url: 图片URL
        
        Returns:
            是否重复
        """
        self.stats["total_checked"] += 1
        url_hash = self._hash_string(url)
        
        if url_hash in self.url_hashes:
            self.stats["duplicates_found"] += 1
            logger.debug(f"Duplicate URL found: {url}")
            return True
        
        self.url_hashes.add(url_hash)
        self.stats["unique_images"] += 1
        return False
    
    def is_duplicate_file(self, file_path: Path) -> bool:
        """
        检查文件内容是否重复
        
        Args:
            file_path: 文件路径
        
        Returns:
            是否重复
        """
        try:
            # 计算文件MD5哈希
            file_hash = self._hash_file(file_path)
            
            if file_hash in self.file_hashes:
                logger.debug(f"Duplicate file found: {file_path.name}")
                return True
            
            self.file_hashes.add(file_hash)
            
            # 如果启用感知哈希，还要检查相似图片
            if self.use_perceptual_hash:
                return self._check_perceptual_duplicate(file_path)
            
            return False
        
        except Exception as e:
            logger.warning(f"Failed to check duplicate for {file_path}: {e}")
            return False
    
    def _check_perceptual_duplicate(self, file_path: Path) -> bool:
        """检查感知哈希重复（相似图片）"""
        try:
            img = Image.open(file_path)
            # 使用dHash算法
            phash = str(imagehash.dhash(img))
            
            if phash in self.perceptual_hashes:
                logger.debug(f"Perceptually similar image found: {file_path.name}")
                return True
            
            self.perceptual_hashes.add(phash)
            return False
        
        except Exception as e:
            logger.warning(f"Failed to compute perceptual hash for {file_path}: {e}")
            return False
    
    def _hash_string(self, text: str) -> str:
        """计算字符串哈希"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _hash_file(self, file_path: Path) -> str:
        """计算文件哈希"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def remove_duplicate_file(self, file_path: Path) -> bool:
        """删除重复文件"""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Removed duplicate file: {file_path.name}")
                return True
        except Exception as e:
            logger.error(f"Failed to remove duplicate file {file_path}: {e}")
        return False
    
    def load_existing_hashes(self, directory: Path):
        """加载已存在的文件哈希（用于恢复去重状态）"""
        if not directory.exists():
            return
        
        logger.info(f"Loading existing hashes from {directory}")
        count = 0
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                try:
                    # 添加文件哈希
                    file_hash = self._hash_file(file_path)
                    self.file_hashes.add(file_hash)
                    
                    # 添加感知哈希
                    if self.use_perceptual_hash:
                        img = Image.open(file_path)
                        phash = str(imagehash.dhash(img))
                        self.perceptual_hashes.add(phash)
                    
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to load hash for {file_path}: {e}")
        
        logger.info(f"Loaded {count} existing file hashes")
    
    def get_stats(self) -> dict:
        """获取去重统计"""
        stats = self.stats.copy()
        if stats["total_checked"] > 0:
            stats["duplicate_rate"] = stats["duplicates_found"] / stats["total_checked"]
        else:
            stats["duplicate_rate"] = 0.0
        return stats
    
    def clear(self):
        """清空去重记录"""
        self.url_hashes.clear()
        self.file_hashes.clear()
        self.perceptual_hashes.clear()
        self.stats = {
            "total_checked": 0,
            "duplicates_found": 0,
            "unique_images": 0
        }
        logger.info("Deduplicator cleared")
