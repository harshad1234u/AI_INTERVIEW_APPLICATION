"use client";

import { downloadHtml, printHtml } from "@/lib/download";

type Props = {
  what: "plan" | "report";
  fileName: string;
  /** Builds the document when asked, from what is on screen: never a second fetch. */
  build: () => string;
};

/** Download the document as a file, or print it ("Save as PDF" in the print dialog). */
export default function ExportButtons({ what, fileName, build }: Props) {
  return (
    <div className="actions export-actions">
      <button type="button" onClick={() => downloadHtml(fileName, build())}>
        Download {what}
      </button>
      <button type="button" onClick={() => printHtml(build())}>
        Print or save as PDF
      </button>
    </div>
  );
}
