import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  X,
  Loader2,
  AlertCircle,
  AlertTriangle,
  User as UserIcon,
  Trash2,
  Calendar,
  Video,
  Wallet,
  Printer,
  Copy,
  Check,
  Save,
  Download,
  ChevronRight,
  ArrowDownUp,
  Plus,
  Pencil,
  Send,
  Users,
  FileText as FileTextIcon,
  ShoppingBasket,
  GraduationCap,
  Laptop,
  ContactRound,
  Crown,
  Car as CarIcon,
  Scale,
} from 'lucide-react'
import { getToken } from '@/api'
import PersonnePicker, { type SalarieItem } from '@/components/PersonnePicker'

// --- Types ---------------------------------------------------------------

interface FicheHeader {
  id_salarie: string
  nom: string
  prenom: string
  civilite: number
  photo_url: string
  en_activite: boolean
  en_pause: boolean
  id_ste: string
  rs_societe: string
  id_type_poste: number
  lib_poste: string
  date_debut: string
  date_sortie_demandee: string
  date_sortie_reelle: string
  lib_sortie: string
  datecrea: string
  op_crea: string
  modif_date: string
  modif_op: string
}

interface FicheCoordonnees {
  id_salarie: string
  adresse1: string
  adresse2: string
  cp: string
  ville: string
  tel_fixe: string
  tel_mob: string
  mail: string
  mail2: string
  urg_nom: string
  urg_lien: string
  urg_tel: string
  iban: string
  bic: string
}

interface RefOption { id: number; label: string }
interface StringRefOption { id: string; label: string }

interface FicheEmbaucheRefs {
  societes: StringRefOption[]
  postes: RefOption[]
  type_ctt: RefOption[]
  type_horaire: RefOption[]
  type_sortie: RefOption[]
}

interface SalariePortail {
  id_salarie_partenaire: string
  id_partenaire: string
  lib_partenaire: string
  code: string
  login: string
  mdp: string
}

interface SalariePartDpae {
  id_salarie_partenaire: string
  id_partenaire: string
  lib_partenaire: string
  id_ste: string
  rs_societe: string
}

interface FicheEmbauche {
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

interface FicheIdentite {
  id_salarie: string
  civilite: number
  nom: string
  nom_marital: string
  prenom: string
  sexe: string
  nationalite: string
  date_naiss: string
  lieu_naiss: string
  dep_naiss: number
  num_ss: string
  cpam: string
  num_cin: string
  situation_fam: number
  avec_enfant: boolean
  nb_enfants: number
  travailleur_handi: boolean
  matricule_tr: string
  agenda_actif: boolean
}

type TabKey =
  | 'identite'
  | 'coordonnees'
  | 'infos_embauche'
  | 'orga_suivi'
  | 'suivi_adm'
  | 'contrat_travail'
  | 'documents'
  | 'absences'
  | 'mutuelle'
  | 'note_frais'
  | 'droit_acces'
  | 'declaratif'
  | 'exo_cash'
  | 'ulease'

interface MenuItem {
  key: TabKey
  label: string
  coded: boolean
}

// --- Constants -----------------------------------------------------------

const COLOR_PRIMARY = '#17494E' // vert sombre charte
const COLOR_BRUN = '#4E1D17' // brun-rouge charte
const COLOR_BG_SOFT = '#EFE9E7' // beige clair

const SITUATION_FAM: { v: number; l: string }[] = [
  { v: 0, l: '—' },
  { v: 1, l: 'Célibataire' },
  { v: 2, l: 'Marié(e)' },
  { v: 3, l: 'Pacsé(e)' },
  { v: 4, l: 'Divorcé(e)' },
  { v: 5, l: 'Veuf(ve)' },
  { v: 6, l: 'Concubinage' },
]

const MENU: MenuItem[] = [
  { key: 'identite',        label: 'Infos Principales', coded: true },
  { key: 'coordonnees',     label: 'Coordonnées',       coded: true },
  { key: 'infos_embauche',  label: 'Infos Embauche',    coded: true },
  { key: 'orga_suivi',      label: 'Organigramme',      coded: false },
  { key: 'suivi_adm',       label: 'Suivi ADM',         coded: false },
  { key: 'contrat_travail', label: 'Contrat de travail',coded: false },
  { key: 'documents',       label: 'Documents',         coded: false },
  { key: 'absences',        label: 'Absences',          coded: false },
  { key: 'mutuelle',        label: 'Mutuelle',          coded: false },
  { key: 'note_frais',      label: 'Note de frais',     coded: false },
  { key: 'droit_acces',     label: 'Accès Omaya',       coded: false },
  { key: 'declaratif',      label: 'Déclaratif',        coded: false },
  { key: 'exo_cash',        label: 'Exo Cash',          coded: false },
  { key: 'ulease',          label: 'Ulease',            coded: false },
]

// --- Helpers -------------------------------------------------------------

function formatShortDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

// --- AdmCheckbox : checkbox custom charte (vert fonce + coins arrondis) -

function AdmCheckbox({
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

// --- Composant principal (popup) -----------------------------------------

export default function FicheSalarieModal({
  idSalarie,
  nom: nomInitial,
  prenom: prenomInitial,
  onClose,
}: {
  idSalarie: string
  nom?: string
  prenom?: string
  onClose: () => void
}) {
  const [header, setHeader] = useState<FicheHeader | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [activeTab, setActiveTab] = useState<TabKey>('identite')

  useEffect(() => {
    if (!idSalarie) return
    setLoading(true)
    setError('')
    fetch(`/api/adm/fiche-salarie/${idSalarie}/header`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) =>
        r.ok ? r.json() : r.json().then((j) => Promise.reject(j?.detail || r.status)),
      )
      .then((data: FicheHeader) => setHeader(data))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [idSalarie])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const displayNom = header?.nom || nomInitial || ''
  const displayPrenom = header?.prenom || prenomInitial || ''
  const titleLabel = displayNom
    ? `Fiche de ${displayNom} ${displayPrenom}`
    : 'Fiche salarié'

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.96, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.96, opacity: 0 }}
        className="bg-white rounded-lg shadow-2xl w-full max-w-7xl h-[92vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Barre de titre */}
        <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-200 bg-white">
          <UserIcon className="w-4 h-4" style={{ color: COLOR_PRIMARY }} />
          <span className="text-sm font-medium" style={{ color: COLOR_BRUN }}>
            {titleLabel}
          </span>
          <div className="flex-1" />
          <span className="text-xs" style={{ color: COLOR_BRUN }}>
            Fiche n° <span className="font-semibold">{header?.id_salarie || ''}</span>
          </span>
          <button
            onClick={onClose}
            className="ml-3 p-1 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded"
            title="Fermer (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Barre d'actions */}
        <ActionBar
          header={header}
          idSalarie={idSalarie}
          onHeaderChange={setHeader}
        />

        {/* Erreur de chargement */}
        {error && (
          <div className="px-4 py-2 bg-red-50 border-b border-red-200 text-red-700 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {/* Sidebar + content */}
        <div className="flex-1 flex overflow-hidden">
          <Sidebar activeTab={activeTab} onChange={setActiveTab} />

          <div className="flex-1 overflow-auto" style={{ backgroundColor: '#F9F6F4' }}>
            {activeTab === 'identite' && (
              <IdentiteTab idSalarie={idSalarie} header={header} loading={loading} />
            )}
            {activeTab === 'coordonnees' && (
              <CoordonneesTab idSalarie={idSalarie} />
            )}
            {activeTab === 'infos_embauche' && (
              <EmbaucheTab
                idSalarie={idSalarie}
                onAfterSave={(en_activite) => {
                  if (header) setHeader({ ...header, en_activite })
                }}
              />
            )}
            {activeTab !== 'identite' &&
              activeTab !== 'coordonnees' &&
              activeTab !== 'infos_embauche' && (
                <div className="flex flex-col items-center justify-center h-full text-gray-400 italic">
                  <div className="text-lg mb-2">
                    {MENU.find((m) => m.key === activeTab)?.label}
                  </div>
                  <div className="text-sm">À implémenter dans une prochaine itération.</div>
                </div>
              )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

// --- Action bar ----------------------------------------------------------

function ActionBar({
  header,
  idSalarie,
  onHeaderChange,
}: {
  header: FicheHeader | null
  idSalarie: string
  onHeaderChange: (h: FicheHeader) => void
}) {
  const setActif = async (v: boolean) => {
    if (!header) return
    const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/actif`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: v }),
    })
    if (r.ok) onHeaderChange({ ...header, en_activite: v })
  }
  const setPause = async (v: boolean) => {
    if (!header) return
    const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/en-pause`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: v }),
    })
    if (r.ok) onHeaderChange({ ...header, en_pause: v })
  }
  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-200 bg-white">
      {/* Supprimer */}
      <button
        disabled
        className="flex items-center gap-2 px-2 py-1 border border-red-500 rounded text-red-600 text-xs font-medium disabled:opacity-60 disabled:cursor-not-allowed"
        title="À implémenter"
      >
        <Trash2 className="w-3.5 h-3.5" />
        Supprimer la fiche salarié
      </button>

      {/* Toggle Actif / En pause */}
      <div
        className="flex items-center rounded overflow-hidden ml-2"
        style={{ border: `1px solid ${COLOR_PRIMARY}` }}
      >
        <button
          onClick={() => setActif(true)}
          disabled={!header}
          className="px-4 py-1 text-xs font-medium transition"
          style={{
            backgroundColor: header?.en_activite ? COLOR_PRIMARY : 'transparent',
            color: header?.en_activite ? 'white' : COLOR_PRIMARY,
          }}
        >
          Actif
        </button>
        <button
          onClick={() => setPause(true)}
          disabled={!header}
          className="px-4 py-1 text-xs font-medium transition"
          style={{
            backgroundColor: header?.en_pause ? COLOR_BG_SOFT : 'transparent',
            color: COLOR_BRUN,
            opacity: header?.en_pause ? 1 : 0.7,
          }}
        >
          En pause
        </button>
      </div>

      <div className="flex-1" />

      {/* Actions droite */}
      <HeaderAction icon={<Calendar className="w-4 h-4" />} label="Agenda" />
      <HeaderAction icon={<Video className="w-4 h-4" />} label="Liens Visio" />
      <HeaderAction icon={<Wallet className="w-4 h-4" />} label="Solde de tout compte" />
      <HeaderAction icon={<Printer className="w-4 h-4" />} label="Imprimer" />
      <HeaderAction icon={<Copy className="w-4 h-4" />} label="Dupliquer" />
    </div>
  )
}

function HeaderAction({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <button
      disabled
      className="flex items-center gap-1.5 px-2 py-1 text-xs hover:bg-gray-50 rounded disabled:opacity-50 disabled:cursor-not-allowed"
      style={{ color: COLOR_BRUN }}
      title="À implémenter"
    >
      <span style={{ color: COLOR_PRIMARY }}>{icon}</span>
      {label}
    </button>
  )
}

// --- Sidebar -------------------------------------------------------------

function Sidebar({
  activeTab,
  onChange,
}: {
  activeTab: TabKey
  onChange: (k: TabKey) => void
}) {
  return (
    <nav
      className="w-52 shrink-0 overflow-y-auto py-2 border-r border-gray-200"
      style={{ backgroundColor: '#F5F0EE' }}
    >
      {MENU.map((item) => {
        const active = item.key === activeTab
        return (
          <button
            key={item.key}
            onClick={() => onChange(item.key)}
            disabled={!item.coded}
            className="w-full flex items-center justify-between px-4 py-2 text-sm transition disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              backgroundColor: active ? COLOR_PRIMARY : 'transparent',
              color: active ? 'white' : COLOR_PRIMARY,
              fontWeight: 600,
            }}
            onMouseEnter={(e) => {
              if (!active && item.coded) {
                e.currentTarget.style.backgroundColor = COLOR_BG_SOFT
              }
            }}
            onMouseLeave={(e) => {
              if (!active) e.currentTarget.style.backgroundColor = 'transparent'
            }}
            title={item.coded ? '' : 'À venir'}
          >
            <span>{item.label}</span>
            {active && <ChevronRight className="w-4 h-4" />}
          </button>
        )
      })}
    </nav>
  )
}

// --- Onglet 1 : Infos Principales (Identite) ----------------------------

function IdentiteTab({
  idSalarie,
  header,
  loading,
}: {
  idSalarie: string
  header: FicheHeader | null
  loading: boolean
}) {
  const [data, setData] = useState<FicheIdentite | null>(null)
  const [edit, setEdit] = useState<FicheIdentite | null>(null)
  const [loadingTab, setLoadingTab] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string>('')
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)

  useEffect(() => {
    setLoadingTab(true)
    setError('')
    fetch(`/api/adm/fiche-salarie/${idSalarie}/identite`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) =>
        r.ok ? r.json() : r.json().then((j) => Promise.reject(j?.detail || r.status)),
      )
      .then((d: FicheIdentite) => {
        setData(d)
        setEdit(d)
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoadingTab(false))
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
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/identite`, {
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
      setToast({ kind: 'ok', msg: 'Enregistré' })
    } finally {
      setSaving(false)
      setTimeout(() => setToast(null), 3000)
    }
  }

  if (loadingTab) {
    return (
      <div className="flex items-center gap-2 text-gray-500 p-6">
        <Loader2 className="w-4 h-4 animate-spin" /> Chargement de l'identité…
      </div>
    )
  }
  if (error || !edit) {
    return (
      <div className="text-red-600 text-sm flex items-center gap-2 p-6">
        <AlertCircle className="w-4 h-4" /> {error || 'Pas de données'}
      </div>
    )
  }

  const set = (patch: Partial<FicheIdentite>) =>
    setEdit((prev) => (prev ? { ...prev, ...patch } : prev))

  return (
    <div className="p-6">
      {/* Bandeau infos + actions enregistrer (cf. WinDev CallbackInfoEmbauche) */}
      <div className="flex items-start justify-between mb-4">
        <div className="text-sm" style={{ color: COLOR_BRUN }}>
          {header && (
            <>
              <div className="font-semibold">
                {header.lib_poste || '—'} =&gt; {header.rs_societe || '—'}
              </div>
              <div>{buildEmbaucheLine(header)}</div>
            </>
          )}
          {loading && !header && (
            <div className="text-gray-400 italic">Chargement des infos…</div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Indicateur alerte (placeholder) */}
          <div
            className="w-9 h-9 rounded flex items-center justify-center cursor-default"
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
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Enregistrer
          </button>
        </div>
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

      <div className="flex gap-8">
        {/* Avatar + bouton charger photo */}
        <div className="flex flex-col items-center gap-3 shrink-0">
          <PhotoAvatar photoUrl={header?.photo_url || ''} />
          <button
            disabled
            className="flex items-center gap-2 px-2 py-1 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ color: COLOR_BRUN }}
            title="À implémenter"
          >
            <Download className="w-4 h-4" />
            Charger une photo
          </button>
        </div>

        {/* Formulaire */}
        <div className="flex-1 max-w-2xl space-y-3">
          {/* Civilite toggle + Travailleur handi */}
          <div className="flex items-center gap-6">
            <CiviliteToggle
              value={edit.civilite}
              onChange={(v) => set({ civilite: v })}
            />
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <AdmCheckbox
                checked={edit.travailleur_handi}
                onChange={(v) => set({ travailleur_handi: v })}
              />
              <span style={{ color: COLOR_BRUN }}>Travailleur Handicapé</span>
            </label>
          </div>

          {/* Nom + Epoux(se) */}
          <div className="grid grid-cols-2 gap-3">
            <InlineField
              label="Nom"
              value={edit.nom}
              onChange={(v) => set({ nom: v })}
            />
            <InlineField
              label="Époux (se)"
              value={edit.nom_marital}
              onChange={(v) => set({ nom_marital: v })}
            />
          </div>

          {/* Prenom */}
          <InlineField
            label="Prénom"
            value={edit.prenom}
            onChange={(v) => set({ prenom: v })}
            labelWidth={56}
          />

          {/* Sexe + Nationalite */}
          <div className="grid grid-cols-[1fr_2fr] gap-3">
            <InlineField
              label="Sexe (H/F)"
              value={edit.sexe}
              onChange={(v) => set({ sexe: v.toUpperCase().slice(0, 1) })}
              width={50}
            />
            <InlineField
              label="Nationalité"
              value={edit.nationalite}
              onChange={(v) => set({ nationalite: v })}
            />
          </div>

          {/* Date Naiss + Lieu + Dep */}
          <div className="grid grid-cols-[2fr_3fr_1fr] gap-3">
            <InlineField
              label="Date Naiss"
              type="date"
              value={edit.date_naiss}
              onChange={(v) => set({ date_naiss: v })}
            />
            <InlineField
              label="Lieu Naiss"
              value={edit.lieu_naiss}
              onChange={(v) => set({ lieu_naiss: v })}
            />
            <InlineField
              label="Dép"
              type="number"
              value={String(edit.dep_naiss || '')}
              onChange={(v) => set({ dep_naiss: parseInt(v, 10) || 0 })}
              width={50}
            />
          </div>

          {/* Sécu + CPAM */}
          <div className="grid grid-cols-2 gap-3">
            <InlineField
              label="N° Sécu Sociale"
              value={edit.num_ss}
              onChange={(v) => set({ num_ss: v })}
            />
            <InlineField
              label="CPAM"
              value={edit.cpam}
              onChange={(v) => set({ cpam: v })}
            />
          </div>

          {/* CIN + Matricule TR */}
          <div className="grid grid-cols-2 gap-3">
            <InlineField
              label="N° CIN"
              value={edit.num_cin}
              onChange={(v) => set({ num_cin: v })}
            />
            <InlineField
              label="Matricule TR"
              value={edit.matricule_tr}
              onChange={(v) => set({ matricule_tr: v })}
            />
          </div>

          {/* Situation famille + Avec enfant + Nb enfants */}
          <div className="flex items-center gap-4 pt-2">
            <select
              value={edit.situation_fam}
              onChange={(e) => set({ situation_fam: parseInt(e.target.value, 10) })}
              className="px-3 py-1.5 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1"
              style={{
                border: `1px solid ${COLOR_BG_SOFT}`,
                color: COLOR_BRUN,
                minWidth: 180,
              }}
            >
              {SITUATION_FAM.map((s) => (
                <option key={s.v} value={s.v}>
                  {s.l}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-sm font-normal cursor-pointer">
              <AdmCheckbox
                checked={edit.avec_enfant}
                onChange={(v) => set({ avec_enfant: v })}
              />
              <span className="font-normal" style={{ color: COLOR_BRUN }}>Avec Enfant</span>
            </label>
            <div className="flex items-center gap-2">
              <span className="text-sm font-normal" style={{ color: COLOR_BRUN }}>
                Nb Enfants
              </span>
              <input
                type="number"
                value={edit.nb_enfants || ''}
                onChange={(e) => set({ nb_enfants: parseInt(e.target.value, 10) || 0 })}
                className="w-16 px-2 py-1.5 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1 text-center"
                style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// --- Bandeau Embauche / Sortie ------------------------------------------

function buildEmbaucheLine(h: FicheHeader): string {
  const parts: string[] = []
  if (h.date_debut) parts.push(`Emb. le ${formatShortDate(h.date_debut)}`)
  if (h.en_activite) {
    parts.push('tjrs en activité')
  } else if (h.lib_sortie) {
    let s = `sorti(e) en ${h.lib_sortie}`
    if (h.date_sortie_demandee) {
      s += ` le ${formatShortDate(h.date_sortie_demandee)}`
    } else if (h.date_sortie_reelle) {
      s += ` le ${formatShortDate(h.date_sortie_reelle)}`
    }
    parts.push(s)
  } else {
    parts.push('sorti(e)')
  }
  return parts.join(', ')
}

// --- Onglet 2 : Coordonnees ----------------------------------------------

function CoordonneesTab({ idSalarie }: { idSalarie: string }) {
  const [data, setData] = useState<FicheCoordonnees | null>(null)
  const [edit, setEdit] = useState<FicheCoordonnees | null>(null)
  const [loadingTab, setLoadingTab] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string>('')
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)

  useEffect(() => {
    setLoadingTab(true)
    setError('')
    fetch(`/api/adm/fiche-salarie/${idSalarie}/coordonnees`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) =>
        r.ok ? r.json() : r.json().then((j) => Promise.reject(j?.detail || r.status)),
      )
      .then((d: FicheCoordonnees) => {
        setData(d)
        setEdit(d)
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoadingTab(false))
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
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/coordonnees`, {
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
      // Recharge depuis le serveur pour recuperer les valeurs normalisees (tel, mail)
      const reload = await fetch(`/api/adm/fiche-salarie/${idSalarie}/coordonnees`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (reload.ok) {
        const d = (await reload.json()) as FicheCoordonnees
        setData(d)
        setEdit(d)
      } else {
        setData(edit)
      }
      setToast({ kind: 'ok', msg: 'Informations enregistrées' })
    } finally {
      setSaving(false)
      setTimeout(() => setToast(null), 3000)
    }
  }

  if (loadingTab) {
    return (
      <div className="flex items-center gap-2 text-gray-500 p-6">
        <Loader2 className="w-4 h-4 animate-spin" /> Chargement des coordonnées…
      </div>
    )
  }
  if (error || !edit) {
    return (
      <div className="text-red-600 text-sm flex items-center gap-2 p-6">
        <AlertCircle className="w-4 h-4" /> {error || 'Pas de données'}
      </div>
    )
  }

  const set = (patch: Partial<FicheCoordonnees>) =>
    setEdit((prev) => (prev ? { ...prev, ...patch } : prev))

  const swapEmails = () => set({ mail: edit.mail2, mail2: edit.mail })

  return (
    <div className="p-6">
      {/* Bouton enregistrer en haut a droite */}
      <div className="flex justify-end mb-4">
        <button
          onClick={handleSave}
          disabled={!dirty || saving}
          className="flex items-center gap-2 px-4 py-2 text-white rounded text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition"
          style={{ backgroundColor: COLOR_PRIMARY }}
        >
          {saving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
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

      {/* Layout 2 colonnes */}
      <div className="grid grid-cols-2 gap-12 max-w-5xl">
        {/* Colonne gauche : Postales + telephoniques + emails */}
        <div>
          <SectionTitle>Coordonnées postales et téléphoniques</SectionTitle>

          <div className="space-y-2 mb-5">
            <PlainInput
              placeholder="Adresse 1"
              value={edit.adresse1}
              onChange={(v) => set({ adresse1: v })}
            />
            <PlainInput
              placeholder="Complément"
              value={edit.adresse2}
              onChange={(v) => set({ adresse2: v })}
            />
            <div className="grid grid-cols-[100px_1fr] gap-2">
              <PlainInput
                placeholder="CP"
                value={edit.cp}
                onChange={(v) => set({ cp: v })}
              />
              <PlainInput
                placeholder="Ville"
                value={edit.ville}
                onChange={(v) => set({ ville: v })}
              />
            </div>
          </div>

          {/* Telephones */}
          <div className="space-y-2 mb-5">
            <FieldWithCopy
              placeholder="Téléphone fixe"
              value={edit.tel_fixe}
              onChange={(v) => set({ tel_fixe: v })}
            />
            <FieldWithCopy
              placeholder="Téléphone mobile"
              value={edit.tel_mob}
              onChange={(v) => set({ tel_mob: v })}
            />
          </div>

          {/* Emails avec swap */}
          <div className="space-y-1">
            <FieldWithCopy
              label="Courriel 1*"
              type="email"
              value={edit.mail}
              onChange={(v) => set({ mail: v })}
              labelWidth={75}
            />
            <div
              className="text-xs italic ml-[83px]"
              style={{ color: '#C97064' }}
            >
              * Adresse mail utilisée dans OMAYA
            </div>
            {/* Bouton swap entre les 2 emails */}
            <div className="flex justify-end pr-12 py-1">
              <button
                onClick={swapEmails}
                className="p-1 rounded hover:bg-gray-100"
                style={{ color: COLOR_PRIMARY }}
                title="Permuter Courriel 1 et Courriel 2"
              >
                <ArrowDownUp className="w-4 h-4" />
              </button>
            </div>
            <FieldWithCopy
              label="Courriel 2"
              type="email"
              value={edit.mail2}
              onChange={(v) => set({ mail2: v })}
              labelWidth={75}
            />
          </div>
        </div>

        {/* Colonne droite : Urgence + Bancaires */}
        <div>
          <SectionTitle>Personnes à contacter en cas d'urgence</SectionTitle>
          <div className="space-y-2 mb-8">
            <PlainInput
              placeholder="Nom et prénom"
              value={edit.urg_nom}
              onChange={(v) => set({ urg_nom: v })}
            />
            <PlainInput
              placeholder="Lien (époux, parent...)"
              value={edit.urg_lien}
              onChange={(v) => set({ urg_lien: v })}
            />
            <PlainInput
              placeholder="Téléphone"
              value={edit.urg_tel}
              onChange={(v) => set({ urg_tel: v })}
            />
          </div>

          <SectionTitle>Coordonnées bancaires</SectionTitle>
          <div className="space-y-2">
            <div className="grid grid-cols-[60px_1fr] gap-2 items-center">
              <label className="text-sm font-normal" style={{ color: COLOR_BRUN }}>
                IBAN
              </label>
              <PlainInput
                value={edit.iban}
                onChange={(v) => set({ iban: v })}
              />
            </div>
            <div className="grid grid-cols-[60px_1fr] gap-2 items-center">
              <label className="text-sm font-normal" style={{ color: COLOR_BRUN }}>
                BIC
              </label>
              <PlainInput
                value={edit.bic}
                onChange={(v) => set({ bic: v })}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3
      className="text-sm uppercase tracking-wide font-normal mb-3"
      style={{ color: COLOR_BRUN }}
    >
      {children}
    </h3>
  )
}

// --- Onglet 3 : Infos Embauche ------------------------------------------

function EmbaucheTab({
  idSalarie,
  onAfterSave,
}: {
  idSalarie: string
  onAfterSave: (en_activite: boolean) => void
}) {
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

  useEffect(() => {
    let cancelled = false
    setLoadingTab(true)
    setError('')
    Promise.all([
      fetch(`/api/adm/fiche-salarie/${idSalarie}/embauche`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) =>
        r.ok ? r.json() : r.json().then((j) => Promise.reject(j?.detail || r.status)),
      ),
      fetch(`/api/adm/fiche-salarie/embauche/refs`, {
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
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/embauche`, {
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
      onAfterSave(edit.en_activite)
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

  return (
    <div className="p-6">
      {/* Top bar */}
      <div className="flex items-center gap-6 mb-5">
        <ActivToggle
          en_activite={edit.en_activite}
          onChange={(v) => set({ en_activite: v })}
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
                className="shrink-0 p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
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
            iconBg="#DC2626"
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
          disabled
        />
        <OverlayButton
          label="S'Cool"
          icon={<Laptop className="w-4 h-4" />}
          bgColor="#1E3A8A"
          active={overlay === 'scool'}
          onClick={() => toggleOverlay('scool')}
          disabled
        />
      </div>

      {/* Panneau overlay actif */}
      {overlay === 'partenaires' && (
        <OverlayPartenaires
          idSalarie={idSalarie}
          onClose={() => setOverlay(null)}
        />
      )}
      {overlay === 'origine_dpae' && (
        <OverlayOrigineDPAE
          idSalarie={idSalarie}
          edit={edit}
          set={set}
          onClose={() => setOverlay(null)}
        />
      )}

      {/* Boutons sortie (visibles si pas en activite, placeholder pour la
          logique complete avec mails/tickets/etc.) */}
      {!edit.en_activite && (
        <>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-6">
            <SortieButton label="Annul DUE" bgColor="#D97706" />
            <SortieButton label="FPE entreprise" bgColor="#DC2626" />
            <SortieButton label="Dém / FPE Salarié" bgColor="#DC2626" />
            <SortieButton label="Dém présumée" bgColor="#DC2626" />
            <SortieButton label="Licenciement" bgColor="#DC2626" />
            <SortieButton label="Rupture conv" bgColor="#DC2626" />
          </div>

          <div className="mt-6 grid grid-cols-3 gap-4">
            <SortieBlock title="Information de sortie">
              <LabeledField
                label="Date Sortie Demandée"
                type="date"
                value={edit.date_sortie_demandee}
                onChange={(v) => set({ date_sortie_demandee: v })}
              />
              <LabeledField
                label="Date Sortie Réelle"
                type="date"
                value={edit.date_sortie_reelle}
                onChange={(v) => set({ date_sortie_reelle: v })}
              />
              <LabeledSelectNum
                label="Type Sortie"
                value={edit.id_type_sortie}
                options={refs.type_sortie}
                onChange={(v) => set({ id_type_sortie: v })}
              />
              <LabeledField
                label="Info Cplt"
                value={edit.info_cpl}
                onChange={(v) => set({ info_cpl: v })}
              />
            </SortieBlock>

            <SortieBlock title="Courrier FPE / DEM">
              <LabeledField
                label="Envoyé le"
                type="date"
                value={edit.courrier_date_envoi}
                onChange={(v) => set({ courrier_date_envoi: v })}
              />
              <LabeledField
                label="Reçu le"
                type="date"
                value={edit.courrier_date_recep}
                onChange={(v) => set({ courrier_date_recep: v })}
              />
              <LabeledField
                label="Num Suivi"
                value={edit.courrier_num_suivi}
                onChange={(v) => set({ courrier_num_suivi: v })}
              />
              <LabeledField
                label="Délai Prév."
                value={edit.courrier_delai_prev}
                onChange={(v) => set({ courrier_delai_prev: v })}
              />
            </SortieBlock>

            <SortieBlock title="Solde de tout compte">
              <LabeledField
                label="Envoyé le"
                type="date"
                value={edit.stc_date_envoi}
                onChange={(v) => set({ stc_date_envoi: v })}
              />
              <LabeledField
                label="Reçu le"
                type="date"
                value={edit.stc_date_recep}
                onChange={(v) => set({ stc_date_recep: v })}
              />
              <LabeledField
                label="Num Suivi"
                value={edit.stc_num_suivi}
                onChange={(v) => set({ stc_num_suivi: v })}
              />
              <LabeledField
                label="Retourné le"
                type="date"
                value={edit.stc_retourne_le}
                onChange={(v) => set({ stc_retourne_le: v })}
              />
            </SortieBlock>
          </div>
        </>
      )}
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
        className="px-2 py-1 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1"
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
        className="px-2 py-1 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1"
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
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex items-center gap-2 px-2 py-1 text-sm font-normal rounded transition disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
      style={{
        color: COLOR_BRUN,
        textDecoration: active ? 'underline' : 'none',
        textUnderlineOffset: 4,
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
}: {
  label: string
  bgColor: string
}) {
  return (
    <button
      disabled
      className="flex items-center gap-2 px-2 py-1 text-sm font-normal rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
      style={{ color: COLOR_BRUN }}
      title="À implémenter (action de sortie complète à venir)"
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
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="border rounded p-3" style={{ borderColor: COLOR_BG_SOFT }}>
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

// --- Overlay "Partenaires" (codes portails + societes DPAE) -------------

function OverlayPartenaires({
  idSalarie,
  onClose,
}: {
  idSalarie: string
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
      fetch(`/api/adm/fiche-salarie/${idSalarie}/partenaires/portails`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) =>
        r.ok ? r.json() : r.json().then((j) => Promise.reject(j?.detail || r.status)),
      ),
      fetch(`/api/adm/fiche-salarie/${idSalarie}/partenaires/dpae`, {
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
      // Endpoint à venir : POST /partenaires/portails/{id}/send-codes
      // Pour cette phase : juste un toast informatif.
      alert(
        "Envoi mail + SMS des codes : à brancher backend (route /partenaires/portails/{id}/send-codes).",
      )
    } finally {
      setSending(false)
    }
  }

  const handleDeleteDpae = async (id: string) => {
    if (!window.confirm("Voulez-vous supprimer cette association 'Ste de DPAE-Partenaire' ?")) return
    const r = await fetch(`/api/adm/fiche-salarie/partenaires/dpae/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!r.ok) {
      const j = await r.json().catch(() => ({}))
      alert(`Suppression échouée : ${j?.detail || r.status}`)
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
          className="p-1 rounded hover:bg-gray-100"
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
              className="p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ color: COLOR_PRIMARY }}
              title="Ajouter (Fen_DPAE_Nouvelle, à venir)"
            >
              <Plus className="w-4 h-4" />
            </button>
            <button
              onClick={handleSendCodes}
              disabled={!selectedPortail || sending}
              className="flex items-center gap-1.5 px-2 py-1 text-xs font-normal rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
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
              className="p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ color: COLOR_PRIMARY }}
              title="Ajouter (Fen_PartDpae, à venir)"
            >
              <Plus className="w-4 h-4" />
            </button>
            <button
              disabled
              className="p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
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
  edit,
  set,
  onClose,
}: {
  idSalarie: string
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
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/embauche`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id_cvtheque: edit.id_cvtheque || '' }),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        alert(`Erreur : ${j?.detail || r.status}`)
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
          className="p-1 rounded hover:bg-gray-100"
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
            className="flex-1 flex items-center gap-2 px-3 py-1.5 text-sm font-normal rounded border disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
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
            className="flex-1 flex items-center gap-2 px-3 py-1.5 text-sm font-normal rounded border disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
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
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-normal rounded border disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 min-w-[130px]"
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
            className="shrink-0 w-9 h-9 rounded flex items-center justify-center hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
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

function PlainInput({
  placeholder,
  value,
  onChange,
  type = 'text',
}: {
  placeholder?: string
  value: string
  onChange: (v: string) => void
  type?: string
}) {
  return (
    <input
      type={type}
      value={value || ''}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-1.5 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1 placeholder:italic placeholder:text-gray-400 placeholder:font-normal"
      style={{
        border: `1px solid ${COLOR_BG_SOFT}`,
        color: COLOR_BRUN,
      }}
    />
  )
}

function FieldWithCopy({
  label,
  placeholder,
  value,
  onChange,
  type = 'text',
  labelWidth,
}: {
  label?: string
  placeholder?: string
  value: string
  onChange: (v: string) => void
  type?: string
  labelWidth?: number
}) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      /* indispo */
    }
  }
  return (
    <div className="flex items-center gap-2">
      {label && (
        <span
          className="text-sm font-normal shrink-0"
          style={{ color: COLOR_BRUN, minWidth: labelWidth }}
        >
          {label}
        </span>
      )}
      <input
        type={type}
        value={value || ''}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1 px-3 py-1.5 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1 placeholder:italic placeholder:text-gray-400 placeholder:font-normal"
        style={{ border: `1px solid ${COLOR_BG_SOFT}`, color: COLOR_BRUN }}
      />
      <button
        onClick={handleCopy}
        disabled={!value}
        className="shrink-0 w-8 h-8 rounded flex items-center justify-center hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
        style={{ color: COLOR_PRIMARY }}
        title="Copier"
      >
        {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
      </button>
    </div>
  )
}

// --- Photo avatar avec fallback ------------------------------------------

function PhotoAvatar({ photoUrl }: { photoUrl: string }) {
  // L'endpoint est protege par Bearer token : on ne peut pas mettre l'URL
  // dans <img src=...> tel quel (le navigateur n'envoie pas le header).
  // On fetch en JS et on cree un objectURL revoque au cleanup.
  const [blobUrl, setBlobUrl] = useState<string>('')

  useEffect(() => {
    if (!photoUrl) {
      setBlobUrl('')
      return
    }
    let cancelled = false
    let createdUrl = ''
    ;(async () => {
      try {
        const r = await fetch(photoUrl, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        if (!r.ok) {
          if (!cancelled) setBlobUrl('')
          return
        }
        const blob = await r.blob()
        if (cancelled) return
        createdUrl = URL.createObjectURL(blob)
        setBlobUrl(createdUrl)
      } catch {
        if (!cancelled) setBlobUrl('')
      }
    })()
    return () => {
      cancelled = true
      if (createdUrl) URL.revokeObjectURL(createdUrl)
    }
  }, [photoUrl])

  return (
    <div
      className="w-44 h-44 rounded-full bg-gray-100 flex items-center justify-center overflow-hidden"
      style={{ border: `2px solid ${COLOR_BG_SOFT}` }}
    >
      {blobUrl ? (
        <img src={blobUrl} alt="Photo salarié" className="w-full h-full object-cover" />
      ) : (
        <UserIcon className="w-20 h-20 text-gray-400" />
      )}
    </div>
  )
}

// --- Helpers d'UI form ---------------------------------------------------

function CiviliteToggle({
  value,
  onChange,
}: {
  value: number
  onChange: (v: number) => void
}) {
  // 1 = M, 2 = Mme
  return (
    <div
      className="flex items-center rounded overflow-hidden"
      style={{ border: `1px solid ${COLOR_BG_SOFT}` }}
    >
      {[
        { v: 1, l: 'M.' },
        { v: 2, l: 'Mme' },
      ].map((o) => {
        const active = value === o.v
        return (
          <button
            key={o.v}
            onClick={() => onChange(o.v)}
            className="px-4 py-1 text-sm transition"
            style={{
              backgroundColor: active ? COLOR_PRIMARY : 'white',
              color: active ? 'white' : COLOR_BRUN,
              fontWeight: active ? 600 : 400,
            }}
          >
            {o.l}
          </button>
        )
      })}
    </div>
  )
}

function InlineField({
  label,
  value,
  onChange,
  type = 'text',
  width,
  labelWidth,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  width?: number
  labelWidth?: number
}) {
  return (
    <label className="flex items-center gap-2 text-sm font-normal">
      <span
        className="shrink-0 font-normal"
        style={{
          color: COLOR_BRUN,
          minWidth: labelWidth,
        }}
      >
        {label}
      </span>
      <input
        type={type}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1 px-2 py-1 rounded text-sm font-normal bg-white focus:outline-none focus:ring-1"
        style={{
          border: `1px solid ${COLOR_BG_SOFT}`,
          color: COLOR_BRUN,
          maxWidth: width,
        }}
      />
    </label>
  )
}
