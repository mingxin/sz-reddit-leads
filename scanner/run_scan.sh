#!/bin/bash
# Reddit Shenzhen Lead Scanner - 通过Claude CLI + WebSearch每日扫描
# 由系统crontab调用，每天10:03执行

DATE=$(date +%Y-%m-%d)
PROJECT_DIR="/Users/martinlok/Projects/SZtravel"
SCRIPT_DIR="$PROJECT_DIR/scanner"
REPORTS_DIR="$SCRIPT_DIR/reports"
OUTPUT_FILE="$REPORTS_DIR/$DATE.md"
LOG_FILE="$SCRIPT_DIR/cron.log"
CLAUDE="/Users/martinlok/.npm-global/bin/claude"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始执行扫描..." >> "$LOG_FILE"

# 检查今天是否已生成
if [ -f "$OUTPUT_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 今日报告已存在，跳过" >> "$LOG_FILE"
    exit 0
fi

# 用Claude CLI执行搜索和分析
# 关键：用 -p 非交互模式，--output-format text 确保纯文本输出
"$CLAUDE" -p "IMPORTANT: 你必须直接输出markdown报告全文。不要使用Write工具。不要说'报告已生成'。把完整markdown内容直接打印出来。

你是深圳本地向导服务的市场调研员。今天是 $(date +%Y-%m-%d)。

## 步骤1：搜索
用WebSearch搜索以下关键词，每个搜一次（结果去重）：
1. \"shenzhen guide\" site:reddit.com
2. \"shenzhen travel help\" site:reddit.com
3. \"shenzhen hospital\" OR \"shenzhen medical\" site:reddit.com
4. \"visit shenzhen\" OR \"shenzhen trip\" site:reddit.com
5. \"shenzhen translator\" OR \"shenzhen local help\" site:reddit.com
6. \"moving to shenzhen\" OR \"shenzhen expat\" site:reddit.com

## 步骤2：筛选
只保留外国人需要深圳本地帮助的帖子（找向导、旅游、医疗、翻译、生活帮助）。

## 步骤3：输出报告
直接输出以下格式的markdown（不要省略任何内容，每条帖子都要完整输出）：

# Reddit 深圳相关帖子日报 — $(date +%Y-%m-%d)

📅 生成时间：当前时间
📊 发现相关帖子：X 条

---

（对每条帖子：）

## N. 帖子标题
- **链接**: URL
- **Subreddit**: r/xxx
- **作者**: u/xxx
- **需求类型**: 旅游向导/医疗/翻译/生活帮助

**内容摘要**：（3-5句话）

---

## 📋 汇总

| # | 标题 | 作者 | Subreddit | 需求类型 |
|---|------|------|-----------|----------|

## 💡 重点关注
（需求最明确、时间最紧迫的帖子）

如果没有找到相关帖子，输出：\"今日未发现符合条件的深圳相关帖子\"" \
  --allowedTools WebSearch \
  --output-format text \
  > "$OUTPUT_FILE" 2>> "$LOG_FILE"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ] && [ -s "$OUTPUT_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 报告生成成功：$OUTPUT_FILE ($(wc -c < "$OUTPUT_FILE") bytes)" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 报告生成失败，退出码: $EXIT_CODE" >> "$LOG_FILE"
    exit $EXIT_CODE
fi

# === Post-scan: 解析报告 → 生成JSON → 推送到GitHub ===
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始解析报告..." >> "$LOG_FILE"

cd "$PROJECT_DIR/dashboard"
npx tsx scripts/parse-reports.ts >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 解析成功，开始推送..." >> "$LOG_FILE"
    cd "$PROJECT_DIR"
    git add scanner/reports/ dashboard/src/data/
    git diff --cached --quiet
    if [ $? -ne 0 ]; then
        git commit -m "daily: $(date +%Y-%m-%d) report" >> "$LOG_FILE" 2>&1
        git push origin main >> "$LOG_FILE" 2>&1
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 推送完成，GitHub Actions将自动部署" >> "$LOG_FILE"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 无变更需要提交" >> "$LOG_FILE"
    fi
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 解析失败，跳过推送" >> "$LOG_FILE"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 全部完成" >> "$LOG_FILE"
