"use client";

import { useState, useRef, useEffect } from "react";

interface EditableFieldProps {
  value: string | undefined;
  editable: boolean;
  onChange: (value: string) => void;
  className?: string;
  inputClassName?: string;
  placeholder?: string;
  multiline?: boolean;
}

/**
 * 可编辑字段组件。
 * - editable=false 时：显示纯文本
 * - editable=true 时：显示 input/textarea，浅色背景标识可编辑
 */
export function EditableField({
  value,
  editable,
  onChange,
  className,
  inputClassName,
  placeholder,
  multiline = false,
}: EditableFieldProps) {
  const [localValue, setLocalValue] = useState(value ?? "");
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  useEffect(() => {
    setLocalValue(value ?? "");
  }, [value]);

  if (!editable) {
    // 不可编辑时，没有值就不渲染
    if (!value) return null;
    return <span className={className}>{value}</span>;
  }

  // 可编辑时
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setLocalValue(e.target.value);
  };

  const handleBlur = () => {
    if (localValue !== (value ?? "")) {
      onChange(localValue);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      // Esc 还原
      setLocalValue(value ?? "");
      (e.target as HTMLElement).blur();
    }
    if (!multiline && e.key === "Enter") {
      (e.target as HTMLElement).blur();
    }
  };

  if (multiline) {
    return (
      <textarea
        ref={inputRef as React.RefObject<HTMLTextAreaElement>}
        value={localValue}
        onChange={handleChange}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className={inputClassName}
        rows={3}
      />
    );
  }

  return (
    <input
      ref={inputRef as React.RefObject<HTMLInputElement>}
      type="text"
      value={localValue}
      onChange={handleChange}
      onBlur={handleBlur}
      onKeyDown={handleKeyDown}
      placeholder={placeholder}
      className={inputClassName}
    />
  );
}
