import React, { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface ComposerProps {
    isLoading: boolean;
    selectedCollection: string;
    onSend: (message: string) => void;
}

export const Composer: React.FC<ComposerProps> = ({
    isLoading,
    selectedCollection,
    onSend,
}) => {
    const [input, setInput] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading || !selectedCollection) return;

        onSend(input);
        setInput('');
    };

    return (
        <div className="p-4 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800">
            <div className="max-w-3xl mx-auto">
                <form onSubmit={handleSubmit} className="relative">
                    <div className="relative flex items-center">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder={
                                selectedCollection
                                    ? "Message KnowHub..."
                                    : "Select a collection to start"
                            }
                            className="w-full bg-white dark:bg-gray-800 text-gray-900 dark:text-white py-3.5 pl-4 pr-12 rounded-xl border border-gray-200 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm placeholder-gray-400 dark:placeholder-gray-500"
                            disabled={isLoading || !selectedCollection}
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || isLoading || !selectedCollection}
                            className="absolute right-2 p-2 bg-gray-900 dark:bg-white hover:bg-gray-700 dark:hover:bg-gray-200 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-white dark:text-gray-900 transition-colors"
                        >
                            {isLoading ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <Send className="w-4 h-4" />
                            )}
                        </button>
                    </div>
                </form>
                <p className="text-center text-xs text-gray-400 dark:text-gray-500 mt-2">
                    KnowHub can make mistakes. Consider checking important information.
                </p>
            </div>
        </div>
    );
};
