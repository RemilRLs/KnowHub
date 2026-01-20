import React from 'react';
import { Bot, User, Loader2 } from 'lucide-react';
import type { Message } from '../../types';
import { SourcesList } from './SourcesList';

/**
 * Props for the MessageItem component
 */
interface MessageItemProps {
    /** The message object to display */
    message: Message;
}

/**
 * MessageItem Component
 * 
 * Renders a single message in the chat interface with appropriate styling
 * based on the sender (user or assistant). For assistant messages, displays
 * sources and metadata if available.
 * 
 * @param message - The message object containing content, role, and metadata
 */
export const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
    return (
        <div
            className={`flex gap-4 max-w-3xl mx-auto ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
        >
            {/* Assistant avatar */}
            {message.role === 'assistant' && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green-600 flex items-center justify-center mt-1">
                    <Bot size={16} className="text-white" />
                </div>
            )}

            <div className={`flex-1 min-w-0 max-w-[85%] ${message.role === 'user' ? 'text-right' : 'text-left'}`}>
                {/* Message bubble */}
                <div
                    className={`inline-block text-left px-4 py-3 rounded-2xl ${
                        message.role === 'user'
                            ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-tr-sm'
                            : 'text-gray-900 dark:text-gray-100'
                    }`}
                >
                    {message.isPending ? (
                        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span className="text-sm">Thinking...</span>
                        </div>
                    ) : (
                        <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed">
                            <p className="whitespace-pre-wrap">{message.content}</p>
                        </div>
                    )}
                </div>

                {/* Sources list - only shown for assistant messages with metadata */}
                {message.role === 'assistant' && message.metadata?.sources && (
                    <SourcesList
                        sources={message.metadata.sources}
                        retrievalTime={message.metadata.retrieval_time_ms}
                        chunkCount={message.metadata.retrieved_chunks}
                    />
                )}
            </div>

            {/* User avatar */}
            {message.role === 'user' && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center mt-1">
                    <User size={16} className="text-gray-600 dark:text-gray-300" />
                </div>
            )}
        </div>
    );
};
