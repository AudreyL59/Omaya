// Système de dialogue charté (couleurs --color-c-brand → vert ADM / emerald
// Vendeur). Remplace window.alert / window.confirm par :
//   - showToast(message, variant?)  → notification coin écran (auto-dismiss)
//   - showConfirm({ message, ... }) → Promise<boolean> (modale centrée)
//
// Monter <DialogHost /> UNE fois dans la page (cf. TicketsPage). Rendu via
// un portail sur document.body. Les couleurs de marque sont lues au runtime
// (var CSS de thème) et appliquées en inline pour être garanties visibles.
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'

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
  durationMs = 4000,
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

function _brandColor(): string {
  if (typeof document === 'undefined') return '#17494E'
  const v = getComputedStyle(document.documentElement)
    .getPropertyValue('--color-c-brand')
    .trim()
  return v || '#17494E'
}

// --- composant hôte (toasts + modale de confirmation) ---
export function DialogHost() {
  const [toasts, setToasts] = useState<Toast[]>([])
  const [confirm, setConfirm] = useState<ConfirmReq | null>(null)

  useEffect(() => {
    const sync = () => {
      setToasts([..._toasts])
      setConfirm(_confirm)
    }
    _listeners.add(sync)
    sync()
    return () => {
      _listeners.delete(sync)
    }
  }, [])

  if (typeof document === 'undefined') return null
  const brand = _brandColor()

  return createPortal(
    <>
      {/* Toasts (coin haut-droit) */}
      <div
        style={{
          position: 'fixed',
          top: 16,
          right: 16,
          zIndex: 2147483647,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          pointerEvents: 'none',
        }}
      >
        {toasts.map((t) => {
          const bg =
            t.variant === 'error'
              ? '#dc2626'
              : t.variant === 'info'
                ? '#ffffff'
                : brand
          const fg = t.variant === 'info' ? '#1e293b' : '#ffffff'
          return (
            <div
              key={t.id}
              style={{
                pointerEvents: 'auto',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '12px 16px',
                borderRadius: 10,
                boxShadow: '0 10px 25px rgba(0,0,0,.18)',
                fontSize: 14,
                fontWeight: 500,
                maxWidth: 360,
                background: bg,
                color: fg,
                border: t.variant === 'info' ? '1px solid #e5e7eb' : 'none',
              }}
            >
              {t.variant === 'error' ? (
                <XCircle className="w-4 h-4 shrink-0" />
              ) : t.variant === 'info' ? (
                <Info className="w-4 h-4 shrink-0" style={{ color: brand }} />
              ) : (
                <CheckCircle2 className="w-4 h-4 shrink-0" />
              )}
              <span style={{ whiteSpace: 'pre-line' }}>{t.message}</span>
            </div>
          )
        })}
      </div>

      {/* Modale de confirmation */}
      {confirm && (
        <>
          <div
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 2147483646,
              background: 'rgba(0,0,0,.4)',
            }}
            onClick={() => _closeConfirm(false)}
          />
          <div
            role="dialog"
            aria-modal="true"
            style={{
              position: 'fixed',
              left: '50%',
              top: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 2147483647,
              width: 'min(92vw, 28rem)',
              background: '#fff',
              borderRadius: 16,
              boxShadow: '0 20px 50px rgba(0,0,0,.25)',
              border: '1px solid #e5e7eb',
              padding: 20,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
              <span
                style={{
                  flexShrink: 0,
                  marginTop: 2,
                  color: confirm.variant === 'danger' ? '#dc2626' : brand,
                }}
              >
                {confirm.variant === 'danger' ? (
                  <AlertTriangle className="w-6 h-6" />
                ) : (
                  <Info className="w-6 h-6" />
                )}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                {confirm.title && (
                  <h3
                    style={{
                      fontSize: 14,
                      fontWeight: 600,
                      color: '#1e293b',
                      marginBottom: 4,
                    }}
                  >
                    {confirm.title}
                  </h3>
                )}
                <p
                  style={{
                    fontSize: 14,
                    color: '#475569',
                    whiteSpace: 'pre-line',
                  }}
                >
                  {confirm.message}
                </p>
              </div>
            </div>
            <div
              style={{
                marginTop: 16,
                display: 'flex',
                justifyContent: 'flex-end',
                gap: 8,
              }}
            >
              <button
                onClick={() => _closeConfirm(false)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 10,
                  border: '1px solid #cbd5e1',
                  fontSize: 14,
                  background: '#fff',
                  cursor: 'pointer',
                }}
              >
                {confirm.cancelLabel || 'Annuler'}
              </button>
              <button
                onClick={() => _closeConfirm(true)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: 600,
                  color: '#fff',
                  border: 'none',
                  cursor: 'pointer',
                  background: confirm.variant === 'danger' ? '#dc2626' : brand,
                }}
              >
                {confirm.confirmLabel || 'Confirmer'}
              </button>
            </div>
          </div>
        </>
      )}
    </>,
    document.body,
  )
}
