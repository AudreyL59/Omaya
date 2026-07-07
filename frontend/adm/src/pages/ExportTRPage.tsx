/**
 * Fen_ExportFicTR - Export pour Commande de Titres Restaurant.
 *
 * 2 modes de recherche :
 *   - Par entite  : societe + mois paiement
 *   - Par salarie : PersonnePicker
 *
 * Tableau resultat 16 colonnes + Btn Supprimer ligne + Btn Export CSV.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Loader2, Search, Users, User, Trash2, Download, Ticket,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PersonnePicker, { type SalarieItem } from '@/components/PersonnePicker'
import PageHeader from '@/components/PageHeader'

const API_BASE = '/api/adm'

interface SocieteFDV {
  id_ste: string
  raison_sociale: string
  rs_interne: string
}

interface ExportTRRow {
  id_salarie: string
  matricule: string
  civilite: string
  nom: string
  prenom: string
  date_naissance: string
  adresse_1: string
  adresse_2: string
  adresse_3: string
  code_postal: string
  ville: string
  email: string
  pays: string
  nombre_titres: string
  ref_pdist: string
  nom_employeur: string
  reference_chargement: string
}

const currentMoisPaie = (): string => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const shortDate = (iso: string): string =>
  !iso || iso.length < 10
    ? ''
    : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function ExportTRPage() {
  useDocumentTitle('Export commande TR')

  const [societes, setSocietes] = useState<SocieteFDV[]>([])
  const [idSte, setIdSte] = useState('')
  const [moisPaie, setMoisPaie] = useState(currentMoisPaie())

  const [salarie, setSalarie] = useState<SalarieItem | null>(null)
  const [showPicker, setShowPicker] = useState(false)

  const [lignes, setLignes] = useState<ExportTRRow[]>([])
  const [selectedIdx, setSelectedIdx] = useState<number>(-1)
  const [loading, setLoading] = useState(false)

  const loadSocietes = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/paies/fiches/societes-fdv`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      const d = await r.json()
      setSocietes(d.items || [])
    } catch { /* silent */ }
  }, [])

  useEffect(() => { void loadSocietes() }, [loadSocietes])

  const societeLib =
    societes.find((s) => s.id_ste === idSte)?.rs_interne || ''

  const doRechercheEntite = async () => {
    if (!idSte) {
      showToast('Choisis une entité', 'info')
      return
    }
    if (!moisPaie.match(/^\d{4}-\d{2}$/)) {
      showToast('Mois paiement invalide', 'info')
      return
    }
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/paies/export-tr/recherche-entite`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ id_ste: idSte, mois_paiement: moisPaie }),
        },
      )
      const d = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur', 'error')
        return
      }
      setLignes(d.lignes || [])
      setSelectedIdx(-1)
      showToast(d.message || '', 'success')
    } finally {
      setLoading(false)
    }
  }

  const doRechercheSalarie = async () => {
    if (!salarie) {
      showToast('Choisis un salarié', 'info')
      return
    }
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/paies/export-tr/recherche-salarie`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ id_salarie: salarie.id_salarie }),
        },
      )
      const d = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur', 'error')
        return
      }
      // Ajoute a la table existante (comme WinDev qui ajoute une ligne)
      setLignes((prev) => [...prev, ...(d.lignes || [])])
      showToast('Salarié ajouté', 'success')
    } finally {
      setLoading(false)
    }
  }

  const doSupprimer = () => {
    if (selectedIdx < 0) {
      showToast('Sélectionne une ligne', 'info')
      return
    }
    setLignes((prev) => prev.filter((_, i) => i !== selectedIdx))
    setSelectedIdx(-1)
  }

  const doExportCsv = async () => {
    if (lignes.length === 0) {
      showToast('Aucune ligne à exporter', 'info')
      return
    }
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/paies/export-tr/export-csv`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ lignes, lib_entite: societeLib }),
      })
      if (!r.ok) {
        showToast('Erreur export', 'error')
        return
      }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const disposition = r.headers.get('Content-Disposition') || ''
      const m = disposition.match(/filename="?([^";]+)"?/)
      const fic = m ? m[1] : 'Export_TR.csv'
      const a = document.createElement('a')
      a.href = url
      a.download = fic
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 30_000)
      showToast('CSV téléchargé', 'success')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-full mx-auto">
        <PageHeader
          icon={Ticket}
          title="Export des Salariés pour commande TR"
        />

        {/* Bloc actions */}
        <div className="bg-white rounded-lg shadow p-4 mb-4 space-y-3">
          {/* Ligne 1 : par entite */}
          <div className="flex items-center gap-4 flex-wrap">
            <label className="flex flex-col text-xs gap-1 min-w-[240px]">
              <span className="text-[#8B7355] font-medium">Entité</span>
              <select
                value={idSte}
                onChange={(e) => setIdSte(e.target.value)}
                className="px-2 py-1.5 border border-[#E5E0D5] rounded"
              >
                <option value="">Choisir une entité</option>
                {societes.map((s) => (
                  <option key={s.id_ste} value={s.id_ste}>
                    {s.rs_interne}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-xs gap-1">
              <span className="text-[#8B7355] font-medium">Mois Paiement MM-AAAA</span>
              <input
                type="month"
                value={moisPaie}
                onChange={(e) => setMoisPaie(e.target.value)}
                className="px-2 py-1.5 border border-[#E5E0D5] rounded"
              />
            </label>
            <button
              onClick={doRechercheEntite}
              disabled={loading || !idSte}
              className="ml-auto flex items-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white disabled:opacity-40 hover:bg-[#0F3438]"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Users className="w-4 h-4" />
              )}
              Lancer la recherche par entité
            </button>
          </div>

          {/* Ligne 2 : par salarie */}
          <div className="flex items-center gap-4">
            <button
              onClick={() => setShowPicker(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]"
            >
              <User className="w-4 h-4" />
              {salarie
                ? `${salarie.nom} ${salarie.prenom}`
                : 'Choisir le salarié'}
            </button>
            <button
              onClick={doRechercheSalarie}
              disabled={loading || !salarie}
              className="ml-auto flex items-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white disabled:opacity-40 hover:bg-[#0F3438]"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              Lancer la recherche par salarié
            </button>
          </div>

          {/* Ligne 3 : actions sur table */}
          <div className="flex items-center gap-2 border-t border-[#F0EDE5] pt-3">
            <button
              onClick={doSupprimer}
              disabled={selectedIdx < 0}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#B91C1C] text-[#B91C1C] hover:bg-red-50 disabled:opacity-40 disabled:hover:bg-transparent disabled:cursor-not-allowed"
            >
              <Trash2 className="w-4 h-4" />
              Supprimer la ligne
            </button>
            <span className="text-xs text-gray-500">
              {lignes.length} ligne(s)
              {selectedIdx >= 0 && ` - ligne ${selectedIdx + 1} sélectionnée`}
            </span>
            <button
              onClick={doExportCsv}
              disabled={loading || lignes.length === 0}
              className="ml-auto flex items-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white disabled:opacity-40 hover:bg-[#0F3438]"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          </div>
        </div>

        {/* Tableau vendeurs */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
            <table className="text-xs w-full">
              <thead className="sticky top-0 bg-[#17494E] text-white z-10">
                <tr>
                  {[
                    'MATRICULE', 'Civilité', 'NOM', 'PRÉNOM',
                    'DATE NAISS.', 'ADRESSE 1', 'ADRESSE 2', 'CP',
                    'VILLE', 'Email', 'Employeur',
                  ].map((h) => (
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
                    onClick={() => setSelectedIdx(i)}
                    className={`cursor-pointer border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${
                      selectedIdx === i ? 'bg-[#FFF5E0] ring-1 ring-[#8B7355]' : ''
                    }`}
                  >
                    <td className="py-1.5 px-2 font-mono">{r.matricule}</td>
                    <td className="py-1.5 px-2">{r.civilite}</td>
                    <td className="py-1.5 px-2 font-medium">{r.nom}</td>
                    <td className="py-1.5 px-2">{r.prenom}</td>
                    <td className="py-1.5 px-2 tabular-nums">
                      {shortDate(r.date_naissance)}
                    </td>
                    <td className="py-1.5 px-2 max-w-[220px] truncate" title={r.adresse_1}>
                      {r.adresse_1}
                    </td>
                    <td className="py-1.5 px-2 max-w-[160px] truncate" title={r.adresse_2}>
                      {r.adresse_2}
                    </td>
                    <td className="py-1.5 px-2 tabular-nums">{r.code_postal}</td>
                    <td className="py-1.5 px-2">{r.ville}</td>
                    <td className="py-1.5 px-2 max-w-[200px] truncate" title={r.email}>
                      {r.email}
                    </td>
                    <td className="py-1.5 px-2">{r.nom_employeur}</td>
                  </tr>
                ))}
                {lignes.length === 0 && (
                  <tr>
                    <td colSpan={11} className="py-8 text-center text-gray-400">
                      Aucun salarié - Lance une recherche
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {showPicker && (
        <PersonnePicker
          title="Choisir le salarié"
          onClose={() => setShowPicker(false)}
          onSelect={(s) => { setSalarie(s); setShowPicker(false) }}
        />
      )}
    </div>
  )
}
