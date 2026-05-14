"""
所有配置集中管理
"""
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # ---- AI ----
    ai_provider: str = os.getenv("AI_PROVIDER", "deepseek")
    ai_api_key: str = os.getenv("AI_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "deepseek-chat")

    # ---- 推送方式 ----
    push_mode: str = os.getenv("PUSH_MODE", "email")  # email | wechat

    # ---- 邮箱 ----
    email_sender: str = os.getenv("EMAIL_SENDER", "")
    email_receiver: str = os.getenv("EMAIL_RECEIVER", "")
    email_smtp_code: str = os.getenv("EMAIL_SMTP_CODE", "")

    # ---- 公众号 ----
    wechat_app_id: str = os.getenv("WECHAT_APP_ID", "")
    wechat_app_secret: str = os.getenv("WECHAT_APP_SECRET", "")
    wechat_push_mode: str = os.getenv("WECHAT_PUSH_MODE", "mass")

    # ---- 第三方 API ----
    newsapi_key: str = os.getenv("NEWSAPI_KEY", "")
    tianapi_key: str = os.getenv("TIANAPI_KEY", "")


# ============================================================
# 内容源配置
# ============================================================

# ---- RSS 源 ----
RSS_SOURCES: list[dict] = [
    # == 国际金融 ==
    {"name": "CNBC-Top",          "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "cat": "finance"},
    {"name": "MarketWatch",       "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories", "cat": "finance"},
    # == 国内财经 ==
    {"name": "华尔街见闻",          "url": "https://wallstreetcn.com/rss/latest",            "cat": "finance"},
    {"name": "财联社-电报",          "url": "https://www.cls.cn/rss/telegraph",               "cat": "finance"},
    {"name": "金十数据",            "url": "https://www.jin10.com/rss",                      "cat": "finance"},
    {"name": "东方财富-全球",        "url": "https://rss.eastmoney.com/global.xml",           "cat": "finance"},
    # == 科技 ==
    {"name": "TechCrunch",        "url": "https://techcrunch.com/feed/",                    "cat": "tech"},
    {"name": "HackerNews",        "url": "https://hnrss.org/frontpage",                     "cat": "tech"},
    {"name": "36氪",               "url": "https://36kr.com/feed",                           "cat": "tech"},
    {"name": "少数派",              "url": "https://sspai.com/feed",                          "cat": "tech"},
    # == 宏观/政策/农业 ==
    {"name": "USDA-News",         "url": "https://www.usda.gov/rss.xml",                    "cat": "agriculture"},
    {"name": "新浪财经-宏观",        "url": "https://finance.sina.com.cn/macroscopic/rss.xml", "cat": "finance"},
]

# ---- NewsAPI 分类 ----
NEWSAPI_CATEGORIES = ["business", "technology", "general"]

# ---- 抖音热榜源（通过天行数据 + 其他聚合接口）----
DOUYIN_APIS = [
    {
        "name": "抖音热榜",
        "url": "https://apis.tianapi.com/douyinhot/index",
        "params": {},
        "cat": "douyin_hot",
    },
    {
        "name": "抖音财经热搜",
        "url": "https://apis.tianapi.com/douyinhot/index",
        "params": {"word": "财经"},
        "cat": "douyin_finance",
    },
]

# ---- 抖音KOL参考（手动维护你关注的博主列表，通过RSS/API追踪）----
DOUYIN_KOL_LIST = [
    # 金融类
    {"name": "财经林妹妹", "id": "cjlmm", "cat": "finance"},
    {"name": "直男财经",   "id": "zncj",   "cat": "finance"},
    # 科技类
    {"name": "差评",       "id": "chaping", "cat": "tech"},
    {"name": "科技狐",     "id": "kjh",     "cat": "tech"},
    # 农业/民生
    {"name": "乡村爱情记录", "id": "xcaqjl", "cat": "agriculture"},
    {"name": "新农人计划",   "id": "xnrjh",  "cat": "agriculture"},
]

# ---- 最终推送的每日条数上限 ----
MAX_ITEMS_PER_CATEGORY = {
    "finance":     8,
    "tech":        5,
    "agriculture": 3,
    "douyin":      6,   # 抖音热点单独一类
    "daily_report": 1,  # 每日简报类
    "other":       3,
}

# ---- 本地数据库 ----
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "history.db")
