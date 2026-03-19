"""兜底爬虫，使用 gallery-dl 命令行工具。"""

import asyncio
import json

from app.crawlers.base import BaseCrawler, CrawlResult


class GalleryDLCrawler(BaseCrawler):
    """通用爬虫，使用 gallery-dl 作为后端。用于不支持的平台的兜底方案。"""

    def match(self, url: str) -> bool:
        # 兜底 — 始终匹配
        return True

    async def fetch(self, url: str) -> CrawlResult:
        try:
            proc = await asyncio.create_subprocess_exec(
                "gallery-dl",
                "--dump-json",
                "--no-download",
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return CrawlResult(success=False, error=stderr.decode().strip())

            entries = [json.loads(line) for line in stdout.decode().splitlines() if line.strip()]
            if not entries:
                return CrawlResult(success=False, error="gallery-dl 未返回任何结果")

            # gallery-dl 的 JSON 输出因提取器而异；提取通用字段
            image_urls: list[str] = []
            first = entries[0]
            metadata = first[1] if len(first) > 1 and isinstance(first[1], dict) else {}

            for entry in entries:
                if isinstance(entry, list) and len(entry) >= 3:
                    # 格式: [directory, metadata_dict, url]
                    image_urls.append(str(entry[2]) if len(entry) > 2 else "")

            return CrawlResult(
                success=True,
                platform=metadata.get("category", "unknown"),
                pid=str(metadata.get("id", "")),
                title=metadata.get("title", ""),
                author=metadata.get("author", metadata.get("user", "")),
                source_url=url,
                image_urls=image_urls,
                raw_info=metadata,
            )
        except FileNotFoundError:
            return CrawlResult(success=False, error="gallery-dl 未安装")
        except Exception as e:
            return CrawlResult(success=False, error=str(e))
