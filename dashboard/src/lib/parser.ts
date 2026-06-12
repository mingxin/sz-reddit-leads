import { normalizeCategory, type CategoryKey } from "./categories";

export interface Post {
  id: number;
  title: string;
  url: string;
  subreddit: string;
  author: string;
  category: CategoryKey;
  categoryRaw: string;
  summary: string;
}

export interface DailyReport {
  date: string;
  generatedAt: string;
  totalCount: number;
  posts: Post[];
  priority: string;
}

/**
 * 解析单份markdown报告，提取结构化数据。
 * 格式弹性：兼容LLM输出的多种微小变化。
 */
export function parseReport(markdown: string, filename: string): DailyReport {
  const date = filename.replace(/\.md$/, "");

  // 提取生成时间
  const genMatch = markdown.match(/生成时间[：:]\s*(.+)/);
  const generatedAt = genMatch ? genMatch[1].trim() : date;

  // 提取总数
  const countMatch = markdown.match(/发现相关帖子[：:]\s*(\d+)\s*条/);
  const totalCount = countMatch ? parseInt(countMatch[1], 10) : 0;

  // 提取重点关注（在 📋 汇总之前、最后一个 --- 之后的内容）
  let priority = "";
  const priorityMatch = markdown.match(/## 💡 重点关注([\s\S]*?)$/);
  if (priorityMatch) {
    priority = priorityMatch[1].trim();
  }

  // 按 "## N. " 分割帖子段落
  const postSections = markdown.split(/\n(?=## \d+\. )/);
  const posts: Post[] = [];

  for (const section of postSections) {
    // 跳过非帖子段落
    const titleMatch = section.match(/^## (\d+)\.\s*(.+)/);
    if (!titleMatch) continue;

    const id = parseInt(titleMatch[1], 10);
    const title = titleMatch[2].trim();

    // 提取元数据（兼容 **key**: value 和 **key：** value 两种格式）
    const urlMatch =
      section.match(/\*\*链接\*\*[：:]\s*(.+)/) ||
      section.match(/\*\*URL\*\*[：:]\s*(.+)/) ||
      section.match(/\*\*Link\*\*[：:]\s*(.+)/);
    const url = urlMatch ? urlMatch[1].trim() : "";

    const subMatch =
      section.match(/\*\*Subreddit\*\*[：:]\s*(.+)/) ||
      section.match(/\*\*社区\*\*[：:]\s*(.+)/);
    const subreddit = subMatch ? subMatch[1].trim() : "";

    const authorMatch =
      section.match(/\*\*作者\*\*[：:]\s*(.+)/) ||
      section.match(/\*\*Author\*\*[：:]\s*(.+)/);
    const author = authorMatch ? authorMatch[1].trim() : "未知";

    const catMatch =
      section.match(/\*\*需求类型\*\*[：:]\s*(.+)/) ||
      section.match(/\*\*Category\*\*[：:]\s*(.+)/);
    const categoryRaw = catMatch ? catMatch[1].trim() : "general";

    // 提取摘要
    const summaryMatch =
      section.match(/\*\*内容摘要\*\*[：:：]\s*([\s\S]+?)(?=\n---|\n##|$)/) ||
      section.match(/\*\*摘要\*\*[：:：]\s*([\s\S]+?)(?=\n---|\n##|$)/);
    const summary = summaryMatch
      ? summaryMatch[1].replace(/\n\s*/g, " ").trim()
      : "";

    if (title && url) {
      posts.push({
        id,
        title,
        url,
        subreddit,
        author,
        category: normalizeCategory(categoryRaw),
        categoryRaw,
        summary,
      });
    }
  }

  return { date, generatedAt, totalCount: posts.length || totalCount, posts, priority };
}

/**
 * 解析所有报告文件
 */
export function parseAllReports(fileMap: Record<string, string>): DailyReport[] {
  const reports: DailyReport[] = [];

  for (const [filename, content] of Object.entries(fileMap)) {
    if (!filename.endsWith(".md")) continue;
    // 跳过空或明显无效的文件
    if (!content.includes("深圳") && !content.includes("Shenzhen") && !content.includes("shenzhen")) continue;
    reports.push(parseReport(content, filename));
  }

  // 按日期降序
  reports.sort((a, b) => b.date.localeCompare(a.date));
  return reports;
}
