"use client";

import React from "react";
import {
  Document,
  Page,
  View,
  Text,
  StyleSheet,
  Font,
  pdf,
} from "@react-pdf/renderer";
import type { ResumeData } from "@/store/chat";

/* ============================================================
 * Font Registration
 * ============================================================
 * 使用 Fontsource CDN 加载 Noto Sans SC 中文字体。
 * 首次加载约 7MB，浏览器会缓存后续请求。
 * 如需离线或加速，可将字体文件下载到 public/fonts/ 并修改 src 路径。
 */
Font.register({
  family: "NotoSansSC",
  fonts: [
    {
      src: "https://cdn.jsdelivr.net/fontsource/fonts/noto-sans-sc@latest/chinese-simplified-400-normal.ttf",
      fontWeight: 400,
    },
    {
      src: "https://cdn.jsdelivr.net/fontsource/fonts/noto-sans-sc@latest/chinese-simplified-700-normal.ttf",
      fontWeight: 700,
    },
  ],
});

// 禁用连字符断词（中文不需要）
Font.registerHyphenationCallback((word) => [word]);

/* ============================================================
 * Types & Helpers
 * ============================================================ */

type SectionKey = "summary" | "experience" | "education" | "skills" | "projects";
const DEFAULT_SECTION_ORDER: SectionKey[] = [
  "summary",
  "experience",
  "education",
  "skills",
  "projects",
];
const PROFESSIONAL_MAIN_KEYS: SectionKey[] = [
  "summary",
  "experience",
  "education",
  "projects",
];

function hasSectionContent(data: ResumeData, key: string): boolean {
  switch (key) {
    case "summary":
      return !!data.summary;
    case "experience":
      return data.experience.length > 0;
    case "education":
      return data.education.length > 0;
    case "skills":
      return data.skills.length > 0;
    case "projects":
      return data.projects.length > 0;
    default:
      return false;
  }
}

function buildSectionOrder(
  data: ResumeData,
  allowedKeys?: SectionKey[]
): SectionKey[] {
  const keys = allowedKeys || DEFAULT_SECTION_ORDER;
  const order = (data.section_order || DEFAULT_SECTION_ORDER) as SectionKey[];
  const result: SectionKey[] = [];
  for (const key of order) {
    if (keys.includes(key) && hasSectionContent(data, key) && !result.includes(key)) {
      result.push(key);
    }
  }
  for (const key of keys) {
    if (!result.includes(key) && hasSectionContent(data, key)) {
      result.push(key);
    }
  }
  return result;
}

/** 将 ResumeData 中的联系人信息拼接为行列表 */
function getContactLines(data: ResumeData): { icon: string; text: string }[] {
  const lines: { icon: string; text: string }[] = [];
  if (data.contact.email) lines.push({ icon: "✉", text: data.contact.email });
  if (data.contact.phone) lines.push({ icon: "☎", text: data.contact.phone });
  if (data.contact.location) lines.push({ icon: "📍", text: data.contact.location });
  if (data.contact.website) lines.push({ icon: "🌐", text: data.contact.website });
  if (data.contact.linkedin) lines.push({ icon: "in", text: data.contact.linkedin });
  if (data.contact.wechat) lines.push({ icon: "微", text: data.contact.wechat });
  if (!data.contact.email && !data.contact.phone && data.contact.raw_text) {
    lines.push({ icon: "", text: data.contact.raw_text });
  }
  return lines;
}

/* ============================================================
 * Professional Template — 双栏侧边栏布局
 * ============================================================ */

const proStyles = StyleSheet.create({
  page: {
    flexDirection: "row",
    fontFamily: "NotoSansSC",
    fontSize: 9,
    color: "#1e293b",
    lineHeight: 1.4,
  },
  sidebar: {
    width: "38%",
    backgroundColor: "#1e293b",
    color: "#f1f5f9",
    padding: 22,
    paddingTop: 28,
  },
  sidebarName: {
    fontSize: 18,
    fontWeight: 700,
    color: "#ffffff",
    marginBottom: 10,
  },
  sidebarContactRow: {
    fontSize: 8,
    color: "#94a3b8",
    marginBottom: 3,
    flexDirection: "row",
  },
  sidebarContactIcon: {
    width: 14,
    color: "#64748b",
    fontSize: 8,
  },
  sidebarContactText: {
    flex: 1,
    color: "#cbd5e1",
    fontSize: 8,
  },
  sidebarSectionTitle: {
    fontSize: 10,
    fontWeight: 700,
    color: "#60a5fa",
    marginTop: 16,
    marginBottom: 6,
    paddingBottom: 3,
    borderBottomWidth: 1,
    borderBottomColor: "#475569",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  sidebarSkillCategory: {
    fontSize: 9,
    fontWeight: 700,
    color: "#e2e8f0",
    marginTop: 6,
    marginBottom: 2,
  },
  sidebarSkillItems: {
    fontSize: 8,
    color: "#94a3b8",
    lineHeight: 1.5,
  },
  main: {
    width: "62%",
    padding: 22,
    paddingTop: 28,
  },
  mainSection: {
    marginBottom: 12,
  },
  mainSectionTitle: {
    fontSize: 12,
    fontWeight: 700,
    color: "#1e293b",
    textTransform: "uppercase",
    letterSpacing: 1,
    paddingBottom: 3,
    marginBottom: 8,
    borderBottomWidth: 2,
    borderBottomColor: "#3b82f6",
  },
  summary: {
    fontSize: 9.5,
    color: "#475569",
    lineHeight: 1.5,
  },
  expRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    marginBottom: 1,
  },
  expTitle: { fontSize: 10.5, fontWeight: 700 },
  expCompany: { fontSize: 9.5, color: "#475569" },
  expPeriod: { fontSize: 8.5, color: "#64748b" },
  bulletRow: {
    flexDirection: "row",
    marginLeft: 6,
    marginBottom: 2,
    lineHeight: 1.4,
  },
  bulletChar: { color: "#3b82f6", fontSize: 9, marginRight: 3 },
  bulletText: { fontSize: 9, color: "#475569", flex: 1 },
  eduRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    marginBottom: 1,
  },
  eduSchool: { fontSize: 10, fontWeight: 700 },
  eduDetail: { fontSize: 9, color: "#475569" },
  eduPeriod: { fontSize: 8.5, color: "#64748b" },
  projRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    marginBottom: 1,
  },
  projName: { fontSize: 10, fontWeight: 700 },
  projRole: { fontSize: 9, color: "#94a3b8" },
  projPeriod: { fontSize: 8.5, color: "#64748b" },
  projDesc: { fontSize: 8.5, color: "#64748b", fontStyle: "italic", marginBottom: 2 },
});

function ProfessionalPDF({ data }: { data: ResumeData }) {
  const mainOrder = buildSectionOrder(data, PROFESSIONAL_MAIN_KEYS);
  const contactLines = getContactLines(data);

  const renderMainSection = (key: SectionKey) => {
    switch (key) {
      case "summary":
        return data.summary ? (
          <View key={key} style={proStyles.mainSection}>
            <Text style={proStyles.mainSectionTitle}>个人简介</Text>
            <Text style={proStyles.summary}>{data.summary}</Text>
          </View>
        ) : null;

      case "experience":
        return data.experience.length > 0 ? (
          <View key={key} style={proStyles.mainSection}>
            <Text style={proStyles.mainSectionTitle}>工作经历</Text>
            {data.experience.map((exp, i) => (
              <View key={i} style={{ marginBottom: 8 }}>
                <View style={proStyles.expRow}>
                  <View style={{ flexDirection: "row", alignItems: "baseline", flex: 1 }}>
                    <Text style={proStyles.expTitle}>{exp.title}</Text>
                    {exp.company && <Text style={proStyles.expCompany}> — {exp.company}</Text>}
                  </View>
                  {exp.period && <Text style={proStyles.expPeriod}>{exp.period}</Text>}
                </View>
                {exp.highlights.map((h, j) => (
                  <View key={j} style={proStyles.bulletRow}>
                    <Text style={proStyles.bulletChar}>▸</Text>
                    <Text style={proStyles.bulletText}>{h}</Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        ) : null;

      case "education":
        return data.education.length > 0 ? (
          <View key={key} style={proStyles.mainSection}>
            <Text style={proStyles.mainSectionTitle}>教育背景</Text>
            {data.education.map((edu, i) => (
              <View key={i} style={{ marginBottom: 6 }}>
                <View style={proStyles.eduRow}>
                  <View style={{ flexDirection: "row", alignItems: "baseline", flex: 1 }}>
                    <Text style={proStyles.eduSchool}>{edu.school}</Text>
                    {(edu.degree || edu.major) && (
                      <Text style={proStyles.eduDetail}>
                        {" "}&mdash; {edu.degree}
                        {edu.degree && edu.major ? "，" : ""}
                        {edu.major}
                      </Text>
                    )}
                  </View>
                  {edu.period && <Text style={proStyles.eduPeriod}>{edu.period}</Text>}
                </View>
                {edu.achievements.map((a, j) => (
                  <View key={j} style={proStyles.bulletRow}>
                    <Text style={proStyles.bulletChar}>•</Text>
                    <Text style={proStyles.bulletText}>{a}</Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        ) : null;

      case "projects":
        return data.projects.length > 0 ? (
          <View key={key} style={proStyles.mainSection}>
            <Text style={proStyles.mainSectionTitle}>项目经历</Text>
            {data.projects.map((proj, i) => (
              <View key={i} style={{ marginBottom: 8 }}>
                <View style={proStyles.projRow}>
                  <View style={{ flexDirection: "row", alignItems: "baseline", flex: 1 }}>
                    <Text style={proStyles.projName}>{proj.name}</Text>
                    {proj.role && <Text style={proStyles.projRole}> — {proj.role}</Text>}
                  </View>
                  {proj.period && <Text style={proStyles.projPeriod}>{proj.period}</Text>}
                </View>
                {proj.description && <Text style={proStyles.projDesc}>{proj.description}</Text>}
                {proj.contributions.map((c, j) => (
                  <View key={j} style={proStyles.bulletRow}>
                    <Text style={proStyles.bulletChar}>▸</Text>
                    <Text style={proStyles.bulletText}>{c}</Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        ) : null;

      default:
        return null;
    }
  };

  return (
    <Page size="A4" style={proStyles.page}>
      {/* 侧边栏 */}
      <View style={proStyles.sidebar}>
        <Text style={proStyles.sidebarName}>{data.name}</Text>
        {contactLines.map((line, i) => (
          <View key={i} style={proStyles.sidebarContactRow}>
            <Text style={proStyles.sidebarContactIcon}>{line.icon}</Text>
            <Text style={proStyles.sidebarContactText}>{line.text}</Text>
          </View>
        ))}

        {data.skills.length > 0 && (
          <View>
            <Text style={proStyles.sidebarSectionTitle}>专业技能</Text>
            {data.skills.map((cat, i) => (
              <View key={i}>
                <Text style={proStyles.sidebarSkillCategory}>{cat.category}</Text>
                <Text style={proStyles.sidebarSkillItems}>{cat.skills.join("、")}</Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* 主内容区 */}
      <View style={proStyles.main}>
        {mainOrder.map((key) => renderMainSection(key))}
      </View>
    </Page>
  );
}

/* ============================================================
 * Academic Template — 传统单栏居中布局
 * ============================================================ */

const acaStyles = StyleSheet.create({
  page: {
    fontFamily: "NotoSansSC",
    fontSize: 10,
    color: "#1f2937",
    lineHeight: 1.5,
    padding: 40,
    paddingTop: 36,
  },
  header: {
    alignItems: "center",
    marginBottom: 12,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#1e3a5f",
  },
  headerName: {
    fontSize: 20,
    fontWeight: 700,
    color: "#111827",
    letterSpacing: 2,
    marginBottom: 4,
  },
  headerContact: {
    fontSize: 9,
    color: "#6b7280",
    textAlign: "center",
    lineHeight: 1.6,
  },
  section: { marginBottom: 10 },
  sectionTitle: {
    fontSize: 11,
    fontWeight: 700,
    color: "#1e3a5f",
    textTransform: "uppercase",
    letterSpacing: 1,
    paddingBottom: 2,
    marginBottom: 6,
    borderBottomWidth: 1,
    borderBottomColor: "#1e3a5f",
  },
  summary: {
    fontSize: 9.5,
    color: "#4b5563",
    lineHeight: 1.5,
    textAlign: "justify",
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    marginBottom: 1,
  },
  titleBold: { fontSize: 10.5, fontWeight: 700 },
  detail: { fontSize: 9.5, color: "#4b5563" },
  period: { fontSize: 8.5, color: "#6b7280" },
  bulletRow: {
    flexDirection: "row",
    marginLeft: 10,
    marginBottom: 2,
  },
  bulletChar: { color: "#1e3a5f", fontSize: 9, marginRight: 4 },
  bulletText: { fontSize: 9.5, color: "#4b5563", flex: 1, lineHeight: 1.4 },
  skillsWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  skillBlock: {
    minWidth: 150,
    marginBottom: 4,
  },
  skillCategory: {
    fontSize: 9.5,
    fontWeight: 700,
    color: "#1e3a5f",
    marginBottom: 1,
  },
  skillItems: { fontSize: 9, color: "#4b5563" },
});

function AcademicPDF({ data }: { data: ResumeData }) {
  const sectionOrder = buildSectionOrder(data);
  const contactParts = [
    data.contact.email,
    data.contact.phone,
    data.contact.location,
    data.contact.website,
  ].filter(Boolean);
  const wechatPart = data.contact.wechat ? `微信: ${data.contact.wechat}` : "";
  const contactLine = [...contactParts, wechatPart].filter(Boolean).join(" | ");

  const renderSection = (key: SectionKey) => {
    switch (key) {
      case "summary":
        return data.summary ? (
          <View key={key} style={acaStyles.section}>
            <Text style={acaStyles.sectionTitle}>个人简介</Text>
            <Text style={acaStyles.summary}>{data.summary}</Text>
          </View>
        ) : null;

      case "education":
        return data.education.length > 0 ? (
          <View key={key} style={acaStyles.section}>
            <Text style={acaStyles.sectionTitle}>教育背景</Text>
            {data.education.map((edu, i) => (
              <View key={i} style={{ marginBottom: 6 }}>
                <View style={acaStyles.row}>
                  <View style={{ flexDirection: "row", alignItems: "baseline", flex: 1 }}>
                    <Text style={acaStyles.titleBold}>{edu.school}</Text>
                    {(edu.degree || edu.major) && (
                      <Text style={acaStyles.detail}>
                        {" "}&mdash; {edu.degree}
                        {edu.degree && edu.major ? "，" : ""}
                        {edu.major}
                      </Text>
                    )}
                  </View>
                  {edu.period && <Text style={acaStyles.period}>{edu.period}</Text>}
                </View>
                {edu.achievements.map((a, j) => (
                  <View key={j} style={acaStyles.bulletRow}>
                    <Text style={acaStyles.bulletChar}>•</Text>
                    <Text style={acaStyles.bulletText}>{a}</Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        ) : null;

      case "experience":
        return data.experience.length > 0 ? (
          <View key={key} style={acaStyles.section}>
            <Text style={acaStyles.sectionTitle}>工作经历</Text>
            {data.experience.map((exp, i) => (
              <View key={i} style={{ marginBottom: 6 }}>
                <View style={acaStyles.row}>
                  <View style={{ flexDirection: "row", alignItems: "baseline", flex: 1 }}>
                    <Text style={acaStyles.titleBold}>{exp.title}</Text>
                    {exp.company && <Text style={acaStyles.detail}> — {exp.company}</Text>}
                  </View>
                  {exp.period && <Text style={acaStyles.period}>{exp.period}</Text>}
                </View>
                {exp.highlights.map((h, j) => (
                  <View key={j} style={acaStyles.bulletRow}>
                    <Text style={acaStyles.bulletChar}>•</Text>
                    <Text style={acaStyles.bulletText}>{h}</Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        ) : null;

      case "skills":
        return data.skills.length > 0 ? (
          <View key={key} style={acaStyles.section}>
            <Text style={acaStyles.sectionTitle}>专业技能</Text>
            <View style={acaStyles.skillsWrap}>
              {data.skills.map((cat, i) => (
                <View key={i} style={acaStyles.skillBlock}>
                  <Text style={acaStyles.skillCategory}>{cat.category}</Text>
                  <Text style={acaStyles.skillItems}>{cat.skills.join("、")}</Text>
                </View>
              ))}
            </View>
          </View>
        ) : null;

      case "projects":
        return data.projects.length > 0 ? (
          <View key={key} style={acaStyles.section}>
            <Text style={acaStyles.sectionTitle}>项目经历</Text>
            {data.projects.map((proj, i) => (
              <View key={i} style={{ marginBottom: 6 }}>
                <View style={acaStyles.row}>
                  <View style={{ flexDirection: "row", alignItems: "baseline", flex: 1 }}>
                    <Text style={acaStyles.titleBold}>{proj.name}</Text>
                    {proj.role && <Text style={{ fontSize: 9, color: "#9ca3af" }}> — {proj.role}</Text>}
                  </View>
                  {proj.period && <Text style={acaStyles.period}>{proj.period}</Text>}
                </View>
                {proj.description && (
                  <Text style={{ fontSize: 9, color: "#6b7280", fontStyle: "italic", marginBottom: 2 }}>
                    {proj.description}
                  </Text>
                )}
                {proj.contributions.map((c, j) => (
                  <View key={j} style={acaStyles.bulletRow}>
                    <Text style={acaStyles.bulletChar}>•</Text>
                    <Text style={acaStyles.bulletText}>{c}</Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        ) : null;

      default:
        return null;
    }
  };

  return (
    <Page size="A4" style={acaStyles.page}>
      <View style={acaStyles.header}>
        <Text style={acaStyles.headerName}>{data.name}</Text>
        {contactLine && <Text style={acaStyles.headerContact}>{contactLine}</Text>}
      </View>
      {sectionOrder.map((key) => renderSection(key))}
    </Page>
  );
}

/* ============================================================
 * Creative Template — 渐变头部 + 卡片布局
 * ============================================================ */

const creStyles = StyleSheet.create({
  page: {
    fontFamily: "NotoSansSC",
    fontSize: 9.5,
    color: "#1f2937",
    lineHeight: 1.4,
  },
  hero: {
    backgroundColor: "#7c3aed",
    padding: 28,
    paddingTop: 32,
    paddingBottom: 24,
  },
  heroName: {
    fontSize: 22,
    fontWeight: 700,
    color: "#ffffff",
    letterSpacing: 1,
    marginBottom: 8,
  },
  heroContactRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  heroContactItem: {
    fontSize: 8.5,
    color: "#e9d5ff",
  },
  body: {
    padding: 22,
    paddingTop: 18,
    backgroundColor: "#f9fafb",
  },
  section: { marginBottom: 12 },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 6,
  },
  sectionDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: "#7c3aed",
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: 700,
    color: "#7c3aed",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  summaryCard: {
    backgroundColor: "#ffffff",
    borderRadius: 6,
    padding: 12,
    borderLeftWidth: 3,
    borderLeftColor: "#7c3aed",
  },
  summaryText: {
    fontSize: 9.5,
    color: "#4b5563",
    lineHeight: 1.5,
  },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 5,
    padding: 10,
    marginBottom: 5,
    borderLeftWidth: 2,
    borderLeftColor: "#c4b5fd",
  },
  cardExp: { borderLeftColor: "#c4b5fd" },
  cardProj: { borderLeftColor: "#f9a8d4" },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    marginBottom: 2,
  },
  titleBold: { fontSize: 10.5, fontWeight: 700 },
  detail: { fontSize: 9, color: "#6b7280" },
  period: { fontSize: 8, color: "#9ca3af" },
  desc: { fontSize: 8.5, color: "#6b7280", fontStyle: "italic", marginBottom: 2 },
  bulletRow: {
    flexDirection: "row",
    marginLeft: 6,
    marginBottom: 1,
  },
  bulletChar: { color: "#c4b5fd", fontSize: 7, marginRight: 4, marginTop: 2 },
  bulletText: { fontSize: 9, color: "#4b5563", flex: 1, lineHeight: 1.4 },
  skillsCard: {
    backgroundColor: "#ffffff",
    borderRadius: 5,
    padding: 12,
  },
  skillCategory: {
    fontSize: 9,
    fontWeight: 700,
    color: "#7c3aed",
    marginBottom: 1,
    marginTop: 4,
  },
  skillItems: { fontSize: 8.5, color: "#6b7280" },
});

function CreativePDF({ data }: { data: ResumeData }) {
  const sectionOrder = buildSectionOrder(data);
  const contactLines = getContactLines(data);

  const renderSection = (key: SectionKey) => {
    switch (key) {
      case "summary":
        return data.summary ? (
          <View key={key} style={creStyles.section}>
            <View style={creStyles.summaryCard}>
              <Text style={{ fontSize: 8, color: "#a78bfa", textTransform: "uppercase", letterSpacing: 1, marginBottom: 3, fontWeight: 700 }}>
                个人简介
              </Text>
              <Text style={creStyles.summaryText}>{data.summary}</Text>
            </View>
          </View>
        ) : null;

      case "experience":
        return data.experience.length > 0 ? (
          <View key={key} style={creStyles.section}>
            <View style={creStyles.sectionHeader}>
              <View style={creStyles.sectionDot} />
              <Text style={creStyles.sectionTitle}>工作经历</Text>
            </View>
            {data.experience.map((exp, i) => (
              <View key={i} style={[creStyles.card, creStyles.cardExp]}>
                <View style={creStyles.row}>
                  <View style={{ flexDirection: "row", alignItems: "baseline", flex: 1 }}>
                    <Text style={creStyles.titleBold}>{exp.title}</Text>
                    {exp.company && <Text style={creStyles.detail}> — {exp.company}</Text>}
                  </View>
                  {exp.period && <Text style={creStyles.period}>{exp.period}</Text>}
                </View>
                {exp.highlights.map((h, j) => (
                  <View key={j} style={creStyles.bulletRow}>
                    <Text style={creStyles.bulletChar}>◆</Text>
                    <Text style={creStyles.bulletText}>{h}</Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        ) : null;

      case "skills":
        return data.skills.length > 0 ? (
          <View key={key} style={creStyles.section}>
            <View style={creStyles.sectionHeader}>
              <View style={creStyles.sectionDot} />
              <Text style={creStyles.sectionTitle}>专业技能</Text>
            </View>
            <View style={creStyles.skillsCard}>
              {data.skills.map((cat, i) => (
                <View key={i}>
                  <Text style={creStyles.skillCategory}>{cat.category}</Text>
                  <Text style={creStyles.skillItems}>{cat.skills.join("、")}</Text>
                </View>
              ))}
            </View>
          </View>
        ) : null;

      case "education":
        return data.education.length > 0 ? (
          <View key={key} style={creStyles.section}>
            <View style={creStyles.sectionHeader}>
              <View style={creStyles.sectionDot} />
              <Text style={creStyles.sectionTitle}>教育背景</Text>
            </View>
            {data.education.map((edu, i) => (
              <View key={i} style={creStyles.card}>
                <View style={creStyles.row}>
                  <View style={{ flexDirection: "row", alignItems: "baseline", flex: 1 }}>
                    <Text style={creStyles.titleBold}>{edu.school}</Text>
                    {(edu.degree || edu.major) && (
                      <Text style={creStyles.detail}>
                        {" "}&mdash; {edu.degree}
                        {edu.degree && edu.major ? "，" : ""}
                        {edu.major}
                      </Text>
                    )}
                  </View>
                  {edu.period && <Text style={creStyles.period}>{edu.period}</Text>}
                </View>
                {edu.achievements.map((a, j) => (
                  <View key={j} style={creStyles.bulletRow}>
                    <Text style={{ ...creStyles.bulletChar, color: "#a78bfa" }}>•</Text>
                    <Text style={creStyles.bulletText}>{a}</Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        ) : null;

      case "projects":
        return data.projects.length > 0 ? (
          <View key={key} style={creStyles.section}>
            <View style={creStyles.sectionHeader}>
              <View style={creStyles.sectionDot} />
              <Text style={creStyles.sectionTitle}>项目经历</Text>
            </View>
            {data.projects.map((proj, i) => (
              <View key={i} style={[creStyles.card, creStyles.cardProj]}>
                <View style={creStyles.row}>
                  <View style={{ flexDirection: "row", alignItems: "baseline", flex: 1 }}>
                    <Text style={creStyles.titleBold}>{proj.name}</Text>
                    {proj.role && <Text style={{ fontSize: 9, color: "#9ca3af" }}> — {proj.role}</Text>}
                  </View>
                  {proj.period && <Text style={creStyles.period}>{proj.period}</Text>}
                </View>
                {proj.description && <Text style={creStyles.desc}>{proj.description}</Text>}
                {proj.contributions.map((c, j) => (
                  <View key={j} style={creStyles.bulletRow}>
                    <Text style={{ ...creStyles.bulletChar, color: "#f9a8d4" }}>◆</Text>
                    <Text style={creStyles.bulletText}>{c}</Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        ) : null;

      default:
        return null;
    }
  };

  return (
    <Page size="A4" style={creStyles.page}>
      {/* Hero 头部 */}
      <View style={creStyles.hero}>
        <Text style={creStyles.heroName}>{data.name}</Text>
        <View style={creStyles.heroContactRow}>
          {contactLines.map((line, i) => (
            <Text key={i} style={creStyles.heroContactItem}>
              {line.icon} {line.text}
            </Text>
          ))}
        </View>
      </View>

      {/* 内容区 */}
      <View style={creStyles.body}>
        {sectionOrder.map((key) => renderSection(key))}
      </View>
    </Page>
  );
}

/* ============================================================
 * Main Document Component
 * ============================================================ */

interface ResumePDFProps {
  data: ResumeData;
  template?: string;
}

export function ResumePDFDocument({ data, template = "professional" }: ResumePDFProps) {
  const TemplateComponent =
    template === "academic"
      ? AcademicPDF
      : template === "creative"
        ? CreativePDF
        : ProfessionalPDF;

  return (
    <Document>
      <TemplateComponent data={data} />
    </Document>
  );
}

/* ============================================================
 * PDF 生成 + 下载工具函数
 * ============================================================ */

/** 生成 PDF Blob */
export async function generatePdfBlob(
  data: ResumeData,
  template?: string
): Promise<Blob> {
  const instance = pdf(<ResumePDFDocument data={data} template={template} />);
  return instance.toBlob();
}

/** 触发 PDF 下载 */
export async function downloadResumePdf(
  data: ResumeData,
  template?: string,
  fileName?: string
): Promise<void> {
  const blob = await generatePdfBlob(data, template);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName || "resume.pdf";
  a.click();
  URL.revokeObjectURL(url);
}
