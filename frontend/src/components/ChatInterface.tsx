import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, User, Database, Menu, X, ChevronRight } from 'lucide-react';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    isPending?: boolean;
}

const createMessageId = () => {
    if (globalThis.crypto?.randomUUID) {
        return globalThis.crypto.randomUUID();
    }
    return `${Date.now()}-${Math.random()}`;
};

export const ChatInterface: React.FC = () => {

    const [messages, setMessages] = useState<Message[]>([
        {
            id: 'welcome',
            role: 'assistant',
            content: "Hello. I am the KnowHub Assistant. Please select a collection to begin.",
            timestamp: new Date(),
        },
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [collections, setCollections] = useState<string[]>([]);
    const [selectedCollection, setSelectedCollection] = useState<string>('');
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [activeStream, setActiveStream] = useState<EventSource | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);


    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        fetchCollections();
    }, []);

    useEffect(() => {
        return () => {
            if (activeStream) {
                activeStream.close();
            }
        };
    }, [activeStream]);


    const fetchCollections = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/v1/collections/');
            if (response.ok) {
                const data = await response.json();
                setCollections(data);
                if (data.length > 0) {
                    setSelectedCollection(data[0]);
                }
            }
        } catch (error) {
            console.error('Failed to fetch collections:', error);
        }
    };

    const startStream = (messageId: string, query: string) => {
        if (activeStream) {
            activeStream.close();
        }

        const params = new URLSearchParams({
            query,
            collection: selectedCollection,
            k: '4',
        });

        const stream = new EventSource(`http://localhost:8000/api/v1/generate/stream?${params.toString()}`);
        setActiveStream(stream);

        let buffer = '';
        let flushTimer: number | null = null;

        const flush = () => {
            if (!buffer) return;
            const textToAppend = buffer;
            setMessages((prev) =>
                prev.map((msg) =>
                    msg.id === messageId
                        ? { ...msg, content: msg.content + textToAppend, isPending: false }
                        : msg
                )
            );
            buffer = '';
            flushTimer = null;
        };

        stream.onopen = () => {
            console.log('Stream connection opened');
        };

        stream.onmessage = (event) => {
            if (!event.data) return;

            try {
                const parsed = JSON.parse(event.data);
                const token = parsed?.token;

                if (token) {
                    buffer += token;
                    if (flushTimer === null) {
                        flushTimer = window.setTimeout(flush, 50);
                    }
                }
            } catch (error) {
                console.warn('Received non-JSON message in stream:', event.data);
            }
        };

        stream.addEventListener('done', () => {
            if (flushTimer !== null) {
                window.clearTimeout(flushTimer);
            }
            flush();
            stream.close();
            setActiveStream(null);
            setMessages((prev) =>
                prev.map((msg) =>
                    msg.id === messageId
                        ? {
                            ...msg,
                            content: msg.content || 'No response received.',
                            isPending: false,
                        }
                        : msg
                )
            );
            setIsLoading(false);
        });

        stream.addEventListener('error', (event) => {
            console.error('Streaming error:', event);
            if (flushTimer !== null) {
                window.clearTimeout(flushTimer);
            }
            flush();
            stream.close();
            setActiveStream(null);
            setMessages((prev) =>
                prev.map((msg) =>
                    msg.id === messageId
                        ? {
                            ...msg,
                            content: msg.content || "An error occurred while streaming the response.",
                            isPending: false,
                        }
                        : msg
                )
            );
            setIsLoading(false);
        });

        return stream;
    };


    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading || !selectedCollection) return;

        const userMessage: Message = {
            id: createMessageId(),

            role: 'user',
            content: input,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const assistantMessageId = createMessageId();
            const assistantMessage: Message = {
                id: assistantMessageId,
                role: 'assistant',
                content: '',
                timestamp: new Date(),
                isPending: true,
            };

            setMessages((prev) => [...prev, assistantMessage]);
            startStream(assistantMessageId, input);
        } catch (error) {
            console.error('Submission error:', error);
            setMessages((prev) => [
                ...prev,
                {
                    id: createMessageId(),
                    role: 'assistant',
                    content: "Unable to connect to the server.",
                    timestamp: new Date(),
                },
            ]);
            setIsLoading(false);
        }

    };

    return (
        <div className="flex h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 font-sans overflow-hidden">
            {/* Sidebar */}
            <div
                className={`${isSidebarOpen ? 'w-64' : 'w-0'} bg-gray-50 dark:bg-gray-950 border-r border-gray-200 dark:border-gray-800 transition-all duration-300 ease-in-out flex flex-col overflow-hidden`}
            >
                <div className="p-4 flex items-center gap-2 border-b border-gray-200 dark:border-gray-800 h-16">
                    <div className="p-1.5 bg-blue-600 rounded-lg">
                        <Database className="w-5 h-5 text-white" />
                    </div>
                    <h1 className="text-lg font-semibold tracking-tight">KnowHub</h1>
                </div>

                <div className="p-2 flex-1 overflow-y-auto">
                    <div className="mb-4">
                        <h2 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider px-3 py-2">
                            Collections
                        </h2>
                        <div className="space-y-0.5">
                            {collections.map((col) => (
                                <button
                                    key={col}
                                    onClick={() => setSelectedCollection(col)}
                                    className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center justify-between group ${selectedCollection === col
                                        ? 'bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-white font-medium'
                                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-900 hover:text-gray-900 dark:hover:text-white'
                                        }`}
                                >
                                    <span className="truncate">{col}</span>
                                    {selectedCollection === col && <ChevronRight className="w-4 h-4 text-gray-400" />}
                                </button>
                            ))}
                            {collections.length === 0 && (
                                <div className="text-sm text-gray-500 px-3 py-2">No collections found</div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="p-4 border-t border-gray-200 dark:border-gray-800">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs font-medium">
                            U
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">User</p>
                        </div>
                    </div>
                </div>
            </div>

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
                <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
                    {messages.map((msg) => (
                        <div
                            key={msg.id}
                            className={`flex gap-4 max-w-3xl mx-auto ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            {msg.role === 'assistant' && (
                                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green-600 flex items-center justify-center mt-1">
                                    <Bot size={16} className="text-white" />
                                </div>
                            )}

                            <div className={`flex-1 min-w-0 max-w-[85%] ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                                <div className={`inline-block text-left px-4 py-3 rounded-2xl ${msg.role === 'user'
                                    ? 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-tr-sm'
                                    : 'text-gray-900 dark:text-gray-100'
                                    }`}>
                                    {msg.isPending ? (
                                        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            <span className="text-sm">Thinking...</span>
                                        </div>
                                    ) : (
                                        <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed">
                                            <p className="whitespace-pre-wrap">{msg.content}</p>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {msg.role === 'user' && (
                                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center mt-1">
                                    <User size={16} className="text-gray-600 dark:text-gray-300" />
                                </div>
                            )}
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-4 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800">
                    <div className="max-w-3xl mx-auto">
                        <form onSubmit={handleSubmit} className="relative">
                            <div className="relative flex items-center">
                                <input
                                    type="text"
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    placeholder={selectedCollection ? "Message KnowHub..." : "Select a collection to start"}
                                    className="w-full bg-white dark:bg-gray-800 text-gray-900 dark:text-white py-3.5 pl-4 pr-12 rounded-xl border border-gray-200 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm placeholder-gray-400 dark:placeholder-gray-500"
                                    disabled={isLoading || !selectedCollection}
                                />
                                <button
                                    type="submit"
                                    disabled={!input.trim() || isLoading || !selectedCollection}
                                    className="absolute right-2 p-2 bg-gray-900 dark:bg-white hover:bg-gray-700 dark:hover:bg-gray-200 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg text-white dark:text-gray-900 transition-colors"
                                >
                                    {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                                </button>
                            </div>
                        </form>
                        <p className="text-center text-xs text-gray-400 dark:text-gray-500 mt-2">
                            KnowHub can make mistakes. Consider checking important information.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};
