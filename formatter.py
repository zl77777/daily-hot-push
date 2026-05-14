"""
内容排版 → 深度分析报告 HTML

输出风格: 像一篇人类写的 newsletter，不像 AI 报告
"""
import re
from datetime import datetime


def markdown_to_wechat_html(text: str) -> str:
    lines = text.split("\n")
    out = []
    buf = ""
    in_list = False

    def flush():
        nonlocal buf, in_list
        t = buf.strip()
        buf = ""
        if not t:
            return
        if in_list:
            out.append("</ul>")
            in_list = False

        # 去掉 AI 腔调检测：如果段落太"模板化"，不做特殊处理
        out.append(
            f'<p style="font-size:15px;color:#2c2c2c;line-height:1.9;margin:0 0 14px;letter-spacing:0.3px;">'
            f"{_fmt_inline(t)}</p>"
        )

    for line in lines:
        s = line.strip()

        if not s:
            flush()
            continue

        # h1: 主标题 "今天，有件事不对劲"
        if s.startswith("# "):
            flush()
            out.append(
                f'<h2 style="font-size:21px;color:#111;margin:32px 0 16px;text-align:center;'
                f'font-weight:700;letter-spacing:1px;">{_fmt_inline(s[2:])}</h2>'
            )
            continue

        # h2: 一级分隔标题
        if s.startswith("## "):
            flush()
            t = _fmt_inline(s[3:])
            out.append(
                f'<h3 style="font-size:17px;color:#b71c1c;margin:28px 0 10px;'
                f'padding:6px 0 6px 12px;border-left:4px solid #b71c1c;font-weight:600;">{t}</h3>'
            )
            continue

        # h3: "第一件" / "一个数字" 等子标题
        if s.startswith("### "):
            flush()
            t = _fmt_inline(s[4:])
            out.append(
                f'<h4 style="font-size:15px;color:#1565c0;margin:20px 0 8px;font-weight:600;">{t}</h4>'
            )
            continue

        # 分隔线
        if s == "---":
            flush()
            out.append('<hr style="border:none;border-top:1px dashed #ccc;margin:22px 0;">')
            continue

        # 引用
        if s.startswith("> "):
            flush()
            t = _fmt_inline(s[2:])
            out.append(
                f'<blockquote style="background:#f7f8fa;padding:10px 14px;margin:10px 0;'
                f'border-left:3px solid #333;color:#555;font-size:14px;border-radius:0 6px 6px 0;">{t}</blockquote>'
            )
            continue

        # 加粗单独成行的条目（如 **发生了什么**）
        if re.match(r"^\*\*.+\*\*$", s):
            flush()
            out.append(
                f'<p style="font-size:13px;color:#888;margin:14px 0 2px;font-weight:600;'
                f'text-transform:uppercase;letter-spacing:1px;">{_fmt_inline(s)}</p>'
            )
            continue

        # 无序列表
        if re.match(r"^[\-\•]\s+", s):
            if not in_list:
                out.append('<ul style="padding-left:18px;margin:4px 0 10px;line-height:1.85;">')
                in_list = True
            t = _fmt_inline(re.sub(r"^[\-\•]\s+", "", s))
            out.append(f'<li style="margin-bottom:2px;font-size:14px;color:#444;">{t}</li>')
            continue

        # 普通段落 → 积攒
        buf += " " + s if buf else s

    flush()
    return "\n".join(out)


def _fmt_inline(t: str) -> str:
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" style="color:#1565c0;text-decoration:none;border-bottom:1px solid #90caf9;">\1</a>',
        t,
    )
    return t


def wrap_html_page(body_html: str, date_str: str = "") -> str:
    today = date_str or datetime.now().strftime("%Y年%m月%d日")

    return f"""<section style="padding:0 2px;max-width:100%;word-wrap:break-word;">

  <!-- 头 -->
  <section style="text-align:center;padding:30px 0 18px;border-bottom:3px solid #111;margin-bottom:22px;">
    <h1 style="font-size:23px;color:#111;margin:0 0 8px;font-weight:800;letter-spacing:1px;">
      热点幕后
    </h1>
    <p style="font-size:12px;color:#999;margin:0;">
      {today} · 每日深度分析 · 不止于新闻
    </p>
  </section>

  <!-- 正文 -->
  {body_html}

  <!-- 尾 -->
  <hr style="border:none;border-top:1px solid #e0e0e0;margin:32px 0 14px;">
  <section style="text-align:center;font-size:11px;color:#bbb;padding:8px 0 30px;line-height:1.8;">
    <p style="margin:2px 0;">数据来源：Bloomberg · Reuters · 36氪 · 微博热搜 · 财联社</p>
    <p style="margin:2px 0;">AI 辅助生成 · 人工校验 · 不构成投资建议</p>
  </section>

</section>"""


def format_daily_report(ai_summary: str, date_str: str | None = None) -> str:
    today = date_str or datetime.now().strftime("%Y年%m月%d日")
    return wrap_html_page(markdown_to_wechat_html(ai_summary), today)
