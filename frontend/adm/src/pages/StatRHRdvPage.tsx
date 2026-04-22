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
} from 'lucide-react'
import { getToken } from '@/api'
import { useAuth } from '@/hooks/useAuth'
import PersonnePicker, { type SalarieItem } from '@/components/PersonnePicker'
import ExportButton from '@/components/ExportButton'
import { exportToCSV, csvDate } from '@/utils/csvExport'

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

type TabKey = 'resume' | 'listes'
type TypeRecherche = 'service' | 'personne'
type TypeDate = 'planif' | 'rdv'

interface RdvRow {
  id_cvtheque: string
  nom: string
  prenom: string
  gsm: string
  date_crea: string
  date_debut: string
  lib_categorie: string
  recruteur_nom: string
  op_crea_nom: string
  statut_lib: string
  presente: boolean
  retenu: boolean
  venu_jo: boolean
}

interface AggRow {
  id: string
  nom: string
  rdv: number
  presents: number
  retenus: number
  venus_jo: number
}

interface StatRdvResponse {
  rdv: RdvRow[]
  operateurs: AggRow[]
  recruteurs: AggRow[]
  non_statues: number
}

function toYmd(d: Date): string {
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
}

function formatShortDate(raw: string): string {
  if (!raw) return ''
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (iso) return `${iso[3]}/${iso[2]}/${iso[1]}`
  if (raw.length >= 8 && /^\d+$/.test(raw.slice(0, 8))) {
    return `${raw.slice(6, 8)}/${raw.slice(4, 6)}/${raw.slice(0, 4)}`
  }
  return raw
}

export default function StatRHRdvPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const hasDroitGr = (user?.droits || []).includes('StatsRHGr')

  const today = toYmd(new Date())
  const [typeRecherche, setTypeRecherche] = useState<TypeRecherche>(
    hasDroitGr ? 'service' : 'personne'
  )
  const [typeDate, setTypeDate] = useState<TypeDate>('planif')
  const [dateDu, setDateDu] = useState<string>(today)
  const [dateAu, setDateAu] = useState<string>(today)
  const [tab, setTab] = useState<TabKey>('resume')
  const [selectedPersonne, setSelectedPersonne] = useState<SalarieItem | null>(null)
  const [showPicker, setShowPicker] = useState(false)

  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<StatRdvResponse | null>(null)
  const [error, setError] = useState<string>('')

  // Libelle du bouton "Une personne" : si quelqu'un est selectionne, on affiche son prenom
  const labelPersonne = selectedPersonne
    ? capitalize(selectedPersonne.prenom)
    : 'Une personne ...'

  const onToggleType = (v: TypeRecherche) => {
    if (v === 'service') {
      setTypeRecherche('service')
      setSelectedPersonne(null)
    } else {
      // "Une personne" : ouvre le picker seulement si droit StatsRHGr
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
      type_date: typeDate,
      type_recherche: typeRecherche,
    })
    // Si une personne specifique est selectionnee, on la transmet au backend
    if (typeRecherche === 'personne' && selectedPersonne) {
      params.set('id_salarie', selectedPersonne.id_salarie)
    }
    fetch(`/api/adm/stat-rh/rdv?${params.toString()}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Erreur API (${r.status})`)
        return r.json()
      })
      .then((res: StatRdvResponse) => setData(res))
      .catch((e) => setError(e.message || 'Erreur'))
      .finally(() => setLoading(false))
  }

  return (
    <div className="p-8 max-w-7xl">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <button
          onClick={() => navigate('/stat-rh')}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 mb-3"
        >
          <ChevronLeft className="w-4 h-4" />
          Retour Stats RH
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Stats Prise de RDV</h1>
        <p className="text-gray-500 mt-1">
          Volumetrie des RDV planifies sur la periode.
        </p>
      </motion.div>

      {/* Filtres */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mt-6 flex flex-wrap items-center gap-3">
        {hasDroitGr && (
          <Toggle
            value={typeRecherche}
            options={[
              { v: 'service', label: 'Service complet', icon: <Users className="w-3.5 h-3.5" /> },
              { v: 'personne', label: labelPersonne, icon: <User className="w-3.5 h-3.5" /> },
            ]}
            onChange={(v) => onToggleType(v as TypeRecherche)}
          />
        )}

        <div className="h-6 w-px bg-gray-200" />

        <DateField label="Du" value={dateDu} onChange={setDateDu} />
        <DateField label="Au" value={dateAu} onChange={setDateAu} />

        <div className="h-6 w-px bg-gray-200" />

        <Toggle
          value={typeDate}
          options={[
            { v: 'planif', label: 'Date de planif' },
            { v: 'rdv', label: 'Date de RDV' },
          ]}
          onChange={(v) => setTypeDate(v as TypeDate)}
        />

        <div className="flex-1" />

        <button
          onClick={runCalcul}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50 shadow-sm"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          Demarrer le calcul
        </button>
      </div>

      {/* Compteur non statues */}
      {data && (
        <div className="mt-3 text-right text-sm text-gray-500">
          RDV non statue(s) :{' '}
          <span className="font-semibold text-gray-900 tabular-nums">
            {data.non_statues.toLocaleString('fr-FR')}
          </span>
        </div>
      )}

      {/* Erreur */}
      {error && (
        <div className="mt-3 flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 px-4 py-2.5 rounded-lg text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Onglets */}
      <div className="mt-4 border-b border-gray-200 flex gap-1">
        <TabButton active={tab === 'resume'} onClick={() => setTab('resume')} label="Resume" />
        <TabButton active={tab === 'listes'} onClick={() => setTab('listes')} label="Listes des RDV" />
      </div>

      {/* Contenu onglets */}
      <div className="mt-4">
        <AnimatePresence mode="wait">
          {tab === 'resume' && (
            <motion.div
              key="resume"
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              className="space-y-4"
            >
              <ResumeTable
                title="Par operateur (qui a pris le RDV)"
                rows={data?.operateurs || []}
                loading={loading}
              />
              <ResumeTable
                title="Par recruteur (qui mene l'entretien)"
                rows={data?.recruteurs || []}
                loading={loading}
              />
            </motion.div>
          )}
          {tab === 'listes' && (
            <motion.div
              key="listes"
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
            >
              <ListeTable rows={data?.rdv || []} loading={loading} />
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
      </AnimatePresence>
    </div>
  )
}

// --- Sous-composants -----------------------------------------------------

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
    <div className="inline-flex bg-gray-100 rounded-lg p-0.5">
      {options.map((o) => (
        <button
          key={o.v}
          onClick={() => onChange(o.v)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            value === o.v
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-500 hover:text-gray-700'
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
  // value au format YYYYMMDD, input HTML en YYYY-MM-DD
  const inputValue =
    value.length === 8
      ? `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`
      : value

  return (
    <label className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 rounded-lg text-sm">
      <CalendarIcon className="w-4 h-4 text-gray-400" />
      <span className="text-gray-500">{label}</span>
      <input
        type="date"
        value={inputValue}
        onChange={(e) => onChange(e.target.value.replace(/-/g, ''))}
        className="outline-none bg-transparent font-medium text-gray-900 w-32"
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
          ? 'border-gray-900 text-gray-900'
          : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      {label}
    </button>
  )
}

function ResumeTable({
  title,
  rows,
  loading,
}: {
  title: string
  rows: AggRow[]
  loading: boolean
}) {
  if (loading) return <TableLoader />

  const total = rows.reduce(
    (acc, r) => ({
      rdv: acc.rdv + r.rdv,
      presents: acc.presents + r.presents,
      retenus: acc.retenus + r.retenus,
      venus_jo: acc.venus_jo + r.venus_jo,
    }),
    { rdv: 0, presents: 0, retenus: 0, venus_jo: 0 }
  )

  // Formules WinDev :
  // PourcentPresent = NBPrésent / NBRDV
  // PourcentRetenu  = NBRetenu / NBPrésent
  // PourcentJO      = NBJO     / NBRetenu
  const pctPres = (r: { presents: number; rdv: number }) =>
    r.rdv > 0 ? ((r.presents / r.rdv) * 100).toFixed(1) : '0.0'
  const pctRet = (r: { retenus: number; presents: number }) =>
    r.presents > 0 ? ((r.retenus / r.presents) * 100).toFixed(1) : '0.0'
  const pctJO = (r: { venus_jo: number; retenus: number }) =>
    r.retenus > 0 ? ((r.venus_jo / r.retenus) * 100).toFixed(1) : '0.0'

  const handleExport = () => {
    exportToCSV(
      `stats-rdv-${title.toLowerCase().replace(/\s+/g, '-')}`,
      ['Nom', 'RDV', 'Presents', '% Pres', 'Retenus', '% Ret', 'Venus JO', '% JO'],
      [
        ...rows.map((r) => [
          r.nom || r.id,
          r.rdv,
          r.presents,
          pctPres(r),
          r.retenus,
          pctRet(r),
          r.venus_jo,
          pctJO(r),
        ]),
        [
          'TOTAL',
          total.rdv,
          total.presents,
          pctPres(total),
          total.retenus,
          pctRet(total),
          total.venus_jo,
          pctJO(total),
        ],
      ],
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
          {title}
        </span>
        {rows.length > 0 && <ExportButton onClick={handleExport} />}
      </div>
      {rows.length === 0 ? (
        <div className="text-center py-12 text-gray-400 text-sm italic">
          Pas de donnees. Demarre le calcul.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-white border-b border-gray-200">
              <tr>
                <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Nom</th>
                <th className="text-right py-2 px-3 text-xs font-medium text-gray-500 uppercase">RDV</th>
                <th className="text-right py-2 px-3 text-xs font-medium text-gray-500 uppercase">Presents</th>
                <th className="text-right py-2 px-3 text-xs font-medium text-gray-500 uppercase">Retenus</th>
                <th className="text-right py-2 px-3 text-xs font-medium text-gray-500 uppercase">Venu en JO</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                  <td className="py-2 px-3 font-medium text-gray-900">{r.nom || r.id}</td>
                  <td className="py-2 px-3 text-right tabular-nums">{r.rdv}</td>
                  <td className="py-2 px-3 text-right tabular-nums">
                    {r.presents}
                    <span className="text-gray-400 ml-1 text-xs">({pctPres(r)} %)</span>
                  </td>
                  <td className="py-2 px-3 text-right tabular-nums">
                    {r.retenus}
                    <span className="text-gray-400 ml-1 text-xs">({pctRet(r)} %)</span>
                  </td>
                  <td className="py-2 px-3 text-right tabular-nums">
                    {r.venus_jo}
                    <span className="text-gray-400 ml-1 text-xs">({pctJO(r)} %)</span>
                  </td>
                </tr>
              ))}
              <tr className="bg-gray-50 font-semibold">
                <td className="py-2 px-3 text-gray-900">TOTAL</td>
                <td className="py-2 px-3 text-right tabular-nums">{total.rdv}</td>
                <td className="py-2 px-3 text-right tabular-nums">
                  {total.presents}
                  <span className="text-gray-400 ml-1 text-xs">({pctPres(total)} %)</span>
                </td>
                <td className="py-2 px-3 text-right tabular-nums">
                  {total.retenus}
                  <span className="text-gray-400 ml-1 text-xs">({pctRet(total)} %)</span>
                </td>
                <td className="py-2 px-3 text-right tabular-nums">
                  {total.venus_jo}
                  <span className="text-gray-400 ml-1 text-xs">({pctJO(total)} %)</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function ListeTable({
  rows,
  loading,
}: {
  rows: RdvRow[]
  loading: boolean
}) {
  if (loading) return <TableLoader />
  if (rows.length === 0) return <EmptyState label="Pas de RDV sur cette periode." />

  const handleExport = () => {
    exportToCSV(
      'stats-rdv-listes',
      ['Nom', 'Prenom', 'Tel', 'Statut entretien', 'Date de debut', 'Recruteur', 'Planifie le', 'Ope_Planif'],
      rows.map((r) => [
        r.nom,
        r.prenom,
        r.gsm,
        r.statut_lib,
        csvDate(r.date_debut),
        r.recruteur_nom,
        csvDate(r.date_crea),
        r.op_crea_nom,
      ]),
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-end">
        <ExportButton onClick={handleExport} />
      </div>
      <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 sticky top-0">
            <tr>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Nom</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Tel</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Statut Entretien</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Date de debut</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Recruteur</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Planifie le</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Ope_Planif</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id_cvtheque + r.date_debut} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                <td className="py-2 px-3 font-medium text-gray-900">
                  {r.nom} <span className="font-normal text-gray-700">{r.prenom}</span>
                </td>
                <td className="py-2 px-3 text-gray-600">{r.gsm || '—'}</td>
                <td className="py-2 px-3 text-gray-600">{r.statut_lib || '—'}</td>
                <td className="py-2 px-3 text-gray-600">{formatShortDate(r.date_debut)}</td>
                <td className="py-2 px-3 text-gray-600">{r.recruteur_nom || '—'}</td>
                <td className="py-2 px-3 text-gray-600">{formatShortDate(r.date_crea)}</td>
                <td className="py-2 px-3 text-gray-600">{r.op_crea_nom || '—'}</td>
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
    <div className="flex items-center justify-center py-20 bg-white rounded-xl border border-gray-200">
      <Loader2 className="w-6 h-6 text-gray-300 animate-spin" />
    </div>
  )
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="text-center py-20 text-gray-400 text-sm italic bg-white rounded-xl border border-gray-200">
      {label}
    </div>
  )
}
