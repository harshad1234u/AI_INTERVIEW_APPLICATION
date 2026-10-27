// Browser-only: saves or prints a document built by lib/exportDoc.ts. Nothing leaves the browser.

/** Saves the HTML document as a file the candidate keeps (it opens in any browser). */
export function downloadHtml(fileName: string, html: string): void {
  const url = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

/** Opens the browser's print dialog for exactly that document ("Save as PDF" is one choice),
 * from a hidden frame, so the page itself is never what gets printed. */
export function printHtml(html: string): void {
  const frame = document.createElement("iframe");
  frame.setAttribute("aria-hidden", "true");
  frame.tabIndex = -1;
  frame.style.cssText = "position:fixed;width:0;height:0;border:0;left:-9999px";
  frame.srcdoc = html;
  frame.onload = () => {
    frame.contentWindow?.focus();
    frame.contentWindow?.print();
    setTimeout(() => frame.remove(), 60_000); // the dialog may stay open a while
  };
  document.body.appendChild(frame);
}
