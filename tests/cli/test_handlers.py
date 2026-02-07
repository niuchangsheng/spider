"""
CLI handlers 单元测试
"""
import unittest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock

from config import config
from core.storage import storage
from cli.handlers import handle_checkpoint_status


class TestHandleCheckpointStatus(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self._orig = config.database.sqlite_path
        config.database.sqlite_path = self.db_path

    def tearDown(self):
        storage.close()
        config.database.sqlite_path = self._orig
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_no_checkpoint(self):
        args = MagicMock(site="test.com", board="b1", clear=False)
        asyncio.run(handle_checkpoint_status(args))

    def test_clear_when_none(self):
        args = MagicMock(site="test.com", board="b1", clear=True)
        asyncio.run(handle_checkpoint_status(args))

    def test_with_data(self):
        storage.connect()
        storage.save_checkpoint("test.com", "b1", {"current_page": 2, "last_thread_id": "123", "status": "running", "stats": {}})
        storage.close()
        args = MagicMock(site="test.com", board="b1", clear=False)
        asyncio.run(handle_checkpoint_status(args))

    def test_clear_existing(self):
        storage.connect()
        storage.save_checkpoint("clear.com", "b1", {"current_page": 1, "last_thread_id": "", "status": "running", "stats": {}})
        storage.close()
        args = MagicMock(site="clear.com", board="b1", clear=True)
        asyncio.run(handle_checkpoint_status(args))
