"""Fallback crawler using gallery-dl CLI tool."""

import asyncio
import json

from app.crawlers.base import BaseCrawler, CrawlResult


class GalleryDLCrawler(BaseCrawler):
    """Generic crawler using gallery-dl as backend. Used as fallback for unsupported platforms."""

    def match(self, url: str) -> bool:
        # Fallback — always matches
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
                return CrawlResult(success=False, error="No results from gallery-dl")

            # gallery-dl JSON output varies by extractor; extract common fields
            image_urls: list[str] = []
            first = entries[0]
            metadata = first[1] if len(first) > 1 and isinstance(first[1], dict) else {}

            for entry in entries:
                if isinstance(entry, list) and len(entry) >= 3:
                    # Format: [directory, metadata_dict, url]
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
            return CrawlResult(success=False, error="gallery-dl is not installed")
        except Exception as e:
            return CrawlResult(success=False, error=str(e))
