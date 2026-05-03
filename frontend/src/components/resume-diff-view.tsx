"use client";

import { useState, useMemo } from "react";
import { ChevronDown, ChevronRight, ArrowLeftRight } from "lucide-react";
import { cn } from "@/lib/utils";

/** 简单的行级 diff 算法，返回增加/删除/不变的行列表 */
function computeLineDiff(
  oldText: string,
  newText: string,
): { type: "added" | "removed" | "unchanged"; content: string }[] {
  const oldLines = oldText.split("\n");
  const newLines = newText.split("\n");

  // 使用简单的 LCS 启发式：逐行匹配
  const result: { type: "added" | "removed" | "unchanged"; content: string }[] = [];

  // 简单策略：用双指针扫描
  let i = 0;
  let j = 0;

  while (i < oldLines.length || j < newLines.length) {
    if (i < oldLines.length && j < newLines.length && oldLines[i] === newLines[j]) {
      result.push({ type: "unchanged", content: oldLines[i] });
      i++;
      j++;
    } else {
      // 尝试在下方寻找匹配
      let foundInOld = -1;
      let foundInNew = -1;

      // 在 new 中查找 old[i]
      for (let k = j + 1; k < Math.min(j + 10, newLines.length); k++) {
        if (oldLines[i] === newLines[k]) {
          foundInNew = k;
          break;
        }
      }

      // 在 old 中查找 new[j]
      for (let k = i + 1; k < Math.min(i + 10, oldLines.length); k++) {
        if (oldLines[k] === newLines[j]) {
          foundInOld = k;
          break;
        }
      }

      if (foundInNew !== -1 && (foundInOld === -1 || foundInNew - j <= foundInOld - i)) {
        // new 中有额外的行
        while (j < foundInNew) {
          result.push({ type: "added", content: newLines[j] });
          j++;
        }
      } else if (foundInOld !== -1) {
        // old 中有被删除的行
        while (i < foundInOld) {
          result.push({ type: "removed", content: oldLines[i] });
          i++;
        }
      } else {
        // 无法匹配，标记为删除旧行+添加新行
        if (i < oldLines.length) {
          result.push({ type: "removed", content: oldLines[i] });
          i++;
        }
        if (j < newLines.length) {
          result.push({ type: "added", content: newLines[j] });
          j++;
        }
      }
    }
  }

  return result;
}

interface ResumeDiffViewProps {
  oldContent: string;
  newContent: string;
}

export function ResumeDiffView({ oldContent, newContent }: ResumeDiffViewProps) {
  const [expanded, setExpanded] = useState(true);

  const diffLines = useMemo(
    () => computeLineDiff(oldContent, newContent),
    [oldContent, newContent],
  );

  const stats = useMemo(() => {
    let added = 0;
    let removed = 0;
    let unchanged = 0;
    for (const line of diffLines) {
      if (line.type === "added") added++;
      else if (line.type === "removed") removed++;
      else unchanged++;
    }
    return { added, removed, unchanged };
  }, [diffLines]);

  // 如果没有差异，不显示
  if (stats.added === 0 && stats.removed === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border bg-background">
      <button
        type="button"
        className="flex w-full items-center gap-2 px-3 py-2"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
        <ArrowLeftRight className="h-4 w-4 text-blue-500" />
        <span className="text-sm font-medium">修改对比</span>
        <span className="text-xs text-muted-foreground">
          +{stats.added} / -{stats.removed}
        </span>
      </button>

      {expanded && (
        <div className="border-t px-3 py-2">
          <div className="max-h-[400px] overflow-y-auto rounded bg-muted/50 p-2 font-mono text-xs">
            {diffLines.map((line, i) => (
              <div
                key={i}
                className={cn(
                  "flex",
                  line.type === "added" && "bg-green-500/10 text-green-700 dark:text-green-400",
                  line.type === "removed" && "bg-red-500/10 text-red-700 dark:text-red-400",
                )}
              >
                <span className="w-6 shrink-0 text-right text-muted-foreground select-none">
                  {line.type === "added" ? "+" : line.type === "removed" ? "-" : " "}
                </span>
                <span className="whitespace-pre-wrap break-all">
                  {line.content || " "}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
