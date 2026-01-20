import { FileText } from "lucide-react";
import { getFileExtension, getFileIcon } from "../../utils/sourceUtils";

interface SourceBadgeProps {
  source: string;
}

export const SourceBadge: React.FC<SourceBadgeProps> = ({ source }) => {
  const extension = getFileExtension(source);
  const Icon = getFileIcon(extension) ?? FileText;

  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs
                    bg-gray-100 dark:bg-gray-800
                    text-gray-700 dark:text-gray-300
                    border-gray-200 dark:border-gray-700">
      <Icon className="w-3 h-3 text-gray-400" />
      <span
        className="font-medium truncate max-w-[200px]"
        title={source}
      >
        {source}
      </span>
    </div>
  );
}