import React from 'react';
import { ChevronRight } from 'lucide-react';

interface CollectionItemProps {
    name: string;
    isSelected: boolean;
    onSelect: (name: string) => void;
}

export const CollectionItem: React.FC<CollectionItemProps> = ({
    name,
    isSelected,
    onSelect,
}) => {
    return (
        <button
            onClick={() => onSelect(name)}
            className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center justify-between group ${
                isSelected
                    ? 'bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-white font-medium'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-900 hover:text-gray-900 dark:hover:text-white'
            }`}
        >
            <span className="truncate">{name}</span>
            {isSelected && <ChevronRight className="w-4 h-4 text-gray-400" />}
        </button>
    );
};
