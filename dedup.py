"""去重 + 历史记录管理"""
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta

from config import DB_PATH
from fetchers.base import Article


class DedupManager:
    """基于 SQLite 的 URL 去重，防止同一条新闻重复推送"""

    def __init__(self, db_path: str = DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_table()

    def _init_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS pushed_urls (
                url_hash TEXT PRIMARY KEY,
                title    TEXT,
                source   TEXT,
                pushed_at TEXT
            )
        """)
        self.conn.commit()

    def is_new(self, article: Article) -> bool:
        h = self._hash(article.url)
        row = self.conn.execute("SELECT 1 FROM pushed_urls WHERE url_hash = ?", (h,)).fetchone()
        return row is None

    def filter_new(self, articles: list[Article]) -> list[Article]:
        """过滤掉已推送过的文章"""
        return [a for a in articles if self.is_new(a)]

    def mark_pushed(self, articles: list[Article]):
        now = datetime.now().isoformat()
        rows = [
            (self._hash(a.url), a.title, a.source, now)
            for a in articles
        ]
        self.conn.executemany(
            "INSERT OR IGNORE INTO pushed_urls VALUES (?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()

    def clean_old(self, days: int = 14):
        """定期清理 14 天前的记录，防止 DB 无限膨胀"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        self.conn.execute("DELETE FROM pushed_urls WHERE pushed_at < ?", (cutoff,))
        self.conn.commit()

    @staticmethod
    def _hash(url: str) -> str:
        return hashlib.sha256(url.strip().encode()).hexdigest()
