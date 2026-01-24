import React from 'react';
import { Database } from 'lucide-react';

export const SidebarHeader: React.FC = () => {
    return (
        <div className="p-4 flex items-center gap-2 border-b border-gray-200 dark:border-gray-800 h-16">
            <div className="p-1.5 bg-blue-600 rounded-lg">
                <Database className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-lg font-semibold tracking-tight">KnowHub</h1>
        </div>
    );
};
