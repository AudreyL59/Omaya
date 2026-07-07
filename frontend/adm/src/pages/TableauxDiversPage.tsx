/**
 * Fen_TableauDivers - Generation de tableaux divers.
 *
 * 3 actions :
 *   - Lister les vendeurs (embauches entre Du et Au)
 *   - Generer le fichier Valandre EXO (XLSX 6 colonnes, cases cochees)
 *   - Generer le fichier Comptable (XLSX 20 colonnes, tous salaries de la periode)
 */
import { useState } from 'react'
import {
  ArrowLeft, Loader2, Search, FileSpreadsheet, Send, Table2,
  CheckSquare, Square,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const API_BASE = '/api/adm'

interface DemandeRow {
  id_salarie: string
  choix: boolean
  nom: string
  prenom: string
  poste: string
  email: string
  agence: string
  equipe: string
  type_demande: string
}

const today = (): string => new Date().toISOString().slice(0, 10)
const firstOfMonth = (): string => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

export default function TableauxDiversPage() {
  useDocumentTitle('Génération tableaux divers')

  const [du, setDu] = useState(firstOfMonth())
  const [au, setAu] = useState(today())

  const [lignes, setLignes] = useState<DemandeRow[]>([])
  const [loading, setLoading] = useState(false)

  const doLister = async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/paies/tableaux-divers/lister`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ du, au }),
      })
      const d = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur', 'error')
        return
      }
      setLignes(d.lignes || [])
      showToast(d.message || '', 'success')
    } finally {
      setLoading(false)
    }
  }

  const toggleAll = () => {
    const allSelected = lignes.every((l) => l.choix)
    setLignes((prev) => prev.map((l) => ({ ...l, choix: !allSelected })))
  }

  const toggleLine = (i: number) => {
    setLignes((prev) =>
      prev.map((l, idx) => (idx === i ? { ...l, choix: !l.choix } : l)),
    )
  }

  const doDownload = async (
    endpoint: 'generer-valandre' | 'generer-comptable',
    body: object,
    successMsg: string,
  ) => {
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/paies/tableaux-divers/${endpoint}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: 'Erreur' }))
        showToast(err.detail || 'Erreur', 'error')
        return
      }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const disp = r.headers.get('Content-Disposition') || ''
      const m = disp.match(/filename="?([^";]+)"?/)
      const fic = m ? m[1] : 'export.xlsx'
      const a = document.createElement('a')
      a.href = url
      a.download = fic
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 30_000)
      showToast(successMsg, 'success')
    } finally {
      setLoading(false)
    }
  }

  const doGenererValandre = () => {
    const nbCoche = lignes.filter((l) => l.choix).length
    if (nbCoche === 0) {
      showToast('Coche au moins un vendeur', 'info')
      return
    }
    doDownload(
      'generer-valandre', { lignes },
      `XLSX Valandre téléchargé (${nbCoche} vendeurs)`,
    )
  }

  const doGenererComptable = () => {
    doDownload('generer-comptable', { du, au }, 'XLSX Comptable téléchargé')
  }

  const nbCoche = lignes.filter((l) => l.choix).length

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-full mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <Link to="/" className="p-2 rounded hover:bg-white/50" title="Retour">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <Table2 className="w-6 h-6 text-[#8B7355]" />
          <h1 className="text-2xl font-semibold text-[#8B7355]">
            Génération de tableaux divers
          </h1>
        </div>

        {/* Bloc actions */}
        <div className="bg-white rounded-lg shadow p-4 mb-4 space-y-3">
          <div className="flex items-end gap-4 flex-wrap">
            <label className="flex flex-col text-xs gap-1">
              <span className="text-[#8B7355] font-medium">Du</span>
              <input
                type="date"
                value={du}
                onChange={(e) => setDu(e.target.value)}
                className="px-2 py-1.5 border border-[#E5E0D5] rounded"
              />
            </label>
            <label className="flex flex-col text-xs gap-1">
              <span className="text-[#8B7355] font-medium">Au</span>
              <input
                type="date"
                value={au}
                onChange={(e) => setAu(e.target.value)}
                className="px-2 py-1.5 border border-[#E5E0D5] rounded"
              />
            </label>
            <button
              onClick={doLister}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white disabled:opacity-40 hover:bg-[#0F3438]"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              Lister les vendeurs
            </button>
          </div>

          <div className="flex items-center gap-2 border-t border-[#F0EDE5] pt-3">
            <button
              onClick={doGenererValandre}
              disabled={loading || lignes.length === 0}
              className="flex items-center gap-2 px-3 py-2 rounded bg-[#8B7355] text-white disabled:opacity-40 hover:bg-[#725e46]"
            >
              <FileSpreadsheet className="w-4 h-4" />
              Générer le fichier Valandre EXO
            </button>
            <button
              onClick={doGenererComptable}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-2 rounded bg-[#8B7355] text-white disabled:opacity-40 hover:bg-[#725e46]"
            >
              <FileSpreadsheet className="w-4 h-4" />
              Générer le fichier Comptable
            </button>
            <span className="ml-auto text-xs text-gray-500">
              {lignes.length} ligne(s) - {nbCoche} coché(s) pour Valandre
            </span>
          </div>
        </div>

        {/* Tableau vendeurs */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
            <table className="text-xs w-full">
              <thead className="sticky top-0 bg-[#17494E] text-white z-10">
                <tr>
                  <th className="py-2 px-2 text-center w-8">
                    <button
                      onClick={toggleAll}
                      className="p-0.5 hover:bg-white/10 rounded"
                      title="Tout cocher / décocher"
                    >
                      {lignes.length > 0 && lignes.every((l) => l.choix) ? (
                        <CheckSquare className="w-4 h-4" />
                      ) : (
                        <Square className="w-4 h-4" />
                      )}
                    </button>
                  </th>
                  {['NOM', 'PRÉNOM', 'POSTE', 'EMAIL', 'AGENCE', 'ÉQUIPE'].map((h) => (
                    <th key={h} className="py-2 px-2 text-left whitespace-nowrap font-semibold">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {lignes.map((r, i) => (
                  <tr
                    key={i}
                    className={`border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${
                      r.choix ? '' : 'opacity-50'
                    }`}
                  >
                    <td className="py-1.5 px-2 text-center">
                      <button
                        onClick={() => toggleLine(i)}
                        className="p-0.5 hover:bg-[#ECF1F2] rounded"
                      >
                        {r.choix ? (
                          <CheckSquare className="w-4 h-4 text-[#17494E]" />
                        ) : (
                          <Square className="w-4 h-4 text-gray-400" />
                        )}
                      </button>
                    </td>
                    <td className="py-1.5 px-2 font-medium">{r.nom}</td>
                    <td className="py-1.5 px-2">{r.prenom}</td>
                    <td className="py-1.5 px-2">{r.poste}</td>
                    <td className="py-1.5 px-2 truncate max-w-[220px]" title={r.email}>
                      {r.email}
                    </td>
                    <td className="py-1.5 px-2">{r.agence}</td>
                    <td className="py-1.5 px-2">{r.equipe}</td>
                  </tr>
                ))}
                {lignes.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-gray-400">
                      Aucune ligne - Lance une recherche
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-3 text-xs text-gray-500 italic">
          <Send className="w-3 h-3 inline mr-1" />
          Après téléchargement du fichier Valandre, envoie-le manuellement à
          <span className="font-mono"> caroline@editions-valandre.fr</span> (cc
          <span className="font-mono"> marie@exosphere.fr</span>,
          <span className="font-mono"> bo@exosphere.fr</span>).
        </div>
      </div>
    </div>
  )
}
