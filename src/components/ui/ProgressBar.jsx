export function ProgressBar({ progress }) {
  return (
    <div className="h-2.5 w-full overflow-hidden rounded-full bg-gray-200">
      <div
        className="h-2.5 rounded-full bg-blue-600 transition-all duration-300"
        style={{ width: `${progress}%` }}
      ></div>
    </div>
  );
}
