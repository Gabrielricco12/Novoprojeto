import React from 'react';

export function StatusMessage({ message, type, children }) {
  const baseClasses = 'w-full rounded-md p-4 text-center text-sm font-medium';
  const typeClasses = {
    info: 'bg-blue-100 text-blue-800 border border-blue-200',
    error: 'bg-red-100 text-red-800 border border-red-200',
    success: 'bg-green-100 text-green-800 border border-green-200',
  };
  return (
    <div className={`${baseClasses} ${typeClasses[type]}`}>
      {message}
      {children}
    </div>
  );
}
