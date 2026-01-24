import React from "react";
import type { ChunkReference as ChunkReferenceType } from "../../types";

interface ChunkReferenceProps {
  chunkNumber: number;
  chunks?: ChunkReferenceType[];
  showBrackets?: boolean;
}

const PAGE_UNKNOWN_VALUES = new Set([null, undefined, "-1", -1, "N/A", "NA", ""]);

const normalizePageLabel = (page: ChunkReferenceType["page"]) => {
  if (PAGE_UNKNOWN_VALUES.has(page)) {
    return "NA";
  }
  if (typeof page === "number") {
    return page.toString();
  }
  return page ?? "NA";
};

const buildTooltipText = (chunk: ChunkReferenceType) => {
  const sourceLine = `Source: ${chunk.source ?? "Unknown"}`;
  const pageLine = `Page: ${normalizePageLabel(chunk.page)}`;
  return `${sourceLine}\n${pageLine}\n\n${chunk.text ?? ""}`.trim();
};

export const ChunkReference: React.FC<ChunkReferenceProps> = ({
  chunkNumber,
  chunks,
  showBrackets = false,
}) => {
  const chunk = chunks?.find((item) => item.chunk_number === chunkNumber);
  const label = showBrackets ? `[${chunkNumber}]` : `${chunkNumber}`;

  if (!chunk) {
    return (
      <sup className="text-xs font-medium text-gray-400" aria-label={`Chunk ${chunkNumber}`}>
        {label}
      </sup>
    );
  }

  const tooltipText = buildTooltipText(chunk);

  return (
    <span
      className="relative inline-flex align-baseline group"
      aria-label={tooltipText}
      title={tooltipText}
    >
      <sup className="text-xs font-semibold text-blue-600">{label}</sup>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 w-80 -translate-x-1/2 rounded-md border border-gray-200 bg-white px-3 py-2 text-[11px] leading-relaxed text-gray-700 shadow-lg opacity-0 transition-opacity duration-150 group-hover:opacity-100 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
      >
        <span className="block max-h-64 whitespace-pre-wrap break-words overflow-y-auto">
          {tooltipText}
        </span>
      </span>
    </span>
  );
};
