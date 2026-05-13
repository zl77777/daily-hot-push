"""RSS 源抓取"""
import asyncio
import re
from datetime import datetime, timezone

import aiohttp
import feedparser

from .base import Article, BaseFetcher
from config import RSS_SOURCES


class RSSFetcher(BaseFetcher):

    def __init__(self, sources: list[dict] | None = None):
        self.sources = sources or RSS_SOURCES

    async def fetch(self) -> list[Article]:
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_one(session, s) for s in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        articles: list[Article] = []
        for res in results:
            if isinstance(res, list):
                articles.extend(res)
        return articles

    async def _fetch_one(self, session: aiohttp.ClientSession, source: dict) -> list[Article]:
        try:
            async with session.get(source["url"], timeout=aiohttp.ClientTimeout(total=15)) as resp:
                raw = await resp.text()
        except Exception:
            return []

        feed = feedparser.parse(raw)
        articles: list[Article] = []
        for entry in feed.entries[:12]:
            title = self._clean_text(entry.get("title", ""))
            url = entry.get("link", "")
            if not title or not url:
                continue

            pub = entry.get("published", "") or entry.get("updated", "")
            try:
                pub_iso = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat() if entry.get("published_parsed") else ""
            except Exception:
                pub_iso = ""

            summary = self._clean_text(entry.get("summary", "") or entry.get("description", ""))[:300]

            articles.append(Article(
                title=title,
                url=url,
                source=source["name"],
                category=source.get("cat", "other"),
                summary=summary,
                published_at=pub_iso,
            ))

        return articles

    @staticmethod
    def _clean_text(text: str) -> str:
        """去除 HTML 标签和多余空白"""
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
