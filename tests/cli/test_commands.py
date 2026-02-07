"""
CLI commands 单元测试
"""
import unittest
from cli.commands import create_parser


class TestCreateParser(unittest.TestCase):
    """create_parser 测试"""

    def test_parser_has_subparsers(self):
        """解析器有子命令"""
        parser = create_parser()
        self.assertIsNotNone(parser)
        # 无子命令时应报错
        with self.assertRaises(SystemExit):
            parser.parse_args([])

    def test_parse_crawl_command(self):
        """解析 crawl 子命令"""
        parser = create_parser()
        args = parser.parse_args(["crawl", "--config", "xindong"])
        self.assertEqual(args.command, "crawl")
        self.assertEqual(args.config, "xindong")

    def test_parse_crawl_bbs_command(self):
        """解析 crawl-bbs 子命令"""
        parser = create_parser()
        args = parser.parse_args([
            "crawl-bbs", "https://bbs.xd.com/thread/1",
            "--type", "thread", "--config", "xindong",
        ])
        self.assertEqual(args.command, "crawl-bbs")
        self.assertEqual(args.target, "https://bbs.xd.com/thread/1")
        self.assertEqual(args.type, "thread")
        self.assertEqual(args.config, "xindong")

    def test_parse_crawl_news_command(self):
        """解析 crawl-news 子命令"""
        parser = create_parser()
        args = parser.parse_args(["crawl-news", "https://sxd.xd.com/", "--download-images"])
        self.assertEqual(args.command, "crawl-news")
        self.assertEqual(args.url, "https://sxd.xd.com/")
        self.assertTrue(args.download_images)

    def test_parse_checkpoint_status_command(self):
        """解析 checkpoint-status 子命令"""
        parser = create_parser()
        args = parser.parse_args(["checkpoint-status", "--site", "sxd.xd.com", "--board", "all"])
        self.assertEqual(args.command, "checkpoint-status")
        self.assertEqual(args.site, "sxd.xd.com")
        self.assertEqual(args.board, "all")
