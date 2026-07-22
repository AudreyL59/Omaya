// Modals annexes du chat Dialogues :
// - PjListModal    : liste des PJ du dialogue ouvert
// - TachesITModal  : taches IT liees au dialogue ouvert (onglet WinDev
//                    "Suivi IT")

import { useEffect, useState } from 'react'
import { CheckCircle2, X } from 'lucide-react'

import { fetchTachesIT } from './api'
import { PjInline } from './PjInline'
import type { DialoguePJ, TacheIT } from './types'

type Ctx = { apiBase: string; getToken: () => string | null }

// WinDev COLORREF (R + G*256 + B*65536) -> CSS hex
const wdColor = (n: number): string => {
  if (!n) return '#9ca3af'
  const r = n & 0xff
  const g = (n >> 8) & 0xff
  const b = (n >> 16) & 0xff
  const h = (v: number) => v.toString(16).padStart(2, '0')
  return `#${h(r)}${h(g)}${h(b)}`
}

// Choix noir ou blanc pour le texte selon la luminance de la couleur
// de fond — formule Rec. 709 simplifiee. Seuil 0.6 pour privilegier le
// blanc sur les mi-tons (mieux lu que du noir sur bleu moyen).
const readableFg = (n: number): string => {
  if (!n) return '#ffffff'
  const r = n & 0xff, g = (n >> 8) & 0xff, b = (n >> 16) & 0xff
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return lum > 0.6 ? '#111827' : '#ffffff'
}

const fmtFR = (raw: string): string => {
  if (!raw) return ''
  const clean = raw.replace(/[^0-9]/g, '')
  if (clean.length < 12) return raw
  const y = clean.slice(0, 4), mo = clean.slice(4, 6), d = clean.slice(6, 8)
  const h = clean.slice(8, 10), mi = clean.slice(10, 12)
  const dt = new Date(+y, +mo - 1, +d, +h, +mi)
  const jours = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam']
  const mois = ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Juin',
                'Juil', 'Aou', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${jours[dt.getDay()]} ${dt.getDate().toString().padStart(2, '0')} ` +
         `${mois[dt.getMonth()]} ${dt.getFullYear()} a ${h}:${mi}`
}

function ModalShell({ title, onClose, children, wide }: {
  title: string; onClose: () => void
  children: React.ReactNode; wide?: boolean
}) {
  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onEsc)
    return () => window.removeEventListener('keydown', onEsc)
  }, [onClose])
  return (
    <div className="fixed inset-0 z-[90] bg-black/50 flex items-center justify-center p-4"
      onClick={onClose}>
      <div onClick={e => e.stopPropagation()}
        className={`bg-white rounded-lg shadow-xl w-full ${
          wide ? 'max-w-3xl' : 'max-w-lg'} max-h-[80vh] flex flex-col`}>
        <header className="flex items-center justify-between px-4 py-3 border-b border-c-line-soft">
          <h3 className="text-base font-semibold">{title}</h3>
          <button onClick={onClose}
            className="p-1 rounded hover:bg-gray-100">
            <X className="w-4 h-4" />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
//  Liste des PJ du dialogue
// ---------------------------------------------------------------------------

export function PjListModal({ pjs, ctx, idDialogue, onClose }: {
  pjs: DialoguePJ[]; ctx: Ctx; idDialogue: string; onClose: () => void
}) {
  return (
    <ModalShell title={`Pièces jointes (${pjs.length})`} onClose={onClose} wide>
      {pjs.length === 0 && (
        <div className="text-sm italic text-c-ink-faint text-center py-6">
          Aucune pièce jointe dans ce dialogue.
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {pjs.map(pj => (
          <div key={pj.IDPJ}
            className="border border-c-line-soft rounded p-2 flex flex-col gap-1 bg-c-surface-soft">
            <PjInline pj={pj} ctx={ctx} idDialogue={idDialogue} />
            <div className="text-[10px] text-c-ink-soft mt-1">
              {pj.NomExp} · {fmtFR(pj.DateHeureCreation)}
            </div>
          </div>
        ))}
      </div>
    </ModalShell>
  )
}

// ---------------------------------------------------------------------------
//  Taches IT liees au dialogue (onglet WinDev "Suivi IT")
// ---------------------------------------------------------------------------

export function TachesITModal({ ctx, idDialogue, onClose }: {
  ctx: Ctx; idDialogue: string; onClose: () => void
}) {
  const [taches, setTaches] = useState<TacheIT[] | null>(null)
  useEffect(() => {
    void fetchTachesIT(ctx, idDialogue).then(r => setTaches(r || []))
  }, [ctx, idDialogue])

  return (
    <ModalShell title="Suivi IT" onClose={onClose} wide>
      {taches === null && (
        <div className="text-sm italic text-c-ink-soft text-center py-6">
          Chargement…
        </div>
      )}
      {taches !== null && taches.length === 0 && (
        <div className="text-sm italic text-c-ink-faint text-center py-6">
          Aucune tâche IT associée à ce dialogue.
        </div>
      )}
      <div className="space-y-3">
        {taches?.map(t => (
          <div key={t.IDTacheIT}
            className="border border-c-line-soft rounded p-3 bg-white"
            style={{ borderLeft: `4px solid ${wdColor(t.CouleurStatut)}` }}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="font-semibold text-sm truncate">
                  {t.Titre || '(sans titre)'}
                </div>
                {t.NomOpTraitement && (
                  <div className="text-xs text-c-ink-soft mt-0.5">
                    Traitée par {t.NomOpTraitement}
                  </div>
                )}
                <div className="text-[11px] italic text-c-ink-faint mt-1">
                  Créée par {t.NomOpCrea || `#${t.OpCrea}`} le {fmtFR(t.DateCrea)}
                </div>
                {t.LibTache && (
                  <div className="text-[10px] text-c-ink-soft mt-1">
                    Type : {t.LibTache}{t.Version && ` · v${t.Version}`}
                  </div>
                )}
                {t.Contenu && (
                  <details className="mt-1">
                    <summary className="text-xs text-c-brand cursor-pointer">
                      Voir le contenu
                    </summary>
                    <p className="text-xs mt-1 whitespace-pre-wrap text-c-ink-soft">
                      {t.Contenu}
                    </p>
                  </details>
                )}
              </div>
              <div className="text-right shrink-0 flex flex-col items-end gap-1">
                <span className="text-[11px] font-semibold px-2 py-1 rounded whitespace-nowrap"
                  style={{ backgroundColor: wdColor(t.CouleurStatut),
                           color: readableFg(t.CouleurStatut) }}>
                  {t.LibStatut || 'Statut ?'}
                </span>
                {t.Terminee && (
                  <CheckCircle2 className="w-4 h-4 text-green-600"
                    aria-label="Terminée" />
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </ModalShell>
  )
}
