"use client";

import React from "react";
import type { ResumeData } from "@/store/chat";
import type { TemplateProps } from "./templates/shared";
import { ProfessionalTemplate } from "./templates/professional";
import { AcademicTemplate } from "./templates/academic";
import { CreativeTemplate } from "./templates/creative";
import { MinimalTemplate } from "./templates/minimal";
import { ElegantTemplate } from "./templates/elegant";
import { TechTemplate } from "./templates/tech";
import { CompactTemplate } from "./templates/compact";

/** 模板名 → 组件映射 */
const TEMPLATE_MAP: Record<string, React.FC<TemplateProps>> = {
  professional: ProfessionalTemplate,
  academic: AcademicTemplate,
  creative: CreativeTemplate,
  minimal: MinimalTemplate,
  elegant: ElegantTemplate,
  tech: TechTemplate,
  compact: CompactTemplate,
};

interface ResumePreviewProps {
  data: ResumeData;
  template?: string;
  editable?: boolean;
  onChange?: (data: ResumeData) => void;
}

export function ResumePreview({ data, template = "professional", editable = false, onChange }: ResumePreviewProps) {
  const Template = TEMPLATE_MAP[template] || ProfessionalTemplate;
  return <Template data={data} editable={editable} onChange={onChange} />;
}
