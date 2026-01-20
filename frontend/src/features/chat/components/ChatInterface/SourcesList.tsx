import React from 'react';
import { FileText, Clock } from 'lucide-react';
import { SourceBadge } from './SourceBadge';

/**
 * Props for the SourcesList component
 */
interface SourcesListProps {
    /** Array of source file names used to generate the response */
    sources: string[];
    /** Time taken to retrieve chunks in milliseconds */
    retrievalTime?: number;
    /** Number of chunks retrieved */
    chunkCount?: number;
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
    chunkCount 
}) => {
    if (!sources || sources.length === 0) return null;

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
                {sources.map((source) => (
                        <SourceBadge source={source} />
                ))}
            </div>
        </div>
    );
};
