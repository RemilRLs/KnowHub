import React, { useState } from 'react';
import { FileText, Clock } from 'lucide-react';
import { SourceBadge } from './SourceBadge';
import { fetchDownloadUrl } from '../../api/chat.api';

/**
 * Props for the SourcesList component
 */
interface SourcesListProps {
    sources: string[];
    retrievalTime?: number;
    chunkCount?: number;
    sourceMap?: Record<string, string>;
}

/**
 * SourcesList Component
 * 
 * Displays the list of sources (documents) that were used to generate an AI response.
 * Shows source names as badges along with optional metadata like retrieval time and chunk count.
 * 
 * @param sources - Array of source document names
 * @param retrievalTime - Optional retrieval time in milliseconds
 * @param chunkCount - Optional number of chunks retrieved
 */
export const SourcesList: React.FC<SourcesListProps> = ({
    sources,
    retrievalTime,
    chunkCount,
    sourceMap,
}) => {
    console.log("[SourcesList] Rendering with sources:", sources, "retrievalTime:", retrievalTime, "chunkCount:", chunkCount);
    if (!sources || sources.length === 0) {
        console.log("[SourcesList] No sources to display");
        return null;
    }

    const [downloadingSource, setDownloadingSource] = useState<string | null>(null);

    const handleDownload = async (source: string) => {
        const key = sourceMap?.[source];
        if (!key || downloadingSource) {
            return;
        }

        try {
            setDownloadingSource(source);
            const response = await fetchDownloadUrl(key);
            window.open(response.url, '_blank', 'noopener,noreferrer');
        } catch (error) {
            console.error(`[SourcesList] Download failed for ${source}:`, error);
        } finally {
            setDownloadingSource(null);
        }
    };

    return (
        <div className="mt-2 space-y-2">
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <FileText className="w-3 h-3" />
                <span className="font-medium">Sources ({sources.length})</span>
                

                {retrievalTime && (
                    <>
                        <span>•</span>
                        <Clock className="w-3 h-3" />
                        <span>{retrievalTime.toFixed(0)}ms</span>
                    </>
                )}
                
                {chunkCount && (
                    <>
                        <span>•</span>
                        <span>{chunkCount} chunks</span>
                    </>
                )}
            </div>
            
            <div className="flex flex-wrap gap-2">
                {sources.map((source, index) => {
                    const isDownloadable = Boolean(sourceMap?.[source]);
                    return (
                        <SourceBadge
                            key={`${source}-${index}`}
                            source={source}
                            onClick={isDownloadable ? () => handleDownload(source) : undefined}
                            isLoading={downloadingSource === source}
                        />
                    );
                })}
            </div>
        </div>
    );
};
