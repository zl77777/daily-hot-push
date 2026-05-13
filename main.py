#!/usr/bin/env python3
"""
每日全球热点聚合推送 —— 主入口

用法:
  # 运行一次（测试/手动触发）
  python main.py

  # 生产环境：每天 8:30 自动运行（配合 cron / 云函数）
  # crontab -e 添加：
  # 30 8 * * * cd /path/to/daily-hot-push && python main.py >> logs/daily.log 2>&1

架构流程:
  1. 并行抓取 RSS / NewsAPI / 抖音热榜
  2. 去重（过滤已推送过的 URL）
  3. AI 分类 + 摘要 + 提炼
  4. 排版成公众号格式
  5. 推送到公众号（群发 / 模板消息）
  6. 记录已推送 URL 到本地 DB
"""
import asyncio
import argparse
import os
import sys
from datetime import datetime

# 加载 .env
def load_dotenv(path: str = ".env"):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if not os.path.isfile(p):
        return
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


load_dotenv()

from config import Config
from fetchers import RSSFetcher, NewsAPIFetcher, DouyinFetcher, Article
from dedup import DedupManager
from summarizer import AISummarizer
from formatter import format_daily_report
from wechat_push import WeChatPusher


async def fetch_all(config: Config) -> list[Article]:
    """并行抓取所有内容源"""
    print("[1/5] 📡 开始抓取内容源...")

    fetchers = [
        ("RSS",        RSSFetcher()),
        ("NewsAPI",    NewsAPIFetcher(config)),
        ("抖音",        DouyinFetcher(config)),
    ]

    all_articles: list[Article] = []
    for name, fetcher in fetchers:
        try:
            articles = await fetcher.fetch()
            print(f"  [{name}] 获取 {len(articles)} 条")
            all_articles.extend(articles)
        except Exception as e:
            print(f"  [{name}] ❌ 抓取失败: {e}")

    print(f"  合计抓取 {len(all_articles)} 条原始内容")
    return all_articles


def dedup_articles(all_articles: list[Article]) -> list[Article]:
    """去重"""
    print("[2/5] 🧹 去重...")

    mgr = DedupManager()
    fresh = mgr.filter_new(all_articles)
    removed = len(all_articles) - len(fresh)
    print(f"  过滤重复 {removed} 条，剩余 {len(fresh)} 条")
    return fresh


async def ai_summarize(config: Config, articles: list[Article]) -> str:
    """AI 摘要"""
    print("[3/5] 🤖 AI 分类整理中...")

    if not config.ai_api_key:
        print("  ⚠️  未配置 AI_API_KEY，使用模板化摘要")
        print("  建议配置 DeepSeek (deepseek-chat)，性价比最高：1元/百万token")
        print("  注册地址: https://platform.deepseek.com")

    summarizer = AISummarizer(config)
    result = await summarizer.summarize(articles)
    lines = result.split("\n")
    print(f"  生成摘要 {len(lines)} 行 / {len(result)} 字")
    return result


def format_content(ai_result: str) -> str:
    """排版"""
    print("[4/5] 📝 排版...")
    return format_daily_report(ai_result)


async def push_to_wechat(config: Config, content: str, brief: str) -> dict:
    """推送"""
    print("[5/5] 📲 推送公众号...")
    pusher = WeChatPusher(config)
    return await pusher.push(content, brief)


async def main(dry_run: bool = False):
    print("=" * 60)
    print(f"  🗞️  每日全球热点聚合推送")
    print(f"  ⏰  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    config = Config()

    # ---- Step 1-5 ----
    articles = await fetch_all(config)

    if not articles:
        print("\n❌ 未获取到任何内容，检查网络或 API 配置")
        return 1

    fresh = dedup_articles(articles)

    if not fresh:
        print("\n✅ 没有新的内容需要推送")
        return 0

    ai_result = await ai_summarize(config, fresh)
    content = format_content(ai_result)

    if dry_run:
        print("\n" + "=" * 60)
        print("  📋 预览模式 — 以下是推送内容：")
        print("=" * 60)
        print(content)
        print("=" * 60)
        print("\n💡 预览结束。去掉 --preview 参数即可正式推送。")
        return 0

    result = await push_to_wechat(config, content, ai_result[:200])

    # ---- 记录已推送 ----
    if result.get("status") == "success":
        mgr = DedupManager()
        mgr.mark_pushed(fresh)
        mgr.clean_old(days=14)

    print("\n" + "=" * 60)
    print(f"  推送结果: {result}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="每日全球热点聚合推送")
    parser.add_argument("--preview", action="store_true", help="仅预览不推送")
    parser.add_argument("--fetch-only", action="store_true", help="仅抓取预览忽略 AI 和推送")
    args = parser.parse_args()

    if args.fetch_only:
        async def _fetch_preview():
            config = Config()
            articles = await fetch_all(config)
            for a in articles:
                print(f"  [{a.category}] {a.title[:70]} — {a.source}")
        asyncio.run(_fetch_preview())
    else:
        sys.exit(asyncio.run(main(dry_run=args.preview)))
