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

import { useCallback, useEffect, useRef, useState } from 'react'
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
import SendEmailModal from '@shared/email/SendEmailModal'
import { showConfirm, showToast } from '@shared/ui/dialog'
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

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export default function DocumentsTab({ idSalarie }: Props) {
  const [current, setCurrent] = useState<SousRep>('internes')
  const [data, setData] = useState<DocListResp | null>(null)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [uploading, setUploading] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [mailOpen, setMailOpen] = useState(false)
  const [mailHtml, setMailHtml] = useState('')
  const [tkMutBusy, setTkMutBusy] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

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

  const handleAjouter = () => fileInputRef.current?.click()

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (!fileList || fileList.length === 0) return
    setUploading(true)
    let okCount = 0
    let lastErr = ''
    try {
      for (const file of Array.from(fileList)) {
        const fd = new FormData()
        fd.append('file', file)
        const r = await fetch(
          `/api/adm/fiche-salarie/${idSalarie}/documents/upload?sous_rep=${current}`,
          {
            method: 'POST',
            headers: { Authorization: `Bearer ${getToken()}` },
            body: fd,
          },
        )
        if (r.ok) {
          okCount++
        } else {
          const j = await r.json().catch(() => ({}))
          lastErr = (j as { detail?: string }).detail || String(r.status)
        }
      }
      if (okCount > 0) {
        showToast(`${okCount} fichier(s) envoyé(s).`, 'success')
        await reload(current)
      }
      if (lastErr) {
        showToast(`Échec : ${lastErr}`, 'error')
      }
    } finally {
      setUploading(false)
      e.target.value = '' // reset pour permettre re-upload du meme fichier
    }
  }

  const handleTelechargement = () => {
    if (!someSelected) {
      showToast('Sélectionner au moins un fichier.', 'info')
      return
    }
    // Ouvre chaque fichier dans un nouvel onglet (cohérent avec 'Voir le doc')
    let count = 0
    for (const nom of selected) {
      const f = files.find((x) => x.nom === nom)
      if (!f) continue
      window.open(f.url, '_blank', 'noopener,noreferrer')
      count++
    }
    if (count > 0) showToast(`${count} fichier(s) ouvert(s).`, 'success')
  }

  const handleSuppression = async () => {
    if (!someSelected) {
      showToast('Sélectionner au moins un fichier.', 'info')
      return
    }
    const list = Array.from(selected)
    const message =
      list.length === 1
        ? `Voulez-vous supprimer le fichier "${list[0]}" ?`
        : `Voulez-vous supprimer les ${list.length} fichiers sélectionnés ?`
    const ok = await showConfirm({
      title: 'Suppression',
      message,
      confirmLabel: 'Supprimer',
      variant: 'danger',
    })
    if (!ok) return
    setDeleting(true)
    let okCount = 0
    let lastErr = ''
    try {
      for (const nom of list) {
        const r = await fetch(
          `/api/adm/fiche-salarie/${idSalarie}/documents?sous_rep=${current}&filename=${encodeURIComponent(nom)}`,
          {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${getToken()}` },
          },
        )
        if (r.ok) {
          okCount++
        } else {
          const j = await r.json().catch(() => ({}))
          lastErr = (j as { detail?: string }).detail || String(r.status)
        }
      }
      if (okCount > 0) {
        showToast(`${okCount} fichier(s) supprimé(s).`, 'success')
        await reload(current)
      }
      if (lastErr) {
        showToast(`Échec : ${lastErr}`, 'error')
      }
    } finally {
      setDeleting(false)
    }
  }

  const handleEnvoyerMail = () => {
    if (!someSelected) {
      showToast('Sélectionner au moins un fichier.', 'info')
      return
    }
    // Construit le HTML facon WinDev : liste des liens 'Telecharger ici'
    const liens = Array.from(selected)
      .map((nom) => {
        const f = files.find((x) => x.nom === nom)
        if (!f) return ''
        return `<li>${escapeHtml(nom)} (<a href="${f.url}">Télécharger ici</a>)</li>`
      })
      .filter(Boolean)
      .join('')
    const html =
      `<p>Bonjour,</p>` +
      `<p>Voici les fichiers provenant du dossier salarié :</p>` +
      `<ul>${liens}</ul>` +
      `<p>Cdt</p>`
    setMailHtml(html)
    setMailOpen(true)
  }

  const handleTkMutuelle = async () => {
    if (!someSelected) {
      showToast('Sélectionner au moins un fichier.', 'info')
      return
    }
    const ok = await showConfirm({
      title: 'Ticket Mutuelle',
      message: `Créer un ticket Mutuelle (service JU) avec les ${selected.size} fichier(s) sélectionné(s) ?`,
      confirmLabel: 'Créer le ticket',
    })
    if (!ok) return
    setTkMutBusy(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/documents/tk-mutuelle`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({
            sous_rep: current,
            filenames: Array.from(selected),
          }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const j = (await r.json()) as { id_tk_liste: string }
      showToast(`Ticket Mutuelle créé (id ${j.id_tk_liste}).`, 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setTkMutBusy(false)
    }
  }

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

      {/* Input file invisible pour Btn 'Ajouter' */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <ToolBtn
          icon={uploading ? Loader2 : Plus}
          spin={uploading}
          label="Ajouter"
          onClick={handleAjouter}
          disabled={uploading}
          primary
        />
        <ToolBtn
          icon={Upload}
          label="Téléchargement"
          onClick={handleTelechargement}
          disabled={!someSelected}
        />
        <ToolBtn
          icon={deleting ? Loader2 : Trash2}
          spin={deleting}
          label="Suppression"
          onClick={handleSuppression}
          disabled={!someSelected || deleting}
          danger
        />
        <div className="flex-1" />
        <ToolBtn
          icon={Mail}
          label="Envoyer par mail"
          onClick={handleEnvoyerMail}
          disabled={!someSelected}
        />
        <ToolBtn
          icon={tkMutBusy ? Loader2 : Ticket}
          spin={tkMutBusy}
          label="Tk Mutuelle"
          onClick={handleTkMutuelle}
          disabled={!someSelected || tkMutBusy}
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

      <SendEmailModal
        open={mailOpen}
        onClose={() => setMailOpen(false)}
        getToken={getToken}
        subject="Documents salarié"
        html={mailHtml}
      />
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
  spin,
}: {
  icon: typeof Briefcase
  label: string
  onClick: () => void
  disabled?: boolean
  primary?: boolean
  danger?: boolean
  spin?: boolean
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
      <Icon className={`w-4 h-4 ${spin ? 'animate-spin' : ''}`} />
      {label}
    </button>
  )
}
