import { useCallback, useEffect, useState } from 'react'
import {
  CheckCircle, ExternalLink, FileText, Loader2, Save, Wallet, XCircle,
} from 'lucide-react'

import type { FIProps } from './index'
import { showConfirm, showToast } from '../../ui/dialog'

const COLOR_PRIMARY = '#17494E'
const COLOR_BRUN = '#4E1D17'
const COLOR_BG_SOFT = '#EFE9E7'

interface TypeSortieOption {
  id: number
  label: string
}
interface RefOption {
  id: number
  label: string
}
interface StringRefOption {
  id: string
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

interface FicheEmbauche {
  id_salarie: string
  date_debut: string
  date_fin_per_essai: string
  date_anciennete: string
  en_activite: boolean
  dpae_date: string
  dpae_num: string
  id_type_poste: number
  id_type_ctt: number
  id_type_horaire: number
  id_ste: string
  multi_prod: boolean
  resp_equipe: boolean
  resp_adjoint: boolean
  chauffeur: boolean
  cin_envoyee: boolean
  cj_envoye: boolean
  formation_iag: boolean
  date_sortie_demandee: string
  date_sortie_reelle: string
  info_cpl: string
  courrier_date_envoi: string
  courrier_num_suivi: string
  courrier_date_recep: string
  courrier_delai_prev: string
  stc_date_envoi: string
  stc_num_suivi: string
  stc_date_recep: string
  stc_retourne_le: string
}

interface EmbaucheRefs {
  societes: StringRefOption[]
  postes: RefOption[]
  type_ctt: RefOption[]
  type_horaire: RefOption[]
  type_sortie: RefOption[]
}

function formatShortDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

function refLabel(opts: RefOption[], id: number): string {
  return opts.find((o) => o.id === id)?.label || ''
}

// FI_SortieRH (types 12 / 36 / 37) - Tickets de sortie RH.
// Affiche le bandeau action ticket + la fiche infos embauche du salarie
// (lecture seule sur les infos contractuelles) + edition complete de la
// partie sortie (info_cplt + courrier FPE + SDTC).
export default function FISortieRH({ apiBase, getToken, idTicket, onClose }: FIProps) {
  const [data, setData] = useState<SortieRHData | null>(null)
  const [embauche, setEmbauche] = useState<FicheEmbauche | null>(null)
  const [embaucheEdit, setEmbaucheEdit] = useState<FicheEmbauche | null>(null)
  const [refs, setRefs] = useState<EmbaucheRefs | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [typeSortie, setTypeSortie] = useState<number>(0)
  const [infoCplt, setInfoCplt] = useState<string>('')

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
        // Charge embauche + refs en parallele
        const [embR, refsR] = await Promise.all([
          fetch(`${fsaBase}/fiche-salarie/${dd.id_salarie}/embauche`, {
            headers: { Authorization: `Bearer ${getToken()}` },
          }).then((res) => (res.ok ? res.json() : null)),
          fetch(`${fsaBase}/fiche-salarie/embauche/refs`, {
            headers: { Authorization: `Bearer ${getToken()}` },
          }).then((res) => (res.ok ? res.json() : null)),
        ])
        setEmbauche(embR as FicheEmbauche | null)
        setEmbaucheEdit(embR as FicheEmbauche | null)
        setRefs(refsR as EmbaucheRefs | null)
      }
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [apiBase, idTicket, getToken, fsaBase])

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
    // 1. UPDATE ticket sortie RH (type_sortie + info_cplt)
    const r = await post({ action: 'enregistrer', type_sortie: typeSortie, info_cplt: infoCplt })
    if (!r) return

    // 2. UPDATE embauche (champs sortie repris du formulaire)
    if (embaucheEdit && data) {
      try {
        await fetch(`${fsaBase}/fiche-salarie/${data.id_salarie}/embauche`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({
            date_sortie_demandee: embaucheEdit.date_sortie_demandee,
            date_sortie_reelle: embaucheEdit.date_sortie_reelle,
            info_cpl: embaucheEdit.info_cpl,
            courrier_date_envoi: embaucheEdit.courrier_date_envoi,
            courrier_num_suivi: embaucheEdit.courrier_num_suivi,
            courrier_date_recep: embaucheEdit.courrier_date_recep,
            courrier_delai_prev: embaucheEdit.courrier_delai_prev,
            stc_date_envoi: embaucheEdit.stc_date_envoi,
            stc_num_suivi: embaucheEdit.stc_num_suivi,
            stc_date_recep: embaucheEdit.stc_date_recep,
            stc_retourne_le: embaucheEdit.stc_retourne_le,
          }),
        })
      } catch {
        /* tolerant */
      }
    }

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
    showToast('Solde de tout compte : module à brancher (Fen_SDTC)', 'info')
  }

  const setEmb = (patch: Partial<FicheEmbauche>) =>
    setEmbaucheEdit((prev) => (prev ? { ...prev, ...patch } : prev))

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

  const showCourrier = typeSortie > 1
  const showSdtcBlock = typeSortie > 1
  const fpeEditable = typeSortie >= 2 && typeSortie <= 4

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {/* Header : salarie + actions principales */}
      <div className="flex items-start justify-between gap-4">
        <div>
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

      {/* Bloc infos embauche (lecture seule) */}
      {embauche && refs && (
        <div className="border rounded-lg p-3" style={{ borderColor: COLOR_BG_SOFT }}>
          <h3
            className="text-xs uppercase tracking-wide font-normal mb-2 pb-1 border-b"
            style={{ color: COLOR_BRUN, borderColor: COLOR_BG_SOFT }}
          >
            Informations d'embauche
          </h3>
          <div className="grid grid-cols-3 gap-x-6 gap-y-2 text-sm">
            <Info label="Date d'embauche" value={formatShortDate(embauche.date_debut)} />
            <Info label="Fin Période Essai" value={formatShortDate(embauche.date_fin_per_essai)} />
            <Info label="Date Ancienneté" value={formatShortDate(embauche.date_anciennete)} />
            <Info
              label="Poste"
              value={refLabel(refs.postes, embauche.id_type_poste)}
            />
            <Info
              label="Type Ctt"
              value={refLabel(refs.type_ctt, embauche.id_type_ctt)}
            />
            <Info
              label="Horaire"
              value={refLabel(refs.type_horaire, embauche.id_type_horaire)}
            />
            <Info
              label="Société"
              value={refs.societes.find((s) => s.id === embauche.id_ste)?.label || ''}
            />
            <Info label="Date DPAE" value={formatShortDate(embauche.dpae_date)} />
            <Info label="N° DPAE" value={embauche.dpae_num} />
          </div>
        </div>
      )}

      {/* Bloc edition Sortie (Type Sortie + Doc + Info Cplt) */}
      <div className="border rounded-lg p-3" style={{ borderColor: COLOR_BG_SOFT }}>
        <h3
          className="text-xs uppercase tracking-wide font-normal mb-3 pb-1 border-b"
          style={{ color: COLOR_BRUN, borderColor: COLOR_BG_SOFT }}
        >
          Sortie
        </h3>
        <div className="grid grid-cols-[200px_1fr] gap-x-4 gap-y-3">
          <label className="text-sm self-center" style={{ color: COLOR_BRUN }}>
            Type Sortie
          </label>
          <select
            value={typeSortie}
            onChange={(e) => setTypeSortie(parseInt(e.target.value, 10) || 0)}
            className="px-3 py-1.5 rounded text-sm bg-white focus:outline-none focus:ring-1"
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
            rows={3}
            className="px-3 py-2 rounded text-sm bg-white focus:outline-none focus:ring-1 resize-y"
            style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
            placeholder="Informations complémentaires…"
          />
        </div>
      </div>

      {/* Bloc detail sortie - 3 colonnes (Info de sortie / Courrier FPE / SDTC) */}
      {embaucheEdit && (
        <div className="grid grid-cols-3 gap-4">
          <BlockBox title="Information de sortie">
            <StackedInput
              label="Date Sortie Demandée"
              type="date"
              value={embaucheEdit.date_sortie_demandee}
              onChange={(v) => setEmb({ date_sortie_demandee: v })}
            />
            <StackedInput
              label="Date Sortie Réelle"
              type="date"
              value={embaucheEdit.date_sortie_reelle}
              onChange={(v) => setEmb({ date_sortie_reelle: v })}
            />
            <StackedInput
              label="Info Cplt"
              value={embaucheEdit.info_cpl}
              onChange={(v) => setEmb({ info_cpl: v })}
            />
          </BlockBox>

          {showCourrier ? (
            <BlockBox title="Courrier FPE / DEM" disabled={!fpeEditable}>
              <StackedInput
                label="Envoyé le"
                type="date"
                value={embaucheEdit.courrier_date_envoi}
                onChange={(v) => setEmb({ courrier_date_envoi: v })}
              />
              <StackedInput
                label="Reçu le"
                type="date"
                value={embaucheEdit.courrier_date_recep}
                onChange={(v) => setEmb({ courrier_date_recep: v })}
              />
              <StackedInput
                label="Num Suivi"
                value={embaucheEdit.courrier_num_suivi}
                onChange={(v) => setEmb({ courrier_num_suivi: v })}
              />
              <StackedInput
                label="Délai Prév."
                value={embaucheEdit.courrier_delai_prev}
                onChange={(v) => setEmb({ courrier_delai_prev: v })}
              />
            </BlockBox>
          ) : (
            <div />
          )}

          {showSdtcBlock ? (
            <BlockBox title="Solde de tout compte">
              <StackedInput
                label="Envoyé le"
                type="date"
                value={embaucheEdit.stc_date_envoi}
                onChange={(v) => setEmb({ stc_date_envoi: v })}
              />
              <StackedInput
                label="Reçu le"
                type="date"
                value={embaucheEdit.stc_date_recep}
                onChange={(v) => setEmb({ stc_date_recep: v })}
              />
              <StackedInput
                label="Num Suivi"
                value={embaucheEdit.stc_num_suivi}
                onChange={(v) => setEmb({ stc_num_suivi: v })}
              />
              <StackedInput
                label="Retourné le"
                type="date"
                value={embaucheEdit.stc_retourne_le}
                onChange={(v) => setEmb({ stc_retourne_le: v })}
              />
            </BlockBox>
          ) : (
            <div />
          )}
        </div>
      )}

      {/* Lien fiche complete pour les overlays avances */}
      <div className="text-center pt-2">
        <a
          href={`/adm/salaries/registre`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-xs hover:underline"
          style={{ color: COLOR_PRIMARY }}
          title="Ouvrir le registre RH puis sélectionner le salarié pour accéder aux overlays Partenaires / Origine DPAE / Formation IAG / S'Cool"
        >
          <ExternalLink className="w-3 h-3" />
          Voir la fiche salarié complète
        </a>
      </div>
    </div>
  )
}

// --- Helpers UI ---------------------------------------------------------

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
        {label}
      </div>
      <div className="text-sm" style={{ color: COLOR_BRUN }}>
        {value || '—'}
      </div>
    </div>
  )
}

function BlockBox({
  title,
  children,
  disabled,
}: {
  title: string
  children: React.ReactNode
  disabled?: boolean
}) {
  return (
    <div
      className="border rounded p-3"
      style={{
        borderColor: COLOR_BG_SOFT,
        opacity: disabled ? 0.5 : 1,
        pointerEvents: disabled ? 'none' : 'auto',
      }}
    >
      <h4
        className="text-xs uppercase tracking-wide font-normal mb-2 pb-1 border-b"
        style={{ color: COLOR_BRUN, borderColor: COLOR_BG_SOFT }}
      >
        {title}
      </h4>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

function StackedInput({
  label,
  value,
  onChange,
  type = 'text',
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
}) {
  return (
    <div className="flex items-center gap-2">
      <label
        className="text-xs font-normal shrink-0 w-24 leading-tight"
        style={{ color: COLOR_BRUN }}
      >
        {label}
      </label>
      <input
        type={type}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1 min-w-0 px-2 py-1 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1"
        style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
      />
    </div>
  )
}
