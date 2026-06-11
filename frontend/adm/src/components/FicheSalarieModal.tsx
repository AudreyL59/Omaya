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
} from 'lucide-react'
import { getToken } from '@/api'
import EmbaucheTab, {
  AdmCheckbox,
  COLOR_PRIMARY,
  COLOR_BRUN,
  COLOR_BG_SOFT,
} from '@shared/fiche/EmbaucheTab'
import AbsencesTab from './fiche/AbsencesTab'
import DocRHTab from './fiche/DocRHTab'
import DocumentsTab from './fiche/DocumentsTab'
import MutuelleTab from './fiche/MutuelleTab'
import NoteFraisTab from './fiche/NoteFraisTab'
import OrgaSuiviTab from './fiche/OrgaSuiviTab'
import SuiviADMTab from './fiche/SuiviADMTab'

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

// Types lies a l'embauche (FicheEmbauche, FicheEmbaucheRefs, SalariePortail,
// SalariePartDpae, RefOption, StringRefOption) sont desormais definis dans
// @shared/fiche/EmbaucheTab et utilises uniquement par ce composant shared.

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

// COLOR_PRIMARY / COLOR_BRUN / COLOR_BG_SOFT : importes depuis @shared/fiche/EmbaucheTab.

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
  { key: 'orga_suivi',      label: 'Organigramme',      coded: true },
  { key: 'suivi_adm',       label: 'Suivi ADM',         coded: true },
  { key: 'contrat_travail', label: 'Contrat de travail',coded: true },
  { key: 'documents',       label: 'Documents',         coded: true },
  { key: 'absences',        label: 'Absences',          coded: true },
  { key: 'mutuelle',        label: 'Mutuelle',          coded: true },
  { key: 'note_frais',      label: 'Note de frais',     coded: true },
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
            className="ml-3 p-1 text-gray-500 hover:text-gray-800 hover:bg-[#ECF1F2] rounded"
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
                apiBase="/api/adm"
                getToken={getToken}
                onAfterSave={(en_activite) => {
                  if (header) setHeader({ ...header, en_activite })
                }}
              />
            )}
            {activeTab === 'orga_suivi' && (
              <div className="p-5">
                <OrgaSuiviTab idSalarie={idSalarie} />
              </div>
            )}
            {activeTab === 'suivi_adm' && (
              <div className="p-5">
                <SuiviADMTab idSalarie={idSalarie} />
              </div>
            )}
            {activeTab === 'contrat_travail' && (
              <div className="p-5">
                <DocRHTab idSalarie={idSalarie} />
              </div>
            )}
            {activeTab === 'documents' && (
              <div className="p-5 h-full">
                <DocumentsTab idSalarie={idSalarie} />
              </div>
            )}
            {activeTab === 'absences' && (
              <div className="p-5 h-full">
                <AbsencesTab idSalarie={idSalarie} />
              </div>
            )}
            {activeTab === 'mutuelle' && (
              <div className="p-5 h-full">
                <MutuelleTab idSalarie={idSalarie} />
              </div>
            )}
            {activeTab === 'note_frais' && (
              <div className="p-5 h-full">
                <NoteFraisTab idSalarie={idSalarie} />
              </div>
            )}
            {activeTab !== 'identite' &&
              activeTab !== 'coordonnees' &&
              activeTab !== 'infos_embauche' &&
              activeTab !== 'orga_suivi' &&
              activeTab !== 'suivi_adm' &&
              activeTab !== 'contrat_travail' &&
              activeTab !== 'documents' &&
              activeTab !== 'absences' &&
              activeTab !== 'mutuelle' &&
              activeTab !== 'note_frais' && (
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
      className="flex items-center gap-1.5 px-2 py-1 text-xs hover:bg-[#ECF1F2] rounded disabled:opacity-50 disabled:cursor-not-allowed"
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
                className="p-1 rounded hover:bg-[#ECF1F2]"
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
        className="shrink-0 w-8 h-8 rounded flex items-center justify-center hover:bg-[#ECF1F2] disabled:opacity-40 disabled:cursor-not-allowed"
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
