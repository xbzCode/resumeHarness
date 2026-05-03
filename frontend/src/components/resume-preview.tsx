"use client";

import { ResumeData } from "@/store/chat";

interface ResumePreviewProps {
  data: ResumeData;
  template?: string;
}

export function ResumePreview({ data, template = "professional" }: ResumePreviewProps) {
  if (template === "professional") {
    return <ProfessionalTemplate data={data} />;
  }
  if (template === "academic") {
    return <AcademicTemplate data={data} />;
  }
  if (template === "creative") {
    return <CreativeTemplate data={data} />;
  }
  return <ProfessionalTemplate data={data} />;
}

/* ============================================================
 * Professional 模板 - 双栏侧边栏布局
 * ============================================================ */
function ProfessionalTemplate({ data }: { data: ResumeData }) {
  return (
    <div className="flex w-full max-w-[800px] mx-auto bg-white shadow-lg rounded-lg overflow-hidden text-[10pt] leading-[1.5] text-gray-800">
      {/* 侧边栏 */}
      <div className="w-[38%] bg-slate-800 text-gray-100 p-5">
        <h1 className="text-[18pt] font-bold text-white mb-1 break-all">
          {data.name}
        </h1>

        <div className="space-y-0.5 text-[8.5pt] text-gray-400 mt-2">
          {data.contact.email && <p>✉ {data.contact.email}</p>}
          {data.contact.phone && <p>☎ {data.contact.phone}</p>}
          {data.contact.location && <p>📍 {data.contact.location}</p>}
          {data.contact.website && <p>🌐 {data.contact.website}</p>}
          {data.contact.wechat && <p>微信: {data.contact.wechat}</p>}
          {!data.contact.email && !data.contact.phone && data.contact.raw_text && (
            <p>{data.contact.raw_text}</p>
          )}
        </div>

        {data.skills.length > 0 && (
          <div className="mt-4">
            <h2 className="text-[10pt] font-bold text-blue-400 uppercase tracking-wider pb-1 border-b border-slate-600 mb-2">
              专业技能
            </h2>
            <div className="space-y-2">
              {data.skills.map((cat, i) => (
                <div key={i}>
                  <p className="text-[9pt] font-bold text-gray-200">{cat.category}</p>
                  <p className="text-[8.5pt] text-gray-400">{cat.skills.join("、")}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 主内容区 */}
      <div className="flex-1 p-5">
        {data.summary && (
          <section className="mb-4">
            <h2 className="text-[12pt] font-bold text-slate-800 uppercase tracking-wider pb-1 border-b-2 border-blue-500 mb-2">
              个人简介
            </h2>
            <p className="text-[9.5pt] text-gray-600 leading-relaxed">{data.summary}</p>
          </section>
        )}

        {data.experience.length > 0 && (
          <section className="mb-4">
            <h2 className="text-[12pt] font-bold text-slate-800 uppercase tracking-wider pb-1 border-b-2 border-blue-500 mb-2">
              工作经历
            </h2>
            <div className="space-y-3">
              {data.experience.map((exp, i) => (
                <div key={i}>
                  <div className="flex justify-between items-baseline">
                    <div>
                      <span className="text-[10.5pt] font-bold text-slate-800">{exp.title}</span>
                      {exp.company && <span className="text-[9.5pt] text-gray-600"> — {exp.company}</span>}
                    </div>
                    {exp.period && <span className="text-[8.5pt] text-gray-400 whitespace-nowrap">{exp.period}</span>}
                  </div>
                  {exp.highlights.length > 0 && (
                    <ul className="mt-1 space-y-0.5">
                      {exp.highlights.map((h, j) => (
                        <li key={j} className="text-[9pt] text-gray-600 pl-3 relative before:content-['▸'] before:absolute before:left-0 before:text-blue-500">
                          {h}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {data.education.length > 0 && (
          <section className="mb-4">
            <h2 className="text-[12pt] font-bold text-slate-800 uppercase tracking-wider pb-1 border-b-2 border-blue-500 mb-2">
              教育背景
            </h2>
            <div className="space-y-2">
              {data.education.map((edu, i) => (
                <div key={i}>
                  <div className="flex justify-between items-baseline">
                    <div>
                      <span className="text-[10pt] font-bold text-slate-800">{edu.school}</span>
                      {(edu.degree || edu.major) && (
                        <span className="text-[9pt] text-gray-600">
                          {" "}&mdash; {edu.degree}{edu.degree && edu.major ? "，" : ""}{edu.major}
                        </span>
                      )}
                    </div>
                    {edu.period && <span className="text-[8.5pt] text-gray-400">{edu.period}</span>}
                  </div>
                  {edu.achievements.length > 0 && (
                    <ul className="mt-0.5">
                      {edu.achievements.map((a, j) => (
                        <li key={j} className="text-[8.5pt] text-gray-500 pl-3 relative before:content-['•'] before:absolute before:left-0 before:text-blue-500">
                          {a}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {data.projects.length > 0 && (
          <section className="mb-4">
            <h2 className="text-[12pt] font-bold text-slate-800 uppercase tracking-wider pb-1 border-b-2 border-blue-500 mb-2">
              项目经历
            </h2>
            <div className="space-y-3">
              {data.projects.map((proj, i) => (
                <div key={i}>
                  <div className="flex justify-between items-baseline">
                    <div>
                      <span className="text-[10pt] font-bold text-slate-800">{proj.name}</span>
                      {proj.role && <span className="text-[9pt] text-gray-400"> — {proj.role}</span>}
                    </div>
                    {proj.period && <span className="text-[8.5pt] text-gray-400">{proj.period}</span>}
                  </div>
                  {proj.description && <p className="text-[8.5pt] text-gray-500 italic mt-0.5">{proj.description}</p>}
                  {proj.contributions.length > 0 && (
                    <ul className="mt-1 space-y-0.5">
                      {proj.contributions.map((c, j) => (
                        <li key={j} className="text-[9pt] text-gray-600 pl-3 relative before:content-['▸'] before:absolute before:left-0 before:text-blue-500">
                          {c}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

/* ============================================================
 * Academic 模板 - 传统单栏居中布局
 * ============================================================ */
function AcademicTemplate({ data }: { data: ResumeData }) {
  return (
    <div className="w-full max-w-[800px] mx-auto bg-white shadow-lg rounded-lg p-6 text-[10.5pt] leading-[1.6] text-gray-800">
      {/* 头部 */}
      <div className="text-center mb-4 pb-3 border-b border-gray-800">
        <h1 className="text-[20pt] font-bold text-gray-900 tracking-wider mb-1.5">{data.name}</h1>
        <p className="text-[9pt] text-gray-500">
          {[data.contact.email, data.contact.phone, data.contact.location, data.contact.website]
            .filter(Boolean)
            .join(" | ")}
          {data.contact.wechat && ` | 微信: ${data.contact.wechat}`}
          {!data.contact.email && !data.contact.phone && data.contact.raw_text && data.contact.raw_text}
        </p>
      </div>

      {data.summary && (
        <section className="mb-3">
          <h2 className="text-[11pt] font-bold text-gray-900 uppercase tracking-wider pb-1 border-b border-blue-900 mb-2">
            个人简介
          </h2>
          <p className="text-[9.5pt] text-gray-600 text-justify leading-relaxed">{data.summary}</p>
        </section>
      )}

      {data.education.length > 0 && (
        <section className="mb-3">
          <h2 className="text-[11pt] font-bold text-gray-900 uppercase tracking-wider pb-1 border-b border-blue-900 mb-2">
            教育背景
          </h2>
          <div className="space-y-2">
            {data.education.map((edu, i) => (
              <div key={i}>
                <div className="flex justify-between items-baseline">
                  <div>
                    <span className="text-[10.5pt] font-bold text-gray-900">{edu.school}</span>
                    {(edu.degree || edu.major) && (
                      <span className="text-[9.5pt] text-gray-600"> &mdash; {edu.degree}{edu.degree && edu.major ? "，" : ""}{edu.major}</span>
                    )}
                  </div>
                  {edu.period && <span className="text-[8.5pt] text-gray-400">{edu.period}</span>}
                </div>
                {edu.achievements.length > 0 && (
                  <ul className="mt-0.5 pl-4">
                    {edu.achievements.map((a, j) => (
                      <li key={j} className="text-[9pt] text-gray-500 list-disc">{a}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {data.experience.length > 0 && (
        <section className="mb-3">
          <h2 className="text-[11pt] font-bold text-gray-900 uppercase tracking-wider pb-1 border-b border-blue-900 mb-2">
            工作经历
          </h2>
          <div className="space-y-2">
            {data.experience.map((exp, i) => (
              <div key={i}>
                <div className="flex justify-between items-baseline">
                  <div>
                    <span className="text-[10.5pt] font-bold text-gray-900">{exp.title}</span>
                    {exp.company && <span className="text-[9.5pt] text-gray-600"> — {exp.company}</span>}
                  </div>
                  {exp.period && <span className="text-[8.5pt] text-gray-400">{exp.period}</span>}
                </div>
                {exp.highlights.length > 0 && (
                  <ul className="mt-0.5 pl-4">
                    {exp.highlights.map((h, j) => (
                      <li key={j} className="text-[9.5pt] text-gray-600 list-disc">{h}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {data.skills.length > 0 && (
        <section className="mb-3">
          <h2 className="text-[11pt] font-bold text-gray-900 uppercase tracking-wider pb-1 border-b border-blue-900 mb-2">
            专业技能
          </h2>
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {data.skills.map((cat, i) => (
              <div key={i} className="min-w-[200px] flex-1">
                <span className="text-[9.5pt] font-bold text-blue-900">{cat.category}：</span>
                <span className="text-[9pt] text-gray-600">{cat.skills.join("、")}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {data.projects.length > 0 && (
        <section className="mb-3">
          <h2 className="text-[11pt] font-bold text-gray-900 uppercase tracking-wider pb-1 border-b border-blue-900 mb-2">
            项目经历
          </h2>
          <div className="space-y-2">
            {data.projects.map((proj, i) => (
              <div key={i}>
                <div className="flex justify-between items-baseline">
                  <div>
                    <span className="text-[10.5pt] font-bold text-gray-900">{proj.name}</span>
                    {proj.role && <span className="text-[9pt] text-gray-400"> — {proj.role}</span>}
                  </div>
                  {proj.period && <span className="text-[8.5pt] text-gray-400">{proj.period}</span>}
                </div>
                {proj.description && <p className="text-[9pt] text-gray-500 italic mt-0.5">{proj.description}</p>}
                {proj.contributions.length > 0 && (
                  <ul className="mt-0.5 pl-4">
                    {proj.contributions.map((c, j) => (
                      <li key={j} className="text-[9.5pt] text-gray-600 list-disc">{c}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

/* ============================================================
 * Creative 模板 - 卡片式布局
 * ============================================================ */
function CreativeTemplate({ data }: { data: ResumeData }) {
  return (
    <div className="w-full max-w-[800px] mx-auto bg-gray-50 rounded-lg overflow-hidden text-[10pt] leading-[1.5] text-gray-800">
      {/* Hero 头部 */}
      <div className="bg-gradient-to-br from-purple-600 to-purple-400 text-white px-7 py-7">
        <h1 className="text-[22pt] font-bold tracking-wide mb-1.5">{data.name}</h1>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[8.5pt] opacity-90">
          {data.contact.email && <span>✉ {data.contact.email}</span>}
          {data.contact.phone && <span>☎ {data.contact.phone}</span>}
          {data.contact.location && <span>📍 {data.contact.location}</span>}
          {data.contact.website && <span>🌐 {data.contact.website}</span>}
          {data.contact.wechat && <span>微信: {data.contact.wechat}</span>}
        </div>
      </div>

      {/* 内容区域 */}
      <div className="p-5 space-y-4">
        {data.summary && (
          <div className="bg-white rounded-lg p-4 border-l-4 border-purple-500 shadow-sm">
            <p className="text-[8pt] uppercase tracking-wider text-purple-400 mb-1 font-semibold">个人简介</p>
            <p className="text-[9.5pt] text-gray-600 leading-relaxed">{data.summary}</p>
          </div>
        )}

        {data.experience.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-2.5">
              <div className="w-2 h-2 rounded-full bg-purple-600" />
              <h2 className="text-[11pt] font-bold text-purple-600 uppercase tracking-wider">工作经历</h2>
            </div>
            <div className="space-y-2">
              {data.experience.map((exp, i) => (
                <div key={i} className="bg-white rounded-lg p-3.5 shadow-sm border-l-3 border-purple-300">
                  <div className="flex justify-between items-baseline mb-1">
                    <div>
                      <span className="text-[10.5pt] font-bold text-gray-800">{exp.title}</span>
                      {exp.company && <span className="text-[9pt] text-gray-500"> — {exp.company}</span>}
                    </div>
                    {exp.period && (
                      <span className="text-[8pt] text-gray-400 bg-purple-50 px-2 py-0.5 rounded-full">{exp.period}</span>
                    )}
                  </div>
                  {exp.highlights.length > 0 && (
                    <ul className="space-y-0.5">
                      {exp.highlights.map((h, j) => (
                        <li key={j} className="text-[9pt] text-gray-500 pl-3.5 relative before:content-['◆'] before:absolute before:left-0 before:text-purple-300 before:text-[6pt] before:top-[5px]">
                          {h}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {data.skills.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-2.5">
              <div className="w-2 h-2 rounded-full bg-purple-600" />
              <h2 className="text-[11pt] font-bold text-purple-600 uppercase tracking-wider">专业技能</h2>
            </div>
            <div className="bg-white rounded-lg p-4 shadow-sm space-y-2">
              {data.skills.map((cat, i) => (
                <div key={i}>
                  <p className="text-[9pt] font-bold text-purple-600 mb-1">{cat.category}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {cat.skills.map((s, j) => (
                      <span key={j} className="text-[8pt] text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full border border-purple-100">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {data.education.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-2.5">
              <div className="w-2 h-2 rounded-full bg-purple-600" />
              <h2 className="text-[11pt] font-bold text-purple-600 uppercase tracking-wider">教育背景</h2>
            </div>
            <div className="space-y-2">
              {data.education.map((edu, i) => (
                <div key={i} className="bg-white rounded-lg p-3 shadow-sm">
                  <div className="flex justify-between items-baseline">
                    <div>
                      <span className="text-[10pt] font-bold text-gray-800">{edu.school}</span>
                      {(edu.degree || edu.major) && (
                        <span className="text-[9pt] text-gray-500"> &mdash; {edu.degree}{edu.degree && edu.major ? "，" : ""}{edu.major}</span>
                      )}
                    </div>
                    {edu.period && (
                      <span className="text-[8pt] text-gray-400 bg-purple-50 px-2 py-0.5 rounded-full">{edu.period}</span>
                    )}
                  </div>
                  {edu.achievements.length > 0 && (
                    <ul className="mt-1 pl-3.5">
                      {edu.achievements.map((a, j) => (
                        <li key={j} className="text-[8.5pt] text-gray-500 list-none before:content-['•'] before:text-purple-400 before:mr-1">{a}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {data.projects.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-2.5">
              <div className="w-2 h-2 rounded-full bg-purple-600" />
              <h2 className="text-[11pt] font-bold text-purple-600 uppercase tracking-wider">项目经历</h2>
            </div>
            <div className="space-y-2">
              {data.projects.map((proj, i) => (
                <div key={i} className="bg-white rounded-lg p-3.5 shadow-sm border-l-3 border-pink-400">
                  <div className="flex justify-between items-baseline mb-1">
                    <div>
                      <span className="text-[10pt] font-bold text-gray-800">{proj.name}</span>
                      {proj.role && <span className="text-[9pt] text-gray-400"> — {proj.role}</span>}
                    </div>
                    {proj.period && (
                      <span className="text-[8pt] text-gray-400 bg-purple-50 px-2 py-0.5 rounded-full">{proj.period}</span>
                    )}
                  </div>
                  {proj.description && <p className="text-[8.5pt] text-gray-500 italic mb-1">{proj.description}</p>}
                  {proj.contributions.length > 0 && (
                    <ul className="space-y-0.5">
                      {proj.contributions.map((c, j) => (
                        <li key={j} className="text-[9pt] text-gray-500 pl-3.5 relative before:content-['◆'] before:absolute before:left-0 before:text-pink-400 before:text-[6pt] before:top-[5px]">
                          {c}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
