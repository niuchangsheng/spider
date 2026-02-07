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
