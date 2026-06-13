#!/usr/bin/env python3
"""
将 scanner/reports/*.md 解析为 dashboard/data/posts.json + dates.json
用法: python3 scanner/parse_reports.py
"""
import json, re, os, sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(PROJECT_DIR, "scanner", "reports")
DATA_DIR = os.path.join(PROJECT_DIR, "dashboard", "data")

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
    """清理发布时间字段"""
    if not raw_date or raw_date.strip() in ("未知", ""):
        return "未知"
    return raw_date.strip()

def parse_report(filepath, filename):
    content = open(filepath, encoding="utf-8").read()
    date = filename.replace(".md", "")

    sections = re.split(r"\n(?=## \d+\. )", content)
    posts = []
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

        raw_date = post_date.group(1).strip() if post_date else "未知"
        final_date = clean_post_date(raw_date)

        posts.append({
            "id": pid,
            "title": title,
            "url": url_val,
            "subreddit": sub.group(1).strip() if sub else "",
            "author": author.group(1).strip() if author else "未知",
            "category": normalize(cat.group(1) if cat else ""),
            "categoryRaw": cat.group(1).strip() if cat else "general",
            "postDate": final_date,
            "plannedDate": planned.group(1).strip() if planned else "未提及",
            "summary": summary.group(1).replace("\n", " ").strip() if summary else "",
        })

    pri = re.search(r"## 💡 重点关注([\s\S]*?)$", content)
    priority = pri.group(1).strip() if pri else ""

    return {"date": date, "totalCount": len(posts), "posts": posts, "priority": priority}

def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    reports = []
    for f in sorted(os.listdir(REPORTS_DIR)):
        if not f.endswith(".md"):
            continue
        report = parse_report(os.path.join(REPORTS_DIR, f), f)
        reports.append(report)
        print(f"Parsed {report['date']}: {len(report['posts'])} posts")

    reports.sort(key=lambda r: r["date"], reverse=True)

    with open(os.path.join(DATA_DIR, "posts.json"), "w", encoding="utf-8") as out:
        json.dump({"reports": reports}, out, ensure_ascii=False, indent=2)

    dates = [r["date"] for r in reports]
    with open(os.path.join(DATA_DIR, "dates.json"), "w", encoding="utf-8") as out:
        json.dump(dates, out)

    print(f"Done! {len(reports)} reports, {sum(len(r['posts']) for r in reports)} total posts")

if __name__ == "__main__":
    main()
