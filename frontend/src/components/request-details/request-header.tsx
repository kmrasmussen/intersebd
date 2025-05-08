import { Link } from "react-router-dom"
import { ChevronLeft } from "lucide-react"

export function RequestHeader({ id, name }: { id: string; name: string }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      <Link to="/" className="text-gray-500 hover:text-gray-700">
        <ChevronLeft className="h-5 w-5" />
      </Link>
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-gray-500">{id.substring(0, 8)}...</span>
        <span className="font-medium">{name}</span>
      </div>
    </div>
  )
}
