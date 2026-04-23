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
} from 'lucide-react'
import { getToken } from '@/api'

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

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

const COLUMNS = [
  { key: 'partenaire', label: 'Part.', width: 'w-16' },
  { key: 'date_signature', label: 'Signature', width: 'w-28' },
  { key: 'num_bs', label: 'Num BS', width: 'w-32' },
  { key: 'lib_produit', label: 'Produit', width: 'w-48' },
  { key: 'type_prod', label: 'Type', width: 'w-28' },
  { key: 'vendeur', label: 'Vendeur', width: 'w-40' },
  { key: 'agence', label: 'Agence', width: 'w-32' },
  { key: 'equipe', label: 'Équipe', width: 'w-32' },
  { key: 'lib_type_etat', label: 'État', width: 'w-28' },
  { key: 'mois_p', label: 'Mois P', width: 'w-24' },
  { key: 'nb_points', label: 'Pts', width: 'w-16', num: true },
  { key: 'client_nom', label: 'Client', width: 'w-40' },
  { key: 'client_cp', label: 'CP', width: 'w-16' },
  { key: 'client_ville', label: 'Ville', width: 'w-32' },
] as const

export default function ProductionDetailPage() {
  const { id: idJob } = useParams<{ id: string }>()
  const [job, setJob] = useState<ProductionJob | null>(null)
  const [data, setData] = useState<ContratPage | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(100)
  const [sort, setSort] = useState<string>('-date_signature')
  const [partenaireFilter, setPartenaireFilter] = useState('')
  const [vendeurFilter, setVendeurFilter] = useState('')
  const [clientFilter, setClientFilter] = useState('')

  // Load job info
  useEffect(() => {
    if (!idJob) return
    fetch(`/api/vendeur/production/jobs/${idJob}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setJob)
      .catch(() => {})
  }, [idJob])

  // Load contrats page
  useEffect(() => {
    if (!idJob) return
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
              {data?.total?.toLocaleString('fr-FR') ?? '…'} contrats
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

      {/* Filtres */}
      <div className="mt-4 flex flex-wrap items-center gap-3">
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

      {/* Tableau */}
      <div className="mt-4 bg-white rounded-xl border border-gray-200 overflow-hidden">
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
                data.rows.map((r) => (
                  <tr key={`${r.partenaire}-${r.id_contrat}`} className="hover:bg-gray-50">
                    <td className="px-3 py-2 font-medium text-gray-900">{r.partenaire}</td>
                    <td className="px-3 py-2 text-gray-700 tabular-nums">
                      {r.date_signature}
                    </td>
                    <td className="px-3 py-2 text-gray-700 font-mono text-xs">
                      {r.num_bs}
                    </td>
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

        {/* Pagination */}
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
    </div>
  )
}
