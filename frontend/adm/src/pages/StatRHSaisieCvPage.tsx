import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  ChevronLeft,
  Calendar as CalendarIcon,
  Users,
  User,
  Play,
  Loader2,
  AlertCircle,
  Eye,
  RotateCw,
} from 'lucide-react'
import { getToken } from '@/api'
import { useAuth } from '@/hooks/useAuth'
import PersonnePicker, { type SalarieItem } from '@/components/PersonnePicker'
import ExportButton from '@/components/ExportButton'
import StatSaisieCvDetailModal from '@/components/StatSaisieCvDetailModal'
import { exportToCSV, csvDate } from '@/utils/csvExport'

type TabKey = 'resume' | 'saisis' | 'traites'
type TypeRecherche = 'service' | 'personne'

interface CvSaisiRow {
  id_cvtheque: string
  ope_id: string
  ope_nom: string
  date_traitement: string
  est_reactivation: boolean
  nom_prenom: string
  commune: string
  tel: string
  statut_actuel: string
  id_source: number
  lib_source: string
  annonceur_coopteur: string
}

interface CvTraiteRow {
  id_cvtheque: string
  ope_id: string
  ope_nom: string
  date_traitement: string
  nom_prenom: string
  commune: string
  tel: string
  statut_actuel: string
  id_cv_statut: number
  date_saisie: string
  id_source: number
  lib_source: string
  annonceur_coopteur: string
}

interface OpeResumeRow {
  id_ope: string
  nom: string
  nb_cv_saisis: number
  nb_cv_traites: number
}

interface StatSaisieCvResponse {
  saisis: CvSaisiRow[]
  traites: CvTraiteRow[]
  resume: OpeResumeRow[]
}

function toYmd(d: Date): string {
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
}

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

export default function StatRHSaisieCvPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const hasDroitGr = (user?.droits || []).includes('StatsRHGr')

  const today = toYmd(new Date())
  const [typeRecherche, setTypeRecherche] = useState<TypeRecherche>('service')
  const [dateDu, setDateDu] = useState<string>(today)
  const [dateAu, setDateAu] = useState<string>(today)
  const [tab, setTab] = useState<TabKey>('resume')
  const [selectedPersonne, setSelectedPersonne] = useState<SalarieItem | null>(null)
  const [showPicker, setShowPicker] = useState(false)

  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<StatSaisieCvResponse | null>(null)
  const [error, setError] = useState<string>('')
  const [detail, setDetail] = useState<{ title: string; opeId: string | null } | null>(null)

  const labelPersonne = selectedPersonne
    ? capitalize(selectedPersonne.prenom)
    : 'Une personne ...'

  const onToggleType = (v: TypeRecherche) => {
    if (v === 'service') {
      setTypeRecherche('service')
      setSelectedPersonne(null)
    } else {
      if (hasDroitGr) {
        setShowPicker(true)
      } else {
        setTypeRecherche('personne')
        setSelectedPersonne(null)
      }
    }
  }

  const runCalcul = () => {
    setError('')
    setLoading(true)
    const params = new URLSearchParams({
      date_du: dateDu,
      date_au: dateAu,
      type_recherche: typeRecherche,
    })
    if (typeRecherche === 'personne' && selectedPersonne) {
      params.set('id_salarie', selectedPersonne.id_salarie)
    }
    fetch(`/api/adm/stat-rh/saisie-cv?${params.toString()}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Erreur API (${r.status})`)
        return r.json()
      })
      .then((res: StatSaisieCvResponse) => setData(res))
      .catch((e) => setError(e.message || 'Erreur'))
      .finally(() => setLoading(false))
  }

  return (
    <div className="p-8">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <button
          onClick={() => navigate('/stat-rh')}
          className="flex items-center gap-1.5 text-sm text-[#A68D8A] hover:text-[#4E1D17] mb-3"
        >
          <ChevronLeft className="w-4 h-4" />
          Retour Stats RH
        </button>
        <h1 className="text-2xl font-bold text-[#4E1D17]">
          Saisie &amp; traitement des CV
        </h1>
        <p className="text-[#A68D8A] mt-1">
          Volumetrie des CV saisis et traites sur la periode.
        </p>
      </motion.div>

      {/* Filtres */}
      <div className="bg-white rounded-[10px] border border-[#E5DDDC] p-4 mt-6 flex flex-wrap items-center gap-3">
        {hasDroitGr && (
          <Toggle
            value={typeRecherche}
            options={[
              {
                v: 'service',
                label: 'Service complet',
                icon: <Users className="w-3.5 h-3.5" />,
              },
              {
                v: 'personne',
                label: labelPersonne,
                icon: <User className="w-3.5 h-3.5" />,
              },
            ]}
            onChange={(v) => onToggleType(v as TypeRecherche)}
          />
        )}

        <div className="h-6 w-px bg-[#E5DDDC]" />

        <DateField label="Du" value={dateDu} onChange={setDateDu} />
        <DateField label="Au" value={dateAu} onChange={setDateAu} />

        <div className="flex-1" />

        <button
          onClick={runCalcul}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-[#17494E] text-white rounded-lg text-sm font-medium hover:bg-[#17494E]/90 disabled:opacity-50 shadow-sm"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          Demarrer le calcul
        </button>
      </div>

      {/* Erreur */}
      {error && (
        <div className="mt-3 flex items-center gap-2 bg-red-50 border border-red-200 text-[#993636] px-4 py-2.5 rounded-lg text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Onglets */}
      <div className="mt-4 border-b border-[#E5DDDC] flex gap-1">
        <TabButton
          active={tab === 'resume'}
          onClick={() => setTab('resume')}
          label="Resume"
        />
        <TabButton
          active={tab === 'saisis'}
          onClick={() => setTab('saisis')}
          label={`CV Saisis${data ? ` (${data.saisis.length})` : ''}`}
        />
        <TabButton
          active={tab === 'traites'}
          onClick={() => setTab('traites')}
          label={`CV Traites${data ? ` (${data.traites.length})` : ''}`}
        />
      </div>

      {/* Contenu */}
      <div className="mt-4">
        <AnimatePresence mode="wait">
          {tab === 'resume' && (
            <motion.div
              key="resume"
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
            >
              <ResumeTable
                rows={data?.resume || []}
                loading={loading}
                onDetail={(r) =>
                  setDetail({ title: r.nom, opeId: r.id_ope })
                }
                onDetailTotal={() =>
                  setDetail({ title: 'Total', opeId: null })
                }
              />
            </motion.div>
          )}
          {tab === 'saisis' && (
            <motion.div
              key="saisis"
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
            >
              <SaisisTable rows={data?.saisis || []} loading={loading} />
            </motion.div>
          )}
          {tab === 'traites' && (
            <motion.div
              key="traites"
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
            >
              <TraitesTable rows={data?.traites || []} loading={loading} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {showPicker && (
          <PersonnePicker
            title="Choisir un operateur"
            onClose={() => setShowPicker(false)}
            onSelect={(s) => {
              setSelectedPersonne(s)
              setTypeRecherche('personne')
              setShowPicker(false)
            }}
          />
        )}
        {detail && data && (
          <StatSaisieCvDetailModal
            title={detail.title}
            opeId={detail.opeId}
            saisis={data.saisis}
            traites={data.traites}
            onClose={() => setDetail(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// --- Sous-composants ------------------------------------------------------

function Toggle<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: { v: T; label: string; icon?: React.ReactNode }[]
  onChange: (v: T) => void
}) {
  return (
    <div className="inline-flex bg-[#EFE9E7] rounded-lg p-0.5">
      {options.map((o) => (
        <button
          key={o.v}
          onClick={() => onChange(o.v)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            value === o.v
              ? 'bg-white text-[#17494E] shadow-sm'
              : 'text-[#A68D8A] hover:text-[#4E1D17]'
          }`}
        >
          {o.icon}
          {o.label}
        </button>
      ))}
    </div>
  )
}

function DateField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (v: string) => void
}) {
  const inputValue =
    value.length === 8
      ? `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`
      : value
  return (
    <label className="flex items-center gap-2 px-3 py-1.5 border border-[#E5DDDC] rounded-lg text-sm">
      <CalendarIcon className="w-4 h-4 text-[#A68D8A]/80" />
      <span className="text-[#A68D8A]">{label}</span>
      <input
        type="date"
        value={inputValue}
        onChange={(e) => onChange(e.target.value.replace(/-/g, ''))}
        className="outline-none bg-transparent font-medium text-[#4E1D17] w-32"
      />
    </label>
  )
}

function TabButton({
  active,
  onClick,
  label,
}: {
  active: boolean
  onClick: () => void
  label: string
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
        active
          ? 'border-[#17494E] text-[#4E1D17]'
          : 'border-transparent text-[#A68D8A] hover:text-[#4E1D17]'
      }`}
    >
      {label}
    </button>
  )
}

function ResumeTable({
  rows,
  loading,
  onDetail,
  onDetailTotal,
}: {
  rows: OpeResumeRow[]
  loading: boolean
  onDetail: (r: OpeResumeRow) => void
  onDetailTotal: () => void
}) {
  if (loading) return <TableLoader />
  if (rows.length === 0)
    return <EmptyState label="Pas de donnees. Demarre le calcul." />

  const total = rows.reduce(
    (acc, r) => ({
      saisis: acc.saisis + r.nb_cv_saisis,
      traites: acc.traites + r.nb_cv_traites,
    }),
    { saisis: 0, traites: 0 }
  )

  const handleExport = () => {
    exportToCSV(
      'stats-saisie-cv-resume',
      ['Operateur', 'CV Saisis', 'CV Traites'],
      [
        ...rows.map((r) => [r.nom, r.nb_cv_saisis, r.nb_cv_traites]),
        ['TOTAL', total.saisis, total.traites],
      ]
    )
  }

  return (
    <div className="bg-white rounded-[10px] border border-[#E5DDDC] overflow-hidden">
      <div className="px-4 py-2 bg-white border-b border-[#E5DDDC] flex items-center justify-end">
        <ExportButton onClick={handleExport} />
      </div>
      <table className="w-full text-sm">
        <thead className="bg-white border-b border-[#E5DDDC]">
          <tr>
            <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">
              Operateur
            </th>
            <th className="text-right py-2 px-3 text-xs font-medium text-blue-600 uppercase">
              CV Saisis
            </th>
            <th className="text-right py-2 px-3 text-xs font-medium text-[#17494E] uppercase">
              CV Traites
            </th>
            <th className="w-12 py-2 px-2 text-xs font-medium text-[#A68D8A] uppercase text-center">
              Detail
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.id_ope}
              className="border-b border-[#E5DDDC] last:border-0 hover:bg-[#EFE9E7]"
            >
              <td className="py-2 px-3 font-medium text-[#4E1D17]">{r.nom}</td>
              <td className="py-2 px-3 text-right tabular-nums text-blue-700">
                {r.nb_cv_saisis}
              </td>
              <td className="py-2 px-3 text-right tabular-nums text-[#17494E]">
                {r.nb_cv_traites}
              </td>
              <td className="py-1 px-2 text-center">
                <button
                  onClick={() => onDetail(r)}
                  title={`Detail ${r.nom}`}
                  className="p-1.5 rounded-md text-[#A68D8A]/80 hover:text-[#4E1D17] hover:bg-white border border-transparent hover:border-[#E5DDDC] transition-colors"
                >
                  <Eye className="w-3.5 h-3.5" />
                </button>
              </td>
            </tr>
          ))}
          <tr className="bg-white font-semibold border-t-2 border-[#E5DDDC]">
            <td className="py-2 px-3 text-[#4E1D17]">TOTAL</td>
            <td className="py-2 px-3 text-right tabular-nums">{total.saisis}</td>
            <td className="py-2 px-3 text-right tabular-nums">{total.traites}</td>
            <td className="py-1 px-2 text-center">
              <button
                onClick={onDetailTotal}
                title="Detail Total"
                className="p-1.5 rounded-md text-[#A68D8A]/80 hover:text-[#4E1D17] hover:bg-white border border-transparent hover:border-[#E5DDDC] transition-colors"
              >
                <Eye className="w-3.5 h-3.5" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

function SaisisTable({
  rows,
  loading,
}: {
  rows: CvSaisiRow[]
  loading: boolean
}) {
  if (loading) return <TableLoader />
  if (rows.length === 0)
    return <EmptyState label="Pas de CV saisi sur cette periode." />

  const handleExport = () => {
    exportToCSV(
      'stats-saisie-cv-saisis',
      [
        'Ope saisie',
        'Date saisie',
        'Reactivation',
        'Candidat',
        'Commune',
        'Tel',
        'Statut actuel',
        'Source',
        'Annonceur/Coopteur',
      ],
      rows.map((r) => [
        r.ope_nom,
        csvDate(r.date_traitement),
        r.est_reactivation,
        r.nom_prenom,
        r.commune,
        r.tel,
        r.statut_actuel,
        r.lib_source,
        r.annonceur_coopteur,
      ])
    )
  }

  return (
    <div className="bg-white rounded-[10px] border border-[#E5DDDC] overflow-hidden">
      <div className="px-4 py-2 bg-white border-b border-[#E5DDDC] flex items-center justify-end">
        <ExportButton onClick={handleExport} />
      </div>
      <div className="overflow-x-auto max-h-[calc(100vh-400px)] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-white border-b border-[#E5DDDC] sticky top-0">
            <tr>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase whitespace-nowrap min-w-[160px]">
                Ope saisie
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase whitespace-nowrap">
                Date saisie
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">
                Candidat
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">
                Commune
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">
                Tel
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">
                Statut actuel
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">
                Source
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">
                Annonceur/Coopteur
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={`${r.id_cvtheque}-${i}`}
                className="border-b border-[#E5DDDC] last:border-0 hover:bg-[#EFE9E7]"
              >
                <td className="py-2 px-3 text-[#4E1D17]/80 whitespace-nowrap">{r.ope_nom}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80 whitespace-nowrap">
                  {csvDate(r.date_traitement)}
                  {r.est_reactivation && (
                    <RotateCw
                      className="inline w-3 h-3 ml-1 text-amber-500"
                      aria-label="Reactivation"
                    />
                  )}
                </td>
                <td className="py-2 px-3 font-medium text-[#4E1D17] truncate max-w-xs">
                  {r.nom_prenom}
                </td>
                <td className="py-2 px-3 text-[#4E1D17]/80 truncate max-w-xs">{r.commune}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{r.tel}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{r.statut_actuel || '—'}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{r.lib_source}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80 truncate max-w-xs">
                  {r.annonceur_coopteur || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function TraitesTable({
  rows,
  loading,
}: {
  rows: CvTraiteRow[]
  loading: boolean
}) {
  if (loading) return <TableLoader />
  if (rows.length === 0)
    return <EmptyState label="Pas de CV traite sur cette periode." />

  const handleExport = () => {
    exportToCSV(
      'stats-saisie-cv-traites',
      [
        'Ope traitement',
        'Date traitement',
        'Candidat',
        'Commune',
        'Tel',
        'Statut actuel',
        'Date de saisie',
      ],
      rows.map((r) => [
        r.ope_nom,
        csvDate(r.date_traitement),
        r.nom_prenom,
        r.commune,
        r.tel,
        r.statut_actuel,
        csvDate(r.date_saisie),
      ])
    )
  }

  return (
    <div className="bg-white rounded-[10px] border border-[#E5DDDC] overflow-hidden">
      <div className="px-4 py-2 bg-white border-b border-[#E5DDDC] flex items-center justify-end">
        <ExportButton onClick={handleExport} />
      </div>
      <div className="overflow-x-auto max-h-[calc(100vh-400px)] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-white border-b border-[#E5DDDC] sticky top-0">
            <tr>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase whitespace-nowrap min-w-[160px]">
                Ope traitement
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase whitespace-nowrap">
                Date traitement
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">
                Candidat
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">
                Commune
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">
                Tel
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">
                Statut actuel
              </th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">
                Date saisie
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={`${r.id_cvtheque}-${i}`}
                className="border-b border-[#E5DDDC] last:border-0 hover:bg-[#EFE9E7]"
              >
                <td className="py-2 px-3 text-[#4E1D17]/80 whitespace-nowrap">{r.ope_nom}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80 whitespace-nowrap">
                  {csvDate(r.date_traitement)}
                </td>
                <td className="py-2 px-3 font-medium text-[#4E1D17] truncate max-w-xs">
                  {r.nom_prenom}
                </td>
                <td className="py-2 px-3 text-[#4E1D17]/80 truncate max-w-xs">{r.commune}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{r.tel}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{r.statut_actuel || '—'}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80 whitespace-nowrap">
                  {csvDate(r.date_saisie)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function TableLoader() {
  return (
    <div className="flex items-center justify-center py-20 bg-white rounded-[10px] border border-[#E5DDDC]">
      <Loader2 className="w-6 h-6 text-[#E5DDDC] animate-spin" />
    </div>
  )
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="text-center py-20 text-[#A68D8A]/80 text-sm italic bg-white rounded-[10px] border border-[#E5DDDC]">
      {label}
    </div>
  )
}
