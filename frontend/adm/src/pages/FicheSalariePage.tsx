import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ChevronLeft,
  Loader2,
  AlertCircle,
  User,
  Phone,
  Briefcase,
  Network,
  ClipboardList,
  FileSignature,
  Files,
  CalendarOff,
  HeartPulse,
  Receipt,
  KeyRound,
  FileText,
  PiggyBank,
  Car,
  Trash2,
  Calendar,
  Video,
  Wallet,
  Printer,
  Copy,
  Save,
  Pause,
  Play,
} from 'lucide-react'
import { getToken } from '@/api'

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
  icon: React.ReactNode
  coded: boolean
}

// --- Constants -----------------------------------------------------------

const CIVILITES: { v: number; l: string }[] = [
  { v: 0, l: '—' },
  { v: 1, l: 'M.' },
  { v: 2, l: 'Mme' },
  { v: 3, l: 'Mlle' },
]

const SITUATION_FAM: { v: number; l: string }[] = [
  { v: 0, l: '—' },
  { v: 1, l: 'Célibataire' },
  { v: 2, l: 'Marié(e)' },
  { v: 3, l: 'Pacsé(e)' },
  { v: 4, l: 'Divorcé(e)' },
  { v: 5, l: 'Veuf(ve)' },
  { v: 6, l: 'Concubinage' },
]

const SEXES = [
  { v: '', l: '—' },
  { v: 'H', l: 'H' },
  { v: 'F', l: 'F' },
]

const MENU: MenuItem[] = [
  { key: 'identite',        label: 'Infos Principales', icon: <User className="w-4 h-4" />,           coded: true },
  { key: 'coordonnees',     label: 'Coordonnées',       icon: <Phone className="w-4 h-4" />,          coded: false },
  { key: 'infos_embauche',  label: 'Infos Embauche',    icon: <Briefcase className="w-4 h-4" />,      coded: false },
  { key: 'orga_suivi',      label: 'Organigramme',      icon: <Network className="w-4 h-4" />,        coded: false },
  { key: 'suivi_adm',       label: 'Suivi ADM',         icon: <ClipboardList className="w-4 h-4" />,  coded: false },
  { key: 'contrat_travail', label: 'Contrat de travail',icon: <FileSignature className="w-4 h-4" />,  coded: false },
  { key: 'documents',       label: 'Documents',         icon: <Files className="w-4 h-4" />,          coded: false },
  { key: 'absences',        label: 'Absences',          icon: <CalendarOff className="w-4 h-4" />,    coded: false },
  { key: 'mutuelle',        label: 'Mutuelle',          icon: <HeartPulse className="w-4 h-4" />,     coded: false },
  { key: 'note_frais',      label: 'Note de frais',     icon: <Receipt className="w-4 h-4" />,        coded: false },
  { key: 'droit_acces',     label: 'Accès Omaya',       icon: <KeyRound className="w-4 h-4" />,       coded: false },
  { key: 'declaratif',      label: 'Déclaratif',        icon: <FileText className="w-4 h-4" />,       coded: false },
  { key: 'exo_cash',        label: 'Exo Cash',          icon: <PiggyBank className="w-4 h-4" />,      coded: false },
  { key: 'ulease',          label: 'Ulease',            icon: <Car className="w-4 h-4" />,            coded: false },
]

// --- Helpers -------------------------------------------------------------

function civiliteLib(v: number): string {
  return CIVILITES.find((c) => c.v === v)?.l || ''
}

// --- Page ----------------------------------------------------------------

export default function FicheSalariePage() {
  const { idSalarie } = useParams<{ idSalarie: string }>()
  const navigate = useNavigate()

  const [header, setHeader] = useState<FicheHeader | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [activeTab, setActiveTab] = useState<TabKey>('identite')

  // Charge le header au mount
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

  if (!idSalarie) {
    return <div className="p-6 text-red-600">ID salarié manquant dans l'URL</div>
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <FicheHeaderBlock
        loading={loading}
        error={error}
        header={header}
        onBack={() => navigate(-1)}
        onActifChange={async (v) => {
          if (!header) return
          const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/actif`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${getToken()}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ value: v }),
          })
          if (r.ok) setHeader({ ...header, en_activite: v })
        }}
        onPauseChange={async (v) => {
          if (!header) return
          const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/en-pause`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${getToken()}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ value: v }),
          })
          if (r.ok) setHeader({ ...header, en_pause: v })
        }}
      />

      {/* Sidebar + content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar menu vertical */}
        <nav className="w-64 shrink-0 border-r border-c-line bg-c-bg-soft overflow-y-auto py-3">
          {MENU.map((item) => {
            const active = item.key === activeTab
            return (
              <button
                key={item.key}
                onClick={() => setActiveTab(item.key)}
                disabled={!item.coded}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm text-left transition border-l-4 ${
                  active
                    ? 'bg-[#17494E] text-white border-l-white font-semibold'
                    : item.coded
                      ? 'text-c-ink hover:bg-c-bg border-l-transparent'
                      : 'text-c-ink-faint italic border-l-transparent cursor-not-allowed opacity-60'
                }`}
                title={item.coded ? '' : 'À venir'}
              >
                {item.icon}
                <span className="flex-1">{item.label}</span>
                {!item.coded && (
                  <span className="text-[10px] uppercase tracking-wide">soon</span>
                )}
              </button>
            )
          })}
        </nav>

        {/* Content de l'onglet actif */}
        <div className="flex-1 overflow-auto p-6">
          {activeTab === 'identite' && idSalarie && (
            <IdentiteTab idSalarie={idSalarie} />
          )}
          {activeTab !== 'identite' && (
            <div className="flex flex-col items-center justify-center h-full text-c-ink-faint italic">
              <div className="text-lg mb-2">
                {MENU.find((m) => m.key === activeTab)?.label}
              </div>
              <div className="text-sm">À implémenter dans une prochaine itération.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// --- Header --------------------------------------------------------------

function FicheHeaderBlock({
  loading,
  error,
  header,
  onBack,
  onActifChange,
  onPauseChange,
}: {
  loading: boolean
  error: string
  header: FicheHeader | null
  onBack: () => void
  onActifChange: (v: boolean) => void
  onPauseChange: (v: boolean) => void
}) {
  return (
    <div className="border-b border-c-line bg-white">
      <div className="flex items-center gap-3 px-6 py-3">
        <button
          onClick={onBack}
          className="flex items-center gap-1 px-2 py-1 text-xs text-c-ink-soft hover:text-c-brand hover:bg-c-bg-soft rounded"
        >
          <ChevronLeft className="w-4 h-4" />
          Retour
        </button>

        <div className="flex-1 flex items-center gap-4">
          {loading ? (
            <div className="flex items-center gap-2 text-c-ink-soft text-sm">
              <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 text-red-600 text-sm">
              <AlertCircle className="w-4 h-4" /> {error}
            </div>
          ) : header ? (
            <>
              <div className="w-12 h-12 rounded-full bg-c-brand-soft flex items-center justify-center text-c-brand font-semibold">
                {(header.prenom?.[0] || '') + (header.nom?.[0] || '')}
              </div>
              <div>
                <div className="text-base font-semibold text-c-ink">
                  {civiliteLib(header.civilite)} {header.prenom} {header.nom}
                </div>
                <div className="text-xs text-c-ink-soft">
                  {header.lib_poste || '—'} · {header.rs_societe || '—'}
                </div>
              </div>
            </>
          ) : null}
        </div>

        {/* Toggles Actif / En pause */}
        {header && (
          <div className="flex items-center gap-1 p-0.5 bg-c-bg-soft rounded-lg">
            <button
              onClick={() => onActifChange(!header.en_activite)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition ${
                header.en_activite
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-c-ink-soft hover:bg-white'
              }`}
            >
              <Play className="w-3.5 h-3.5" />
              {header.en_activite ? 'Actif' : 'Inactif'}
            </button>
            <button
              onClick={() => onPauseChange(!header.en_pause)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition ${
                header.en_pause
                  ? 'bg-amber-500 text-white shadow-sm'
                  : 'text-c-ink-soft hover:bg-white'
              }`}
            >
              <Pause className="w-3.5 h-3.5" />
              En pause
            </button>
          </div>
        )}

        {/* Actions header (placeholder pour l'instant) */}
        <div className="flex items-center gap-1">
          <HeaderAction icon={<Calendar className="w-4 h-4" />} label="Agenda" />
          <HeaderAction icon={<Video className="w-4 h-4" />} label="Liens Visio" />
          <HeaderAction icon={<Wallet className="w-4 h-4" />} label="Solde de tout compte" />
          <HeaderAction icon={<Printer className="w-4 h-4" />} label="Imprimer" />
          <HeaderAction icon={<Copy className="w-4 h-4" />} label="Dupliquer" />
        </div>
      </div>

      {/* N° fiche + Supprimer */}
      {header && (
        <div className="flex items-center gap-2 px-6 pb-2 text-xs text-c-ink-soft">
          <span>Fiche n° {header.id_salarie}</span>
          <div className="flex-1" />
          <button
            disabled
            className="flex items-center gap-1.5 px-2 py-1 text-red-600 hover:bg-red-50 rounded disabled:opacity-40 disabled:cursor-not-allowed"
            title="À implémenter"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Supprimer la fiche salarié
          </button>
        </div>
      )}
    </div>
  )
}

function HeaderAction({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <button
      disabled
      className="flex items-center gap-1.5 px-2 py-1.5 text-xs text-c-ink-soft hover:bg-c-bg-soft rounded disabled:opacity-40 disabled:cursor-not-allowed"
      title="À implémenter"
    >
      {icon}
      {label}
    </button>
  )
}

// --- Onglet 1 : Infos Principales (Identite) ----------------------------

function IdentiteTab({ idSalarie }: { idSalarie: string }) {
  const [data, setData] = useState<FicheIdentite | null>(null)
  const [edit, setEdit] = useState<FicheIdentite | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string>('')
  const [toast, setToast] = useState<{ kind: 'ok' | 'err'; msg: string } | null>(null)

  useEffect(() => {
    setLoading(true)
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
      .finally(() => setLoading(false))
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

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-c-ink-soft">
        <Loader2 className="w-4 h-4 animate-spin" /> Chargement de l'identité…
      </div>
    )
  }
  if (error || !edit) {
    return (
      <div className="text-red-600 text-sm flex items-center gap-2">
        <AlertCircle className="w-4 h-4" /> {error || 'Pas de données'}
      </div>
    )
  }

  const set = (patch: Partial<FicheIdentite>) =>
    setEdit((prev) => (prev ? { ...prev, ...patch } : prev))

  return (
    <div className="max-w-4xl">
      {/* Titre + bouton enregistrer */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-c-ink">Infos Principales</h2>
        <button
          onClick={handleSave}
          disabled={!dirty || saving}
          className="flex items-center gap-2 px-3 py-1.5 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700 disabled:opacity-40 disabled:cursor-not-allowed"
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

      {/* Identite */}
      <Section title="Identité">
        <SelectField
          label="Civilité"
          value={edit.civilite}
          options={CIVILITES.map((c) => ({ v: c.v, l: c.l }))}
          onChange={(v) => set({ civilite: v })}
        />
        <Field label="Nom" value={edit.nom} onChange={(v) => set({ nom: v })} />
        <Field
          label="Nom marital"
          value={edit.nom_marital}
          onChange={(v) => set({ nom_marital: v })}
        />
        <Field label="Prénom" value={edit.prenom} onChange={(v) => set({ prenom: v })} />
        <SelectFieldStr
          label="Sexe"
          value={edit.sexe}
          options={SEXES}
          onChange={(v) => set({ sexe: v })}
        />
        <Field
          label="Nationalité"
          value={edit.nationalite}
          onChange={(v) => set({ nationalite: v })}
        />
      </Section>

      <Section title="Naissance">
        <Field
          label="Date naissance"
          type="date"
          value={edit.date_naiss}
          onChange={(v) => set({ date_naiss: v })}
        />
        <Field
          label="Lieu naissance"
          value={edit.lieu_naiss}
          onChange={(v) => set({ lieu_naiss: v })}
        />
        <Field
          label="Département naissance"
          type="number"
          value={String(edit.dep_naiss || '')}
          onChange={(v) => set({ dep_naiss: parseInt(v, 10) || 0 })}
        />
      </Section>

      <Section title="Numéros officiels">
        <Field
          label="N° Sécu Sociale"
          value={edit.num_ss}
          onChange={(v) => set({ num_ss: v })}
        />
        <Field label="CPAM" value={edit.cpam} onChange={(v) => set({ cpam: v })} />
        <Field
          label="N° CIN"
          value={edit.num_cin}
          onChange={(v) => set({ num_cin: v })}
        />
        <Field
          label="Matricule TR"
          value={edit.matricule_tr}
          onChange={(v) => set({ matricule_tr: v })}
        />
      </Section>

      <Section title="Situation familiale">
        <SelectField
          label="Situation famille"
          value={edit.situation_fam}
          options={SITUATION_FAM.map((s) => ({ v: s.v, l: s.l }))}
          onChange={(v) => set({ situation_fam: v })}
        />
        <Checkbox
          label="Avec enfant"
          checked={edit.avec_enfant}
          onChange={(v) => set({ avec_enfant: v })}
        />
        <Field
          label="Nombre d'enfants"
          type="number"
          value={String(edit.nb_enfants || '')}
          onChange={(v) => set({ nb_enfants: parseInt(v, 10) || 0 })}
        />
      </Section>

      <Section title="Particularités">
        <Checkbox
          label="Travailleur handicapé (RQTH)"
          checked={edit.travailleur_handi}
          onChange={(v) => set({ travailleur_handi: v })}
        />
        <Checkbox
          label="Agenda actif"
          checked={edit.agenda_actif}
          onChange={() => {}}
          disabled
        />
      </Section>
    </div>
  )
}

// --- Form helpers --------------------------------------------------------

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <h3 className="text-sm font-semibold text-c-ink mb-2 pb-1 border-b border-c-line-soft">
        {title}
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-2">{children}</div>
    </div>
  )
}

function Field({
  label,
  value,
  type = 'text',
  onChange,
  disabled,
}: {
  label: string
  value: string
  type?: string
  onChange: (v: string) => void
  disabled?: boolean
}) {
  return (
    <label className="flex flex-col text-xs gap-1">
      <span className="text-c-ink-soft">{label}</span>
      <input
        type={type}
        value={value || ''}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="px-2 py-1.5 border border-c-line rounded text-sm focus:border-c-brand focus:outline-none disabled:bg-c-bg-soft disabled:opacity-60"
      />
    </label>
  )
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: number
  options: { v: number; l: string }[]
  onChange: (v: number) => void
}) {
  return (
    <label className="flex flex-col text-xs gap-1">
      <span className="text-c-ink-soft">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        className="px-2 py-1.5 border border-c-line rounded text-sm bg-white focus:border-c-brand focus:outline-none"
      >
        {options.map((o) => (
          <option key={o.v} value={o.v}>
            {o.l}
          </option>
        ))}
      </select>
    </label>
  )
}

function SelectFieldStr({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: { v: string; l: string }[]
  onChange: (v: string) => void
}) {
  return (
    <label className="flex flex-col text-xs gap-1">
      <span className="text-c-ink-soft">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-2 py-1.5 border border-c-line rounded text-sm bg-white focus:border-c-brand focus:outline-none"
      >
        {options.map((o) => (
          <option key={o.v} value={o.v}>
            {o.l}
          </option>
        ))}
      </select>
    </label>
  )
}

function Checkbox({
  label,
  checked,
  onChange,
  disabled,
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
}) {
  return (
    <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="w-4 h-4"
      />
      <span className={disabled ? 'text-c-ink-faint' : 'text-c-ink'}>{label}</span>
    </label>
  )
}
