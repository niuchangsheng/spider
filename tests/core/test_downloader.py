"""
ImageDownloader 单元测试（mock aiohttp）
"""
import unittest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from core.downloader import ImageDownloader


class TestImageDownloaderGetHeaders(unittest.TestCase):
    """get_headers 测试"""

    def test_get_headers_returns_dict(self):
        """get_headers 返回包含 User-Agent 等的字典"""
        d = ImageDownloader()
        headers = d.get_headers()
        self.assertIsInstance(headers, dict)
        self.assertIn("User-Agent", headers)
        self.assertIn("Accept", headers)


class TestImageDownloaderInitSession(unittest.TestCase):
    """init_session / close 测试"""

    @patch("core.downloader.aiohttp.ClientSession")
    def test_init_session_creates_session(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session.close = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        async def run():
            d = ImageDownloader()
            await d.init_session()
            mock_session_cls.assert_called_once()
            d.session = mock_session
            await d.close()

        asyncio.run(run())


class TestImageDownloaderDownloadImage(unittest.TestCase):
    """download_image 测试（mock 响应为异步上下文管理器）"""

    @patch("core.downloader.aiohttp.ClientSession")
    def test_download_image_success_returns_result_dict(self, mock_session_cls):
        """模拟 200 响应：download_image 返回包含 success/file_size 等的结果字典"""
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        resp = MagicMock()
        resp.status = 200
        resp.read = AsyncMock(return_value=png_bytes)
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=None)
        mock_session = MagicMock()
        mock_session.get.return_value = resp

        async def run():
            d = ImageDownloader()
            d.session = mock_session
            save_path = Path("/tmp/test_dl_img.png")
            result = await d.download_image("https://example.com/img.png", save_path)
            self.assertIn("success", result)
            self.assertIn("url", result)
            if save_path.exists():
                save_path.unlink(missing_ok=True)

        asyncio.run(run())

    @patch("core.downloader.aiohttp.ClientSession")
    def test_download_image_http_error(self, mock_session_cls):
        """模拟 HTTP 非 200：记录失败"""
        resp = MagicMock()
        resp.status = 404
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=None)
        mock_session = MagicMock()
        mock_session.get.return_value = resp

        async def run():
            d = ImageDownloader()
            d.session = mock_session
            result = await d.download_image("https://example.com/404.png", Path("/tmp/none.png"))
            self.assertFalse(result.get("success"))
            self.assertIn("error", result)

        asyncio.run(run())

    @patch("core.downloader.aiohttp.ClientSession")
    def test_download_image_validation_failed(self, mock_session_cls):
        """模拟返回数据过小导致 _validate_image 失败"""
        tiny = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        resp = MagicMock()
        resp.status = 200
        resp.read = AsyncMock(return_value=tiny)
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=None)
        mock_session = MagicMock()
        mock_session.get.return_value = resp

        async def run():
            d = ImageDownloader()
            d.session = mock_session
            result = await d.download_image("https://example.com/tiny.png", Path("/tmp/tiny.png"))
            self.assertFalse(result.get("success"))
            self.assertEqual(result.get("reason"), "validation_failed")

        asyncio.run(run())

    @patch("core.downloader.aiohttp.ClientSession")
    def test_download_image_exception(self, mock_session_cls):
        """模拟请求抛异常"""
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("network error")

        async def run():
            d = ImageDownloader()
            d.session = mock_session
            result = await d.download_image("https://example.com/x.png", Path("/tmp/x.png"))
            self.assertFalse(result.get("success"))
            self.assertIn("error", result)

        asyncio.run(run())


class TestImageDownloaderBatchAndStats(unittest.TestCase):
    """download_batch / get_stats 测试"""

    def test_get_stats(self):
        d = ImageDownloader()
        stats = d.get_stats()
        self.assertIn("total", stats)
        self.assertIn("success", stats)
        self.assertIn("failed", stats)
        self.assertIn("skipped", stats)

    @patch("core.downloader.aiohttp.ClientSession")
    def test_download_batch_empty(self, mock_session_cls):
        async def run():
            d = ImageDownloader()
            d.session = MagicMock()
            results = await d.download_batch([], Path("/tmp/out"))
            self.assertEqual(results, [])

        asyncio.run(run())

    @patch("core.downloader.aiohttp.ClientSession")
    def test_download_batch_one_url(self, mock_session_cls):
        """download_batch 单 URL 调用路径（可能因校验失败返回空列表）"""
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        resp = MagicMock()
        resp.status = 200
        resp.read = AsyncMock(return_value=png_bytes)
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=None)
        mock_session = MagicMock()
        mock_session.get.return_value = resp

        async def run():
            d = ImageDownloader()
            d.session = mock_session
            save_dir = Path("/tmp/coverage_batch_out")
            save_dir.mkdir(parents=True, exist_ok=True)
            try:
                results = await d.download_batch(
                    ["https://example.com/one.png"],
                    save_dir,
                    metadata={"board": "b1", "thread_id": "t1"},
                )
                self.assertIsInstance(results, list)
            finally:
                for f in save_dir.glob("*"):
                    f.unlink(missing_ok=True)
                if save_dir.exists():
                    save_dir.rmdir()

        asyncio.run(run())

    @patch("core.downloader.aiohttp.ClientSession")
    def test_download_batch_two_urls_hits_delay_path(self, mock_session_cls):
        """download_batch 多 URL 时走 delay 与 gather 路径"""
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        resp = MagicMock()
        resp.status = 200
        resp.read = AsyncMock(return_value=png_bytes)
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=None)
        mock_session = MagicMock()
        mock_session.get.return_value = resp

        async def run():
            d = ImageDownloader()
            d.session = mock_session
            save_dir = Path("/tmp/coverage_batch_two")
            save_dir.mkdir(parents=True, exist_ok=True)
            try:
                results = await d.download_batch(
                    ["https://example.com/a.png", "https://example.com/b.png"],
                    save_dir,
                    metadata=None,
                )
                self.assertIsInstance(results, list)
                self.assertEqual(len(results), 2)
            finally:
                for f in save_dir.glob("*"):
                    f.unlink(missing_ok=True)
                if save_dir.exists():
                    save_dir.rmdir()

        asyncio.run(run())


class TestImageDownloaderContextManager(unittest.TestCase):
    """__aenter__ / __aexit__ 测试"""

    @patch("core.downloader.aiohttp.ClientSession")
    def test_async_context_manager(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session.close = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        async def run():
            async with ImageDownloader() as d:
                self.assertIsNotNone(d.session)
            mock_session.close.assert_called_once()

        asyncio.run(run())


class TestImageDownloaderGenerateFilename(unittest.TestCase):
    """_generate_filename 覆盖 ext/convert_to_jpg/metadata 分支"""

    def test_generate_filename_ext_not_allowed_uses_jpg(self):
        """URL 扩展名不在 allowed_formats 时用 jpg"""
        d = ImageDownloader()
        name = d._generate_filename("https://example.com/photo.xyz", 1, {"board": "b1", "thread_id": "t1"})
        self.assertIn(".jpg", name)
        self.assertIn("b1", name)
        self.assertIn("t1", name)

    def test_generate_filename_no_metadata(self):
        """无 metadata 时使用 image_xxx 格式"""
        d = ImageDownloader()
        name = d._generate_filename("https://example.com/a.png", 1, None)
        self.assertIn("image_", name)
        self.assertIn(".png", name)
