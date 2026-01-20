import React, { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';
import { CollectionsSidebar } from '../../../collections';
import { useChat } from '../../hooks/useChat';
import { MessageList } from './MessageList';
import { Composer } from './Composer';

/**
 * ChatInterface Component
 * 
 * Main chat interface component that combines the collections sidebar,
 * message list, and message composer. Manages the overall chat state
 * including selected collection and sidebar visibility.
 * 
 * Features:
 * - Collection selection sidebar
 * - Streaming message responses
 * - Source attribution for AI responses
 * - Responsive design with collapsible sidebar
 */
export const ChatInterface: React.FC = () => {
    const [selectedCollection, setSelectedCollection] = useState<string>('');
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    
    const { messages, isLoading, sendMessage, cleanup } = useChat(selectedCollection);

    useEffect(() => {
        return cleanup;
    }, [cleanup]);

    return (
        <div className="flex h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 font-sans overflow-hidden">
            {/* Sidebar */}
            <CollectionsSidebar
                isOpen={isSidebarOpen}
                selectedCollection={selectedCollection}
                onCollectionSelect={setSelectedCollection}
            />

            {/* Main Content */}
            <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-gray-900 relative">
                {/* Header */}
                <header className="h-16 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between px-4 bg-white dark:bg-gray-900 sticky top-0 z-10">
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md text-gray-500 dark:text-gray-400 transition-colors"
                        >
                            {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                        </button>
                        <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                            {selectedCollection ? selectedCollection : 'Select a collection'}
                        </span>
                    </div>
                </header>

                {/* Chat Area */}
                <MessageList messages={messages} />

                {/* Input Area */}
                <Composer
                    isLoading={isLoading}
                    selectedCollection={selectedCollection}
                    onSend={sendMessage}
                />
            </div>
        </div>
    );
};
