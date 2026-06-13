#!/usr/bin/env python3
"""
将 scanner/reports/*.md 解析为 dashboard/data/posts.json + dates.json
用法: python3 scanner/parse_reports.py
"""
import json, re, os, sys
from datetime import datetime, timedelta

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(PROJECT_DIR, "scanner", "reports")
DATA_DIR = os.path.join(PROJECT_DIR, "dashboard", "data")

# 只保留最近30天的帖子
MAX_AGE_DAYS = 30

CATEGORIES = {
    "tour_guide": ["旅游", "向导", "guide", "tour", "trip", "travel", "visit", "游览", "景点"],
    "medical": ["医疗", "medical", "hospital", "doctor", "医院", "诊所", "clinic", "dentist"],
    "translation": ["翻译", "translator", "translation", "translate", "语言", "language"],
    "living": ["生活", "living", "move", "moving", "expat", "搬到", "居住", "搬家", "社区", "apartment"],
}

def normalize(raw):
    lower = raw.lower()
    for cat, kws in CATEGORIES.items():
        if any(k in lower for k in kws):
            return cat
    return "general"

def clean_post_date(raw_date):
    """清理发布时间字段，提取YYYY-MM-DD部分"""
    if not raw_date or raw_date.strip() in ("未知", ""):
        return "未知"
    raw_date = raw_date.strip()
    # 提取日期部分（去掉"（推断）"等后缀）
    m = re.search(r'(\d{4}-\d{2}-\d{2})', raw_date)
    if m:
        return m.group(1)
    return raw_date

def parse_relative_age(date_str):
    """从日期字符串解析出datetime，用于计算相对时间"""
    if not date_str or date_str == "未知":
        return None
    m = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            pass
    return None

def relative_age_label(dt, now=None):
    """计算相对时间标签，如 '3天前'、'2周前'"""
    if dt is None:
        return ""
    if now is None:
        now = datetime.now()
    delta = now - dt
    days = delta.days
    if days < 0:
        return ""
    if days == 0:
        return "今天"
    if days == 1:
        return "昨天"
    if days < 7:
        return f"{days}天前"
    if days < 30:
        return f"{days // 7}周前"
    if days < 365:
        return f"{days // 30}个月前"
    return f"{days // 365}年前"

def is_within_month(date_str, now=None):
    """判断帖子是否在最近一个月内发布"""
    dt = parse_relative_age(date_str)
    if dt is None:
        # 未知日期的帖子保留（可能是今天的新帖子，Claude没提取到日期）
        return True
    if now is None:
        now = datetime.now()
    return (now - dt).days <= MAX_AGE_DAYS

def parse_report(filepath, filename):
    content = open(filepath, encoding="utf-8").read()
    date = filename.replace(".md", "")
    now = datetime.now()

    sections = re.split(r"\n(?=## \d+\. )", content)
    posts = []
    skipped = 0
    for sec in sections:
        m = re.match(r"^## (\d+)\.\s*(.+)", sec)
        if not m:
            continue
        pid = int(m.group(1))
        title = m.group(2).strip()

        url = re.search(r"\*\*链接\*\*[：:]\s*(.+)", sec) or re.search(r"\*\*URL\*\*[：:]\s*(.+)", sec)
        sub = re.search(r"\*\*Subreddit\*\*[：:]\s*(.+)", sec)
        author = re.search(r"\*\*作者\*\*[：:]\s*(.+)", sec)
        cat = re.search(r"\*\*需求类型\*\*[：:]\s*(.+)", sec)
        post_date = re.search(r"\*\*发布时间\*\*[：:]\s*(.+)", sec)
        planned = re.search(r"\*\*计划来深圳时间\*\*[：:]\s*(.+)", sec) or re.search(r"\*\*计划到达时间\*\*[：:]\s*(.+)", sec)
        summary = re.search(r"\*\*内容摘要\*\*[：:：]\s*([\s\S]+?)(?=\n---|\n## |\Z)", sec)

        url_val = url.group(1).strip() if url else ""
        if not url_val:
            continue

        final_date = clean_post_date(post_date.group(1).strip() if post_date else "未知")

        # 过滤：只保留最近30天
        if not is_within_month(final_date, now):
            skipped += 1
            continue

        # 计算相对时间
        post_dt = parse_relative_age(final_date)
        age_label = relative_age_label(post_dt, now)

        posts.append({
            "id": pid,
            "title": title,
            "url": url_val,
            "subreddit": sub.group(1).strip() if sub else "",
            "author": author.group(1).strip() if author else "未知",
            "category": normalize(cat.group(1) if cat else ""),
            "categoryRaw": cat.group(1).strip() if cat else "general",
            "postDate": final_date,
            "postAge": age_label,
            "plannedDate": planned.group(1).strip() if planned else "未提及",
            "summary": summary.group(1).replace("\n", " ").strip() if summary else "",
        })

    pri = re.search(r"## 💡 重点关注([\s\S]*?)$", content)
    priority = pri.group(1).strip() if pri else ""

    print(f"  {date}: {len(posts)} posts kept, {skipped} older than {MAX_AGE_DAYS} days filtered out")

    return {"date": date, "totalCount": len(posts), "posts": posts, "priority": priority}

def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    reports = []
    for f in sorted(os.listdir(REPORTS_DIR)):
        if not f.endswith(".md"):
            continue
        report = parse_report(os.path.join(REPORTS_DIR, f), f)
        reports.append(report)

    reports.sort(key=lambda r: r["date"], reverse=True)

    with open(os.path.join(DATA_DIR, "posts.json"), "w", encoding="utf-8") as out:
        json.dump({"reports": reports}, out, ensure_ascii=False, indent=2)

    dates = [r["date"] for r in reports]
    with open(os.path.join(DATA_DIR, "dates.json"), "w", encoding="utf-8") as out:
        json.dump(dates, out)

    total = sum(len(r["posts"]) for r in reports)
    print(f"Done! {len(reports)} reports, {total} posts (last {MAX_AGE_DAYS} days only)")

if __name__ == "__main__":
    main()
