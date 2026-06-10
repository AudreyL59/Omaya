/**
 * Onglet 'Documents' de la fiche salarie ADM.
 *
 * Transposition de la fenetre WinDev FI_SalarieDocuments :
 *   - 5 sous-onglets de navigation (Docs internes / Espace salarie /
 *     ADF / Bilans / Facture) qui changent le sous-repertoire FTP
 *     liste.
 *   - Tableau Choix | Nom Fichier | Taille | Date | Heure
 *   - Toolbar (a brancher dans les prochains commits) :
 *     + (upload), telechargement, suppression, Envoyer par mail,
 *     Tk Mutuelle, Voir le doc.
 *
 * Pour ce commit on a : navigation + tableau + 'Voir le doc' (ouvre
 * l'URL HTTP dans un nouvel onglet).
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Briefcase,
  ChartLine,
  Eye,
  FileText,
  GraduationCap,
  Loader2,
  Mail,
  Plus,
  Receipt,
  Ticket,
  Trash2,
  Upload,
  User as UserIcon,
} from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'

type SousRep = 'internes' | 'espace_salarie' | 'adf' | 'bilan_evo' | 'factures'

const NAV: { key: SousRep; label: string; icon: typeof FileText }[] = [
  { key: 'internes', label: 'Docs internes', icon: FileText },
  { key: 'espace_salarie', label: 'Espace salarié', icon: UserIcon },
  { key: 'adf', label: 'ADF', icon: GraduationCap },
  { key: 'bilan_evo', label: 'Bilans d\'évolution', icon: ChartLine },
  { key: 'factures', label: 'Facture', icon: Receipt },
]

interface DocFile {
  nom: string
  taille_mo: number
  date_iso: string
  url: string
}

interface DocListResp {
  ok: boolean
  srv: string
  etat: string
  sous_rep: string
  files: DocFile[]
}

interface Props {
  idSalarie: string
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

function fmtHeure(iso: string): string {
  if (!iso || iso.length < 16) return ''
  return iso.slice(11, 16)
}

export default function DocumentsTab({ idSalarie }: Props) {
  const [current, setCurrent] = useState<SousRep>('internes')
  const [data, setData] = useState<DocListResp | null>(null)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const reload = useCallback(
    async (sr: SousRep) => {
      if (!idSalarie) return
      setLoading(true)
      try {
        const r = await fetch(
          `/api/adm/fiche-salarie/${idSalarie}/documents?sous_rep=${sr}`,
          { headers: { Authorization: `Bearer ${getToken()}` } },
        )
        if (!r.ok) throw new Error(String(r.status))
        const j = (await r.json()) as DocListResp
        setData(j)
        setSelected(new Set())
      } catch (e) {
        showToast(`Échec chargement : ${(e as Error).message}`, 'error')
      } finally {
        setLoading(false)
      }
    },
    [idSalarie],
  )

  useEffect(() => {
    void reload(current)
  }, [reload, current])

  const files = data?.files || []
  const oneSelected = selected.size === 1
  const someSelected = selected.size > 0

  const toggle = (nom: string) => {
    const next = new Set(selected)
    if (next.has(nom)) next.delete(nom)
    else next.add(nom)
    setSelected(next)
  }

  const toggleAll = () => {
    if (selected.size === files.length) setSelected(new Set())
    else setSelected(new Set(files.map((f) => f.nom)))
  }

  const handleVoirDoc = () => {
    if (!oneSelected) {
      showToast('Sélectionner un seul document.', 'info')
      return
    }
    const nom = Array.from(selected)[0]
    const f = files.find((x) => x.nom === nom)
    if (!f) return
    window.open(f.url, '_blank', 'noopener,noreferrer')
  }

  const placeholder = (label: string) => () =>
    showToast(`${label} : à brancher dans un prochain commit`, 'info')

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Sous-onglets de navigation */}
      <div
        className="flex items-center gap-1 border-b"
        style={{ borderColor: COLOR_BG_SOFT }}
      >
        {NAV.map((n) => {
          const active = n.key === current
          const Icon = n.icon
          return (
            <button
              key={n.key}
              type="button"
              onClick={() => setCurrent(n.key)}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-t transition"
              style={{
                color: active ? COLOR_PRIMARY : COLOR_BRUN,
                backgroundColor: active ? '#ECF1F2' : 'transparent',
                borderBottom: active
                  ? `2px solid ${COLOR_PRIMARY}`
                  : '2px solid transparent',
                fontWeight: active ? 600 : 400,
              }}
            >
              <Icon className="w-4 h-4" />
              {n.label}
            </button>
          )
        })}
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <ToolBtn icon={Plus} label="Ajouter" onClick={placeholder('Ajouter')} primary />
        <ToolBtn
          icon={Upload}
          label="Téléchargement"
          onClick={placeholder('Téléchargement')}
          disabled={!someSelected}
        />
        <ToolBtn
          icon={Trash2}
          label="Suppression"
          onClick={placeholder('Suppression')}
          disabled={!someSelected}
          danger
        />
        <div className="flex-1" />
        <ToolBtn
          icon={Mail}
          label="Envoyer par mail"
          onClick={placeholder('Envoyer par mail')}
          disabled={!someSelected}
        />
        <ToolBtn
          icon={Ticket}
          label="Tk Mutuelle"
          onClick={placeholder('Tk Mutuelle')}
          disabled={!someSelected}
        />
        <ToolBtn
          icon={Eye}
          label="Voir le doc"
          onClick={handleVoirDoc}
          disabled={!oneSelected}
        />
      </div>

      {/* Tableau */}
      <div
        className="flex-1 border rounded overflow-hidden flex flex-col"
        style={{ borderColor: COLOR_BG_SOFT }}
      >
        <div
          className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
          style={{
            gridTemplateColumns: '36px 1fr 90px 100px 70px',
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div className="flex justify-center">
            <input
              type="checkbox"
              checked={files.length > 0 && selected.size === files.length}
              onChange={toggleAll}
            />
          </div>
          <div>Nom Fichier</div>
          <div className="text-right">Taille (Mo)</div>
          <div>Date</div>
          <div>Heure</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="p-3 flex items-center gap-2 text-xs" style={{ color: COLOR_BRUN }}>
              <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
            </div>
          )}
          {!loading && files.length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucun fichier dans ce dossier.
            </div>
          )}
          {!loading &&
            files.map((f) => {
              const checked = selected.has(f.nom)
              return (
                <div
                  key={f.nom}
                  onClick={() => toggle(f.nom)}
                  onDoubleClick={() => window.open(f.url, '_blank', 'noopener,noreferrer')}
                  className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
                  style={{
                    gridTemplateColumns: '36px 1fr 90px 100px 70px',
                    backgroundColor: checked ? COLOR_BG_SOFT : 'white',
                    borderColor: COLOR_BG_SOFT,
                    color: COLOR_BRUN,
                  }}
                >
                  <div className="flex justify-center">
                    <input type="checkbox" checked={checked} onChange={() => toggle(f.nom)} />
                  </div>
                  <div className="truncate" title={f.nom}>
                    {f.nom}
                  </div>
                  <div className="text-right">{f.taille_mo}</div>
                  <div>{fmtDate(f.date_iso)}</div>
                  <div>{fmtHeure(f.date_iso)}</div>
                </div>
              )
            })}
        </div>
      </div>

      {/* Footer info */}
      <div
        className="flex items-center gap-6 text-xs px-1"
        style={{ color: COLOR_BRUN, opacity: 0.7 }}
      >
        <span>nb Fichiers : <strong>{files.length}</strong></span>
        <span>Srv : {data?.srv || ''}</span>
        <span>État : {data?.etat || ''}</span>
      </div>
    </div>
  )
}

function ToolBtn({
  icon: Icon,
  label,
  onClick,
  disabled,
  primary,
  danger,
}: {
  icon: typeof Briefcase
  label: string
  onClick: () => void
  disabled?: boolean
  primary?: boolean
  danger?: boolean
}) {
  const color = primary ? 'white' : danger ? '#B91C1C' : COLOR_PRIMARY
  const bg = primary ? COLOR_PRIMARY : 'white'
  const border = primary ? COLOR_PRIMARY : danger ? '#B91C1C' : COLOR_PRIMARY
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border disabled:opacity-40"
      style={{ backgroundColor: bg, color, borderColor: border }}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  )
}
