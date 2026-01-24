import React, { useRef, useEffect } from 'react';
import { MessageItem } from './MessageItem';
import type { Message } from '../../types';

interface MessageListProps {
    messages: Message[];
}

export const MessageList: React.FC<MessageListProps> = ({ messages }) => {
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    return (
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
            {messages.map((msg) => (
                <MessageItem key={msg.id} message={msg} />
            ))}
            <div ref={messagesEndRef} />
        </div>
    );
};
