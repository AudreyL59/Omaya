import { Download } from 'lucide-react'

export default function ExportButton({
  onClick,
  label = 'Exporter',
}: {
  onClick: () => void
  label?: string
}) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg transition-colors"
      title="Exporter en CSV (compatible Excel)"
    >
      <Download className="w-3.5 h-3.5" />
      {label}
    </button>
  )
}
