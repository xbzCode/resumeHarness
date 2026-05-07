/** 复制文本到剪贴板，兼容非 HTTPS 环境。
 *
 * 优先使用 navigator.clipboard API（仅 HTTPS 安全上下文可用），
 * 不可用时降级到 document.execCommand("copy")。
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }

    // fallback for non-HTTPS / older browsers
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}
