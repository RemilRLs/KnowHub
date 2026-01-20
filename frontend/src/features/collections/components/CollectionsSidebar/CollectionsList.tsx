import React from 'react';
import { CollectionItem } from './CollectionItem';

interface CollectionsListProps {
    collections: string[];
    selectedCollection: string;
    onCollectionSelect: (collection: string) => void;
}

export const CollectionsList: React.FC<CollectionsListProps> = ({
    collections,
    selectedCollection,
    onCollectionSelect,
}) => {
    return (
        <div className="p-2 flex-1 overflow-y-auto">
            <div className="mb-4">
                <h2 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider px-3 py-2">
                    Collections
                </h2>
                <div className="space-y-0.5">
                    {collections.map((col) => (
                        <CollectionItem
                            key={col}
                            name={col}
                            isSelected={selectedCollection === col}
                            onSelect={onCollectionSelect}
                        />
                    ))}
                    {collections.length === 0 && (
                        <div className="text-sm text-gray-500 px-3 py-2">No collections found</div>
                    )}
                </div>
            </div>
        </div>
    );
};
