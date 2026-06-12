/** 标准分类定义 */
export type CategoryKey = "tour_guide" | "medical" | "translation" | "living" | "general";

export interface CategoryDef {
  key: CategoryKey;
  label: string;
  emoji: string;
  keywords: string[];
}

export const CATEGORIES: CategoryDef[] = [
  {
    key: "tour_guide",
    label: "旅游向导",
    emoji: "✈️",
    keywords: ["旅游", "向导", "guide", "tour", "trip", "travel", "visit", "游览", "景点"],
  },
  {
    key: "medical",
    label: "医疗协助",
    emoji: "🏥",
    keywords: ["医疗", "medical", "hospital", "doctor", "医院", "诊所", "clinic", "dentist", "surgery"],
  },
  {
    key: "translation",
    label: "翻译协助",
    emoji: "🗣️",
    keywords: ["翻译", "translator", "translation", "translate", "语言", "language", "english"],
  },
  {
    key: "living",
    label: "生活帮助",
    emoji: "🏠",
    keywords: ["生活", "living", "move", "moving", "expat", "搬到", "居住", "搬家", "社区", "apartment"],
  },
];

/** 从需求类型文本推断标准分类 */
export function normalizeCategory(raw: string): CategoryKey {
  const lower = raw.toLowerCase();
  for (const cat of CATEGORIES) {
    if (cat.keywords.some((kw) => lower.includes(kw))) {
      return cat.key;
    }
  }
  return "general";
}

/** 获取分类显示信息 */
export function getCategoryInfo(key: CategoryKey): CategoryDef {
  return CATEGORIES.find((c) => c.key === key) || { key: "general", label: "其他", emoji: "📌", keywords: [] };
}
