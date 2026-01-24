import { buildStreamUrl, http } from '../../../shared/api/http';
import type { StreamParams, DownloadUrlResponse } from '../types';

export function createStreamConnection(params: StreamParams): EventSource {
    const url = buildStreamUrl('/api/v1/generate/stream', {
        query: params.query,
        collection: params.collection,
        k: params.k,
    });
    
    return new EventSource(url);
}

export async function fetchDownloadUrl(key: string): Promise<DownloadUrlResponse> {
    return http<DownloadUrlResponse>('/api/v1/files/download', {
        params: { key },
    });
}
