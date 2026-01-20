import React from 'react';

export const SidebarFooter: React.FC = () => {
    return (
        <div className="p-4 border-t border-gray-200 dark:border-gray-800">
            <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs font-medium">
                    U
                </div>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">User</p>
                </div>
            </div>
        </div>
    );
};
