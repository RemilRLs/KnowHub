import { buildStreamUrl } from '../../../shared/api/http';
import type { StreamParams } from '../types';

export function createStreamConnection(params: StreamParams): EventSource {
    const url = buildStreamUrl('/api/v1/generate/stream', {
        query: params.query,
        collection: params.collection,
        k: params.k,
    });
    
    return new EventSource(url);
}