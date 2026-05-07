"use client";

import React from "react";
import { EditableField } from "../editable-field";
import { SortableList, SortableItem, type HandlePosition } from "../sortable-section";
import { X } from "lucide-react";
import type { TemplateProps } from "./shared";
import {
  type SectionKey,
  TWO_COLUMN_KEYS,
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

function MaybeSortableItem({ enabled, id, handlePosition, children }: {
  enabled: boolean;
  id: string;
  handlePosition?: HandlePosition;
  children: React.ReactNode;
}) {
  if (!enabled) return <>{children}</>;
  return <SortableItem id={id} handlePosition={handlePosition}>{children}</SortableItem>;
}

export function ProfessionalTemplate({ data, editable, onChange }: TemplateProps) {
  const mainOrder = buildSectionOrder(data, TWO_COLUMN_KEYS, editable);

  const onSectionReorder = (oldIndex: number, newIndex: number) => {
    handleSectionReorder(data, mainOrder, oldIndex, newIndex, DEFAULT_SECTION_ORDER, onChange);
  };

  const onItemReorder = (section: string, oldIndex: number, newIndex: number) => {
    handleItemReorder(data, section, oldIndex, newIndex, onChange);
  };

  const renderMainSection = (key: SectionKey): React.ReactNode => {
    switch (key) {
      case "summary":
        return data.summary || editable ? (
          <section className="mb-4">
            <h2 className="text-[12pt] font-bold text-slate-800 uppercase tracking-wider pb-1 border-b-2 border-blue-500 mb-2">
              个人简介
            </h2>
            {data.summary ? (
              <EditableField
                value={data.summary}
                editable={!!editable}
                onChange={(v) => onChange?.(updateData(data, "summary", v))}
                multiline
                className="text-[9.5pt] text-gray-600 leading-relaxed"
                inputClassName="bg-blue-50 rounded px-2 py-1 w-full text-[9.5pt] text-gray-800 min-h-[60px]"
              />
            ) : editable ? (
              <EditableField
                value=""
                editable
                onChange={(v) => onChange?.(updateData(data, "summary", v))}
                multiline
                inputClassName="bg-blue-50 rounded px-2 py-1 w-full text-[9.5pt] text-gray-800 min-h-[60px]"
                placeholder="点击输入个人简介…"
              />
            ) : null}
          </section>
        ) : null;

      case "experience":
        return data.experience.length > 0 || editable ? (
          <section className="mb-4">
            <h2 className="text-[12pt] font-bold text-slate-800 uppercase tracking-wider pb-1 border-b-2 border-blue-500 mb-2">
              工作经历
            </h2>
            <MaybeSortable
              enabled={!!editable}
              items={data.experience.map((_, i) => `experience-${i}`)}
              onReorder={(o, n) => onItemReorder("experience", o, n)}
            >
              <div className="space-y-3">
                {data.experience.map((exp, i) => (
                  <MaybeSortableItem key={`experience-${i}`} enabled={!!editable} id={`experience-${i}`} handlePosition="right">
                    <div className="group/exp-item">
                      <div className="flex justify-between items-baseline">
                        <div>
                          <EditableField value={exp.title} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "experience", i, "title", v))} inputClassName="bg-blue-50 rounded px-1 text-[10.5pt] font-bold" placeholder="职位" />
                          {exp.company || editable ? <span className="text-[9.5pt] text-gray-600"> — <EditableField value={exp.company} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "experience", i, "company", v))} inputClassName="bg-blue-50 rounded px-1 text-[9.5pt]" placeholder="公司" /></span> : null}
                        </div>
                        <div className="flex items-center">
                          {exp.period || editable ? <EditableField value={exp.period} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "experience", i, "period", v))} inputClassName="bg-blue-50 rounded px-1 text-[8.5pt] w-32" placeholder="时间" /> : null}
                          {editable && <DeleteItemButton onClick={() => onChange?.(removeArrayItem(data, "experience", i))} />}
                        </div>
                      </div>
                      {exp.highlights.length > 0 && (
                        <ul className="mt-1 space-y-0.5">
                          {exp.highlights.map((h, j) => (
                            <li key={j} className="text-[9pt] text-gray-600 pl-3 relative before:content-['▸'] before:absolute before:left-0 before:text-blue-500 flex items-start gap-1">
                              <span className="flex-1"><EditableField value={h} editable={!!editable} onChange={(v) => onChange?.(updateSubListItem(data, "experience", i, j, "highlights", v))} inputClassName="bg-blue-50 rounded px-1 w-full text-[9pt]" /></span>
                              {editable && <DeleteItemButton onClick={() => onChange?.(removeSubListItem(data, "experience", i, "highlights", j))} />}
                            </li>
                          ))}
                        </ul>
                      )}
                      {editable && (
                        <AddItemButton label="添加工作亮点" onClick={() => {
                          const newData = JSON.parse(JSON.stringify(data));
                          newData.experience[i].highlights.push("");
                          onChange?.(newData);
                        }} />
                      )}
                    </div>
                  </MaybeSortableItem>
                ))}
              </div>
            </MaybeSortable>
            {editable && (
              <AddItemButton label="添加工作经历" onClick={() => {
                const newData = JSON.parse(JSON.stringify(data));
                newData.experience.push(emptyExperience());
                onChange?.(newData);
              }} />
            )}
          </section>
        ) : null;

      case "education":
        return data.education.length > 0 || editable ? (
          <section className="mb-4">
            <h2 className="text-[12pt] font-bold text-slate-800 uppercase tracking-wider pb-1 border-b-2 border-blue-500 mb-2">
              教育背景
            </h2>
            <MaybeSortable
              enabled={!!editable}
              items={data.education.map((_, i) => `education-${i}`)}
              onReorder={(o, n) => onItemReorder("education", o, n)}
            >
              <div className="space-y-2">
                {data.education.map((edu, i) => (
                  <MaybeSortableItem key={`education-${i}`} enabled={!!editable} id={`education-${i}`} handlePosition="right">
                    <div className="group/exp-item">
                      <div className="flex justify-between items-baseline">
                        <div>
                          <EditableField value={edu.school} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "education", i, "school", v))} inputClassName="bg-blue-50 rounded px-1 text-[10pt] font-bold" placeholder="学校" />
                          {(edu.degree || edu.major || editable) && (
                            <span className="text-[9pt] text-gray-600">
                              {" "}&mdash; <EditableField value={edu.degree} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "education", i, "degree", v))} inputClassName="bg-blue-50 rounded px-1 text-[9pt]" placeholder="学位" />
                              {edu.degree && edu.major ? "，" : ""}
                              <EditableField value={edu.major} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "education", i, "major", v))} inputClassName="bg-blue-50 rounded px-1 text-[9pt]" placeholder="专业" />
                            </span>
                          )}
                        </div>
                        <div className="flex items-center">
                          {edu.period || editable ? <EditableField value={edu.period} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "education", i, "period", v))} inputClassName="bg-blue-50 rounded px-1 text-[8.5pt] w-32" placeholder="时间" /> : null}
                          {editable && <DeleteItemButton onClick={() => onChange?.(removeArrayItem(data, "education", i))} />}
                        </div>
                      </div>
                      {edu.achievements.length > 0 && (
                        <ul className="mt-0.5">
                          {edu.achievements.map((a, j) => (
                            <li key={j} className="text-[8.5pt] text-gray-500 pl-3 relative before:content-['•'] before:absolute before:left-0 before:text-blue-500 flex items-start gap-1">
                              <span className="flex-1"><EditableField value={a} editable={!!editable} onChange={(v) => onChange?.(updateSubListItem(data, "education", i, j, "achievements", v))} inputClassName="bg-blue-50 rounded px-1 w-full text-[8.5pt]" /></span>
                              {editable && <DeleteItemButton onClick={() => onChange?.(removeSubListItem(data, "education", i, "achievements", j))} />}
                            </li>
                          ))}
                        </ul>
                      )}
                      {editable && (
                        <AddItemButton label="添加成就" onClick={() => {
                          const newData = JSON.parse(JSON.stringify(data));
                          newData.education[i].achievements.push("");
                          onChange?.(newData);
                        }} />
                      )}
                    </div>
                  </MaybeSortableItem>
                ))}
              </div>
            </MaybeSortable>
            {editable && (
              <AddItemButton label="添加教育经历" onClick={() => {
                const newData = JSON.parse(JSON.stringify(data));
                newData.education.push(emptyEducation());
                onChange?.(newData);
              }} />
            )}
          </section>
        ) : null;

      case "projects":
        return data.projects.length > 0 || editable ? (
          <section className="mb-4">
            <h2 className="text-[12pt] font-bold text-slate-800 uppercase tracking-wider pb-1 border-b-2 border-blue-500 mb-2">
              项目经历
            </h2>
            <MaybeSortable
              enabled={!!editable}
              items={data.projects.map((_, i) => `projects-${i}`)}
              onReorder={(o, n) => onItemReorder("projects", o, n)}
            >
              <div className="space-y-3">
                {data.projects.map((proj, i) => (
                  <MaybeSortableItem key={`projects-${i}`} enabled={!!editable} id={`projects-${i}`} handlePosition="right">
                    <div className="group/exp-item">
                      <div className="flex justify-between items-baseline">
                        <div>
                          <EditableField value={proj.name} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "projects", i, "name", v))} inputClassName="bg-blue-50 rounded px-1 text-[10pt] font-bold" placeholder="项目名" />
                          {proj.role || editable ? <span className="text-[9pt] text-gray-400"> — <EditableField value={proj.role || ""} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "projects", i, "role", v))} inputClassName="bg-blue-50 rounded px-1 text-[9pt]" placeholder="角色" /></span> : null}
                        </div>
                        <div className="flex items-center">
                          {proj.period || editable ? <EditableField value={proj.period || ""} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "projects", i, "period", v))} inputClassName="bg-blue-50 rounded px-1 text-[8.5pt] w-32" placeholder="时间" /> : null}
                          {editable && <DeleteItemButton onClick={() => onChange?.(removeArrayItem(data, "projects", i))} />}
                        </div>
                      </div>
                      {proj.description || editable ? <p className="text-[8.5pt] text-gray-500 italic mt-0.5"><EditableField value={proj.description || ""} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "projects", i, "description", v))} inputClassName="bg-blue-50 rounded px-1 w-full text-[8.5pt]" placeholder="项目描述" /></p> : null}
                      {proj.contributions.length > 0 && (
                        <ul className="mt-1 space-y-0.5">
                          {proj.contributions.map((c, j) => (
                            <li key={j} className="text-[9pt] text-gray-600 pl-3 relative before:content-['▸'] before:absolute before:left-0 before:text-blue-500 flex items-start gap-1">
                              <span className="flex-1"><EditableField value={c} editable={!!editable} onChange={(v) => onChange?.(updateSubListItem(data, "projects", i, j, "contributions", v))} inputClassName="bg-blue-50 rounded px-1 w-full text-[9pt]" /></span>
                              {editable && <DeleteItemButton onClick={() => onChange?.(removeSubListItem(data, "projects", i, "contributions", j))} />}
                            </li>
                          ))}
                        </ul>
                      )}
                      {editable && (
                        <AddItemButton label="添加贡献" onClick={() => {
                          const newData = JSON.parse(JSON.stringify(data));
                          newData.projects[i].contributions.push("");
                          onChange?.(newData);
                        }} />
                      )}
                    </div>
                  </MaybeSortableItem>
                ))}
              </div>
            </MaybeSortable>
            {editable && (
              <AddItemButton label="添加项目经历" onClick={() => {
                const newData = JSON.parse(JSON.stringify(data));
                newData.projects.push(emptyProject());
                onChange?.(newData);
              }} />
            )}
          </section>
        ) : null;

      default:
        return null;
    }
  };

  return (
    <div className="flex w-full bg-white overflow-hidden text-[10pt] leading-[1.5] text-gray-800">
      {/* 侧边栏 */}
      <div className={`w-[38%] bg-slate-800 text-gray-100 p-5 ${editable ? "pr-8" : ""}`}>
        <h1 className="text-[18pt] font-bold text-white mb-1 break-all">
          <EditableField
            value={data.name}
            editable={!!editable}
            onChange={(v) => onChange?.(updateData(data, "name", v))}
            className="bg-transparent text-white font-bold w-full"
            inputClassName="bg-slate-700 text-white rounded px-1 w-full"
          />
        </h1>

        <div className="space-y-0.5 text-[8.5pt] text-gray-400 mt-2">
          {data.contact.email && (
            <p>✉ <EditableField value={data.contact.email} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "contact.email", v))} inputClassName="bg-slate-700 text-gray-100 rounded px-1 w-full text-[8.5pt]" /></p>
          )}
          {data.contact.phone && (
            <p>☎ <EditableField value={data.contact.phone} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "contact.phone", v))} inputClassName="bg-slate-700 text-gray-100 rounded px-1 w-full text-[8.5pt]" /></p>
          )}
          {data.contact.location && (
            <p>📍 <EditableField value={data.contact.location} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "contact.location", v))} inputClassName="bg-slate-700 text-gray-100 rounded px-1 w-full text-[8.5pt]" /></p>
          )}
          {data.contact.website && (
            <p>🌐 <EditableField value={data.contact.website} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "contact.website", v))} inputClassName="bg-slate-700 text-gray-100 rounded px-1 w-full text-[8.5pt]" /></p>
          )}
          {data.contact.wechat && (
            <p>微信: <EditableField value={data.contact.wechat} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "contact.wechat", v))} inputClassName="bg-slate-700 text-gray-100 rounded px-1 w-full text-[8.5pt]" /></p>
          )}
          {!data.contact.email && !data.contact.phone && data.contact.raw_text && (
            <p><EditableField value={data.contact.raw_text} editable={!!editable} onChange={(v) => onChange?.(updateData(data, "contact.raw_text", v))} inputClassName="bg-slate-700 text-gray-100 rounded px-1 w-full text-[8.5pt]" /></p>
          )}
        </div>

        {data.skills.length > 0 || editable ? (
          <div className="mt-4">
            <h2 className="text-[10pt] font-bold text-blue-400 uppercase tracking-wider pb-1 border-b border-slate-600 mb-2">
              专业技能
            </h2>
            <MaybeSortable
              enabled={!!editable}
              items={data.skills.map((_, i) => `skills-${i}`)}
              onReorder={(o, n) => onItemReorder("skills", o, n)}
            >
              <div className="space-y-2">
                {data.skills.map((cat, i) => (
                  <MaybeSortableItem key={`skills-${i}`} enabled={!!editable} id={`skills-${i}`} handlePosition="right">
                    <div className="group/exp-item flex items-start gap-1">
                      <div className="flex-1">
                        <p className="text-[9pt] font-bold text-gray-200">
                          <EditableField value={cat.category} editable={!!editable} onChange={(v) => onChange?.(updateListItem(data, "skills", i, "category", v))} inputClassName="bg-slate-700 text-gray-100 rounded px-1 w-full text-[9pt]" placeholder="分类" />
                        </p>
                        <p className="text-[8.5pt] text-gray-400">
                          <EditableField value={cat.skills.join("、")} editable={!!editable} onChange={(v) => onChange?.(updateSkillItems(data, i, v))} inputClassName="bg-slate-700 text-gray-100 rounded px-1 w-full text-[8.5pt]" placeholder="用顿号分隔技能" />
                        </p>
                      </div>
                      {editable && <DeleteItemButton onClick={() => onChange?.(removeArrayItem(data, "skills", i))} />}
                    </div>
                  </MaybeSortableItem>
                ))}
              </div>
            </MaybeSortable>
            {editable && (
              <AddItemButton label="添加技能分类" onClick={() => {
                const newData = JSON.parse(JSON.stringify(data));
                newData.skills.push(emptySkillCategory());
                onChange?.(newData);
              }} />
            )}
          </div>
        ) : null}
      </div>

      {/* 主内容区 */}
      <div className={`flex-1 p-5 ${editable ? "pl-8 pr-8" : ""}`}>
        <MaybeSortable enabled={!!editable} items={mainOrder} onReorder={onSectionReorder}>
          {mainOrder.map(key => (
            <MaybeSortableItem key={key} enabled={!!editable} id={key} handlePosition="left">
              {renderMainSection(key)}
            </MaybeSortableItem>
          ))}
        </MaybeSortable>
      </div>
    </div>
  );
}
