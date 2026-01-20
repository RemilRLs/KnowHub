import {
  FileText,
  FileCode,
  FileJson,
  FileSpreadsheet,
  FileImage,
  File,
} from "lucide-react";

import type { LucideIcon } from "lucide-react";
import PdfIcon from "../../../shared/icons/pdf-icon.svg?react";

export function getFileExtension(source: string): string {
    console.log(`Getting file extension for source: ${source}`);
    return source.split(".").pop()?.toLowerCase() ?? "";
}

export type SourceIcon = LucideIcon | React.FC<React.SVGProps<SVGSVGElement>>;


/**
 * Returns the appropriate icon component for a given file extension
 * 
 * @param ext - File extension without the dot (e.g., 'pdf', 'txt', 'json')
 * @returns Icon component corresponding to the file type
 *
 */
export function getFileIcon(ext: string): SourceIcon {
  switch (ext) {
    case "pdf":
      return PdfIcon;
    case "txt":
    case "md":
      return FileText;
    case "json":
      return FileJson;
    case "csv":
    case "xls":
    case "xlsx":
      return FileSpreadsheet;
    case "js":
    case "ts":
    case "tsx":
    case "py":
      return FileCode;
    case "png":
    case "jpg":
    case "jpeg":
    case "svg":
      return FileImage;
    default:
      return File;
  }
}
