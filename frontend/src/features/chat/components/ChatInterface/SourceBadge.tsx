import { FileText, Download, Loader2 } from "lucide-react";
import { getFileExtension, getFileIcon } from "../../utils/sourceUtils";

interface SourceBadgeProps {
  source: string;
  onClick?: () => void;
  isLoading?: boolean;
}

export const SourceBadge: React.FC<SourceBadgeProps> = ({ source, onClick, isLoading }) => {
  const extension = getFileExtension(source);
  const Icon = getFileIcon(extension) ?? FileText;
  const isClickable = Boolean(onClick);

  const content = (
    <>
      <Icon className="w-3 h-3 text-gray-400" />
      <span className="font-medium truncate max-w-[200px]" title={source}>
        {source}
      </span>
      {isClickable && (
        <span className="ml-1 text-gray-400">
          {isLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
        </span>
      )}
    </>
  );

  const className =
    "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs " +
    "bg-gray-100 dark:bg-gray-800 " +
    "text-gray-700 dark:text-gray-300 " +
    "border-gray-200 dark:border-gray-700";

  if (isClickable) {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={isLoading}
        className={`${className} hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed`}
        title={`Download ${source}`}
      >
        {content}
      </button>
    );
  }

  return <div className={className}>{content}</div>;
}
