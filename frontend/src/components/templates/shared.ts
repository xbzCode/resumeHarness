import type { ResumeData } from "@/store/chat";

/** 模板元信息 */
export interface TemplateMeta {
  name: string;
  label: string;
  description: string;
  color: string; // 代表色（用于模板选择 UI）
  category: "professional" | "creative" | "minimal";
}

/** 模板组件 props */
export interface TemplateProps {
  data: ResumeData;
  editable?: boolean;
  onChange?: (data: ResumeData) => void;
}

/** 章节键类型 */
export type SectionKey = "summary" | "experience" | "education" | "skills" | "projects";
export const DEFAULT_SECTION_ORDER: SectionKey[] = ["summary", "experience", "education", "skills", "projects"];
export const TWO_COLUMN_KEYS: SectionKey[] = ["summary", "experience", "education", "projects"];

/** 空白模板数据 */
export function emptyExperience() {
  return { title: "", company: "", period: "", highlights: [] };
}
export function emptyEducation() {
  return { degree: "", major: "", school: "", period: "", achievements: [] };
}
export function emptySkillCategory() {
  return { category: "", skills: [] };
}
export function emptyProject() {
  return { name: "", role: "", period: "", description: "", contributions: [] };
}

/** 深拷贝并更新 ResumeData 的辅助函数 */
export function updateData(data: ResumeData, path: string, value: string): ResumeData {
  const newData = JSON.parse(JSON.stringify(data)) as ResumeData;
  const keys = path.split(".");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let obj: any = newData;
  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    if (Array.isArray(obj)) {
      obj = obj[parseInt(key)];
    } else {
      obj = obj[key];
    }
  }
  const lastKey = keys[keys.length - 1];
  if (Array.isArray(obj)) {
    obj[parseInt(lastKey)] = value;
  } else {
    obj[lastKey] = value;
  }
  return newData;
}

/** 更新列表项的辅助函数 */
export function updateListItem(
  data: ResumeData,
  listPath: string,
  index: number,
  field: string,
  value: string
): ResumeData {
  const newData = JSON.parse(JSON.stringify(data)) as ResumeData;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let obj: any = newData;
  const keys = listPath.split(".");
  for (const key of keys) {
    if (Array.isArray(obj)) {
      obj = obj[parseInt(key)];
    } else {
      obj = obj[key];
    }
  }
  if (Array.isArray(obj) && obj[index]) {
    obj[index][field] = value;
  }
  return newData;
}

/** 更新 highlights/contributions/achievements 中的某一项 */
export function updateSubListItem(
  data: ResumeData,
  listPath: string,
  index: number,
  subIndex: number,
  subField: string,
  value: string
): ResumeData {
  const newData = JSON.parse(JSON.stringify(data)) as ResumeData;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let obj: any = newData;
  const keys = listPath.split(".");
  for (const key of keys) {
    if (Array.isArray(obj)) {
      obj = obj[parseInt(key)];
    } else {
      obj = obj[key];
    }
  }
  if (Array.isArray(obj) && obj[index] && Array.isArray(obj[index][subField])) {
    obj[index][subField][subIndex] = value;
  }
  return newData;
}

/** 更新 skills 列表中某项的 skills 数组 */
export function updateSkillItems(
  data: ResumeData,
  index: number,
  value: string
): ResumeData {
  const newData = JSON.parse(JSON.stringify(data)) as ResumeData;
  if (newData.skills[index]) {
    newData.skills[index].skills = value.split("、").map(s => s.trim()).filter(Boolean);
  }
  return newData;
}

/** 重排数组 */
export function reorderArray<T>(array: T[], oldIndex: number, newIndex: number): T[] {
  const newArray = [...array];
  const [moved] = newArray.splice(oldIndex, 1);
  newArray.splice(newIndex, 0, moved);
  return newArray;
}

/** 检查章节是否有内容（编辑模式下始终视为有内容） */
export function hasSectionContent(data: ResumeData, key: string, editable?: boolean): boolean {
  if (editable) return true;
  switch (key) {
    case "summary": return !!data.summary;
    case "experience": return data.experience.length > 0;
    case "education": return data.education.length > 0;
    case "skills": return data.skills.length > 0;
    case "projects": return data.projects.length > 0;
    default: return false;
  }
}

/** 构建章节显示顺序 */
export function buildSectionOrder(data: ResumeData, allowedKeys?: SectionKey[], editable?: boolean): SectionKey[] {
  const keys = allowedKeys || DEFAULT_SECTION_ORDER;
  const order = (data.section_order || DEFAULT_SECTION_ORDER) as SectionKey[];
  const result: SectionKey[] = [];

  for (const key of order) {
    if (keys.includes(key) && hasSectionContent(data, key, editable) && !result.includes(key)) {
      result.push(key);
    }
  }
  for (const key of keys) {
    if (!result.includes(key) && hasSectionContent(data, key, editable)) {
      result.push(key);
    }
  }
  return result;
}

/** 重排章节后更新 section_order */
export function handleSectionReorder(
  data: ResumeData,
  currentOrder: SectionKey[],
  oldIndex: number,
  newIndex: number,
  allKeys: SectionKey[],
  onChange?: (data: ResumeData) => void
) {
  const reordered = reorderArray(currentOrder, oldIndex, newIndex);
  const fullOrder: string[] = [...reordered];
  const baseOrder = data.section_order || DEFAULT_SECTION_ORDER;
  for (const key of baseOrder) {
    if (!allKeys.includes(key as SectionKey) && !fullOrder.includes(key)) {
      fullOrder.push(key);
    }
  }
  for (const key of DEFAULT_SECTION_ORDER) {
    if (!fullOrder.includes(key)) {
      fullOrder.push(key);
    }
  }
  onChange?.({ ...JSON.parse(JSON.stringify(data)), section_order: fullOrder });
}

/** 重排章节内条目 */
export function handleItemReorder(
  data: ResumeData,
  section: string,
  oldIndex: number,
  newIndex: number,
  onChange?: (data: ResumeData) => void
) {
  const newData = JSON.parse(JSON.stringify(data)) as ResumeData;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const arr = (newData as any)[section] as any[];
  if (Array.isArray(arr)) {
    const [moved] = arr.splice(oldIndex, 1);
    arr.splice(newIndex, 0, moved);
  }
  onChange?.(newData);
}

/** 从数组中删除一项 */
export function removeArrayItem(data: ResumeData, path: string, index: number): ResumeData {
  const newData = JSON.parse(JSON.stringify(data)) as ResumeData;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let obj: any = newData;
  const keys = path.split(".");
  for (const key of keys) {
    if (Array.isArray(obj)) {
      obj = obj[parseInt(key)];
    } else {
      obj = obj[key];
    }
  }
  if (Array.isArray(obj)) {
    obj.splice(index, 1);
  }
  return newData;
}

/** 从子列表中删除一项 */
export function removeSubListItem(
  data: ResumeData,
  listPath: string,
  index: number,
  subField: string,
  subIndex: number
): ResumeData {
  const newData = JSON.parse(JSON.stringify(data)) as ResumeData;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let obj: any = newData;
  const keys = listPath.split(".");
  for (const key of keys) {
    if (Array.isArray(obj)) {
      obj = obj[parseInt(key)];
    } else {
      obj = obj[key];
    }
  }
  if (Array.isArray(obj) && obj[index] && Array.isArray(obj[index][subField])) {
    obj[index][subField].splice(subIndex, 1);
  }
  return newData;
}
