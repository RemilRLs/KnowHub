import { http } from '../../../shared/api/http';

export async function fetchCollections(): Promise<string[]> {
    console.log('Fetching collections from API');
    return http<string[]>('/api/v1/collections/');
}