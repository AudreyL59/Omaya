/**
 * EmbaucheTab : composant React partage (frontend/shared/fiche/).
 *
 * Onglet "Infos Embauche" de la fiche salarie ADM, extrait depuis
 * frontend/adm/src/components/FicheSalarieModal.tsx pour permettre la
 * reutilisation dans :
 *   - frontend/adm/src/components/FicheSalarieModal.tsx (fiche salarie)
 *   - frontend/shared/tickets/forms/FISortieRH.tsx (ticket sortie RH)
 *
 * Props :
 *   - idSalarie     : id du salarie
 *   - apiBase       : prefixe API (defaut '/api/adm')
 *   - getToken      : fonction qui retourne le Bearer token
 *   - onAfterSave?  : callback (en_activite) appele apres save reussi
 *                     (utilise pour synchroniser le header parent)
 *
 * Le composant gere son propre etat, ses 4 overlays (Partenaires, Origine
 * DPAE, Formation IAG, S'Cool) et toutes les actions de sortie. Tous les
 * fetchs partent de apiBase + '/fiche-salarie/...'.
 */

import { useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  Car as CarIcon,
  Check,
  Crown,
  FileText as FileTextIcon,
  GraduationCap,
  Laptop,
  Loader2,
  Pencil,
  Plus,
  Printer,
  Save,
  Scale,
  Send,
  ShoppingBasket,
  Trash2,
  Users,
  X,
  ContactRound,
} from 'lucide-react'
import { showConfirm, showToast } from '../ui/dialog'
import PersonnePicker, { type SalarieItem } from './PersonnePicker'
import SendEmailModal from '../email/SendEmailModal'

// --- Constantes charte ---------------------------------------------------

export const COLOR_PRIMARY = '#17494E'
export const COLOR_BRUN = '#4E1D17'
export const COLOR_BG_SOFT = '#EFE9E7'

// --- Types ---------------------------------------------------------------

export interface RefOption { id: number; label: string }
export interface StringRefOption { id: string; label: string }

export interface FicheEmbaucheRefs {
  societes: StringRefOption[]
  postes: RefOption[]
  type_ctt: RefOption[]
  type_horaire: RefOption[]
  type_sortie: RefOption[]
}

export interface SalariePortail {
  id_salarie_partenaire: string
  id_partenaire: string
  lib_partenaire: string
  code: string
  login: string
  mdp: string
}

export interface SalariePartDpae {
  id_salarie_partenaire: string
  id_partenaire: string
  lib_partenaire: string
  id_ste: string
  rs_societe: string
}

export interface FicheEmbauche {
  id_salarie: string
  date_debut: string
  date_fin_per_essai: string
  date_anciennete: string
  en_activite: boolean
  dpae_date: string
  dpae_num: string
  dpae_ope: string
  id_type_poste: number
  id_type_ctt: number
  id_type_horaire: number
  id_ste: string
  id_ste_dpae_energie: string
  id_ste_dpae_fibre: string
  coopte: boolean
  coopteur: string
  coopteur_lib: string
  j_odirecte: boolean
  jo_coopteur: string
  jo_coopteur_lib: string
  resp_equipe: boolean
  resp_adjoint: boolean
  chauffeur: boolean
  multi_prod: boolean
  cin_envoyee: boolean
  cj_envoye: boolean
  formation_iag: boolean
  formation_iag_date: string
  formation_iag_score: number
  id_cvtheque: string
  id_type_sortie: number
  date_sortie_demandee: string
  date_sortie_reelle: string
  demandeur_sortie: string
  demandeur_sortie_lib: string
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

interface Props {
  idSalarie: string
  apiBase?: string
  getToken: () => string | null
  onAfterSave?: (en_activite: boolean) => void
}

// --- AdmCheckbox : reutilise ailleurs aussi (export public) -------------

export function AdmCheckbox({
  checked,
  onChange,
  disabled,
  size = 18,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
  size?: number
}) {
  return (
    <span
      className="inline-flex shrink-0 cursor-pointer select-none"
      onClick={(e) => {
        if (disabled) return
        e.preventDefault()
        e.stopPropagation()
        onChange(!checked)
      }}
      style={{ width: size, height: size, cursor: disabled ? 'not-allowed' : 'pointer' }}
    >
      <span
        className="flex items-center justify-center transition"
        style={{
          width: size,
          height: size,
          borderRadius: 4,
          backgroundColor: checked ? COLOR_PRIMARY : 'white',
          border: `1.5px solid ${checked ? COLOR_PRIMARY : '#CBD5E1'}`,
          opacity: disabled ? 0.5 : 1,
        }}
      >
        {checked && (
          <svg
            viewBox="0 0 16 16"
            width={size - 4}
            height={size - 4}
            fill="none"
            stroke="white"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="3.5,8 7,11.5 12.5,5" />
          </svg>
        )}
      </span>
    </span>
  )
}

export default function EmbaucheTab({
  idSalarie,
  apiBase = '/api/adm',
  getToken,
  onAfterSave,
}: Props) {
  const _emitAfterSave = (v: boolean) => onAfterSave?.(v)
  const [data, setData] = useState<FicheEmbauche | null>(null)
  const [edit, setEdit] = useState<FicheEmbauche | null>(null)
  const [refs, setRefs] = useState<FicheEmbaucheRefs | null>(null)
  const [loadingTab, setLoadingTab] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string>('')
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)
  // IMPORTANT : tous les useState doivent etre AVANT les early returns
  // (loading / error) sinon "Rendered more hooks than during the previous render".
  const [overlay, setOverlay] = useState<
    null | 'partenaires' | 'origine_dpae' | 'formation_iag' | 'scool'
  >(null)
  const [sortieLoading, setSortieLoading] = useState<number | null>(null)
  const [emailOpen, setEmailOpen] = useState(false)
  const [loadingFPE, setLoadingFPE] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoadingTab(true)
    setError('')
    Promise.all([
      fetch(`${apiBase}/fiche-salarie/${idSalarie}/embauche`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) =>
        r.ok ? r.json() : r.json().then((j) => Promise.reject(j?.detail || r.status)),
      ),
      fetch(`${apiBase}/fiche-salarie/embauche/refs`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) =>
        r.ok ? r.json() : r.json().then((j) => Promise.reject(j?.detail || r.status)),
      ),
    ])
      .then(([emb, refsData]) => {
        if (cancelled) return
        setData(emb)
        setEdit(emb)
        setRefs(refsData)
      })
      .catch((e) => !cancelled && setError(String(e)))
      .finally(() => !cancelled && setLoadingTab(false))
    return () => {
      cancelled = true
    }
  }, [idSalarie])

  const dirty = useMemo(() => {
    if (!data || !edit) return false
    return JSON.stringify(data) !== JSON.stringify(edit)
  }, [data, edit])

  const handleSave = async () => {
    if (!edit) return
    setSaving(true)
    setToast(null)
    try {
      const r = await fetch(`${apiBase}/fiche-salarie/${idSalarie}/embauche`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(edit),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        setToast({ kind: 'err', msg: `Erreur : ${j?.detail || r.status}` })
        return
      }
      setData(edit)
      _emitAfterSave(edit.en_activite)
      setToast({ kind: 'ok', msg: 'Informations enregistrées' })
    } finally {
      setSaving(false)
      setTimeout(() => setToast(null), 3000)
    }
  }

  if (loadingTab) {
    return (
      <div className="flex items-center gap-2 text-gray-500 p-6">
        <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
      </div>
    )
  }
  if (error || !edit || !refs) {
    return (
      <div className="text-red-600 text-sm flex items-center gap-2 p-6">
        <AlertCircle className="w-4 h-4" /> {error || 'Pas de données'}
      </div>
    )
  }

  const set = (patch: Partial<FicheEmbauche>) =>
    setEdit((prev) => (prev ? { ...prev, ...patch } : prev))

  // Overlay actif sous la ligne de boutons (analogue WinDev Cell_*..Visible)
  const toggleOverlay = (k: typeof overlay) =>
    setOverlay((cur) => (cur === k ? null : k))

  // Action de sortie (MVP : UPDATE en_activite/type_sortie/dates)
  const handleSortie = async (type: number, label: string) => {
    if (!edit) return
    const ok = await showConfirm({
      title: 'Sortie du salarié',
      message: `Vous êtes sur le point de sortir le salarié en "${label}". Voulez-vous continuer ?`,
      confirmLabel: 'Continuer',
      variant: 'danger',
    })
    if (!ok) return
    setSortieLoading(type)
    try {
      // Body : reprend les champs du formulaire (cf. WinDev sortirSalarie qui
      // injecte les valeurs courantes dans le UPDATE salarie_sortie).
      const body = {
        type_sortie: type,
        info_cpl: edit.info_cpl,
        courrier_date_envoi: edit.courrier_date_envoi,
        courrier_num_suivi: edit.courrier_num_suivi,
        courrier_date_recep: edit.courrier_date_recep,
        courrier_delai_prev: edit.courrier_delai_prev,
        stc_date_envoi: edit.stc_date_envoi,
        stc_num_suivi: edit.stc_num_suivi,
        stc_date_recep: edit.stc_date_recep,
        stc_retourne_le: edit.stc_retourne_le,
      }
      const r = await fetch(`${apiBase}/fiche-salarie/${idSalarie}/sortie`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        setToast({ kind: 'err', msg: `Erreur : ${j?.detail || r.status}` })
        return
      }
      const result = await r.json().catch(() => ({}))

      // Recharge la fiche embauche pour avoir les nouvelles valeurs
      const reload = await fetch(`${apiBase}/fiche-salarie/${idSalarie}/embauche`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (reload.ok) {
        const d = (await reload.json()) as FicheEmbauche
        setData(d)
        setEdit(d)
        _emitAfterSave(d.en_activite)
      }

      if (result.mail_envoye) {
        showToast(`Sortie enregistrée + mail envoyé : ${label}`, 'success')
      } else {
        showToast(`Sortie enregistrée : ${label}`, 'success')
      }
      // Note WinDev : la proposition "Voulez-vous cloturer le ticket ?"
      // ne s'applique que si la fenetre embauche a ete ouverte depuis un
      // ticket existant (parametre `type` du MaFenetre). Ouverture depuis
      // la fiche salarie ADM = type=0, donc cette proposition est skipped.
    } finally {
      setSortieLoading(null)
    }
  }

  // Genere le courrier de rupture de periode d'essai au format PDF
  // (WeasyPrint cote backend). Le delai_prev courant est passe en query
  // string pour qu'il soit pris en compte meme si pas encore enregistre.
  const handleCourrierFPE = async () => {
    if (!edit || loadingFPE) return
    const delaiPrev = edit.courrier_delai_prev || ''
    const url =
      `${apiBase}/fiche-salarie/${idSalarie}/sortie/courrier-fpe.pdf` +
      `?delai_prev=${encodeURIComponent(delaiPrev)}`
    setLoadingFPE(true)
    try {
      const r = await fetch(url, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        showToast(`Échec : ${(j as { detail?: string })?.detail || r.status}`, 'error')
        return
      }
      const blob = await r.blob()
      const blobUrl = URL.createObjectURL(blob)
      window.open(blobUrl, '_blank')
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 30000)
    } catch {
      showToast('Erreur réseau (PDF Courrier FPE).', 'error')
    } finally {
      setLoadingFPE(false)
    }
  }

  return (
    <div className="p-6">
      {/* Top bar */}
      <div className="flex items-center gap-6 mb-5">
        <ActivToggle
          en_activite={edit.en_activite}
          onChange={(v) => {
            // Transposition WinDev AffInfoSortie() : au passage en Sorti(e),
            // si DateSortieDemandee est vide -> la mettre a aujourd'hui.
            const patch: Partial<FicheEmbauche> = { en_activite: v }
            if (!v && !edit.date_sortie_demandee) {
              patch.date_sortie_demandee = new Date().toISOString().slice(0, 10)
            }
            set(patch)
          }}
        />
        <label className="flex items-center gap-2 text-sm font-normal cursor-pointer">
          <AdmCheckbox
            checked={edit.multi_prod}
            onChange={(v) => set({ multi_prod: v })}
          />
          <span className="font-normal" style={{ color: COLOR_BRUN }}>
            Multi Produit
          </span>
        </label>
        <div className="flex-1" />
        <div
          className="w-9 h-9 rounded flex items-center justify-center"
          style={{ backgroundColor: '#FEE2E2', color: '#DC2626' }}
          title="Indicateur d'alerte"
        >
          <AlertTriangle className="w-4 h-4" />
        </div>
        <button
          onClick={handleSave}
          disabled={!dirty || saving}
          className="flex items-center gap-2 px-4 py-2 text-white rounded text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition"
          style={{ backgroundColor: COLOR_PRIMARY }}
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Enregistrer
        </button>
      </div>

      {toast && (
        <div
          className={`mb-3 px-3 py-2 rounded text-sm ${
            toast.kind === 'ok'
              ? 'bg-emerald-50 text-emerald-800'
              : 'bg-red-50 text-red-800'
          }`}
        >
          {toast.msg}
        </div>
      )}

      {/* 3 colonnes principales */}
      <div className="grid grid-cols-3 gap-8 max-w-6xl">
        <div className="space-y-2">
          <LabeledField
            label="Date d'embauche"
            type="date"
            value={edit.date_debut}
            onChange={(v) => set({ date_debut: v })}
          />
          <LabeledField
            label="Fin Période Essai"
            type="date"
            value={edit.date_fin_per_essai}
            onChange={(v) => set({ date_fin_per_essai: v })}
          />
          <LabeledField
            label="Date Ancienneté"
            type="date"
            value={edit.date_anciennete}
            onChange={(v) => set({ date_anciennete: v })}
          />
          <LabeledSelectNum
            label="Poste"
            value={edit.id_type_poste}
            options={refs.postes}
            onChange={(v) => set({ id_type_poste: v })}
          />
          <div className="grid grid-cols-[120px_1fr] gap-2 items-center">
            <span className="text-sm font-normal" style={{ color: COLOR_BRUN }}>
              Société
            </span>
            <div className="flex items-center gap-1 min-w-0">
              <select
                value={edit.id_ste}
                onChange={(e) => set({ id_ste: e.target.value })}
                className="flex-1 min-w-0 px-2 py-1 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1"
                style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
              >
                <option value="">—</option>
                {refs.societes.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.label}
                  </option>
                ))}
              </select>
              <button
                disabled
                className="shrink-0 p-1 rounded hover:bg-[#ECF1F2] disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ color: COLOR_PRIMARY }}
                title="Modifier la société (à implémenter)"
              >
                <Pencil className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <LabeledField
            label="Date DPAE"
            type="date"
            value={edit.dpae_date}
            onChange={(v) => set({ dpae_date: v })}
          />
          <LabeledField
            label="N° DPAE"
            value={edit.dpae_num}
            onChange={(v) => set({ dpae_num: v })}
          />
          <LabeledField
            label="DPAE Opé"
            value={edit.dpae_ope}
            onChange={(v) => set({ dpae_ope: v })}
          />
          <LabeledSelectNum
            label="Type Ctt"
            value={edit.id_type_ctt}
            options={refs.type_ctt}
            onChange={(v) => set({ id_type_ctt: v })}
          />
          <LabeledSelectNum
            label="Horaire"
            value={edit.id_type_horaire}
            options={refs.type_horaire}
            onChange={(v) => set({ id_type_horaire: v })}
          />
        </div>

        <div className="space-y-3 pt-1 pl-12">
          <EmbCheckDeco
            icon={<Crown className="w-4 h-4" />}
            iconBg="#DC2626"
            label="Responsable d'équipe"
            checked={edit.resp_equipe}
            onChange={(v) => set({ resp_equipe: v })}
          />
          <EmbCheckDeco
            icon={<Crown className="w-4 h-4" />}
            iconBg="#F97316"
            label="Responsable Adjoint"
            checked={edit.resp_adjoint}
            onChange={(v) => set({ resp_adjoint: v })}
          />
          <EmbCheckDeco
            icon={<CarIcon className="w-4 h-4" />}
            iconBg="#7C3AED"
            label="Chauffeur"
            checked={edit.chauffeur}
            onChange={(v) => set({ chauffeur: v })}
          />
          <EmbCheckDeco
            icon={<Scale className="w-4 h-4" />}
            iconBg="#17494E"
            label="Casier judiciaire envoyé"
            checked={edit.cj_envoye}
            onChange={(v) => set({ cj_envoye: v })}
          />
          <EmbCheckDeco
            label="CIN envoyée"
            checked={edit.cin_envoyee}
            onChange={(v) => set({ cin_envoyee: v })}
          />
        </div>
      </div>

      {/* Boutons overlays (analogue WinDev Cellule3) */}
      <div className="mt-6 flex flex-wrap items-center justify-center gap-8">
        <OverlayButton
          label="Partenaires"
          icon={<ShoppingBasket className="w-4 h-4" />}
          bgColor="#4E1D17"
          active={overlay === 'partenaires'}
          onClick={() => toggleOverlay('partenaires')}
        />
        <OverlayButton
          label="Origine DPAE"
          icon={<Users className="w-4 h-4" />}
          bgColor="#7C3AED"
          active={overlay === 'origine_dpae'}
          onClick={() => toggleOverlay('origine_dpae')}
        />
        <OverlayButton
          label="Formation IAG"
          icon={<GraduationCap className="w-4 h-4" />}
          bgColor="#0F766E"
          active={overlay === 'formation_iag'}
          onClick={() => toggleOverlay('formation_iag')}
        />
        <OverlayButton
          label="S'Cool"
          icon={<Laptop className="w-4 h-4" />}
          bgColor="#1E3A8A"
          active={overlay === 'scool'}
          onClick={() => toggleOverlay('scool')}
        />
      </div>

      {/* Panneau overlay actif */}
      {overlay === 'partenaires' && (
        <OverlayPartenaires
          idSalarie={idSalarie}
          apiBase={apiBase}
          getToken={getToken}
          onClose={() => setOverlay(null)}
        />
      )}
      {overlay === 'origine_dpae' && (
        <OverlayOrigineDPAE
          idSalarie={idSalarie}
          apiBase={apiBase}
          getToken={getToken}
          edit={edit}
          set={set}
          onClose={() => setOverlay(null)}
        />
      )}
      {overlay === 'formation_iag' && (
        <OverlayFormationIAG
          edit={edit}
          set={set}
          onClose={() => setOverlay(null)}
        />
      )}
      {overlay === 'scool' && (
        <OverlayScool
          idSalarie={idSalarie}
          apiBase={apiBase}
          getToken={getToken}
          onClose={() => setOverlay(null)}
        />
      )}

      {/* Boutons sortie (toujours visibles, cf. GrBTN_Sortie WinDev qui depend
          seulement de VerifDroit("Sa_FicheModif")). Placeholders en attendant
          la phase B (popup confirm + mails + tickets + droits OMAYA). */}
      <div className="mt-6 flex flex-wrap items-center justify-center gap-6">
        <SortieButton
          label="Annul DUE"
          bgColor="#D97706"
          onClick={() => handleSortie(1, 'Annulation DUE')}
          disabled={sortieLoading !== null}
        />
        <SortieButton
          label="FPE entreprise"
          bgColor="#C2410C"
          onClick={() => handleSortie(3, 'FPE entreprise')}
          disabled={sortieLoading !== null}
        />
        <SortieButton
          label="Dém / FPE Salarié"
          bgColor="#DC2626"
          onClick={() => {
            // Cf. WinDev : si Fin_Periode_Essai >= aujourd'hui -> FPE salarie (2),
            // sinon -> Demission (4).
            const today = new Date().toISOString().slice(0, 10)
            const type = edit.date_fin_per_essai && edit.date_fin_per_essai >= today ? 2 : 4
            handleSortie(type, type === 2 ? 'FPE salarié' : 'Démission')
          }}
          disabled={sortieLoading !== null}
        />
        <SortieButton
          label="Dém présumée"
          bgColor="#475569"
          onClick={() => handleSortie(10, 'Démission présumée')}
          disabled={sortieLoading !== null}
        />
        <SortieButton
          label="Licenciement"
          bgColor="#475569"
          onClick={() => handleSortie(5, 'Licenciement')}
          disabled={sortieLoading !== null}
        />
        <SortieButton
          label="Rupture conv"
          bgColor="#C026D3"
          onClick={() => handleSortie(6, 'Rupture conventionnelle')}
          disabled={sortieLoading !== null}
        />
      </div>

      {/* Blocs detail sortie : transposition WinDev AffInfoSortie() +
          GrSortie..Visible = pas EnActivite.
          - Sorti + type<=1 (rien ou Annul DUE) : seul bloc Information visible.
          - Sorti + type>1 : 3 blocs visibles. Courrier FPE actif si type
            2-4, sinon grise.
      */}
      {!edit.en_activite && (() => {
        const t = edit.id_type_sortie
        const showCourrierAndSdtc = t > 1
        const fpeEditable = t >= 2 && t <= 4
        // Si pas de type encore choisi : seul "Information de sortie" pour
        // permettre a l'utilisateur d'en saisir un.
        return (
          <div className="mt-6 grid grid-cols-3 gap-4">
            <SortieBlock title="Information de sortie">
              <StackedField
                label="Date Sortie Demandée"
                type="date"
                value={edit.date_sortie_demandee}
                onChange={(v) => set({ date_sortie_demandee: v })}
              />
              <StackedField
                label="Date Sortie Réelle"
                type="date"
                value={edit.date_sortie_reelle}
                onChange={(v) => set({ date_sortie_reelle: v })}
              />
              <div className="flex items-center gap-2">
                <label
                  className="text-xs font-normal shrink-0 w-24 leading-tight"
                  style={{ color: COLOR_BRUN }}
                >
                  Demandeur
                </label>
                <span
                  className="flex-1 min-w-0 px-2 py-1 text-sm font-normal truncate"
                  style={{ color: COLOR_BRUN }}
                  title={edit.demandeur_sortie_lib || ''}
                >
                  {edit.demandeur_sortie_lib || '—'}
                </span>
              </div>
              <StackedSelectNum
                label="Type Sortie"
                value={edit.id_type_sortie}
                options={refs.type_sortie}
                onChange={(v) => set({ id_type_sortie: v })}
              />
              <StackedField
                label="Info Cplt"
                value={edit.info_cpl}
                onChange={(v) => set({ info_cpl: v })}
              />
            </SortieBlock>

            {showCourrierAndSdtc ? (
              <SortieBlock title="Courrier FPE / DEM" disabled={!fpeEditable}>
                <StackedField
                  label="Envoyé le"
                  type="date"
                  value={edit.courrier_date_envoi}
                  onChange={(v) => set({ courrier_date_envoi: v })}
                />
                <StackedField
                  label="Reçu le"
                  type="date"
                  value={edit.courrier_date_recep}
                  onChange={(v) => set({ courrier_date_recep: v })}
                />
                <StackedField
                  label="Num Suivi"
                  value={edit.courrier_num_suivi}
                  onChange={(v) => set({ courrier_num_suivi: v })}
                />
                <StackedSelectStr
                  label="Délai Prév."
                  value={edit.courrier_delai_prev}
                  options={DELAI_PREV_OPTIONS}
                  onChange={(v) => set({ courrier_delai_prev: v })}
                />
                <button
                  type="button"
                  onClick={handleCourrierFPE}
                  disabled={loadingFPE}
                  className="w-full flex items-center justify-center gap-2 mt-2 px-3 py-1.5 text-xs font-normal rounded hover:bg-[#ECF1F2] border disabled:opacity-60 disabled:cursor-wait"
                  style={{ color: COLOR_PRIMARY, borderColor: COLOR_BG_SOFT }}
                  title={loadingFPE ? 'Génération du PDF en cours…' : "Générer le courrier de rupture de période d'essai (PDF)"}
                >
                  {loadingFPE ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Printer className="w-3.5 h-3.5" />
                  )}
                  {loadingFPE ? 'Génération…' : 'Courrier Type FPE'}
                </button>
              </SortieBlock>
            ) : (
              <div />
            )}

            {showCourrierAndSdtc ? (
              <SortieBlock title="Solde de tout compte">
                <StackedField
                  label="Envoyé le"
                  type="date"
                  value={edit.stc_date_envoi}
                  onChange={(v) => set({ stc_date_envoi: v })}
                />
                <StackedField
                  label="Reçu le"
                  type="date"
                  value={edit.stc_date_recep}
                  onChange={(v) => set({ stc_date_recep: v })}
                />
                <StackedField
                  label="Num Suivi"
                  value={edit.stc_num_suivi}
                  onChange={(v) => set({ stc_num_suivi: v })}
                />
                <StackedField
                  label="Retourné le"
                  type="date"
                  value={edit.stc_retourne_le}
                  onChange={(v) => set({ stc_retourne_le: v })}
                />
                <button
                  type="button"
                  onClick={() => setEmailOpen(true)}
                  className="w-full flex items-center justify-center gap-2 mt-2 px-3 py-1.5 text-xs font-normal rounded hover:bg-[#ECF1F2] border"
                  style={{ color: COLOR_PRIMARY, borderColor: COLOR_BG_SOFT }}
                  title="Envoyer le mail de solde de tout compte"
                >
                  <Send className="w-3.5 h-3.5" />
                  Mail SDTC
                </button>
              </SortieBlock>
            ) : (
              <div />
            )}
          </div>
        )
      })()}

      <SendEmailModal
        open={emailOpen}
        onClose={() => setEmailOpen(false)}
        getToken={getToken}
        subject={`Solde de tout compte - salarié ${idSalarie}`}
        html={`<p>Bonjour,</p><p>Veuillez trouver ci-joint le solde de tout compte du salarié.</p><p>Cordialement.</p>`}
      />
    </div>
  )
}

// --- Helpers UI Embauche -------------------------------------------------

function ActivToggle({
  en_activite,
  onChange,
}: {
  en_activite: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <div
      className="flex items-center rounded overflow-hidden"
      style={{ border: `1px solid ${COLOR_PRIMARY}` }}
    >
      <button
        onClick={() => onChange(false)}
        className="px-4 py-1 text-sm transition"
        style={{
          backgroundColor: !en_activite ? COLOR_PRIMARY : 'transparent',
          color: !en_activite ? 'white' : COLOR_PRIMARY,
          fontWeight: 600,
        }}
      >
        Sorti(e)
      </button>
      <button
        onClick={() => onChange(true)}
        className="px-4 py-1 text-sm transition"
        style={{
          backgroundColor: en_activite ? COLOR_PRIMARY : 'transparent',
          color: en_activite ? 'white' : COLOR_PRIMARY,
          fontWeight: 600,
        }}
      >
        En Activité
      </button>
    </div>
  )
}

function LabeledField({
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
    <div className="grid grid-cols-[120px_1fr] gap-2 items-center">
      <span className="text-sm font-normal" style={{ color: COLOR_BRUN }}>
        {label}
      </span>
      <input
        type={type}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className="min-w-0 w-full px-2 py-1 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1"
        style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
      />
    </div>
  )
}

function LabeledSelectNum({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: number
  options: RefOption[]
  onChange: (v: number) => void
}) {
  return (
    <div className="grid grid-cols-[120px_1fr] gap-2 items-center">
      <span className="text-sm font-normal" style={{ color: COLOR_BRUN }}>
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10) || 0)}
        className="min-w-0 w-full px-2 py-1 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1"
        style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
      >
        <option value={0}>—</option>
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  )
}

function EmbCheckDeco({
  icon,
  iconBg,
  label,
  checked,
  onChange,
}: {
  icon?: React.ReactNode
  iconBg?: string
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex items-center gap-2 text-sm font-normal cursor-pointer">
      {icon ? (
        <span
          className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-white"
          style={{ backgroundColor: iconBg }}
        >
          {icon}
        </span>
      ) : (
        <span className="w-7 h-7 shrink-0" />
      )}
      <AdmCheckbox checked={checked} onChange={onChange} />
      <span className="font-normal" style={{ color: COLOR_BRUN }}>
        {label}
      </span>
    </label>
  )
}

function OverlayButton({
  label,
  icon,
  bgColor,
  active,
  onClick,
  disabled,
}: {
  label: string
  icon: React.ReactNode
  bgColor: string
  active?: boolean
  onClick?: () => void
  disabled?: boolean
}) {
  const [hover, setHover] = useState(false)
  const highlight = (hover || active) && !disabled
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      disabled={disabled}
      className="flex items-center gap-2 px-3 py-1.5 text-sm font-normal rounded transition disabled:opacity-50 disabled:cursor-not-allowed"
      style={{
        color: active ? 'white' : COLOR_BRUN,
        backgroundColor: active
          ? COLOR_PRIMARY
          : highlight
            ? '#ECF1F2'
            : 'transparent',
      }}
      title={disabled ? 'À implémenter' : ''}
    >
      <span
        className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-white"
        style={{ backgroundColor: bgColor }}
      >
        {icon}
      </span>
      {label}
    </button>
  )
}

function SortieButton({
  label,
  bgColor,
  onClick,
  disabled,
}: {
  label: string
  bgColor: string
  onClick?: () => void
  disabled?: boolean
}) {
  const [hover, setHover] = useState(false)
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      disabled={disabled}
      className="flex items-center gap-2 px-3 py-1.5 text-sm font-normal rounded transition disabled:opacity-50 disabled:cursor-not-allowed"
      style={{
        color: COLOR_BRUN,
        backgroundColor: hover && !disabled ? '#ECF1F2' : 'transparent',
      }}
      title={disabled ? 'En cours...' : label}
    >
      <span
        className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-white"
        style={{ backgroundColor: bgColor }}
      >
        <ContactRound className="w-4 h-4" />
      </span>
      {label}
    </button>
  )
}

function SortieBlock({
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

function StackedField({
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

function StackedSelectNum({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: number
  options: RefOption[]
  onChange: (v: number) => void
}) {
  return (
    <div className="flex items-center gap-2">
      <label
        className="text-xs font-normal shrink-0 w-24 leading-tight"
        style={{ color: COLOR_BRUN }}
      >
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10) || 0)}
        className="flex-1 min-w-0 px-2 py-1 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1"
        style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
      >
        <option value={0}>—</option>
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  )
}

function StackedSelectStr({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: string[]
  onChange: (v: string) => void
}) {
  return (
    <div className="flex items-center gap-2">
      <label
        className="text-xs font-normal shrink-0 w-24 leading-tight"
        style={{ color: COLOR_BRUN }}
      >
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1 min-w-0 px-2 py-1 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1"
        style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o || '—'}
          </option>
        ))}
      </select>
    </div>
  )
}

const DELAI_PREV_OPTIONS = ['', 'sans', '24 heures', '48 heures', '2 semaines', '1 mois']

// --- Overlay "Partenaires" (codes portails + societes DPAE) -------------

function OverlayPartenaires({
  idSalarie,
  apiBase,
  getToken,
  onClose,
}: {
  idSalarie: string
  apiBase: string
  getToken: () => string | null
  onClose: () => void
}) {
  const [portails, setPortails] = useState<SalariePortail[]>([])
  const [dpae, setDpae] = useState<SalariePartDpae[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [selectedPortailId, setSelectedPortailId] = useState<string>('')
  const [selectedDpaeId, setSelectedDpaeId] = useState<string>('')
  const [sending, setSending] = useState(false)

  const reload = () => {
    setLoading(true)
    Promise.all([
      fetch(`${apiBase}/fiche-salarie/${idSalarie}/partenaires/portails`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) =>
        r.ok ? r.json() : r.json().then((j) => Promise.reject(j?.detail || r.status)),
      ),
      fetch(`${apiBase}/fiche-salarie/${idSalarie}/partenaires/dpae`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) =>
        r.ok ? r.json() : r.json().then((j) => Promise.reject(j?.detail || r.status)),
      ),
    ])
      .then(([ps, ds]) => {
        setPortails(ps)
        setDpae(ds)
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idSalarie])

  const selectedPortail = portails.find((p) => p.id_salarie_partenaire === selectedPortailId) || null

  const handleSendCodes = async () => {
    if (!selectedPortail) return
    setSending(true)
    try {
      const r = await fetch(
        `${apiBase}/fiche-salarie/partenaires/portails/${selectedPortail.id_salarie_partenaire}/send-codes`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      )
      const j = await r.json().catch(() => ({}))
      if (!r.ok) {
        showToast(`Échec : ${j?.detail || r.status}`, 'error')
        return
      }
      const parts: string[] = []
      if (j.mail_envoye) parts.push('mail envoyé')
      if (j.sms_envoye) parts.push('SMS envoyé')
      if (parts.length === 0) {
        showToast(`Aucun envoi (${j.sms_result || 'pas de mail ni GSM'})`, 'error')
      } else {
        showToast(`Codes : ${parts.join(' + ')}`, 'success')
      }
    } finally {
      setSending(false)
    }
  }

  const handleDeleteDpae = async (id: string) => {
    const ok = await showConfirm({
      title: 'Suppression',
      message: "Voulez-vous supprimer cette association 'Société de DPAE - Partenaire' ?",
      confirmLabel: 'Supprimer',
      variant: 'danger',
    })
    if (!ok) return
    const r = await fetch(`${apiBase}/fiche-salarie/partenaires/dpae/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!r.ok) {
      const j = await r.json().catch(() => ({}))
      showToast(`Suppression échouée : ${j?.detail || r.status}`, 'error')
      return
    }
    reload()
  }

  return (
    <div
      className="mt-4 border rounded-lg p-4"
      style={{ borderColor: COLOR_BG_SOFT, backgroundColor: '#FFFDFB' }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-normal uppercase tracking-wide" style={{ color: COLOR_BRUN }}>
          Partenaires
        </h3>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-[#ECF1F2]"
          style={{ color: COLOR_BRUN }}
          title="Fermer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {error && (
        <div className="mb-3 text-red-600 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Tableau 1 : Portails partenaires */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <button
              disabled
              className="p-1 rounded hover:bg-[#ECF1F2] disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ color: COLOR_PRIMARY }}
              title="Ajouter (Fen_DPAE_Nouvelle, à venir)"
            >
              <Plus className="w-4 h-4" />
            </button>
            <button
              onClick={handleSendCodes}
              disabled={!selectedPortail || sending}
              className="flex items-center gap-1.5 px-2 py-1 text-xs font-normal rounded hover:bg-[#ECF1F2] disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ color: COLOR_PRIMARY }}
              title="Renvoyer les codes par mail + SMS"
            >
              {sending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
              Renvoyer les codes
            </button>
          </div>
          <div className="border rounded overflow-hidden" style={{ borderColor: COLOR_BG_SOFT }}>
            <table className="w-full text-xs">
              <thead style={{ backgroundColor: COLOR_BG_SOFT }}>
                <tr style={{ color: COLOR_BRUN }}>
                  <Th2>Partenaire</Th2>
                  <Th2>Code</Th2>
                  <Th2>Login</Th2>
                  <Th2>MDP</Th2>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={4} className="px-2 py-3 text-center text-gray-400 italic">
                      Chargement…
                    </td>
                  </tr>
                ) : portails.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-2 py-3 text-center text-gray-400 italic">
                      Aucun portail
                    </td>
                  </tr>
                ) : (
                  portails.map((p) => {
                    const sel = p.id_salarie_partenaire === selectedPortailId
                    return (
                      <tr
                        key={p.id_salarie_partenaire}
                        onClick={() => setSelectedPortailId(p.id_salarie_partenaire)}
                        className="cursor-pointer border-t"
                        style={{
                          backgroundColor: sel ? '#EFF6FF' : 'white',
                          borderColor: COLOR_BG_SOFT,
                        }}
                      >
                        <Td2>{p.lib_partenaire}</Td2>
                        <Td2 mono>{p.code}</Td2>
                        <Td2 mono>{p.login}</Td2>
                        <Td2 mono>{p.mdp}</Td2>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Tableau 2 : Sociétés DPAE par partenaire */}
        <div>
          <div className="flex items-center gap-1 mb-2">
            <button
              disabled
              className="p-1 rounded hover:bg-[#ECF1F2] disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ color: COLOR_PRIMARY }}
              title="Ajouter (Fen_PartDpae, à venir)"
            >
              <Plus className="w-4 h-4" />
            </button>
            <button
              disabled
              className="p-1 rounded hover:bg-[#ECF1F2] disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ color: COLOR_PRIMARY }}
              title="Modifier (Fen_PartDpae, à venir)"
            >
              <Pencil className="w-4 h-4" />
            </button>
            <button
              onClick={() => selectedDpaeId && handleDeleteDpae(selectedDpaeId)}
              disabled={!selectedDpaeId}
              className="p-1 rounded hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ color: '#DC2626' }}
              title="Supprimer l'association sélectionnée"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
          <div className="border rounded overflow-hidden" style={{ borderColor: COLOR_BG_SOFT }}>
            <table className="w-full text-xs">
              <thead style={{ backgroundColor: COLOR_BG_SOFT }}>
                <tr style={{ color: COLOR_BRUN }}>
                  <Th2>Partenaire</Th2>
                  <Th2>Société</Th2>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={2} className="px-2 py-3 text-center text-gray-400 italic">
                      Chargement…
                    </td>
                  </tr>
                ) : dpae.length === 0 ? (
                  <tr>
                    <td colSpan={2} className="px-2 py-3 text-center text-gray-400 italic">
                      Aucune association
                    </td>
                  </tr>
                ) : (
                  dpae.map((d) => {
                    const sel = d.id_salarie_partenaire === selectedDpaeId
                    return (
                      <tr
                        key={d.id_salarie_partenaire}
                        onClick={() => setSelectedDpaeId(d.id_salarie_partenaire)}
                        className="cursor-pointer border-t"
                        style={{
                          backgroundColor: sel ? '#EFF6FF' : 'white',
                          borderColor: COLOR_BG_SOFT,
                        }}
                      >
                        <Td2>{d.lib_partenaire}</Td2>
                        <Td2>{d.rs_societe}</Td2>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

// --- Overlay "Origine DPAE" (Coopte/JO directe + Fiche CV) --------------

function OverlayOrigineDPAE({
  idSalarie,
  apiBase,
  getToken,
  edit,
  set,
  onClose,
}: {
  idSalarie: string
  apiBase: string
  getToken: () => string | null
  edit: FicheEmbauche
  set: (patch: Partial<FicheEmbauche>) => void
  onClose: () => void
}) {
  const [pickerFor, setPickerFor] = useState<null | 'coopteur' | 'jo_coopteur'>(null)
  const [savingCv, setSavingCv] = useState(false)
  const [savedCv, setSavedCv] = useState(false)

  const handleSaveCv = async () => {
    setSavingCv(true)
    setSavedCv(false)
    try {
      const r = await fetch(`${apiBase}/fiche-salarie/${idSalarie}/embauche`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id_cvtheque: edit.id_cvtheque || '' }),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        showToast(`Erreur : ${j?.detail || r.status}`, 'error')
        return
      }
      setSavedCv(true)
      window.setTimeout(() => setSavedCv(false), 1500)
    } finally {
      setSavingCv(false)
    }
  }

  const pickCoopteur = (s: SalarieItem) => {
    const lib = `${s.nom} ${capitalize(s.prenom)}`
    if (pickerFor === 'coopteur') {
      set({ coopteur: s.id_salarie, coopteur_lib: lib })
    } else if (pickerFor === 'jo_coopteur') {
      set({ jo_coopteur: s.id_salarie, jo_coopteur_lib: lib })
    }
    setPickerFor(null)
  }

  return (
    <div
      className="mt-4 border rounded-lg p-4"
      style={{ borderColor: COLOR_BG_SOFT, backgroundColor: '#FFFDFB' }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-normal uppercase tracking-wide" style={{ color: COLOR_BRUN }}>
          Origine DPAE
        </h3>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-[#ECF1F2]"
          style={{ color: COLOR_BRUN }}
          title="Fermer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-3 max-w-xl">
        {/* Coopté */}
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm font-normal cursor-pointer min-w-[130px]">
            <AdmCheckbox
              checked={edit.coopte}
              onChange={(v) => set({ coopte: v })}
            />
            <span className="font-normal" style={{ color: COLOR_BRUN }}>
              Coopté
            </span>
          </label>
          <button
            onClick={() => setPickerFor('coopteur')}
            disabled={!edit.coopte}
            className="flex-1 flex items-center gap-2 px-3 py-1.5 text-sm font-normal rounded border disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#ECF1F2]"
            style={{
              color: edit.coopteur_lib ? COLOR_BRUN : '#9CA3AF',
              borderColor: COLOR_BG_SOFT,
              fontStyle: edit.coopteur_lib ? 'normal' : 'italic',
            }}
            title="Choisir le coopteur"
          >
            <Users className="w-4 h-4 shrink-0" style={{ color: COLOR_PRIMARY }} />
            {edit.coopteur_lib || 'Choisir le coopteur'}
          </button>
        </div>

        {/* JO directe */}
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm font-normal cursor-pointer min-w-[130px]">
            <AdmCheckbox
              checked={edit.j_odirecte}
              onChange={(v) => set({ j_odirecte: v })}
            />
            <span className="font-normal" style={{ color: COLOR_BRUN }}>
              JO directe
            </span>
          </label>
          <button
            onClick={() => setPickerFor('jo_coopteur')}
            disabled={!edit.j_odirecte}
            className="flex-1 flex items-center gap-2 px-3 py-1.5 text-sm font-normal rounded border disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#ECF1F2]"
            style={{
              color: edit.jo_coopteur_lib ? COLOR_BRUN : '#9CA3AF',
              borderColor: COLOR_BG_SOFT,
              fontStyle: edit.jo_coopteur_lib ? 'normal' : 'italic',
            }}
            title="Choisir le coopteur JO"
          >
            <Users className="w-4 h-4 shrink-0" style={{ color: COLOR_PRIMARY }} />
            {edit.jo_coopteur_lib || 'Choisir le coopteur JO'}
          </button>
        </div>

        {/* Fiche CV */}
        <div className="flex items-center gap-3">
          <button
            disabled={!edit.id_cvtheque}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-normal rounded border disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#ECF1F2] min-w-[130px]"
            style={{
              color: COLOR_BRUN,
              borderColor: COLOR_BG_SOFT,
            }}
            title="Ouvrir la fiche CV (à implémenter)"
          >
            <FileTextIcon className="w-4 h-4 shrink-0" style={{ color: COLOR_PRIMARY }} />
            Fiche CV
          </button>
          <span className="text-sm font-normal" style={{ color: COLOR_BRUN }}>
            IdCV
          </span>
          <input
            value={edit.id_cvtheque || ''}
            onChange={(e) => set({ id_cvtheque: e.target.value })}
            placeholder="ID CVthèque"
            className="flex-1 px-2 py-1 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1"
            style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
          />
          {/* Bouton disquette : save direct (UPDATE id_cvtheque uniquement) */}
          <button
            onClick={handleSaveCv}
            disabled={savingCv}
            className="shrink-0 w-9 h-9 rounded flex items-center justify-center hover:bg-[#ECF1F2] disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              color: savedCv ? '#059669' : COLOR_PRIMARY,
              border: `1px solid ${COLOR_BG_SOFT}`,
            }}
            title="Enregistrer l'ID CVthèque"
          >
            {savingCv ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : savedCv ? (
              <Check className="w-4 h-4" />
            ) : (
              <Save className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {pickerFor && (
        <PersonnePicker
          apiBase={apiBase}
          getToken={getToken}
          title={pickerFor === 'coopteur' ? 'Choisir le coopteur' : 'Choisir le coopteur JO'}
          onClose={() => setPickerFor(null)}
          onSelect={pickCoopteur}
        />
      )}
    </div>
  )
}

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

// --- Overlay "S'Cool" : fiche Formateur ---------------------------------

const NIVEAU_FORMATEUR: { v: number; l: string }[] = [
  { v: 0, l: '—' },
  { v: 1, l: 'Formateur Débutant' },
  { v: 2, l: 'Formateur' },
]

function OverlayScool({
  idSalarie,
  apiBase,
  getToken,
  onClose,
}: {
  idSalarie: string
  apiBase: string
  getToken: () => string | null
  onClose: () => void
}) {
  const [niveau, setNiveau] = useState<number>(0)
  const [actif, setActif] = useState<boolean>(false)
  const [exists, setExists] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(true)
  const [saving, setSaving] = useState<boolean>(false)
  const [error, setError] = useState<string>('')
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    fetch(`${apiBase}/fiche-salarie/${idSalarie}/formateur`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) =>
        r.ok ? r.json() : r.json().then((j) => Promise.reject(j?.detail || r.status)),
      )
      .then((d) => {
        if (cancelled) return
        setNiveau(d.niveau || 0)
        setActif(!!d.formateur_actif)
        setExists(!!d.exists)
      })
      .catch((e) => !cancelled && setError(String(e)))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [idSalarie])

  const handleSave = async () => {
    setSaving(true)
    setToast(null)
    try {
      const r = await fetch(`${apiBase}/fiche-salarie/${idSalarie}/formateur`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          niveau: niveau || 1, // 1 par défaut si jamais 0 lors de la 1ère création (cf. WinDev)
          formateur_actif: actif,
        }),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        setToast({ kind: 'err', msg: `Erreur : ${j?.detail || r.status}` })
        return
      }
      setExists(true)
      setToast({ kind: 'ok', msg: 'Infos formateur enregistrées' })
    } finally {
      setSaving(false)
      window.setTimeout(() => setToast(null), 3000)
    }
  }

  return (
    <div
      className="mt-4 border rounded-lg p-4"
      style={{ borderColor: COLOR_BG_SOFT, backgroundColor: '#FFFDFB' }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-normal uppercase tracking-wide" style={{ color: COLOR_BRUN }}>
          S'Cool — Fiche Formateur
        </h3>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-[#ECF1F2]"
          style={{ color: COLOR_BRUN }}
          title="Fermer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {error && (
        <div className="mb-3 text-red-600 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      )}

      {toast && (
        <div
          className={`mb-3 px-3 py-2 rounded text-sm ${
            toast.kind === 'ok'
              ? 'bg-emerald-50 text-emerald-800'
              : 'bg-red-50 text-red-800'
          }`}
        >
          {toast.msg}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
        </div>
      ) : (
        <div className="space-y-3 max-w-md">
          {/* Combo Niveau */}
          <select
            value={niveau}
            onChange={(e) => setNiveau(parseInt(e.target.value, 10))}
            className="w-full px-3 py-1.5 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1"
            style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
          >
            {NIVEAU_FORMATEUR.map((n) => (
              <option key={n.v} value={n.v}>
                {n.l}
              </option>
            ))}
          </select>

          {/* Checkbox Formateur Actif */}
          <label className="flex items-center gap-2 text-sm font-normal cursor-pointer">
            <AdmCheckbox checked={actif} onChange={setActif} />
            <span className="font-normal" style={{ color: COLOR_BRUN }}>
              Formateur Actif
            </span>
          </label>

          {/* Bouton Enregistrer */}
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-medium border disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#ECF1F2]"
            style={{ color: COLOR_BRUN, borderColor: COLOR_BG_SOFT }}
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {exists ? 'Enregistrer infos formateur' : 'Créer une fiche formateur'}
          </button>
        </div>
      )}
    </div>
  )
}

// --- Overlay "Formation IAG" --------------------------------------------

function OverlayFormationIAG({
  edit,
  set,
  onClose,
}: {
  edit: FicheEmbauche
  set: (patch: Partial<FicheEmbauche>) => void
  onClose: () => void
}) {
  return (
    <div
      className="mt-4 border rounded-lg p-4"
      style={{ borderColor: COLOR_BG_SOFT, backgroundColor: '#FFFDFB' }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-normal uppercase tracking-wide" style={{ color: COLOR_BRUN }}>
          Formation IAG
        </h3>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-[#ECF1F2]"
          style={{ color: COLOR_BRUN }}
          title="Fermer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-3 max-w-md">
        {/* Checkbox Formation IAG */}
        <label className="flex items-center gap-2 text-sm font-normal cursor-pointer">
          <AdmCheckbox
            checked={edit.formation_iag}
            onChange={(v) => set({ formation_iag: v })}
          />
          <span className="font-normal" style={{ color: COLOR_BRUN }}>
            Formation IAG
          </span>
        </label>

        {/* Faite le */}
        <div className="grid grid-cols-[80px_1fr] gap-2 items-center">
          <span className="text-sm font-normal" style={{ color: COLOR_BRUN }}>
            Faite le
          </span>
          <input
            type="date"
            value={edit.formation_iag_date || ''}
            onChange={(e) => set({ formation_iag_date: e.target.value })}
            disabled={!edit.formation_iag}
            className="px-2 py-1 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
          />
        </div>

        {/* Score */}
        <div className="grid grid-cols-[80px_1fr] gap-2 items-center">
          <span className="text-sm font-normal" style={{ color: COLOR_BRUN }}>
            Score
          </span>
          <input
            type="number"
            min={0}
            max={100}
            value={edit.formation_iag_score || 0}
            onChange={(e) =>
              set({ formation_iag_score: parseInt(e.target.value, 10) || 0 })
            }
            disabled={!edit.formation_iag}
            className="w-20 px-2 py-1 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1 disabled:opacity-50 disabled:cursor-not-allowed text-center"
            style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
          />
        </div>
      </div>
    </div>
  )
}

function Th2({ children }: { children: React.ReactNode }) {
  return <th className="px-2 py-1.5 text-left text-xs font-normal">{children}</th>
}

function Td2({ children, mono }: { children: React.ReactNode; mono?: boolean }) {
  return (
    <td
      className={`px-2 py-1.5 text-xs ${mono ? 'font-mono' : ''}`}
      style={{ color: COLOR_BRUN }}
    >
      {children}
    </td>
  )
}

