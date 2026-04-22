import { useState } from 'react'
import { FileDown, Loader2 } from 'lucide-react'
import { exportElementToPDF } from '@/utils/pdfExport'

export default function PdfExportButton({
  targetRef,
  filename,
  title,
}: {
  targetRef: React.RefObject<HTMLElement | null>
  filename: string
  title?: string
}) {
  const [loading, setLoading] = useState(false)

  const handleClick = async () => {
    if (!targetRef.current) return
    setLoading(true)
    try {
      await exportElementToPDF(targetRef.current, filename, title)
    } catch (e) {
      console.error('Export PDF echoue', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      title="Exporter en PDF"
      className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg transition-colors disabled:opacity-50"
    >
      {loading ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
      ) : (
        <FileDown className="w-3.5 h-3.5" />
      )}
      PDF
    </button>
  )
}
