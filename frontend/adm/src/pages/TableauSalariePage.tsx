/**
 * Fen_TableauSalarie - Tableau des salaries par equipe.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Loader2, Search, Download, Users, Check, X as XIcon,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'

const API_BASE = '/api/adm'

interface OrgaCombo {
  id_orga: string
  lib_orga: string
  lib_parent: string
}
interface VendeurRow {
  id_salarie: string
  nom: string
  prenom: string
  poste: string
  is_actif: boolean
  is_sortie: boolean
  date_entree: string
  type_sortie: string
  eq_terrain: string
  is_resp: boolean
  absences: string
  avance: number
}

const currentMoisPaie = (): string => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const shortDate = (iso: string): string =>
  !iso || iso.length < 10
    ? ''
    : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function TableauSalariePage() {
  useDocumentTitle('Tableau Salarié')

  const [orgas, setOrgas] = useState<OrgaCombo[]>([])
  const [idOrga, setIdOrga] = useState('')
  const [moisPaie, setMoisPaie] = useState(currentMoisPaie())
  const [lignes, setLignes] = useState<VendeurRow[]>([])
  const [loading, setLoading] = useState(false)

  const loadOrgas = useCallback(async () => {
    try {
      const r = await fetch(
        `${API_BASE}/paies/tableau-salarie/orgas`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      const d: OrgaCombo[] = await r.json()
      setOrgas(d || [])
    } catch { /* silent */ }
  }, [])
  useEffect(() => { void loadOrgas() }, [loadOrgas])

  const orgaSel = orgas.find((o) => o.id_orga === idOrga)

  const doRechercher = async () => {
    if (!idOrga) { showToast('Choisis une équipe', 'info'); return }
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/paies/tableau-salarie/rechercher`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id_orga: idOrga, mois_paiement: moisPaie,
          }),
        },
      )
      const d = await r.json()
      if (!d.ok) { showToast(d.message || 'Erreur', 'error'); return }
      setLignes(d.lignes || [])
      showToast(d.message || '', 'success')
    } finally { setLoading(false) }
  }

  const doExport = async () => {
    if (lignes.length === 0) {
      showToast('Aucune ligne', 'info'); return
    }
    if (!orgaSel) return
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/paies/tableau-salarie/export-xlsx`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id_orga: idOrga,
            lib_orga: `${orgaSel.lib_parent} > ${orgaSel.lib_orga}`,
            mois_paiement: moisPaie,
            lignes,
          }),
        },
      )
      if (!r.ok) { showToast('Erreur export', 'error'); return }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const disp = r.headers.get('Content-Disposition') || ''
      const m = disp.match(/filename="?([^";]+)"?/)
      const fic = m ? m[1] : 'tableau_salaries.xlsx'
      const a = document.createElement('a')
      a.href = url; a.download = fic; a.click()
      setTimeout(() => URL.revokeObjectURL(url), 30_000)
    } finally { setLoading(false) }
  }

  // Groupe les lignes par equipe pour affichage
  const groupes = (() => {
    const map = new Map<string, VendeurRow[]>()
    for (const l of lignes) {
      const g = map.get(l.eq_terrain) || []
      g.push(l)
      map.set(l.eq_terrain, g)
    }
    return Array.from(map.entries())
      .sort(([a], [b]) => a.localeCompare(b))
  })()

  const nbActifs = lignes.filter((l) => l.is_actif).length
  const nbSorties = lignes.filter((l) => l.is_sortie).length

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-full mx-auto">
        <PageHeader icon={Users} title="Tableau Salarié" />

        {/* Filtres */}
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <div className="flex items-end gap-3 flex-wrap">
            <label className="flex flex-col text-xs gap-1 min-w-[320px]">
              <span className="text-[#8B7355] font-medium">Équipe</span>
              <select value={idOrga} onChange={(e) => setIdOrga(e.target.value)}
                      className="px-2 py-1.5 border border-[#E5E0D5] rounded">
                <option value="">Choisir...</option>
                {orgas.map((o) => (
                  <option key={o.id_orga} value={o.id_orga}>
                    {o.lib_parent ? `${o.lib_parent} > ` : ''}{o.lib_orga}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-xs gap-1">
              <span className="text-[#8B7355] font-medium">Mois Paiement MM-AAAA</span>
              <input type="month" value={moisPaie}
                     onChange={(e) => setMoisPaie(e.target.value)}
                     className="px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <button
              onClick={doRechercher}
              disabled={loading || !idOrga}
              className="flex items-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white disabled:opacity-40 hover:bg-[#0F3438]"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              Lancer la recherche
            </button>
            <button
              onClick={doExport}
              disabled={loading || lignes.length === 0}
              title="Export XLSX"
              className="ml-auto p-2 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] disabled:opacity-40"
            >
              <Download className="w-4 h-4" />
            </button>
          </div>

          {lignes.length > 0 && (
            <div className="mt-3 pt-3 border-t border-[#F0EDE5] flex items-center gap-4 text-sm">
              <span className="text-[#8B7355]">Total :</span>
              <span className="font-semibold text-[#17494E] tabular-nums">{lignes.length}</span>
              <span className="text-green-700">Actifs : {nbActifs}</span>
              <span className="text-orange-700">Sortis : {nbSorties}</span>
            </div>
          )}
        </div>

        {/* Tableau grouped */}
        <div className="space-y-4">
          {groupes.map(([eq, rows], gi) => (
            <div key={gi} className="bg-white rounded-lg shadow p-4">
              <h3 className="text-sm font-semibold text-[#17494E] mb-2 border-b border-[#F0EDE5] pb-1">
                {eq} <span className="text-xs text-gray-500 font-normal">({rows.length})</span>
              </h3>
              <div className="overflow-x-auto">
                <table className="text-xs w-full">
                  <thead className="bg-[#F5F5F0]">
                    <tr>
                      <th className="py-1.5 px-2 text-left">Nom</th>
                      <th className="py-1.5 px-2 text-left">Prénom</th>
                      <th className="py-1.5 px-2 text-left">Poste</th>
                      <th className="py-1.5 px-2 text-center">Actif</th>
                      <th className="py-1.5 px-2 text-center">Sortie</th>
                      <th className="py-1.5 px-2 text-left">Date Entrée</th>
                      <th className="py-1.5 px-2 text-left">Motif Sortie</th>
                      <th className="py-1.5 px-2 text-left">Absences</th>
                      <th className="py-1.5 px-2 text-right">Avance €</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r, i) => (
                      <tr key={i} className="border-b border-[#F0EDE5] hover:bg-[#ECF1F2]">
                        <td className="py-1.5 px-2 font-medium">
                          {r.nom}
                          {r.is_resp && (
                            <span className="ml-1 text-[10px] px-1 rounded bg-[#17494E] text-white">
                              R
                            </span>
                          )}
                        </td>
                        <td className="py-1.5 px-2">{r.prenom}</td>
                        <td className="py-1.5 px-2">{r.poste}</td>
                        <td className="py-1.5 px-2 text-center">
                          {r.is_actif ? <Check className="w-3.5 h-3.5 inline text-green-700" /> :
                            <XIcon className="w-3.5 h-3.5 inline text-gray-300" />}
                        </td>
                        <td className="py-1.5 px-2 text-center">
                          {r.is_sortie ? <Check className="w-3.5 h-3.5 inline text-orange-700" /> : ''}
                        </td>
                        <td className="py-1.5 px-2 tabular-nums">{shortDate(r.date_entree)}</td>
                        <td className="py-1.5 px-2">{r.type_sortie}</td>
                        <td className="py-1.5 px-2 whitespace-pre-line max-w-[300px] text-[11px]"
                            title={r.absences}>
                          {r.absences}
                        </td>
                        <td className="py-1.5 px-2 text-right tabular-nums">
                          {r.avance > 0 ? r.avance.toFixed(2) : ''}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
          {lignes.length === 0 && (
            <div className="bg-white rounded-lg shadow py-12 text-center text-gray-400">
              Choisis une équipe et un mois puis lance la recherche
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
