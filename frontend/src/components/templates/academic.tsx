"use client";

import React from "react";
import { EditableField } from "../editable-field";
import { SortableList, SortableItem } from "../sortable-section";
import { X } from "lucide-react";
import type { TemplateProps } from "./shared";
import {
  type SectionKey,
  DEFAULT_SECTION_ORDER,
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
    <button
      type="button"
      onClick={onClick}
      className="mt-1 flex items-center gap-1 text-xs text-blue-500 hover:text-blue-700 opacity-60 hover:opacity-100 transition-opacity"
    >
      <span className="inline-block w-4 h-4 leading-4 text-center border border-dashed border-blue-400 rounded">+</span>
      {label}
    </button>
  );
}

function DeleteItemButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="ml-1 shrink-0 text-gray-300 hover:text-red-500 transition-colors"
      title="删除"
    >
      <X className="h-3.5 w-3.5" />
    </button>
  );
}

function MaybeSortable({ enabled, items, onReorder, children }: {
  enabled: boolean;
  items: string[];
  onReorder: (oldIndex: number, newIndex: number) => void;
  children: React.ReactNode;
}) {
  if (!enabled) return <>{children}</>;
  return <SortableList items={items} onReorder={onReorder}>{children}</SortableList>;
}

function MaybeSortableItem({ enabled, id, children }: {
  enabled: boolean;
  id: string;
  children: React.ReactNode;
}) {
  if (!enabled) return <>{children}</>;
  return <SortableItem id={id}>{children}</SortableItem>;
}

/** 学术模板章节标题 - 带左侧竖线装饰 */
function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-2 pb-1.5 border-b border-slate-200">
      <div className="w-1 h-5 bg-slate-700 rounded-full" />
      <h2 className="text-[11pt] font-bold text-slate-800 uppercase tracking-wider">{children}</h2>
    </div>
  );
}

export function AcademicTemplate({ data, editable, onChange }: TemplateProps) {
  const sectionOrder = buildSectionOrder(data, undefined, editable);

  const onSectionReorder = (oldIndex: number, newIndex: number) => {
    handleSectionReorder(data, sectionOrder, oldIndex, newIndex, DEFAULT_SECTION_ORDER, onChange);
  };

  const onItemReorder = (section: string, oldIndex: number, newIndex: number) => {
    handleItemReorder(data, section, oldIndex, newIndex, onChange);
  };

  const renderSection = (key: SectionKey): React.ReactNode => {
    switch (key) {
      case "summary":
        return data.summary || editable ? (
          <section className="mb-4">
            <SectionTitle>个人简介</SectionTitle>
            {data.summary ? (
              <EditableField
                value={data.summary}
                editable={!!editable}
                onChange={(v) => onChange?.(updateData(data, "summary", v))}
                multiline
                className="text-[9.5pt] text-gray-600 text-justify leading-relaxed pl-3 border-l border-slate-300"
                inputClassName="bg-slate-50 rounded px-2 py-1 w-full text-[9.5pt] text-gray-800 min-h-[60px]"
              />
            ) : editable ? (
              <EditableField value="" editable onChange={(v) => onChange?.(updateData(data, "summary", v))} multiline inputClassName="bg-slate-50 rounded px-2 py-1 w-full text-[9.5pt] text-gray-800 min-h-[60px]" placeholder="点击输入个人简介…" />
            ) : null}
          </section>
        ) : null;

      case "education":
        return data.education.length > 0 || editable ? (
          <section className="mb-4">
            <SectionTitle>教育背景</SectionTitle>
            <MaybeSortable enabled={!!editable} items={data.education.map((_, i) => `education-${i}`)} onReorder={(o, n) => onItemReorder("education", o, n)}>
              <div className="space-y-2.5">
                {data.education.map((edu, i) => (
                  <MaybeSortableItem key={`education-${i}`} enabled={!!editable} id={`education-${i}`}>
                    <div className="group/exp-item">
                      <div className="flex justify-between items-baseline">
                        <div>
                          <span className="text-[10.5pt] font-bold text-slate-800">
                            <EditableField value={edu.school} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "education", i, "school", v))} inputClassName="bg-slate-50 rounded px-1 text-[10.5pt] font-bold" placeholder="学校" />
                          </span>
                          {(edu.degree || edu.major || editable) && (
                            <span className="text-[9.5pt] text-gray-500"> &mdash; <EditableField value={edu.degree} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "education", i, "degree", v))} inputClassName="bg-slate-50 rounded px-1 text-[9.5pt]" placeholder="学位" />{edu.degree && edu.major ? "，" : ""}<EditableField value={edu.major} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "education", i, "major", v))} inputClassName="bg-slate-50 rounded px-1 text-[9.5pt]" placeholder="专业" /></span>
                          )}
                        </div>
                        <div className="flex items-center">
                          {edu.period || editable ? <span className="text-[8.5pt] text-slate-500 bg-slate-100 px-2 py-0.5 rounded"><EditableField value={edu.period} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "education", i, "period", v))} inputClassName="bg-slate-50 rounded px-1 text-[8.5pt] w-28" placeholder="时间" /></span> : null}
                          {editable && <DeleteItemButton onClick={() => onChange?.(removeArrayItem(data, "education", i))} />}
                        </div>
                      </div>
                      {edu.achievements.length > 0 && (
                        <ul className="mt-1 space-y-0.5 pl-4">
                          {edu.achievements.map((a, j) => (
                            <li key={j} className="text-[9pt] text-gray-500 list-disc flex items-start gap-1">
                              <span className="flex-1"><EditableField value={a} editable={!!editable} onChange={(v) => onChange?.(updateSubListItem(data, "education", i, j, "achievements", v))} inputClassName="bg-slate-50 rounded px-1 w-full text-[9pt]" /></span>
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

      case "experience":
        return data.experience.length > 0 || editable ? (
          <section className="mb-4">
            <SectionTitle>工作经历</SectionTitle>
            <MaybeSortable enabled={!!editable} items={data.experience.map((_, i) => `experience-${i}`)} onReorder={(o, n) => onItemReorder("experience", o, n)}>
              <div className="space-y-2.5">
                {data.experience.map((exp, i) => (
                  <MaybeSortableItem key={`experience-${i}`} enabled={!!editable} id={`experience-${i}`}>
                    <div className="group/exp-item">
                      <div className="flex justify-between items-baseline">
                        <div>
                          <span className="text-[10.5pt] font-bold text-slate-800">
                            <EditableField value={exp.title} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "experience", i, "title", v))} inputClassName="bg-slate-50 rounded px-1 text-[10.5pt] font-bold" placeholder="职位" />
                          </span>
                          {exp.company || editable ? <span className="text-[9.5pt] text-gray-500"> — <EditableField value={exp.company} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "experience", i, "company", v))} inputClassName="bg-slate-50 rounded px-1 text-[9.5pt]" placeholder="公司" /></span> : null}
                        </div>
                        <div className="flex items-center">
                          {exp.period || editable ? <span className="text-[8.5pt] text-slate-500 bg-slate-100 px-2 py-0.5 rounded"><EditableField value={exp.period} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "experience", i, "period", v))} inputClassName="bg-slate-50 rounded px-1 text-[8.5pt] w-28" placeholder="时间" /></span> : null}
                          {editable && <DeleteItemButton onClick={() => onChange?.(removeArrayItem(data, "experience", i))} />}
                        </div>
                      </div>
                      {exp.highlights.length > 0 && (
                        <ul className="mt-1 space-y-0.5 pl-4">
                          {exp.highlights.map((h, j) => (
                            <li key={j} className="text-[9.5pt] text-gray-600 list-disc flex items-start gap-1">
                              <span className="flex-1"><EditableField value={h} editable={!!editable} onChange={(v) => onChange?.(updateSubListItem(data, "experience", i, j, "highlights", v))} inputClassName="bg-slate-50 rounded px-1 w-full text-[9.5pt]" /></span>
                              {editable && <DeleteItemButton onClick={() => onChange?.(removeSubListItem(data, "experience", i, "highlights", j))} />}
                            </li>
                          ))}
                        </ul>
                      )}
                      {editable && <AddItemButton label="添加工作亮点" onClick={() => { const nd = JSON.parse(JSON.stringify(data)); nd.experience[i].highlights.push(""); onChange?.(nd); }} />}
                    </div>
                  </MaybeSortableItem>
                ))}
              </div>
            </MaybeSortable>
            {editable && <AddItemButton label="添加工作经历" onClick={() => { const nd = JSON.parse(JSON.stringify(data)); nd.experience.push(emptyExperience()); onChange?.(nd); }} />}
          </section>
        ) : null;

      case "skills":
        return data.skills.length > 0 || editable ? (
          <section className="mb-4">
            <SectionTitle>专业技能</SectionTitle>
            <MaybeSortable enabled={!!editable} items={data.skills.map((_, i) => `skills-${i}`)} onReorder={(o, n) => onItemReorder("skills", o, n)}>
              <div className="space-y-2 pl-1">
                {data.skills.map((cat, i) => (
                  <MaybeSortableItem key={`skills-${i}`} enabled={!!editable} id={`skills-${i}`}>
                    <div className="flex items-start gap-1">
                      <div className="flex-1">
                        <span className="text-[9.5pt] font-bold text-slate-700">
                          <EditableField value={cat.category} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "skills", i, "category", v))} inputClassName="bg-slate-50 rounded px-1 text-[9.5pt] font-bold" placeholder="分类" />
                        </span>
                        <div className="flex flex-wrap gap-1.5 mt-0.5">
                          {cat.skills.map((s, j) => (
                            <span key={j} className="text-[8pt] bg-slate-100 text-slate-600 px-2 py-0.5 rounded">{s}</span>
                          ))}
                          {editable && (
                            <EditableField
                              value={cat.skills.join("、")}
                              editable
                              onChange={(v) => onChange?.(updateSkillItems(data, i, v))}
                              inputClassName="bg-slate-50 rounded px-1 text-[8pt] w-full"
                              placeholder="用顿号分隔技能"
                            />
                          )}
                        </div>
                      </div>
                      {editable && <DeleteItemButton onClick={() => onChange?.(removeArrayItem(data, "skills", i))} />}
                    </div>
                  </MaybeSortableItem>
                ))}
              </div>
            </MaybeSortable>
            {editable && <AddItemButton label="添加技能分类" onClick={() => { const nd = JSON.parse(JSON.stringify(data)); nd.skills.push(emptySkillCategory()); onChange?.(nd); }} />}
          </section>
        ) : null;

      case "projects":
        return data.projects.length > 0 || editable ? (
          <section className="mb-4">
            <SectionTitle>项目经历</SectionTitle>
            <MaybeSortable enabled={!!editable} items={data.projects.map((_, i) => `projects-${i}`)} onReorder={(o, n) => onItemReorder("projects", o, n)}>
              <div className="space-y-2.5">
                {data.projects.map((proj, i) => (
                  <MaybeSortableItem key={`projects-${i}`} enabled={!!editable} id={`projects-${i}`}>
                    <div className="group/exp-item">
                      <div className="flex justify-between items-baseline">
                        <div>
                          <span className="text-[10.5pt] font-bold text-slate-800">
                            <EditableField value={proj.name} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "projects", i, "name", v))} inputClassName="bg-slate-50 rounded px-1 text-[10.5pt] font-bold" placeholder="项目名" />
                          </span>
                          {proj.role || editable ? <span className="text-[9pt] text-gray-400"> — <EditableField value={proj.role || ""} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "projects", i, "role", v))} inputClassName="bg-slate-50 rounded px-1 text-[9pt]" placeholder="角色" /></span> : null}
                        </div>
                        <div className="flex items-center">
                          {proj.period || editable ? <span className="text-[8.5pt] text-slate-500 bg-slate-100 px-2 py-0.5 rounded"><EditableField value={proj.period || ""} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "projects", i, "period", v))} inputClassName="bg-slate-50 rounded px-1 text-[8.5pt] w-28" placeholder="时间" /></span> : null}
                          {editable && <DeleteItemButton onClick={() => onChange?.(removeArrayItem(data, "projects", i))} />}
                        </div>
                      </div>
                      {proj.description || editable ? <p className="text-[9pt] text-gray-500 italic mt-0.5"><EditableField value={proj.description || ""} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "projects", i, "description", v))} inputClassName="bg-slate-50 rounded px-1 w-full text-[9pt]" placeholder="项目描述" /></p> : null}
                      {proj.contributions.length > 0 && (
                        <ul className="mt-1 space-y-0.5 pl-4">
                          {proj.contributions.map((c, j) => (
                            <li key={j} className="text-[9.5pt] text-gray-600 list-disc flex items-start gap-1">
                              <span className="flex-1"><EditableField value={c} editable={!!editable} onChange={(v) => onChange?.(updateSubListItem(data, "projects", i, j, "contributions", v))} inputClassName="bg-slate-50 rounded px-1 w-full text-[9.5pt]" /></span>
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
            {editable && <AddItemButton label="添加项目经历" onClick={() => { const nd = JSON.parse(JSON.stringify(data)); nd.projects.push(emptyProject()); onChange?.(nd); }} />}
          </section>
        ) : null;

      default:
        return null;
    }
  };

  return (
    <div className={`w-full bg-white p-6 text-[10.5pt] leading-[1.6] text-gray-800 ${editable ? "pl-8" : ""}`}>
      {/* 头部 */}
      <div className="text-center mb-5 pb-3 border-b-2 border-slate-700">
        <h1 className="text-[20pt] font-bold text-slate-900 tracking-wider mb-2">
          <EditableField value={data.name} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "name", v))} inputClassName="bg-slate-50 rounded px-2 text-[20pt] font-bold text-center w-full" />
        </h1>
        <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-[9pt] text-gray-500">
          {data.contact.email && <span>✉ {data.contact.email}</span>}
          {data.contact.phone && <span>☎ {data.contact.phone}</span>}
          {data.contact.location && <span>📍 {data.contact.location}</span>}
          {data.contact.website && <span>🌐 {data.contact.website}</span>}
          {data.contact.wechat && <span>微信: {data.contact.wechat}</span>}
          {!data.contact.email && !data.contact.phone && data.contact.raw_text && <span>{data.contact.raw_text}</span>}
        </div>
        {editable && (
          <div className="flex flex-wrap gap-1 justify-center mt-2">
            {data.contact.email !== undefined && <EditableField value={data.contact.email} editable={editable} onChange={(v) => onChange?.(updateData(data, "contact.email", v))} inputClassName="bg-slate-50 rounded px-1 text-[9pt] w-40" placeholder="邮箱" />}
            {data.contact.phone !== undefined && <EditableField value={data.contact.phone} editable={editable} onChange={(v) => onChange?.(updateData(data, "contact.phone", v))} inputClassName="bg-slate-50 rounded px-1 text-[9pt] w-32" placeholder="电话" />}
            {data.contact.location !== undefined && <EditableField value={data.contact.location} editable={editable} onChange={(v) => onChange?.(updateData(data, "contact.location", v))} inputClassName="bg-slate-50 rounded px-1 text-[9pt] w-24" placeholder="城市" />}
            {data.contact.wechat !== undefined && <EditableField value={data.contact.wechat} editable={editable} onChange={(v) => onChange?.(updateData(data, "contact.wechat", v))} inputClassName="bg-slate-50 rounded px-1 text-[9pt] w-28" placeholder="微信" />}
          </div>
        )}
      </div>

      <MaybeSortable enabled={!!editable} items={sectionOrder} onReorder={onSectionReorder}>
        {sectionOrder.map(key => (
          <MaybeSortableItem key={key} enabled={!!editable} id={key}>
            {renderSection(key)}
          </MaybeSortableItem>
        ))}
      </MaybeSortable>
    </div>
  );
}
