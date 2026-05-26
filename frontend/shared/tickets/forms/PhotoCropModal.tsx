import { useCallback, useState } from 'react'
import Cropper from 'react-easy-crop'
import { Loader2, RotateCw, X } from 'lucide-react'

import { getCroppedDataUrl, type PixelCrop } from './cropImage'
import { showToast } from '../../ui/dialog'

// Éditeur de recadrage/rotation (remplace l'EditeurDImages WinDev).
// Renvoie l'image recadrée en data URL JPEG via onValidate.
export default function PhotoCropModal({
  src,
  aspect = 3 / 4,
  onValidate,
  onClose,
}: {
  src: string
  aspect?: number
  onValidate: (dataUrl: string) => void
  onClose: () => void
}) {
  const [crop, setCrop] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [rotation, setRotation] = useState(0)
  const [areaPx, setAreaPx] = useState<PixelCrop | null>(null)
  const [busy, setBusy] = useState(false)

  const onCropComplete = useCallback(
    (_a: unknown, areaPixels: PixelCrop) => setAreaPx(areaPixels),
    [],
  )

  const valider = async () => {
    if (!areaPx) return
    setBusy(true)
    try {
      const url = await getCroppedDataUrl(src, areaPx, rotation)
      onValidate(url)
    } catch {
      showToast('Erreur lors du recadrage de l’image.', 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-[80] bg-black/50" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-[90] bg-white rounded-2xl shadow-2xl border border-c-line w-[640px] max-w-[95vw] flex flex-col overflow-hidden">
        <header className="flex items-center justify-between px-5 py-3 border-b border-c-line bg-c-surface-soft">
          <span className="text-base font-semibold text-c-ink">
            Recadrer la photo
          </span>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-c-ink-faint hover:bg-c-surface-medium transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </header>

        <div className="relative bg-c-ink-strong h-[420px]">
          <Cropper
            image={src}
            crop={crop}
            zoom={zoom}
            rotation={rotation}
            aspect={aspect}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onRotationChange={setRotation}
            onCropComplete={onCropComplete}
          />
        </div>

        <div className="px-5 py-3 border-t border-c-line space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-xs text-c-ink-soft w-16">Zoom</span>
            <input
              type="range"
              min={1}
              max={3}
              step={0.01}
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
              className="flex-1 accent-c-brand"
            />
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-c-ink-soft w-16">Rotation</span>
            <input
              type="range"
              min={0}
              max={360}
              step={1}
              value={rotation}
              onChange={(e) => setRotation(Number(e.target.value))}
              className="flex-1 accent-c-brand"
            />
            <button
              onClick={() => setRotation((r) => (r + 90) % 360)}
              className="p-1.5 rounded-lg border border-c-line-strong text-c-ink hover:bg-c-surface-medium transition-colors"
              title="Pivoter de 90°"
            >
              <RotateCw className="w-4 h-4" />
            </button>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-c-line-strong text-sm text-c-ink hover:bg-c-surface-medium transition-colors"
            >
              Annuler
            </button>
            <button
              onClick={valider}
              disabled={busy || !areaPx}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
            >
              {busy && <Loader2 className="w-4 h-4 animate-spin" />}
              Valider
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
