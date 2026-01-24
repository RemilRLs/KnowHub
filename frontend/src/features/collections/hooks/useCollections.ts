import { useState, useEffect } from 'react';
import { fetchCollections } from '../api/collections.api';

/**
 * Custom hook for managing collections data
 * Fetches and manages the list of available document collections
 * 
 * @returns Object containing collections array, loading state, error state, and refetch function
 * 
 * @example
 * ```tsx
 * const { collections, isLoading, error, refetch } = useCollections();
 * 
 * if (isLoading) return <div>Loading...</div>;
 * if (error) return <div>Error: {error.message}</div>;
 * 
 * return (
 *   <ul>
 *     {collections.map(col => <li key={col}>{col}</li>)}
 *   </ul>
 * );
 * ```
 */
export function useCollections() {
    const [collections, setCollections] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        loadCollections();
    }, []);

    /**
     * Fetches the list of collections from the API
     * Sets loading, error, and collections state accordingly
     */
    const loadCollections = async () => {
        try {
            setIsLoading(true);
            setError(null);
            const data = await fetchCollections();
            setCollections(data);
        } catch (err) {
            setError(err instanceof Error ? err : new Error('Failed to fetch collections'));
            console.error('Failed to fetch collections:', err);
        } finally {
            setIsLoading(false);
        }
    };

    return {
        /** Array of collection names */
        collections,
        /** Whether collections are currently being loaded */
        isLoading,
        /** Error object if fetch failed, null otherwise */
        error,
        /** Function to manually refetch collections */
        refetch: loadCollections,
    };
}
