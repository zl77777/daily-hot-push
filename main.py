#!/usr/bin/env python3
"""
每日全球热点深度分析 —— 主入口

架构流程:
  1. 并行抓取：全球资讯(RSS/NewsAPI) + 中文热搜(微博/知乎/百度) + 抖音 + 市场数据
  2. 去重
  3. AI 深度分析（金融人视角 × 冲浪人视角）
  4. 排版成 HTML
  5. 邮件推送
"""
import asyncio
import argparse
import os
import sys
from datetime import datetime

# Windows 终端 UTF-8 编码修复
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


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
from fetchers.china_hot import ChinaHotFetcher
from fetchers.market_data import MarketDataFetcher
from dedup import DedupManager
from summarizer import AISummarizer
from formatter import format_daily_report


# ============================================================
async def fetch_all(config: Config):
    """并行抓取所有内容源，分成 news 和 social 两类"""
    print("[1/6] 抓取内容源...")

    # ---- 全球资讯 ----
    news_fetchers = [
        ("RSS",        RSSFetcher()),
        ("NewsAPI",    NewsAPIFetcher(config)),
    ]

    news_articles: list[Article] = []
    for name, fetcher in news_fetchers:
        try:
            items = await fetcher.fetch()
            print(f"  [{name}] 获取 {len(items)} 条")
            news_articles.extend(items)
        except Exception as e:
            print(f"  [{name}] 抓取失败: {e}")

    # ---- 中文热搜 ----
    social_articles: list[Article] = []
    try:
        china = ChinaHotFetcher()
        social_articles = await china.fetch()
    except Exception as e:
        print(f"  [中文热搜] 抓取失败: {e}")

    # ---- 抖音 ----
    try:
        douyin = DouyinFetcher(config)
        dy_items = await douyin.fetch()
        print(f"  [抖音] 获取 {len(dy_items)} 条")
        social_articles.extend(dy_items)
    except Exception as e:
        print(f"  [抖音] 抓取失败: {e}")

    print(f"  合计: 资讯 {len(news_articles)} 条 + 热搜 {len(social_articles)} 条")
    return news_articles, social_articles


# ============================================================
async def fetch_market_context():
    """获取市场情绪数据"""
    print("[2/6] 获取市场数据...")
    try:
        fetcher = MarketDataFetcher()
        ctx = await fetcher.fetch_context()
        # 摘要打印
        fg = ctx.get("fear_greed", {})
        idx = ctx.get("global_indices", {})
        if fg:
            print(f"  恐贪指数: {fg.get('now')} ({fg.get('label')})")
        if idx:
            moves = [f"{k}:{v.get('change_pct','?')}%" for k, v in idx.items()]
            print(f"  关键指数: {', '.join(moves)}")
        return ctx
    except Exception as e:
        print(f"  市场数据获取失败: {e}")
        return {}


# ============================================================
def dedup_articles(news: list[Article], social: list[Article]):
    print("[3/6] 去重...")
    mgr = DedupManager()
    news_fresh = mgr.filter_new(news)
    social_fresh = mgr.filter_new(social)
    print(f"  资讯: {len(news_fresh)} 条新 / 社交: {len(social_fresh)} 条新")
    return news_fresh, social_fresh, mgr


# ============================================================
async def ai_analyze(config: Config, news: list, social: list, market: dict) -> str:
    print("[4/6] AI 深度分析中...")

    if not config.ai_api_key:
        print("  未配置 AI_API_KEY，使用模板化摘要")

    summarizer = AISummarizer(config)
    result = await summarizer.summarize(news, social, market)
    print(f"  生成分析 {len(result)} 字 / {len(result.split(chr(10)))} 行")
    return result


# ============================================================
def format_html(ai_result: str) -> str:
    print("[5/6] 排版...")
    return format_daily_report(ai_result)


# ============================================================
def push_via_email(config: Config, html_content: str) -> dict:
    print("[6/6] 发送邮件...")

    if not config.email_smtp_code or config.email_smtp_code == "your_smtp_code_here":
        print("  未配置 SMTP 授权码，保存到 article.html")
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "article.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(html_content)
        return {"status": "saved", "file": out}

    from email_sender import EmailSender, build_email_title
    sender = EmailSender(config.email_sender, config.email_smtp_code)
    return sender.send_html_email(
        to_email=config.email_receiver or config.email_sender,
        subject=build_email_title(),
        html_body=html_content,
    )


# ============================================================
async def main(dry_run: bool = False):
    print("=" * 60)
    print("  每日全球热点深度分析")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    config = Config()

    # ---- 抓取 ----
    news, social = await fetch_all(config)
    market = await fetch_market_context()

    if not news and not social:
        print("\n未获取到任何内容")
        return 1

    # ---- 去重 ----
    news_fresh, social_fresh, dedup_mgr = dedup_articles(news, social)

    if not news_fresh and not social_fresh:
        print("\n没有新内容需要推送")
        return 0

    # ---- AI 分析 ----
    # 预览模式用全部数据让 AI 看到完整图景
    if dry_run:
        ai_result = await ai_analyze(config, news, social, market)
    else:
        ai_result = await ai_analyze(config, news_fresh, social_fresh, market)

    html_content = format_html(ai_result)

    # ---- 预览 / 推送 ----
    if dry_run:
        preview_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "preview.html"
        )
        with open(preview_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print("\n" + "=" * 60)
        print("  预览 HTML → preview.html")
        print("=" * 60)
        print("\n--- AI 分析全文 (Markdown) ---")
        print(ai_result)
        print("--- END ---")
        return 0

    result = push_via_email(config, html_content)

    if result.get("status") == "sent":
        all_fresh = list(news_fresh) + list(social_fresh)
        dedup_mgr.mark_pushed(all_fresh)
        dedup_mgr.clean_old(days=14)

    print("\n" + "=" * 60)
    print(f"  结果: {result}")
    print("=" * 60)
    return 0


# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="每日全球热点深度分析")
    parser.add_argument("--preview", action="store_true", help="仅预览不推送")
    parser.add_argument("--fetch-only", action="store_true", help="仅抓取，跳过 AI")
    args = parser.parse_args()

    if args.fetch_only:
        async def _preview():
            config = Config()
            news, social = await fetch_all(config)
            print("\n--- 全球资讯 ---")
            for a in news:
                print(f"  [{a.source}] {a.title[:80]}")
            print(f"\n--- 中文热搜 ({len(social)} 条) ---")
            for a in social:
                print(f"  [{a.source}] {a.title[:80]}")
        asyncio.run(_preview())
    else:
        sys.exit(asyncio.run(main(dry_run=args.preview)))
