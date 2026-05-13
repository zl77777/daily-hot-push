"""抓取器基类 + 结果模型"""
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod


@dataclass
class Article:
    title: str
    url: str
    source: str          # 来源名称，如 "Bloomberg" / "36氪"
    category: str        # finance / tech / agriculture / douyin
    summary: str = ""    # 一段简短摘要（抓取时填，AI 会覆盖）
    published_at: str = ""  # ISO 时间字符串

    def __hash__(self):
        return hash(self.url)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "category": self.category,
            "summary": self.summary,
            "published_at": self.published_at,
        }


class BaseFetcher(ABC):
    """所有抓取器继承此类"""

    @abstractmethod
    async def fetch(self) -> list[Article]:
        ...
