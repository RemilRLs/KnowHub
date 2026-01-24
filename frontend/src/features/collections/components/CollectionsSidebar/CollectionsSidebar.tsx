import React, { useEffect } from 'react';
import { useCollections } from '../../hooks/useCollections';
import { SidebarHeader } from './SidebarHeader';
import { CollectionsList } from './CollectionsList';
import { SidebarFooter } from './SidebarFooter';

interface CollectionsSidebarProps {
    isOpen: boolean;
    selectedCollection: string;
    onCollectionSelect: (collection: string) => void;
}

export const CollectionsSidebar: React.FC<CollectionsSidebarProps> = ({
    isOpen,
    selectedCollection,
    onCollectionSelect,
}) => {
    const { collections, isLoading } = useCollections();

    useEffect(() => {
        if (collections.length > 0 && !selectedCollection) {
            onCollectionSelect(collections[0]);
        }
    }, [collections, selectedCollection, onCollectionSelect]);

    return (
        <div
            className={`${
                isOpen ? 'w-64' : 'w-0'
            } bg-gray-50 dark:bg-gray-950 border-r border-gray-200 dark:border-gray-800 transition-all duration-300 ease-in-out flex flex-col overflow-hidden`}
        >
            <SidebarHeader />
            <CollectionsList
                collections={collections}
                selectedCollection={selectedCollection}
                onCollectionSelect={onCollectionSelect}
            />
            <SidebarFooter />
        </div>
    );
};
