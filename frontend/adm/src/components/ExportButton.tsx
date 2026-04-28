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
      className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-[#4E1D17]/80 hover:text-[#4E1D17] bg-white hover:bg-[#EFE9E7] border border-[#E5DDDC] rounded-lg transition-colors"
      title="Exporter en CSV (compatible Excel)"
    >
      <Download className="w-3.5 h-3.5" />
      {label}
    </button>
  )
}
