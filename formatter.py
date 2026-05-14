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


def _extract_key_number(ai_text: str) -> tuple[str, str]:
    """从AI输出中提取关键数字和说明"""
    import re
    # 匹配 "一个数字" 区块 — 一直读到下一个 # 标题或文末
    m = re.search(r'#{1,3}\s*一个数字\s*\n(.*?)(?:\n#{1,3}\s|\Z)', ai_text, re.DOTALL)
    if m:
        block = m.group(1).strip()
        # 提取 **数字** 中的数字
        bold_m = re.search(r'\*\*(.+?)\*\*', block)
        if bold_m:
            num = bold_m.group(1).strip()
            # 取 **数字** 之后的所有内容作为描述
            desc = block[bold_m.end():].strip()
            desc = re.sub(r'^[—\-–\s]+', '', desc)  # 去掉前导破折号
            return num, desc[:80]
    # 降级：从开头钩子提取
    first_line = ai_text.split("\n")[1] if "\n" in ai_text else ai_text[:100]
    return "", first_line[:80]


def _hero_header(date_str: str, key_number: str, key_desc: str) -> str:
    """生成视觉冲击力强的封面头图"""
    # 配色方案：根据是否有数字选择
    has_num = bool(key_number)
    accent = "#ff6b35"  # 醒目的橙色

    num_block = ""
    if has_num:
        num_block = f"""
    <div style="margin:20px 0 6px;">
      <span style="font-size:52px;font-weight:900;color:{accent};letter-spacing:-2px;line-height:1;">
        {key_number}
      </span>
    </div>
    <p style="font-size:13px;color:#8892b0;margin:4px 0 0;max-width:320px;margin-left:auto;margin-right:auto;line-height:1.6;">
      {key_desc}
    </p>"""

    return f"""
  <section style="
    background:linear-gradient(135deg, #0a1628 0%, #1a2a4a 40%, #0d1f3c 100%);
    border-radius:12px;
    padding:36px 20px 30px;
    margin:0 0 24px;
    text-align:center;
    position:relative;
    overflow:hidden;
  ">
    <!-- 装饰几何图形 -->
    <div style="
      position:absolute;top:-30px;right:-30px;
      width:120px;height:120px;
      border:2px solid rgba(255,255,255,0.06);
      border-radius:50%;
    "></div>
    <div style="
      position:absolute;bottom:-20px;left:-20px;
      width:80px;height:80px;
      border:2px solid rgba(255,255,255,0.04);
      border-radius:50%;
    "></div>
    <div style="
      position:absolute;top:40px;right:60px;
      width:8px;height:8px;
      background:rgba(255,255,255,0.08);
      border-radius:50%;
    "></div>

    <p style="
      font-size:10px;color:#5a7a9a;letter-spacing:4px;text-transform:uppercase;margin:0 0 8px;position:relative;
    ">HOT SPOT BEHIND THE SCENES</p>

    <h1 style="
      font-size:24px;color:#e8edf5;margin:0 0 4px;font-weight:700;letter-spacing:2px;position:relative;
    ">热点幕后</h1>

    <p style="
      font-size:12px;color:#5a7a9a;margin:2px 0 0;position:relative;
    ">{date_str} · 全天复盘</p>

    {num_block}

    <div style="
      margin-top:20px;
      display:inline-block;
      border-top:1px solid rgba(255,255,255,0.08);
      padding-top:10px;
    ">
      <span style="font-size:10px;color:#3d5a80;letter-spacing:2px;">
        深度分析 · AI辅助 · 人工甄别
      </span>
    </div>
  </section>"""


def wrap_html_page(body_html: str, ai_raw: str = "", date_str: str = "") -> str:
    today = date_str or datetime.now().strftime("%Y年%m月%d日")
    key_num, key_desc = _extract_key_number(ai_raw)
    header = _hero_header(today, key_num, key_desc)

    return f"""<section style="padding:0 2px;max-width:100%;word-wrap:break-word;">

  <!-- 封面头图 -->
  {header}

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
    return wrap_html_page(
        body_html=markdown_to_wechat_html(ai_summary),
        ai_raw=ai_summary,
        date_str=today,
    )
