/**
 * Message object representing a chat message
 */
export interface Message {
    /** Unique identifier for the message */
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    isPending?: boolean;
    metadata?: MessageMetadata;
}

/**
 * Metadata associated with an assistant message response
 */
export interface MessageMetadata {
    sources?: string[];
    retrieved_chunks?: number;
    retrieval_time_ms?: number;
    generation_time_ms?: number;
    total_time_ms?: number;
    temperature?: number;
    max_tokens?: number;
    k?: number;
}

/**
 * Parameters for streaming chat completion
 */
export interface StreamParams {
    query: string;
    collection: string;
    k: string;
}

/**
 * Creates a unique message ID
 * Uses crypto.randomUUID if available, otherwise falls back to timestamp + random
 * 
 * @returns A unique message identifier string
 */
export const createMessageId = (): string => {
    if (globalThis.crypto?.randomUUID) {
        return globalThis.crypto.randomUUID();
    }
    return `${Date.now()}-${Math.random()}`;
};
