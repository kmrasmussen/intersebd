import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";

interface PageTabsProps {
  projectId: string;
}

export function PageTabs({ projectId }: PageTabsProps) {
  const location = useLocation(); // Use React Router hook
  const pathname = location.pathname;

  // Helper to construct project-specific paths
  const getProjectPath = (path: string) => {
    if (!projectId) return path;
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    return `/${projectId}${cleanPath === "/" ? "" : cleanPath}`;
  };

  const tabs = [
    { name: "Requests Overview", path: "/" },
    { name: "Caller", path: "/caller" },
    { name: "JSON Schema", path: "/json-schema" },
    { name: "Generate Dataset", path: "/generate-dataset" },
  ];

  return (
    <div className="mb-6 border-b border-gray-200">
      <nav className="-mb-px flex space-x-8" aria-label="Tabs">
        {tabs.map((tab) => {
          const fullPath = getProjectPath(tab.path);
          // Determine if the current path matches the tab's path
          // For the root path, check for exact match. For others, check if it startsWith.
          const isActive = tab.path === "/" ? pathname === fullPath : pathname.startsWith(fullPath);

          return (
            <Link
              key={tab.name}
              to={fullPath} // Use 'to' prop
              className={cn(
                isActive
                  ? "border-indigo-500 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300",
                "whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
              )}
              aria-current={isActive ? "page" : undefined}
            >
              {tab.name}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
