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

    # ---- 公众号 ----
    wechat_app_id: str = os.getenv("WECHAT_APP_ID", "")
    wechat_app_secret: str = os.getenv("WECHAT_APP_SECRET", "")
    wechat_push_mode: str = os.getenv("WECHAT_PUSH_MODE", "mass")  # mass | template

    # ---- 第三方 API ----
    newsapi_key: str = os.getenv("NEWSAPI_KEY", "")
    tianapi_key: str = os.getenv("TIANAPI_KEY", "")


# ============================================================
# 内容源配置
# ============================================================

# ---- RSS 源 ----
RSS_SOURCES: list[dict] = [
    # 国际金融
    {"name": "Reuters-Top",       "url": "https://rss.app/feeds/AbCdEf123456.xml",        "cat": "finance"},
    {"name": "CNBC-Top",          "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "cat": "finance"},
    # 国内财经
    {"name": "华尔街见闻",         "url": "https://wallstreetcn.com/rss/latest",            "cat": "finance"},
    {"name": "金十数据-快讯",       "url": "https://www.jin10.com/rss",                     "cat": "finance"},
    # 科技
    {"name": "TechCrunch",        "url": "https://techcrunch.com/feed/",                   "cat": "tech"},
    {"name": "HackerNews",        "url": "https://hnrss.org/frontpage",                    "cat": "tech"},
    {"name": "36氪",               "url": "https://36kr.com/feed",                          "cat": "tech"},
    # 大宗/农业
    {"name": "USDA-News",         "url": "https://www.usda.gov/rss.xml",                   "cat": "agriculture"},
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
