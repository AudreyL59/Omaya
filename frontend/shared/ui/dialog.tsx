// Système de dialogue charté (couleurs --c-brand → vert ADM / emerald Vendeur).
//
// Remplace window.alert / window.confirm par :
//   - showToast(message, variant?)  → notification coin écran (auto-dismiss)
//   - showConfirm({ message, ... }) → Promise<boolean> (modale centrée)
//
// Monter <DialogHost /> UNE fois dans la page (cf. TicketsPage).
import { useEffect, useState } from 'react'
import {
  AlertTriangle, CheckCircle2, Info, XCircle,
} from 'lucide-react'

export type ToastVariant = 'success' | 'info' | 'error'

interface Toast {
  id: number
  message: string
  variant: ToastVariant
}

interface ConfirmReq {
  id: number
  title?: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'brand' | 'danger'
  resolve: (v: boolean) => void
}

// --- store singleton (pub/sub) ---
let _toasts: Toast[] = []
let _confirm: ConfirmReq | null = null
const _listeners = new Set<() => void>()
let _seq = 1

function _emit() {
  _listeners.forEach((l) => l())
}

export function showToast(
  message: string,
  variant: ToastVariant = 'success',
  durationMs = 3500,
) {
  const id = _seq++
  _toasts = [..._toasts, { id, message, variant }]
  _emit()
  setTimeout(() => {
    _toasts = _toasts.filter((t) => t.id !== id)
    _emit()
  }, durationMs)
}

export function showConfirm(opts: {
  title?: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'brand' | 'danger'
}): Promise<boolean> {
  return new Promise((resolve) => {
    _confirm = { id: _seq++, resolve, ...opts }
    _emit()
  })
}

function _closeConfirm(value: boolean) {
  const c = _confirm
  _confirm = null
  _emit()
  c?.resolve(value)
}

// --- composant hôte (toasts + modale de confirmation) ---
export function DialogHost() {
  const [, force] = useState(0)
  useEffect(() => {
    const l = () => force((n) => n + 1)
    _listeners.add(l)
    return () => {
      _listeners.delete(l)
    }
  }, [])

  return (
    <>
      {/* Toasts (coin haut-droit) */}
      <div className="fixed top-4 right-4 z-[200] flex flex-col gap-2 pointer-events-none">
        {_toasts.map((t) => (
          <ToastCard key={t.id} toast={t} />
        ))}
      </div>

      {/* Modale de confirmation */}
      {_confirm && (
        <>
          <div
            className="fixed inset-0 z-[200] bg-black/40"
            onClick={() => _closeConfirm(false)}
          />
          <div
            role="dialog"
            aria-modal="true"
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-[210] w-[min(92vw,28rem)] bg-white rounded-2xl shadow-xl border border-c-line p-5"
          >
            <div className="flex items-start gap-3">
              <span
                className={
                  'shrink-0 mt-0.5 ' +
                  (_confirm.variant === 'danger' ? 'text-red-600' : 'text-c-brand')
                }
              >
                {_confirm.variant === 'danger' ? (
                  <AlertTriangle className="w-6 h-6" />
                ) : (
                  <Info className="w-6 h-6" />
                )}
              </span>
              <div className="flex-1 min-w-0">
                {_confirm.title && (
                  <h3 className="text-sm font-semibold text-c-ink mb-1">
                    {_confirm.title}
                  </h3>
                )}
                <p className="text-sm text-c-ink-soft whitespace-pre-line">
                  {_confirm.message}
                </p>
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => _closeConfirm(false)}
                className="px-3 py-2 rounded-lg border border-c-line-strong text-sm text-c-ink hover:bg-c-surface-soft transition-colors"
              >
                {_confirm.cancelLabel || 'Annuler'}
              </button>
              <button
                onClick={() => _closeConfirm(true)}
                className={
                  'px-3 py-2 rounded-lg text-white text-sm font-semibold hover:brightness-110 transition-all ' +
                  (_confirm.variant === 'danger' ? 'bg-red-600' : 'bg-c-brand')
                }
              >
                {_confirm.confirmLabel || 'Confirmer'}
              </button>
            </div>
          </div>
        </>
      )}
    </>
  )
}

function ToastCard({ toast }: { toast: Toast }) {
  const base =
    'pointer-events-auto flex items-center gap-2 px-3 py-2 rounded-lg shadow-lg text-sm font-medium max-w-sm'
  if (toast.variant === 'error') {
    return (
      <div className={base + ' bg-red-600 text-white'}>
        <XCircle className="w-4 h-4 shrink-0" />
        <span className="whitespace-pre-line">{toast.message}</span>
      </div>
    )
  }
  if (toast.variant === 'info') {
    return (
      <div className={base + ' bg-white border border-c-line text-c-ink'}>
        <Info className="w-4 h-4 shrink-0 text-c-brand" />
        <span className="whitespace-pre-line">{toast.message}</span>
      </div>
    )
  }
  // success
  return (
    <div className={base + ' bg-c-brand text-white'}>
      <CheckCircle2 className="w-4 h-4 shrink-0" />
      <span className="whitespace-pre-line">{toast.message}</span>
    </div>
  )
}
