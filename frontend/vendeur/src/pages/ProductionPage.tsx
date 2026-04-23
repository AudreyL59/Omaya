import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
  Plus,
  Loader2,
  Clock,
  CheckCircle2,
  AlertCircle,
  Trash2,
  FileDown,
  FileText,
  RefreshCw,
} from 'lucide-react'
import { getToken } from '@/api'
import NouvelleExtractionModal from '@/components/NouvelleExtractionModal'

interface ProductionJob {
  id_job: string
  id_salarie_user: string
  date_crea: string
  date_debut_trait: string
  date_fin_trait: string
  statut: string
  progression_pct: number
  progression_msg: string
  nb_lignes: number
  duree_s: number
  path_resultat: string
  message_erreur: string
  titre: string
}

function formatDateHeure(raw: string): string {
  if (!raw) return ''
  // ISO ou WinDev
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/)
  if (iso) return `${iso[3]}/${iso[2]}/${iso[1]} ${iso[4]}:${iso[5]}`
  if (raw.length >= 12 && /^\d+$/.test(raw.slice(0, 12))) {
    return `${raw.slice(6, 8)}/${raw.slice(4, 6)}/${raw.slice(0, 4)} ${raw.slice(
      8,
      10,
    )}:${raw.slice(10, 12)}`
  }
  return raw
}

function formatDuree(s: number): string {
  if (!s) return '—'
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  const r = s % 60
  if (m < 60) return `${m}m ${r}s`
  const h = Math.floor(m / 60)
  const rm = m % 60
  return `${h}h ${rm}m`
}

function StatusBadge({ job }: { job: ProductionJob }) {
  const base =
    'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium'
  switch (job.statut) {
    case 'pending':
      return (
        <span className={`${base} bg-gray-100 text-gray-600`}>
          <Clock className="w-3 h-3" />
          En attente
        </span>
      )
    case 'running':
      return (
        <span className={`${base} bg-amber-50 text-amber-700 border border-amber-200`}>
          <Loader2 className="w-3 h-3 animate-spin" />
          En cours · {job.progression_pct}%
        </span>
      )
    case 'done':
      return (
        <span className={`${base} bg-emerald-50 text-emerald-700 border border-emerald-200`}>
          <CheckCircle2 className="w-3 h-3" />
          Terminé
        </span>
      )
    case 'error':
      return (
        <span className={`${base} bg-red-50 text-red-700 border border-red-200`}>
          <AlertCircle className="w-3 h-3" />
          Erreur
        </span>
      )
    default:
      return <span className={`${base} bg-gray-100 text-gray-600`}>{job.statut}</span>
  }
}

export default function ProductionPage() {
  const [jobs, setJobs] = useState<ProductionJob[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)

  const loadJobs = () => {
    fetch('/api/vendeur/production/jobs', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => setJobs(Array.isArray(d) ? d : []))
      .catch(() => setJobs([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadJobs()
  }, [])

  // Polling automatique s'il y a des jobs en cours/attente
  const hasActive = useMemo(
    () => jobs.some((j) => j.statut === 'pending' || j.statut === 'running'),
    [jobs],
  )
  useEffect(() => {
    if (!hasActive) return
    const id = setInterval(loadJobs, 3000)
    return () => clearInterval(id)
  }, [hasActive])

  const handleDelete = async (idJob: string) => {
    if (!window.confirm('Supprimer cette extraction ?')) return
    await fetch(`/api/vendeur/production/jobs/${idJob}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    loadJobs()
  }

  return (
    <div className="p-8">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Production</h1>
          <p className="text-gray-500 mt-1">
            Extractions de production · historique et résultats
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadJobs}
            title="Rafraîchir"
            className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Nouvelle extraction
          </button>
        </div>
      </motion.div>

      <div className="mt-6 bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="w-6 h-6 text-gray-300 animate-spin" />
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-16 text-gray-400 text-sm">
            Aucune extraction pour le moment. Clique sur "Nouvelle extraction" pour commencer.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
              <tr>
                <th className="text-left px-4 py-3 font-medium">Extraction</th>
                <th className="text-left px-4 py-3 font-medium">Statut</th>
                <th className="text-left px-4 py-3 font-medium">Créé le</th>
                <th className="text-right px-4 py-3 font-medium">Lignes</th>
                <th className="text-right px-4 py-3 font-medium">Durée</th>
                <th className="w-[120px]"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {jobs.map((job) => (
                <tr key={job.id_job} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{job.titre}</div>
                    {job.statut === 'running' && job.progression_msg && (
                      <div className="text-xs text-gray-500 mt-0.5">
                        {job.progression_msg}
                      </div>
                    )}
                    {job.statut === 'error' && job.message_erreur && (
                      <div className="text-xs text-red-600 mt-0.5 line-clamp-2">
                        {job.message_erreur.split('\n')[0]}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge job={job} />
                    {job.statut === 'running' && (
                      <div className="w-32 h-1 bg-gray-100 rounded-full mt-2 overflow-hidden">
                        <div
                          className="h-full bg-amber-500 transition-all"
                          style={{ width: `${job.progression_pct}%` }}
                        />
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {formatDateHeure(job.date_crea)}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-gray-900">
                    {job.statut === 'done' ? job.nb_lignes.toLocaleString('fr-FR') : '—'}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-gray-600">
                    {formatDuree(job.duree_s)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {job.statut === 'done' && (
                        <>
                          <Link
                            to={`/production/jobs/${job.id_job}`}
                            className="p-1.5 text-gray-400 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
                            title="Ouvrir"
                          >
                            <FileText className="w-4 h-4" />
                          </Link>
                          <a
                            href={`/api/vendeur/production/jobs/${job.id_job}/export.csv`}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={async (e) => {
                              e.preventDefault()
                              const r = await fetch(
                                `/api/vendeur/production/jobs/${job.id_job}/export.csv`,
                                { headers: { Authorization: `Bearer ${getToken()}` } },
                              )
                              const blob = await r.blob()
                              const url = URL.createObjectURL(blob)
                              const a = document.createElement('a')
                              a.href = url
                              a.download = `production-job-${job.id_job}.csv`
                              a.click()
                              URL.revokeObjectURL(url)
                            }}
                            className="p-1.5 text-gray-400 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
                            title="Télécharger CSV"
                          >
                            <FileDown className="w-4 h-4" />
                          </a>
                        </>
                      )}
                      <button
                        onClick={() => handleDelete(job.id_job)}
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                        title="Supprimer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <NouvelleExtractionModal
        open={showModal}
        onClose={() => setShowModal(false)}
        onCreated={() => {
          setShowModal(false)
          loadJobs()
        }}
      />
    </div>
  )
}
