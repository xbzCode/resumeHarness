"use client";

import React from "react";
import { EditableField } from "../editable-field";
import { SortableList, SortableItem } from "../sortable-section";
import { X } from "lucide-react";
import type { TemplateProps } from "./shared";
import {
  type SectionKey,
  DEFAULT_SECTION_ORDER,
  TWO_COLUMN_KEYS,
  emptyExperience,
  emptyEducation,
  emptySkillCategory,
  emptyProject,
  updateData,
  updateListItem,
  updateSubListItem,
  updateSkillItems,
  buildSectionOrder,
  handleSectionReorder,
  handleItemReorder,
  removeArrayItem,
  removeSubListItem,
} from "./shared";

function AddItemButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="mt-1 flex items-center gap-1 text-xs text-amber-600 hover:text-amber-800 opacity-60 hover:opacity-100 transition-opacity">
      <span className="inline-block w-4 h-4 leading-4 text-center border border-dashed border-amber-400 rounded">+</span>
      {label}
    </button>
  );
}
function DeleteItemButton({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="ml-1 shrink-0 text-gray-300 hover:text-red-500 transition-colors" title="删除">
      <X className="h-3.5 w-3.5" />
    </button>
  );
}
function MaybeSortable({ enabled, items, onReorder, children }: { enabled: boolean; items: string[]; onReorder: (o: number, n: number) => void; children: React.ReactNode }) {
  if (!enabled) return <>{children}</>;
  return <SortableList items={items} onReorder={onReorder}>{children}</SortableList>;
}
function MaybeSortableItem({ enabled, id, children }: { enabled: boolean; id: string; children: React.ReactNode }) {
  if (!enabled) return <>{children}</>;
  return <SortableItem id={id}>{children}</SortableItem>;
}

/** 优雅模板侧边栏章节标题 */
function SideSectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-[10pt] font-bold text-amber-600 uppercase tracking-[0.15em] mb-2 pb-1 border-b border-amber-700/30">
      {children}
    </h2>
  );
}

export function ElegantTemplate({ data, editable, onChange }: TemplateProps) {
  const mainOrder = buildSectionOrder(data, TWO_COLUMN_KEYS, editable);
  const onSectionReorder = (o: number, n: number) => handleSectionReorder(data, mainOrder, o, n, DEFAULT_SECTION_ORDER, onChange);
  const onItemReorder = (s: string, o: number, n: number) => handleItemReorder(data, s, o, n, onChange);

  const renderMainSection = (key: SectionKey): React.ReactNode => {
    switch (key) {
      case "summary":
        return data.summary || editable ? (
          <section className="mb-5">
            <h2 className="text-[11pt] font-bold text-navy-900 uppercase tracking-wider mb-2 pb-1 border-b-2 border-amber-500">个人简介</h2>
            {data.summary ? (
              <EditableField value={data.summary} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "summary", v))} multiline className="text-[9.5pt] text-gray-600 leading-relaxed" inputClassName="bg-amber-50/50 rounded px-2 py-1 w-full text-[9.5pt] min-h-[60px]" />
            ) : editable ? (
              <EditableField value="" editable onChange={(v) => onChange?.(updateData(data, "summary", v))} multiline inputClassName="bg-amber-50/50 rounded px-2 py-1 w-full text-[9.5pt] min-h-[60px]" placeholder="个人简介…" />
            ) : null}
          </section>
        ) : null;

      case "experience":
        return data.experience.length > 0 || editable ? (
          <section className="mb-5">
            <h2 className="text-[11pt] font-bold text-navy-900 uppercase tracking-wider mb-2 pb-1 border-b-2 border-amber-500">工作经历</h2>
            <MaybeSortable enabled={!!editable} items={data.experience.map((_, i) => `experience-${i}`)} onReorder={(o, n) => onItemReorder("experience", o, n)}>
              <div className="space-y-3">
                {data.experience.map((exp, i) => (
                  <MaybeSortableItem key={`experience-${i}`} enabled={!!editable} id={`experience-${i}`}>
                    <div className="group/exp-item">
                      <div className="flex justify-between items-baseline">
                        <div>
                          <span className="text-[10.5pt] font-bold text-gray-900"><EditableField value={exp.title} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "experience", i, "title", v))} inputClassName="bg-amber-50/50 rounded px-1 text-[10.5pt] font-bold" placeholder="职位" /></span>
                          {exp.company || editable ? <span className="text-[9.5pt] text-gray-500 italic ml-1"><EditableField value={exp.company} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "experience", i, "company", v))} inputClassName="bg-amber-50/50 rounded px-1 text-[9.5pt]" placeholder="公司" /></span> : null}
                        </div>
                        <div className="flex items-center">
                          {exp.period || editable ? <span className="text-[8.5pt] text-amber-700 font-medium"><EditableField value={exp.period} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "experience", i, "period", v))} inputClassName="bg-amber-50/50 rounded px-1 text-[8.5pt] w-28" placeholder="时间" /></span> : null}
                          {editable && <DeleteItemButton onClick={() => onChange?.(removeArrayItem(data, "experience", i))} />}
                        </div>
                      </div>
                      {exp.highlights.length > 0 && (
                        <ul className="mt-1 space-y-0.5">
                          {exp.highlights.map((h, j) => (
                            <li key={j} className="text-[9pt] text-gray-600 pl-4 relative before:content-['◇'] before:absolute before:left-0 before:text-amber-500 before:text-[7pt] before:top-[4px] flex items-start gap-1">
                              <span className="flex-1"><EditableField value={h} editable={!!editable} onChange={(v) => onChange?.(updateSubListItem(data, "experience", i, j, "highlights", v))} inputClassName="bg-amber-50/50 rounded px-1 w-full text-[9pt]" /></span>
                              {editable && <DeleteItemButton onClick={() => onChange?.(removeSubListItem(data, "experience", i, "highlights", j))} />}
                            </li>
                          ))}
                        </ul>
                      )}
                      {editable && <AddItemButton label="添加亮点" onClick={() => { const nd = JSON.parse(JSON.stringify(data)); nd.experience[i].highlights.push(""); onChange?.(nd); }} />}
                    </div>
                  </MaybeSortableItem>
                ))}
              </div>
            </MaybeSortable>
            {editable && <AddItemButton label="添加工作经历" onClick={() => { const nd = JSON.parse(JSON.stringify(data)); nd.experience.push(emptyExperience()); onChange?.(nd); }} />}
          </section>
        ) : null;

      case "education":
        return data.education.length > 0 || editable ? (
          <section className="mb-5">
            <h2 className="text-[11pt] font-bold text-navy-900 uppercase tracking-wider mb-2 pb-1 border-b-2 border-amber-500">教育背景</h2>
            <MaybeSortable enabled={!!editable} items={data.education.map((_, i) => `education-${i}`)} onReorder={(o, n) => onItemReorder("education", o, n)}>
              <div className="space-y-2">
                {data.education.map((edu, i) => (
                  <MaybeSortableItem key={`education-${i}`} enabled={!!editable} id={`education-${i}`}>
                    <div className="group/exp-item">
                      <div className="flex justify-between items-baseline">
                        <div>
                          <span className="text-[10pt] font-bold text-gray-900"><EditableField value={edu.school} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "education", i, "school", v))} inputClassName="bg-amber-50/50 rounded px-1 text-[10pt] font-bold" placeholder="学校" /></span>
                          <span className="text-[9pt] text-gray-500 italic ml-1"><EditableField value={[edu.degree, edu.major].filter(Boolean).join(" · ")} editable={false} onChange={() => {}} /></span>
                        </div>
                        <div className="flex items-center">
                          {edu.period || editable ? <span className="text-[8.5pt] text-amber-700 font-medium"><EditableField value={edu.period} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "education", i, "period", v))} inputClassName="bg-amber-50/50 rounded px-1 text-[8.5pt] w-28" placeholder="时间" /></span> : null}
                          {editable && <DeleteItemButton onClick={() => onChange?.(removeArrayItem(data, "education", i))} />}
                        </div>
                      </div>
                      {edu.achievements.length > 0 && (
                        <ul className="mt-0.5 space-y-0.5">
                          {edu.achievements.map((a, j) => (
                            <li key={j} className="text-[8.5pt] text-gray-500 pl-4 relative before:content-['◇'] before:absolute before:left-0 before:text-amber-500 before:text-[7pt] before:top-[4px] flex items-start gap-1">
                              <span className="flex-1"><EditableField value={a} editable={!!editable} onChange={(v) => onChange?.(updateSubListItem(data, "education", i, j, "achievements", v))} inputClassName="bg-amber-50/50 rounded px-1 w-full text-[8.5pt]" /></span>
                              {editable && <DeleteItemButton onClick={() => onChange?.(removeSubListItem(data, "education", i, "achievements", j))} />}
                            </li>
                          ))}
                        </ul>
                      )}
                      {editable && <AddItemButton label="添加成就" onClick={() => { const nd = JSON.parse(JSON.stringify(data)); nd.education[i].achievements.push(""); onChange?.(nd); }} />}
                    </div>
                  </MaybeSortableItem>
                ))}
              </div>
            </MaybeSortable>
            {editable && <AddItemButton label="添加教育经历" onClick={() => { const nd = JSON.parse(JSON.stringify(data)); nd.education.push(emptyEducation()); onChange?.(nd); }} />}
          </section>
        ) : null;

      case "projects":
        return data.projects.length > 0 || editable ? (
          <section className="mb-5">
            <h2 className="text-[11pt] font-bold text-navy-900 uppercase tracking-wider mb-2 pb-1 border-b-2 border-amber-500">项目经历</h2>
            <MaybeSortable enabled={!!editable} items={data.projects.map((_, i) => `projects-${i}`)} onReorder={(o, n) => onItemReorder("projects", o, n)}>
              <div className="space-y-3">
                {data.projects.map((proj, i) => (
                  <MaybeSortableItem key={`projects-${i}`} enabled={!!editable} id={`projects-${i}`}>
                    <div className="group/exp-item">
                      <div className="flex justify-between items-baseline">
                        <div>
                          <span className="text-[10pt] font-bold text-gray-900"><EditableField value={proj.name} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "projects", i, "name", v))} inputClassName="bg-amber-50/50 rounded px-1 text-[10pt] font-bold" placeholder="项目名" /></span>
                          {proj.role || editable ? <span className="text-[9pt] text-gray-400 italic ml-1"><EditableField value={proj.role || ""} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "projects", i, "role", v))} inputClassName="bg-amber-50/50 rounded px-1 text-[9pt]" placeholder="角色" /></span> : null}
                        </div>
                        <div className="flex items-center">
                          {proj.period || editable ? <span className="text-[8.5pt] text-amber-700 font-medium"><EditableField value={proj.period || ""} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "projects", i, "period", v))} inputClassName="bg-amber-50/50 rounded px-1 text-[8.5pt] w-28" placeholder="时间" /></span> : null}
                          {editable && <DeleteItemButton onClick={() => onChange?.(removeArrayItem(data, "projects", i))} />}
                        </div>
                      </div>
                      {proj.description || editable ? <p className="text-[9pt] text-gray-500 italic mt-0.5"><EditableField value={proj.description || ""} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "projects", i, "description", v))} inputClassName="bg-amber-50/50 rounded px-1 w-full text-[9pt]" placeholder="描述" /></p> : null}
                      {proj.contributions.length > 0 && (
                        <ul className="mt-1 space-y-0.5">
                          {proj.contributions.map((c, j) => (
                            <li key={j} className="text-[9pt] text-gray-600 pl-4 relative before:content-['◇'] before:absolute before:left-0 before:text-amber-500 before:text-[7pt] before:top-[4px] flex items-start gap-1">
                              <span className="flex-1"><EditableField value={c} editable={!!editable} onChange={(v) => onChange?.(updateSubListItem(data, "projects", i, j, "contributions", v))} inputClassName="bg-amber-50/50 rounded px-1 w-full text-[9pt]" /></span>
                              {editable && <DeleteItemButton onClick={() => onChange?.(removeSubListItem(data, "projects", i, "contributions", j))} />}
                            </li>
                          ))}
                        </ul>
                      )}
                      {editable && <AddItemButton label="添加贡献" onClick={() => { const nd = JSON.parse(JSON.stringify(data)); nd.projects[i].contributions.push(""); onChange?.(nd); }} />}
                    </div>
                  </MaybeSortableItem>
                ))}
              </div>
            </MaybeSortable>
            {editable && <AddItemButton label="添加项目" onClick={() => { const nd = JSON.parse(JSON.stringify(data)); nd.projects.push(emptyProject()); onChange?.(nd); }} />}
          </section>
        ) : null;

      default: return null;
    }
  };

  return (
    <div className="flex w-full bg-white overflow-hidden text-[10pt] leading-[1.5] text-gray-800">
      {/* 深蓝侧边栏 */}
      <div className="w-[36%] bg-[#1a2332] text-gray-200 p-5">
        <h1 className="text-[18pt] font-bold text-white mb-1 break-all">
          <EditableField value={data.name} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "name", v))} className="text-white font-bold w-full" inputClassName="bg-[#243447] text-white rounded px-1 w-full" />
        </h1>

        <div className="w-10 h-0.5 bg-amber-500 mt-2 mb-3" />

        <div className="space-y-1 text-[8.5pt] text-gray-400">
          {data.contact.email && <p>✉ <EditableField value={data.contact.email} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "contact.email", v))} inputClassName="bg-[#243447] text-gray-200 rounded px-1 w-full text-[8.5pt]" /></p>}
          {data.contact.phone && <p>☎ <EditableField value={data.contact.phone} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "contact.phone", v))} inputClassName="bg-[#243447] text-gray-200 rounded px-1 w-full text-[8.5pt]" /></p>}
          {data.contact.location && <p>📍 <EditableField value={data.contact.location} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "contact.location", v))} inputClassName="bg-[#243447] text-gray-200 rounded px-1 w-full text-[8.5pt]" /></p>}
          {data.contact.website && <p>🌐 <EditableField value={data.contact.website} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "contact.website", v))} inputClassName="bg-[#243447] text-gray-200 rounded px-1 w-full text-[8.5pt]" /></p>}
          {data.contact.wechat && <p>微信: <EditableField value={data.contact.wechat} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "contact.wechat", v))} inputClassName="bg-[#243447] text-gray-200 rounded px-1 w-full text-[8.5pt]" /></p>}
          {!data.contact.email && !data.contact.phone && data.contact.raw_text && <p><EditableField value={data.contact.raw_text} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "contact.raw_text", v))} inputClassName="bg-[#243447] text-gray-200 rounded px-1 w-full text-[8.5pt]" /></p>}
        </div>

        {data.skills.length > 0 || editable ? (
          <div className="mt-5">
            <SideSectionTitle>专业技能</SideSectionTitle>
            <MaybeSortable enabled={!!editable} items={data.skills.map((_, i) => `skills-${i}`)} onReorder={(o, n) => onItemReorder("skills", o, n)}>
              <div className="space-y-2">
                {data.skills.map((cat, i) => (
                  <MaybeSortableItem key={`skills-${i}`} enabled={!!editable} id={`skills-${i}`}>
                    <div className="group/exp-item flex items-start gap-1">
                      <div className="flex-1">
                        <p className="text-[9pt] font-bold text-amber-400"><EditableField value={cat.category} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "skills", i, "category", v))} inputClassName="bg-[#243447] text-gray-200 rounded px-1 w-full text-[9pt]" placeholder="分类" /></p>
                        <p className="text-[8.5pt] text-gray-400"><EditableField value={cat.skills.join(" · ")} editable={!!editable} onChange={(v) => onChange?.(updateSkillItems(data, i, v))} inputClassName="bg-[#243447] text-gray-200 rounded px-1 w-full text-[8.5pt]" placeholder="用中点分隔技能" /></p>
                      </div>
                      {editable && <DeleteItemButton onClick={() => onChange?.(removeArrayItem(data, "skills", i))} />}
                    </div>
                  </MaybeSortableItem>
                ))}
              </div>
            </MaybeSortable>
            {editable && <AddItemButton label="添加技能分类" onClick={() => { const nd = JSON.parse(JSON.stringify(data)); nd.skills.push(emptySkillCategory()); onChange?.(nd); }} />}
          </div>
        ) : null}
      </div>

      {/* 主内容区 */}
      <div className={`flex-1 p-5 ${editable ? "pl-8" : ""}`}>
        <MaybeSortable enabled={!!editable} items={mainOrder} onReorder={onSectionReorder}>
          {mainOrder.map(key => (
            <MaybeSortableItem key={key} enabled={!!editable} id={key}>
              {renderMainSection(key)}
            </MaybeSortableItem>
          ))}
        </MaybeSortable>
      </div>
    </div>
  );
}
