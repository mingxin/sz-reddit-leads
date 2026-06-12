#!/usr/bin/env python3
"""
Reddit Shenzhen Lead Scanner (Web Scraping版)
每天搜索Reddit上与深圳相关的帖子，找出需要本地向导/帮助的外国人。
无需Reddit API凭证，通过网页抓取实现。

依赖：pip3 install requests beautifulsoup4
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import re
import time
import random
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

SCRIPT_DIR = Path(__file__).parent.resolve()

# ─── 配置 ───────────────────────────────────────────

SEARCH_QUERIES = [
    "shenzhen guide",
    "shenzhen travel",
    "shenzhen hospital medical",
    "visit shenzhen trip",
    "shenzhen local help translator",
    "moving to shenzhen expat",
    "shenzhen tips first time",
]

# 相关性关键词
RELEVANT_KEYWORDS = [
    "guide", "tour", "visit", "travel", "trip", "hospital", "medical",
    "doctor", "move", "moving", "live", "living", "local", "help",
    "recommend", "suggestion", "tip", "first time", "where to",
    "what to do", "how to", "need", "looking for", "anyone",
    "translator", "translate", "english", "expat", "foreigner",
    "clinic", "dentist", "health", "surgery", "treatment",
    "apartment", "hotel", "stay", "food", "restaurant",
    "safe", "weather", "cost", "price", "budget",
]

EXCLUDE_AUTHORS = {"AutoModerator", "ModeratorBot"}

# 多个User-Agent轮换，防封
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
]

SESSION = requests.Session()


def get_random_ua():
    return random.choice(USER_AGENTS)


def fetch_page(url, retries=3):
    """带重试的页面抓取"""
    headers = {
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    for attempt in range(retries):
        try:
            resp = SESSION.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 429:
                wait = (2 ** attempt) * 10 + random.randint(5, 15)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
            elif resp.status_code == 403:
                # 换UA重试
                headers["User-Agent"] = get_random_ua()
                time.sleep(3)
            else:
                print(f"    HTTP {resp.status_code}")
                return None
        except requests.RequestException as e:
            print(f"    请求错误: {e}")
            time.sleep(3)
    return None


def search_reddit_google(query, num_results=10):
    """通过Google搜索Reddit帖子"""
    results = []
    search_url = (
        f"https://www.google.com/search?q=site:reddit.com+{quote_plus(query)}"
        f"&tbs=qdr:w&num={num_results}"
    )
    html = fetch_page(search_url)
    if not html:
        return results

    soup = BeautifulSoup(html, "html.parser")

    # Google搜索结果中的Reddit链接
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # 提取Google跳转链接中的实际URL
        if "/url?q=" in href:
            real_url = href.split("/url?q=")[1].split("&")[0]
        elif href.startswith("http"):
            real_url = href
        else:
            continue

        if "reddit.com/r/" in real_url and "/comments/" in real_url:
            # 清理URL参数
            clean_url = real_url.split("?")[0].split("&")[0]
            title = a_tag.get_text(strip=True)
            if title and clean_url not in [r["url"] for r in results]:
                results.append({"url": clean_url, "title": title})

    return results


def search_reddit_duckduckgo(query, num_results=15):
    """通过DuckDuckGo搜索Reddit帖子（备选，更宽松）"""
    results = []
    search_url = (
        f"https://html.duckduckgo.com/html/?q=site%3Areddit.com+{quote_plus(query)}"
    )
    html = fetch_page(search_url)
    if not html:
        return results

    soup = BeautifulSoup(html, "html.parser")

    for result_div in soup.find_all("div", class_="result"):
        link = result_div.find("a", class_="result__a")
        if not link:
            continue
        href = link.get("href", "")
        title = link.get_text(strip=True)

        # DuckDuckGo的URL格式: //duckduckgo.com/l/?uddg=实际URL
        if "uddg=" in href:
            actual_url = href.split("uddg=")[1].split("&")[0]
            actual_url = requests.utils.unquote(actual_url)
        else:
            actual_url = href

        if "reddit.com/r/" in actual_url:
            clean_url = actual_url.split("?")[0]
            if clean_url not in [r["url"] for r in results]:
                results.append({"url": clean_url, "title": title})

    return results[:num_results]


def parse_reddit_post(url):
    """抓取Reddit帖子页面，提取内容"""
    # 用old.reddit.com更容易解析
    if "www.reddit.com" in url:
        url = url.replace("www.reddit.com", "old.reddit.com")

    html = fetch_page(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # 提取帖子信息
    post_info = {
        "url": url.replace("old.reddit.com", "www.reddit.com"),
        "title": "",
        "author": "",
        "subreddit": "",
        "selftext": "",
        "score": 0,
        "num_comments": 0,
        "created_utc": "",
    }

    # 标题
    title_elem = soup.find("a", class_="title") or soup.find("p", class_="title")
    if title_elem:
        post_info["title"] = title_elem.get_text(strip=True)

    # 作者
    author_elem = soup.find("a", class_=re.compile(r"author"))
    if author_elem:
        post_info["author"] = author_elem.get_text(strip=True).replace("u/", "")

    # Subreddit
    sub_elem = soup.find("a", class_="subreddit")
    if sub_elem:
        post_info["subreddit"] = sub_elem.get_text(strip=True).replace("r/", "")
    else:
        # 从URL提取
        match = re.search(r"/r/([^/]+)/", url)
        if match:
            post_info["subreddit"] = match.group(1)

    # 正文内容
    body_elem = (
        soup.find("div", class_="expando") or
        soup.find("div", class_="md") or
        soup.find("div", class_="usertext-body")
    )
    if body_elem:
        post_info["selftext"] = body_elem.get_text(strip=True)[:800]

    # 得分
    score_elem = soup.find("div", class_="score") or soup.find("span", class_="score")
    if score_elem:
        score_text = score_elem.get_text(strip=True)
        try:
            post_info["score"] = int(re.sub(r"[^\d-]", "", score_text) or "0")
        except ValueError:
            pass

    # 评论数
    comments_elem = soup.find("a", class_="comments")
    if comments_elem:
        comments_text = comments_elem.get_text(strip=True)
        match = re.search(r"(\d+)", comments_text)
        if match:
            post_info["num_comments"] = int(match.group(1))

    # 时间
    time_elem = soup.find("time")
    if time_elem and time_elem.get("datetime"):
        post_info["created_utc"] = time_elem["datetime"][:16]

    return post_info


def get_author_recent_posts(author_name, limit=3):
    """获取博主最近帖子（通过用户页面）"""
    url = f"https://old.reddit.com/user/{author_name}/submitted/?sort=new"
    html = fetch_page(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    posts = []

    for thing in soup.find_all("div", class_="thing", limit=limit + 5):
        if len(posts) >= limit:
            break

        # 跳过非submission
        if "linkflair" not in thing.get("class", []) and "self" not in thing.get("class", []):
            # 通用处理，不严格匹配class
            pass

        title_elem = thing.find("a", class_="title")
        if not title_elem:
            continue

        sub_elem = thing.find("a", class_="subreddit")
        subreddit = sub_elem.get_text(strip=True).replace("r/", "") if sub_elem else ""

        # 正文摘要
        body_elem = thing.find("div", class_="md")
        selftext = body_elem.get_text(strip=True)[:300] if body_elem else ""

        permalink_elem = thing.find("a", class_="comments")
        permalink = ""
        if permalink_elem and permalink_elem.get("href"):
            permalink = permalink_elem["href"]

        posts.append({
            "title": title_elem.get_text(strip=True),
            "url": permalink or f"https://www.reddit.com/user/{author_name}",
            "subreddit": subreddit,
            "selftext": selftext,
        })

    return posts


def is_relevant(post_info):
    """判断帖子是否相关"""
    title = post_info.get("title", "").lower()
    selftext = post_info.get("selftext", "").lower()
    combined = title + " " + selftext

    if "shenzhen" not in combined and "深圳" not in combined:
        return False

    author = post_info.get("author", "")
    if author in EXCLUDE_AUTHORS:
        return False

    hits = sum(1 for kw in RELEVANT_KEYWORDS if kw in combined)
    return hits >= 1


def summarize_text(text, max_len=200):
    """简单摘要"""
    if not text or text in ("[deleted]", "[removed]", ""):
        return "（无正文内容）"
    text = text.strip()
    for sep in ["\n\n", ". ", "。", "\n"]:
        idx = text.find(sep)
        if 50 < idx < max_len * 2:
            text = text[:idx + len(sep)].strip()
            break
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text


def generate_report(relevant_posts, date_str):
    """生成markdown报告"""
    lines = [
        f"# Reddit 深圳相关帖子日报 — {date_str}",
        "",
        f"📅 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"📊 发现相关帖子：{len(relevant_posts)} 条",
        "",
        "---",
        "",
    ]

    if not relevant_posts:
        lines.append("*今日未发现符合条件的深圳相关帖子*")
        lines.append("")
        return "\n".join(lines)

    for i, post in enumerate(relevant_posts, 1):
        lines.append(f"## {i}. {post['title']}")
        lines.append("")
        lines.append(f"| 字段 | 值 |")
        lines.append(f"|------|----|")
        lines.append(f"| Subreddit | r/{post['subreddit']} |")
        lines.append(f"| 作者 | u/{post['author']} |")
        lines.append(f"| 链接 | [{post['url']}]({post['url']}) |")
        lines.append(f"| 得分 | {post['score']} |")
        lines.append(f"| 评论 | {post['num_comments']} |")
        if post.get("created_utc"):
            lines.append(f"| 时间 | {post['created_utc']} |")
        lines.append("")
        lines.append("**内容摘要**：")
        lines.append(f"> {summarize_text(post['selftext'])}")
        lines.append("")

        # 博主最近帖子
        author_posts = post.get("author_posts", [])
        if author_posts:
            lines.append(f"### 👤 博主 u/{post['author']} 最近帖子")
            lines.append("")
            for j, ap in enumerate(author_posts, 1):
                lines.append(f"**{j}. {ap['title']}**")
                lines.append(f"- Subreddit: r/{ap['subreddit']}")
                if ap["url"]:
                    lines.append(f"- 链接: [{ap['url']}]({ap['url']})")
                lines.append(f"- 摘要: {summarize_text(ap['selftext'], 150)}")
                lines.append("")
        else:
            lines.append(f"*博主 u/{post['author']} 最近帖子：无法获取*")
            lines.append("")

        lines.append("---")
        lines.append("")

    # 汇总表
    lines.append("## 📋 汇总")
    lines.append("")
    lines.append("| # | 标题 | 作者 | Subreddit | 评论 |")
    lines.append("|---|------|------|-----------|------|")
    for i, post in enumerate(relevant_posts, 1):
        title_short = post['title'][:35] + ("..." if len(post['title']) > 35 else "")
        lines.append(
            f"| {i} | {title_short} | u/{post['author']} | "
            f"r/{post['subreddit']} | {post['num_comments']} |"
        )
    lines.append("")

    return "\n".join(lines)


# ─── 主流程 ─────────────────────────────────────────

def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_file = SCRIPT_DIR / f"{date_str}.md"

    if output_file.exists() and "--force" not in sys.argv:
        print(f"今天的报告已存在：{output_file}")
        print("使用 --force 强制重新生成")
        return

    print(f"开始扫描 Reddit 深圳相关帖子 ({date_str})...")

    # 1. 搜索Reddit帖子URL
    all_urls = {}  # url -> title

    for query in SEARCH_QUERIES:
        print(f"  DuckDuckGo搜索: {query}")
        ddg_results = search_reddit_duckduckgo(query)
        for r in ddg_results:
            if r["url"] not in all_urls:
                all_urls[r["url"]] = r["title"]
        time.sleep(random.uniform(2, 4))

    print(f"  共找到 {len(all_urls)} 个唯一帖子链接")

    # 2. 抓取每个帖子详情
    relevant = []
    processed = 0

    for url, search_title in all_urls.items():
        processed += 1
        print(f"  [{processed}/{len(all_urls)}] 抓取: {search_title[:50]}...")
        post_info = parse_reddit_post(url)
        if not post_info:
            print(f"    跳过（无法抓取）")
            time.sleep(random.uniform(2, 5))
            continue

        # 用搜索结果的标题作为fallback
        if not post_info["title"]:
            post_info["title"] = search_title

        if is_relevant(post_info):
            relevant.append(post_info)
            print(f"    ✅ 相关: {post_info['title'][:60]}")
        else:
            print(f"    ❌ 不相关")

        time.sleep(random.uniform(3, 6))

    print(f"  相关帖子：{len(relevant)} 条")

    # 按评论数排序
    relevant.sort(key=lambda x: x["num_comments"], reverse=True)

    # 3. 获取博主最近帖子
    processed_authors = {}
    for post in relevant:
        author = post["author"]
        if not author or author in ("[deleted]", "[removed]"):
            post["author_posts"] = []
            continue

        if author in processed_authors:
            post["author_posts"] = processed_authors[author]
            continue

        print(f"  获取 u/{author} 最近帖子...")
        author_posts = get_author_recent_posts(author, limit=3)
        processed_authors[author] = author_posts
        post["author_posts"] = author_posts
        time.sleep(random.uniform(2, 4))

    # 4. 生成报告
    report = generate_report(relevant, date_str)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n✅ 报告已生成：{output_file}")
    print(f"📊 相关帖子：{len(relevant)} 条")

    if "--quiet" not in sys.argv:
        print("\n" + "=" * 60)
        print(report[:3000])
        if len(report) > 3000:
            print(f"\n... (完整报告见 {output_file})")


if __name__ == "__main__":
    main()
