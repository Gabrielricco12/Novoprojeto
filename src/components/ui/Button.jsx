export function Button({ children, className, ...props }) {
  return (
    <button
      className={`w-full rounded-md bg-blue-600 px-4 py-3 text-lg font-semibold text-white shadow-sm
                  transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 
                  focus:ring-blue-500 focus:ring-offset-2
                  disabled:cursor-not-allowed disabled:bg-blue-300 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
