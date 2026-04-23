import { useEffect, useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  FileDown,
  Loader2,
  Search,
  BarChart3,
  Users as UsersIcon,
  Table as TableIcon,
} from 'lucide-react'
import { getToken } from '@/api'

// --- Types -------------------------------------------------------

interface ContratRow {
  id_contrat: string
  partenaire: string
  num_bs: string
  date_signature: string
  date_saisie: string
  mois_p: string
  lib_produit: string
  type_prod: string
  id_type_etat: number
  lib_type_etat: string
  couleur_etat: string
  lib_etat: string
  lib_etat_vend: string
  id_salarie: string
  vendeur_nom: string
  vendeur_prenom: string
  agence: string
  equipe: string
  poste: string
  en_activite: boolean
  date_sortie: string
  id_client: string
  client_nom: string
  client_prenom: string
  client_adresse1: string
  client_cp: string
  client_ville: string
  client_mail: string
  client_mobile: string
  client_age: number
  nb_points: number
  notation: number
  notation_info: string
  info_interne: string
  info_partagee: string
}

interface ContratPage {
  total: number
  page: number
  page_size: number
  rows: ContratRow[]
}

interface ProductionJob {
  id_job: string
  titre: string
  statut: string
  nb_lignes: number
  duree_s: number
}

interface RepartPartenaireRow {
  partenaire: string
  couleur_hex: string
  brut: number
  temporaire: number
  envoye: number
  rejet: number
  resil: number
  payé: number
  decomm: number
  racc_activ_ko: number
  racc_active: number
}

interface VendeurStatRow {
  id_salarie: string
  nom: string
  prenom: string
  agence: string
  equipe: string
  poste: string
  en_activite: boolean
  date_sortie: string
  nb_contrats: number
  nb_paye: number
  nb_hors_rejet: number
  nb_points: number
  par_partenaire: Record<string, number>
}

interface JobStats {
  total_contrats: number
  total_paye: number
  total_points: number
  repart_partenaires: RepartPartenaireRow[]
  vendeurs: VendeurStatRow[]
}

type TabKey = 'contrats' | 'repart' | 'vendeurs'

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

// --- Page --------------------------------------------------------

export default function ProductionDetailPage() {
  const { id: idJob } = useParams<{ id: string }>()
  const [job, setJob] = useState<ProductionJob | null>(null)
  const [stats, setStats] = useState<JobStats | null>(null)
  const [tab, setTab] = useState<TabKey>('contrats')

  // Chargement job + stats (une seule fois)
  useEffect(() => {
    if (!idJob) return
    const headers = { Authorization: `Bearer ${getToken()}` }
    fetch(`/api/vendeur/production/jobs/${idJob}`, { headers })
      .then((r) => r.json())
      .then(setJob)
      .catch(() => {})
    fetch(`/api/vendeur/production/jobs/${idJob}/stats`, { headers })
      .then((r) => r.json())
      .then(setStats)
      .catch(() => {})
  }, [idJob])

  const downloadCsv = async () => {
    const r = await fetch(`/api/vendeur/production/jobs/${idJob}/export.csv`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `production-job-${idJob}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="p-6">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between gap-4"
      >
        <div className="flex items-center gap-3 min-w-0">
          <Link
            to="/production"
            className="p-2 text-gray-400 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-gray-900 truncate">
              {job?.titre || 'Extraction'}
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {stats ? stats.total_contrats.toLocaleString('fr-FR') : '…'} contrats
              {stats && stats.total_paye > 0 && (
                <> · {stats.total_paye.toLocaleString('fr-FR')} payés</>
              )}
            </p>
          </div>
        </div>
        <button
          onClick={downloadCsv}
          className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <FileDown className="w-4 h-4" />
          Export CSV
        </button>
      </motion.div>

      {/* Onglets */}
      <div className="mt-5 border-b border-gray-200 flex items-center gap-1">
        <TabButton
          icon={<TableIcon className="w-4 h-4" />}
          label="Contrats"
          active={tab === 'contrats'}
          onClick={() => setTab('contrats')}
        />
        <TabButton
          icon={<BarChart3 className="w-4 h-4" />}
          label="Répartition"
          active={tab === 'repart'}
          onClick={() => setTab('repart')}
        />
        <TabButton
          icon={<UsersIcon className="w-4 h-4" />}
          label={`Vendeurs${stats ? ` (${stats.vendeurs.length})` : ''}`}
          active={tab === 'vendeurs'}
          onClick={() => setTab('vendeurs')}
        />
      </div>

      <div className="mt-5">
        {tab === 'contrats' && <ContratsTable idJob={idJob!} />}
        {tab === 'repart' && <RepartTable stats={stats} />}
        {tab === 'vendeurs' && <VendeursTable stats={stats} />}
      </div>
    </div>
  )
}

function TabButton({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
        active
          ? 'border-gray-900 text-gray-900'
          : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      {icon}
      {label}
    </button>
  )
}

// --- Onglet Contrats ---------------------------------------------

const COLUMNS = [
  { key: 'partenaire', label: 'Part.' },
  { key: 'date_signature', label: 'Signature' },
  { key: 'num_bs', label: 'Num BS' },
  { key: 'lib_produit', label: 'Produit' },
  { key: 'type_prod', label: 'Type' },
  { key: 'vendeur', label: 'Vendeur' },
  { key: 'agence', label: 'Agence' },
  { key: 'equipe', label: 'Équipe' },
  { key: 'lib_type_etat', label: 'État' },
  { key: 'mois_p', label: 'Mois P' },
  { key: 'nb_points', label: 'Pts', num: true },
  { key: 'client_nom', label: 'Client' },
  { key: 'client_cp', label: 'CP' },
  { key: 'client_ville', label: 'Ville' },
] as const

function ContratsTable({ idJob }: { idJob: string }) {
  const [data, setData] = useState<ContratPage | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(100)
  const [sort, setSort] = useState<string>('-date_signature')
  const [partenaireFilter, setPartenaireFilter] = useState('')
  const [vendeurFilter, setVendeurFilter] = useState('')
  const [clientFilter, setClientFilter] = useState('')

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
      sort,
    })
    if (partenaireFilter) params.set('partenaire', partenaireFilter)
    if (vendeurFilter) params.set('vendeur', vendeurFilter)
    if (clientFilter) params.set('client', clientFilter)
    fetch(`/api/vendeur/production/jobs/${idJob}/contrats?${params}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [idJob, page, pageSize, sort, partenaireFilter, vendeurFilter, clientFilter])

  const totalPages = useMemo(() => {
    if (!data) return 1
    return Math.max(1, Math.ceil(data.total / pageSize))
  }, [data, pageSize])

  const partenairesUniques = useMemo(() => {
    if (!data) return []
    const s = new Set(data.rows.map((r) => r.partenaire))
    return Array.from(s).sort()
  }, [data])

  const toggleSort = (col: string) => {
    if (col === 'vendeur') col = 'vendeur_nom'
    if (sort === col) setSort(`-${col}`)
    else if (sort === `-${col}`) setSort(col)
    else setSort(col)
    setPage(1)
  }

  const sortKey = sort.startsWith('-') ? sort.slice(1) : sort
  const sortDesc = sort.startsWith('-')

  return (
    <>
      {/* Filtres */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        {partenairesUniques.length > 1 && (
          <select
            value={partenaireFilter}
            onChange={(e) => {
              setPartenaireFilter(e.target.value)
              setPage(1)
            }}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
          >
            <option value="">Tous partenaires</option>
            {partenairesUniques.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        )}
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            placeholder="Vendeur…"
            value={vendeurFilter}
            onChange={(e) => {
              setVendeurFilter(e.target.value)
              setPage(1)
            }}
            className="pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-300 w-48"
          />
        </div>
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            placeholder="Client…"
            value={clientFilter}
            onChange={(e) => {
              setClientFilter(e.target.value)
              setPage(1)
            }}
            className="pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-300 w-48"
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
              <tr>
                {COLUMNS.map((c) => (
                  <th
                    key={c.key}
                    onClick={() => toggleSort(c.key)}
                    className={`${(c as any).num ? 'text-right' : 'text-left'} px-3 py-2.5 font-medium cursor-pointer select-none whitespace-nowrap hover:bg-gray-100`}
                  >
                    <span className="inline-flex items-center gap-1">
                      {c.label}
                      {sortKey === (c.key === 'vendeur' ? 'vendeur_nom' : c.key) &&
                        (sortDesc ? (
                          <ChevronDown className="w-3 h-3" />
                        ) : (
                          <ChevronUp className="w-3 h-3" />
                        ))}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan={COLUMNS.length} className="text-center py-12">
                    <Loader2 className="w-5 h-5 text-gray-300 animate-spin mx-auto" />
                  </td>
                </tr>
              ) : !data || data.rows.length === 0 ? (
                <tr>
                  <td colSpan={COLUMNS.length} className="text-center py-12 text-gray-400">
                    Aucun contrat
                  </td>
                </tr>
              ) : (
                data.rows.map((r, idx) => (
                  <tr
                    key={`${r.partenaire}-${r.id_contrat}-${idx}`}
                    className="hover:bg-gray-50"
                  >
                    <td className="px-3 py-2 font-medium text-gray-900">{r.partenaire}</td>
                    <td className="px-3 py-2 text-gray-700 tabular-nums">{r.date_signature}</td>
                    <td className="px-3 py-2 text-gray-700 font-mono text-xs">{r.num_bs}</td>
                    <td className="px-3 py-2 text-gray-900">{r.lib_produit}</td>
                    <td className="px-3 py-2 text-gray-600">{r.type_prod}</td>
                    <td className="px-3 py-2 text-gray-900">
                      {r.vendeur_nom} {capitalize(r.vendeur_prenom)}
                    </td>
                    <td className="px-3 py-2 text-gray-600">{r.agence}</td>
                    <td className="px-3 py-2 text-gray-600">{r.equipe}</td>
                    <td className="px-3 py-2">
                      <span
                        className="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
                        style={{
                          color: r.couleur_etat || '#6b7280',
                          backgroundColor: `${r.couleur_etat}15`,
                          border: `1px solid ${r.couleur_etat}40`,
                        }}
                      >
                        {r.lib_etat_vend || r.lib_etat}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-600 tabular-nums">{r.mois_p}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{r.nb_points}</td>
                    <td className="px-3 py-2 text-gray-900">
                      {r.client_nom} {capitalize(r.client_prenom)}
                    </td>
                    <td className="px-3 py-2 text-gray-600">{r.client_cp}</td>
                    <td className="px-3 py-2 text-gray-600">{r.client_ville}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {data && data.total > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50 text-sm">
            <div className="text-gray-500">
              {(page - 1) * pageSize + 1} – {Math.min(page * pageSize, data.total)} sur{' '}
              {data.total.toLocaleString('fr-FR')}
            </div>
            <div className="flex items-center gap-2">
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(parseInt(e.target.value))
                  setPage(1)
                }}
                className="px-2 py-1 border border-gray-300 rounded text-sm"
              >
                {[50, 100, 200, 500].map((s) => (
                  <option key={s} value={s}>
                    {s}/page
                  </option>
                ))}
              </select>
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-2.5 py-1 border border-gray-300 rounded disabled:opacity-40 hover:bg-white"
              >
                Précédent
              </button>
              <span className="tabular-nums text-gray-700">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-2.5 py-1 border border-gray-300 rounded disabled:opacity-40 hover:bg-white"
              >
                Suivant
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  )
}

// --- Onglet Répartition ------------------------------------------

function RepartTable({ stats }: { stats: JobStats | null }) {
  if (!stats) {
    return (
      <div className="flex items-center justify-center py-16 bg-white rounded-xl border border-gray-200">
        <Loader2 className="w-5 h-5 text-gray-300 animate-spin" />
      </div>
    )
  }

  const rows = stats.repart_partenaires
  if (rows.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400 text-sm border border-dashed border-gray-300 rounded-xl">
        Aucune donnée.
      </div>
    )
  }

  // Total par colonne
  const totals = rows.reduce(
    (acc, r) => {
      acc.brut += r.brut
      acc.temporaire += r.temporaire
      acc.envoye += r.envoye
      acc.rejet += r.rejet
      acc.resil += r.resil
      acc.payé += r.payé
      acc.decomm += r.decomm
      acc.racc_activ_ko += r.racc_activ_ko
      acc.racc_active += r.racc_active
      return acc
    },
    {
      brut: 0, temporaire: 0, envoye: 0, rejet: 0, resil: 0,
      payé: 0, decomm: 0, racc_activ_ko: 0, racc_active: 0,
    },
  )

  const num = (n: number) => n.toLocaleString('fr-FR')

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-2.5 font-medium">Partenaire</th>
              <th className="text-right px-3 py-2.5 font-medium">Brut</th>
              <th className="text-right px-3 py-2.5 font-medium">Temp.</th>
              <th className="text-right px-3 py-2.5 font-medium">Envoyé</th>
              <th className="text-right px-3 py-2.5 font-medium">Rejet</th>
              <th className="text-right px-3 py-2.5 font-medium">Résil.</th>
              <th className="text-right px-3 py-2.5 font-medium">Payé</th>
              <th className="text-right px-3 py-2.5 font-medium">Decomm.</th>
              <th className="text-right px-3 py-2.5 font-medium">Racc/Act. KO</th>
              <th className="text-right px-3 py-2.5 font-medium">Raccordé/Activé</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((r) => (
              <tr key={r.partenaire} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium text-gray-900 flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: r.couleur_hex || '#9ca3af' }}
                  />
                  {r.partenaire}
                </td>
                <td className="px-3 py-2 text-right tabular-nums font-semibold text-gray-900">
                  {num(r.brut)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-600">{num(r.temporaire)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-600">{num(r.envoye)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-red-600">{num(r.rejet)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-orange-600">{num(r.resil)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-emerald-700 font-medium">
                  {num(r.payé)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-500">{num(r.decomm)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-red-500">{num(r.racc_activ_ko)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-emerald-600">
                  {num(r.racc_active)}
                </td>
              </tr>
            ))}
            <tr className="bg-gray-50 font-semibold border-t-2 border-gray-200">
              <td className="px-4 py-2 text-gray-900">TOTAL</td>
              <td className="px-3 py-2 text-right tabular-nums text-gray-900">{num(totals.brut)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-gray-700">{num(totals.temporaire)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-gray-700">{num(totals.envoye)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-red-700">{num(totals.rejet)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-orange-700">{num(totals.resil)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-emerald-800">{num(totals.payé)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-gray-600">{num(totals.decomm)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-red-600">{num(totals.racc_activ_ko)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-emerald-700">{num(totals.racc_active)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

// --- Onglet Vendeurs ---------------------------------------------

function VendeursTable({ stats }: { stats: JobStats | null }) {
  const [filter, setFilter] = useState('')

  if (!stats) {
    return (
      <div className="flex items-center justify-center py-16 bg-white rounded-xl border border-gray-200">
        <Loader2 className="w-5 h-5 text-gray-300 animate-spin" />
      </div>
    )
  }

  const filtered = stats.vendeurs.filter((v) => {
    if (!filter) return true
    const q = filter.toLowerCase()
    return (
      v.nom.toLowerCase().includes(q) ||
      v.prenom.toLowerCase().includes(q) ||
      v.agence.toLowerCase().includes(q) ||
      v.equipe.toLowerCase().includes(q)
    )
  })

  if (stats.vendeurs.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400 text-sm border border-dashed border-gray-300 rounded-xl">
        Aucun vendeur.
      </div>
    )
  }

  // Liste des partenaires uniques présents dans les stats vendeurs (pour les colonnes dynamiques)
  const partenaires = useMemo(() => {
    const s = new Set<string>()
    for (const v of stats.vendeurs) {
      Object.keys(v.par_partenaire).forEach((p) => s.add(p))
    }
    return Array.from(s).sort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stats.vendeurs])

  return (
    <>
      <div className="flex items-center gap-3 mb-4">
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            placeholder="Rechercher vendeur / agence / équipe…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-300 w-96"
          />
        </div>
        <span className="text-xs text-gray-500">
          {filtered.length} / {stats.vendeurs.length} vendeurs
        </span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
              <tr>
                <th className="text-left px-3 py-2.5 font-medium">Vendeur</th>
                <th className="text-left px-3 py-2.5 font-medium">Agence</th>
                <th className="text-left px-3 py-2.5 font-medium">Équipe</th>
                <th className="text-left px-3 py-2.5 font-medium">Poste</th>
                <th className="text-right px-3 py-2.5 font-medium">Contrats</th>
                <th className="text-right px-3 py-2.5 font-medium">Hors rejet</th>
                <th className="text-right px-3 py-2.5 font-medium">Payés</th>
                <th className="text-right px-3 py-2.5 font-medium">Points</th>
                {partenaires.map((p) => (
                  <th key={p} className="text-right px-3 py-2.5 font-medium">
                    {p}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.length === 0 ? (
                <tr>
                  <td
                    colSpan={8 + partenaires.length}
                    className="text-center py-12 text-gray-400"
                  >
                    Aucun résultat
                  </td>
                </tr>
              ) : (
                filtered.map((v) => (
                  <tr key={v.id_salarie} className="hover:bg-gray-50">
                    <td className="px-3 py-2 font-medium text-gray-900">
                      {v.nom} {capitalize(v.prenom)}
                      {!v.en_activite && (
                        <span className="ml-1.5 text-xs text-red-500">(inactif)</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-gray-600">{v.agence || '—'}</td>
                    <td className="px-3 py-2 text-gray-600">{v.equipe || '—'}</td>
                    <td className="px-3 py-2 text-gray-500 text-xs">{v.poste || '—'}</td>
                    <td className="px-3 py-2 text-right tabular-nums font-semibold text-gray-900">
                      {v.nb_contrats.toLocaleString('fr-FR')}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-700">
                      {v.nb_hors_rejet.toLocaleString('fr-FR')}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-emerald-700 font-medium">
                      {v.nb_paye.toLocaleString('fr-FR')}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-700">
                      {v.nb_points.toLocaleString('fr-FR')}
                    </td>
                    {partenaires.map((p) => (
                      <td
                        key={p}
                        className="px-3 py-2 text-right tabular-nums text-gray-500"
                      >
                        {v.par_partenaire[p] ? v.par_partenaire[p] : '—'}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
