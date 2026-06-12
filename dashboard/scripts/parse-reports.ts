/**
 * CLI: 读取 scanner/reports/*.md → 输出 dashboard/src/data/posts.json + dates.json
 *
 * 用法: npx tsx scripts/parse-reports.ts
 */
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import { parseAllReports } from "../src/lib/parser.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PROJECT_ROOT = path.resolve(__dirname, "../..");
const REPORTS_DIR = path.join(PROJECT_ROOT, "scanner", "reports");
const DATA_DIR = path.join(__dirname, "..", "src", "data");

function main() {
  console.log("=== Parse Reports ===");
  console.log(`Reports dir: ${REPORTS_DIR}`);
  console.log(`Data dir:    ${DATA_DIR}`);

  // 确保data目录存在
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }

  // 读取所有md文件
  const files = fs.readdirSync(REPORTS_DIR).filter((f) => f.endsWith(".md"));
  console.log(`Found ${files.length} report(s)`);

  if (files.length === 0) {
    console.log("No reports to parse. Exiting.");
    return;
  }

  const fileMap: Record<string, string> = {};
  for (const file of files) {
    const content = fs.readFileSync(path.join(REPORTS_DIR, file), "utf-8");
    fileMap[file] = content;
  }

  // 解析
  const reports = parseAllReports(fileMap);
  console.log(`Parsed ${reports.length} report(s), ${reports.reduce((sum, r) => sum + r.posts.length, 0)} total posts`);

  // 输出 posts.json
  const postsData = { reports };
  fs.writeFileSync(
    path.join(DATA_DIR, "posts.json"),
    JSON.stringify(postsData, null, 2),
    "utf-8"
  );

  // 输出 dates.json
  const dates = reports.map((r) => r.date);
  fs.writeFileSync(
    path.join(DATA_DIR, "dates.json"),
    JSON.stringify(dates, null, 2),
    "utf-8"
  );

  console.log("Done! Output:");
  console.log(`  posts.json: ${(JSON.stringify(postsData).length / 1024).toFixed(1)} KB`);
  console.log(`  dates.json: ${dates.join(", ")}`);
}

main();
