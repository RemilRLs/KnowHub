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
export interface ChunkReference {
    chunk_number: number;
    text: string;
    source: string;
    page?: number | string | null;
    processed_key?: string | null;
}

export interface MessageMetadata {
    sources?: string[];
    retrieved_chunks?: number;
    retrieval_time_ms?: number;
    generation_time_ms?: number;
    total_time_ms?: number;
    temperature?: number;
    max_tokens?: number;
    k?: number;
    chunk_map?: ChunkReference[];
    source_map?: Record<string, string>;
}


/**
 * Parameters for streaming chat completion
 */
export interface StreamParams {
    query: string;
    collection: string;
    k: string;
}

export interface DownloadUrlResponse {
    key: string;
    url: string;
    expires_in: number;
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
