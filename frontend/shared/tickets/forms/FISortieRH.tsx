import { useCallback, useEffect, useState } from 'react'
import {
  CheckCircle, ExternalLink, FileText, Loader2, Save, Wallet, XCircle,
} from 'lucide-react'

import type { FIProps } from './index'
import { showConfirm, showToast } from '../../ui/dialog'
import EmbaucheTab, {
  COLOR_PRIMARY,
  COLOR_BRUN,
  COLOR_BG_SOFT,
} from '../../fiche/EmbaucheTab'
import SDTCModal from '../../sdtc/SDTCModal'

interface TypeSortieOption {
  id: number
  label: string
}

interface SortieRHData {
  found: boolean
  id_ticket: string
  id_salarie: string
  id_type_demande: number
  show_sdtc: boolean
  lib_nom: string
  nom: string
  prenom: string
  type_sortie: number
  lib_sortie: string
  type_sortie_options: TypeSortieOption[]
  info_cplt: string
  doc_sortie: boolean
  doc_url: string
  date_dernier_ctt: string
}

function formatShortDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

// FI_SortieRH (types 12 / 36 / 37) - Tickets de sortie RH.
//
// Layout :
//   - Header ticket : nom + actions globales (Enregistrer ticket / Cloturer /
//     Voir doc / SDTC). Le bouton "Courrier Type FPE" est porte par
//     EmbaucheTab (bloc Courrier FPE / DEM) car c'est lui qui dispose de
//     `delai_prev` en cours d'edition.
//   - Bloc Sortie specifique au ticket : Type Sortie + Doc + InfoCplt
//     (champs portes par la table TK_DemandeSortieRH).
//   - <EmbaucheTab/> partage : fiche embauche complete + overlays Partenaires /
//     Origine DPAE / Formation IAG / S'Cool + blocs sortie (Information /
//     Courrier FPE / SDTC). L'enregistrement de ces champs se fait via le
//     bouton "Enregistrer" interne au composant shared.
export default function FISortieRH({ apiBase, getToken, idTicket, onClose, onOpenFicheSalarie }: FIProps) {
  const [data, setData] = useState<SortieRHData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [typeSortie, setTypeSortie] = useState<number>(0)
  const [infoCplt, setInfoCplt] = useState<string>('')
  const [sdtcOpen, setSdtcOpen] = useState(false)

  // apiBase pour les endpoints fiche-salarie : par defaut /api/adm
  // car les tickets sortie RH sont traites cote ADM. Si la fonction est
  // utilisee depuis un autre intranet, fallback /api/adm.
  const fsaBase = apiBase.startsWith('/api/adm') ? apiBase : '/api/adm'

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(`${apiBase}/tickets/${idTicket}/form`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      const j = await r.json()
      const dd: SortieRHData | null = j?.data?.found ? j.data : null
      setData(dd)
      if (dd) {
        setTypeSortie(dd.type_sortie || 0)
        setInfoCplt(dd.info_cplt || '')
      }
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [apiBase, idTicket, getToken])

  useEffect(() => {
    reload()
  }, [reload])

  const post = async (body: Record<string, unknown>): Promise<Record<string, unknown> | null> => {
    setSaving(true)
    try {
      const resp = await fetch(`${apiBase}/tickets/${idTicket}/form`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(body),
      })
      const j = await resp.json().catch(() => null)
      if (!resp.ok) {
        showToast(`Erreur : ${(j as { detail?: string })?.detail || resp.status}`, 'error')
        return null
      }
      return (j ?? {}) as Record<string, unknown>
    } catch {
      showToast('Erreur réseau.', 'error')
      return null
    } finally {
      setSaving(false)
    }
  }

  const handleEnregistrer = async () => {
    const r = await post({ action: 'enregistrer', type_sortie: typeSortie, info_cplt: infoCplt })
    if (!r) return
    showToast('Ticket enregistré', 'success')
    const ok = await showConfirm({
      title: 'Clôturer le ticket',
      message: 'Voulez-vous clôturer le ticket ?',
      confirmLabel: 'Clôturer',
    })
    if (ok) await handleCloture(false)
  }

  const handleCloture = async (confirmFirst = true) => {
    if (confirmFirst) {
      const ok = await showConfirm({
        title: 'Clôturer le ticket',
        message: 'Vous êtes sur le point de clôturer le ticket. Voulez-vous continuer ?',
        confirmLabel: 'Clôturer',
        variant: 'danger',
      })
      if (!ok) return
    }
    const r = await post({ action: 'close' })
    if (!r) return
    showToast('Ticket clôturé', 'success')
    if (onClose) onClose()
  }

  const handleVoirDoc = async () => {
    if (!data?.doc_url) return
    window.open(data.doc_url, '_blank')
    await post({ action: 'mark_doc_seen' })
  }

  const handleSDTC = () => {
    if (!data?.id_salarie) return
    setSdtcOpen(true)
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-c-ink-icon animate-spin" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="h-full flex items-center justify-center text-c-ink-soft text-sm">
        Demande de sortie RH introuvable pour ce ticket.
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {/* Header : salarie (gauche) + bloc Sortie ticket (milieu) + actions (droite) */}
      <div className="flex items-start gap-4">
        <div className="shrink-0 w-[220px]">
          <h2 className="text-base font-semibold" style={{ color: COLOR_BRUN }}>
            {data.lib_nom}
          </h2>
          <p className="text-xs text-c-ink-soft mt-0.5">Fiche n° {data.id_salarie}</p>
          {data.date_dernier_ctt ? (
            <p className="text-xs text-emerald-700 mt-1">
              Dernier contrat signé le {formatShortDate(data.date_dernier_ctt)}
            </p>
          ) : (
            <p className="text-xs text-red-700 mt-1">Pas encore productif</p>
          )}
        </div>

        {/* Bloc Sortie (ticket) : Type Sortie + Doc + InfoCplt — au milieu */}
        <div className="flex-1 min-w-0 border rounded-lg p-3" style={{ borderColor: COLOR_BG_SOFT }}>
          <h3
            className="text-xs uppercase tracking-wide font-normal mb-2 pb-1 border-b"
            style={{ color: COLOR_BRUN, borderColor: COLOR_BG_SOFT }}
          >
            Sortie (ticket)
          </h3>
          <div className="grid grid-cols-[140px_1fr] gap-x-3 gap-y-2">
            <label className="text-sm self-center" style={{ color: COLOR_BRUN }}>
              Type Sortie
            </label>
            <select
              value={typeSortie}
              onChange={(e) => setTypeSortie(parseInt(e.target.value, 10) || 0)}
              className="min-w-0 w-full px-3 py-1.5 rounded text-sm bg-white focus:outline-none focus:ring-1"
              style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
            >
              <option value={0}>—</option>
              {data.type_sortie_options.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>

            <label className="text-sm self-center" style={{ color: COLOR_BRUN }}>
              Doc de Sortie
            </label>
            <div className="flex items-center gap-2 text-sm">
              {data.doc_sortie ? (
                <>
                  <CheckCircle className="w-4 h-4 text-emerald-600" />
                  <span style={{ color: COLOR_BRUN }}>Reçu</span>
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4 text-gray-400" />
                  <span className="text-gray-400 italic">En attente</span>
                </>
              )}
            </div>

            <label className="text-sm pt-2" style={{ color: COLOR_BRUN }}>
              InfoCplt (ticket)
            </label>
            <textarea
              value={infoCplt}
              onChange={(e) => setInfoCplt(e.target.value)}
              rows={2}
              className="min-w-0 w-full px-3 py-2 rounded text-sm bg-white focus:outline-none focus:ring-1 resize-y"
              style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
              placeholder="Informations complémentaires…"
            />
          </div>
        </div>

        <div className="flex flex-col gap-2 shrink-0">
          <button
            onClick={handleEnregistrer}
            disabled={saving}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
            style={{ backgroundColor: COLOR_PRIMARY }}
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Enregistrer le ticket
          </button>
          <button
            onClick={() => handleCloture(true)}
            disabled={saving}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-medium text-red-700 border border-red-200 hover:bg-red-50 disabled:opacity-50"
          >
            <XCircle className="w-4 h-4" />
            Clôturer le ticket
          </button>
          {data.doc_sortie && data.doc_url && (
            <button
              onClick={handleVoirDoc}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-normal hover:bg-[#ECF1F2] border"
              style={{ color: COLOR_PRIMARY, borderColor: COLOR_BG_SOFT }}
            >
              <FileText className="w-4 h-4" />
              Voir le document de sortie
            </button>
          )}
          {data.show_sdtc && (
            <button
              onClick={handleSDTC}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-normal hover:bg-[#ECF1F2] border"
              style={{ color: COLOR_PRIMARY, borderColor: COLOR_BG_SOFT }}
            >
              <Wallet className="w-4 h-4" />
              Solde de tout compte
            </button>
          )}
        </div>
      </div>

      {/* Fiche embauche complete partagee : infos embauche + 4 overlays
          (Partenaires / Origine DPAE / Formation IAG / S'Cool) + blocs sortie
          (Information / Courrier FPE / SDTC). Le bouton "Enregistrer" du
          composant gere son propre UPDATE embauche. */}
      <div className="border rounded-lg" style={{ borderColor: COLOR_BG_SOFT }}>
        <EmbaucheTab
          idSalarie={data.id_salarie}
          apiBase={fsaBase}
          getToken={getToken}
        />
      </div>

      {/* Lien fiche complete : bouton si l'hote (ADM) branche la callback,
          sinon lien fallback (Vendeur etc.) vers le registre RH. */}
      <div className="text-center pt-2">
        {onOpenFicheSalarie ? (
          <button
            type="button"
            onClick={() => onOpenFicheSalarie(data.id_salarie, data.nom, data.prenom)}
            className="inline-flex items-center gap-1 text-xs hover:underline"
            style={{ color: COLOR_PRIMARY }}
            title="Ouvrir la fiche salarié complète en popup"
          >
            <ExternalLink className="w-3 h-3" />
            Voir la fiche salarié complète
          </button>
        ) : (
          <a
            href={`/adm/salaries/registre`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs hover:underline"
            style={{ color: COLOR_PRIMARY }}
            title="Ouvrir la fiche salarié complète dans un nouvel onglet"
          >
            <ExternalLink className="w-3 h-3" />
            Voir la fiche salarié complète
          </a>
        )}
      </div>

      <SDTCModal
        open={sdtcOpen}
        onClose={() => setSdtcOpen(false)}
        getToken={getToken}
        idSalarie={data.id_salarie}
      />
    </div>
  )
}
