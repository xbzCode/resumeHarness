"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Star, AlertTriangle, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ResumeScoreData } from "@/store/chat";

const DIMENSION_LABELS: Record<string, string> = {
  structure: "结构完整性",
  content: "内容充实度",
  quantification: "量化数据",
  keyword_match: "关键词匹配",
  format: "格式规范",
};

function ScoreBar({ score, label }: { score: number; label: string }) {
  const color =
    score >= 80
      ? "bg-green-500"
      : score >= 60
        ? "bg-yellow-500"
        : score >= 40
          ? "bg-orange-500"
          : "bg-red-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{score.toFixed(0)}</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted">
        <div
          className={cn("h-1.5 rounded-full transition-all", color)}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
    </div>
  );
}

function getScoreLevel(score: number) {
  if (score >= 80) return { label: "优秀", color: "text-green-600", bg: "bg-green-50 border-green-200" };
  if (score >= 60) return { label: "良好", color: "text-yellow-600", bg: "bg-yellow-50 border-yellow-200" };
  if (score >= 40) return { label: "一般", color: "text-orange-600", bg: "bg-orange-50 border-orange-200" };
  return { label: "待改进", color: "text-red-600", bg: "bg-red-50 border-red-200" };
}

interface ResumeScoreCardProps {
  score: ResumeScoreData;
}

export function ResumeScoreCard({ score }: ResumeScoreCardProps) {
  const [expanded, setExpanded] = useState(true);
  const level = getScoreLevel(score.overall_score);

  return (
    <div className={cn("rounded-lg border p-3", level.bg)}>
      {/* 总分 + 展开/收起 */}
      <button
        type="button"
        className="flex w-full items-center gap-2"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
        <Star className={cn("h-4 w-4", level.color)} />
        <span className="text-sm font-medium">简历评分</span>
        <span className={cn("text-lg font-bold", level.color)}>
          {score.overall_score.toFixed(0)}
        </span>
        <span className={cn("text-xs", level.color)}>{level.label}</span>
      </button>

      {expanded && (
        <div className="mt-3 space-y-3">
          {/* 维度评分 */}
          <div className="space-y-2">
            {Object.entries(score.dimensions).map(([key, value]) => (
              <ScoreBar key={key} score={value} label={DIMENSION_LABELS[key] || key} />
            ))}
          </div>

          {/* 改进建议 */}
          {score.suggestions && score.suggestions.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">改进建议</p>
              <ul className="space-y-1">
                {score.suggestions.map((s, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs">
                    <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-yellow-500" />
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* JD 关键词匹配 */}
          {score.jd_keywords_matched && score.jd_keywords_matched.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">已匹配关键词</p>
              <div className="flex flex-wrap gap-1">
                {score.jd_keywords_matched.map((kw, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-0.5 rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700"
                  >
                    <CheckCircle className="h-2.5 w-2.5" />
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          {score.jd_keywords_missing && score.jd_keywords_missing.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">缺失关键词</p>
              <div className="flex flex-wrap gap-1">
                {score.jd_keywords_missing.map((kw, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-0.5 rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700"
                  >
                    <AlertTriangle className="h-2.5 w-2.5" />
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
