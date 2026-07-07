/**
 * Fen_GestionPodium - Gestion des Podiums.
 *
 * 3 onglets :
 *   1. Podiums Vendeurs (recherche + score visible + calcul + XLSX)
 *   2. Paramètres (CRUD PodiumType + PodiumTypePart)
 *   3. Année Podium (valider année)
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Loader2, Search, Save, Download, Calculator,
  Plus, Pencil, Trash2, Trophy, X, Check,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'

const API_BASE = '/api/adm'

type Tab = 'vendeurs' | 'params' | 'annee'

interface ComboItem { id: string; lib: string }
interface PodiumType {
  id_podium_type: string
  lib_podium_type: string
  lib_court: string
  prod_groupe: boolean
  qualite: boolean
  espoir: boolean
  is_actif: boolean
  ordre_affichage: number
}
interface PodiumTypePart {
  id_podium_type_part: string
  id_podium_type: string
  famille: string
  sous_fam: string
  prefixe_bdd: string
  type_prod: string
  option_vente: string
  jour_cial_deb: number
  jour_cial_fin: number
}
interface VendeurRow {
  id_salarie: string
  nom: string
  date_anciennete: string
  id_equipe: string
  equipe_lib: string
  valeur: number
  brut: number
  paye: number
  taux: number
  visible: boolean
}
interface RechercherResult {
  ok: boolean
  id_podium_mois: string
  score_visible: boolean
  is_qualite: boolean
  is_prod_groupe: boolean
  lignes: VendeurRow[]
  message: string
}

const currentYear = new Date().getFullYear()
const currentMonth = new Date().getMonth() + 1

const shortDate = (iso: string): string =>
  !iso || iso.length < 10
    ? ''
    : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

// ---------------------------------------------------------------------

export default function GestionPodiumPage() {
  useDocumentTitle('Gestion des Podiums')
  const [tab, setTab] = useState<Tab>('vendeurs')

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-full mx-auto">
        <PageHeader icon={Trophy} title="Gestion des Podiums" />

        {/* Onglets */}
        <div className="flex border-b border-[#E5E0D5] mb-4">
          {[
            { key: 'vendeurs' as Tab, label: 'Podiums Vendeurs' },
            { key: 'params' as Tab, label: 'Paramètres' },
            { key: 'annee' as Tab, label: 'Année Podium' },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 ${
                tab === t.key
                  ? 'border-[#17494E] text-[#17494E]'
                  : 'border-transparent text-gray-500 hover:text-[#17494E]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'vendeurs' && <OngletVendeurs />}
        {tab === 'params' && <OngletParametres />}
        {tab === 'annee' && <OngletAnnee />}
      </div>
    </div>
  )
}

// =====================================================================
// Onglet 1 - Podiums Vendeurs
// =====================================================================

function OngletVendeurs() {
  const [types, setTypes] = useState<ComboItem[]>([])
  const [distribs, setDistribs] = useState<ComboItem[]>([])
  const [idType, setIdType] = useState('')
  const [mois, setMois] = useState(currentMonth)
  const [annee, setAnnee] = useState(currentYear)
  const [isDistrib, setIsDistrib] = useState(false)
  const [idDistrib, setIdDistrib] = useState('')

  const [scoreVisible, setScoreVisible] = useState(false)
  const [idPodiumMois, setIdPodiumMois] = useState('')
  const [isQualite, setIsQualite] = useState(false)
  const [lignes, setLignes] = useState<VendeurRow[]>([])
  const [loading, setLoading] = useState(false)

  const [du, setDu] = useState<string>(() => {
    const d = new Date(); d.setDate(1)
    return d.toISOString().slice(0, 10)
  })
  const [au, setAu] = useState<string>(() => new Date().toISOString().slice(0, 10))

  const load = useCallback(async () => {
    try {
      const t = await fetch(`${API_BASE}/comm/podium/combos/types`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) => r.json())
      setTypes(t.items || [])
      const d = await fetch(`${API_BASE}/comm/podium/combos/distributeurs`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) => r.json())
      setDistribs(d.items || [])
    } catch { /* silent */ }
  }, [])
  useEffect(() => { void load() }, [load])

  const doRechercher = async () => {
    if (!idType) { showToast('Choisis un type', 'info'); return }
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/comm/podium/rechercher`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_podium_type: idType, mois, annee,
          is_distrib: isDistrib,
          id_distrib: isDistrib ? idDistrib : '',
        }),
      })
      const d: RechercherResult = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur', 'error')
        return
      }
      setLignes(d.lignes || [])
      setIdPodiumMois(d.id_podium_mois)
      setScoreVisible(d.score_visible)
      setIsQualite(d.is_qualite)
      showToast(d.message || '', 'success')
    } finally { setLoading(false) }
  }

  const doSaveScoreVisible = async () => {
    if (!idPodiumMois) return
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/comm/podium/score-visible`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_podium_mois: idPodiumMois,
          score_visible: scoreVisible,
        }),
      })
      const d = await r.json()
      if (d.ok) showToast('Score enregistré', 'success')
    } finally { setLoading(false) }
  }

  const doTelecharger = async () => {
    if (lignes.length === 0) { showToast('Aucune ligne', 'info'); return }
    setLoading(true)
    try {
      const libPodium = types.find((t) => t.id === idType)?.lib || 'podium'
      const r = await fetch(`${API_BASE}/comm/podium/telecharger-xlsx`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_podium_type: idType, mois, annee,
          is_distrib: isDistrib, id_distrib: isDistrib ? idDistrib : '',
          lignes, lib_podium: libPodium,
        }),
      })
      if (!r.ok) { showToast('Erreur export', 'error'); return }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const disp = r.headers.get('Content-Disposition') || ''
      const m = disp.match(/filename="?([^";]+)"?/)
      const fic = m ? m[1] : 'podium.xlsx'
      const a = document.createElement('a')
      a.href = url; a.download = fic; a.click()
      setTimeout(() => URL.revokeObjectURL(url), 30_000)
    } finally { setLoading(false) }
  }

  const doCalcul = async () => {
    if (!await showConfirm({
      title: 'Recalculer les podiums',
      message: `Recalculer les podiums entre ${shortDate(du)} et ${shortDate(au)} +7j ?`,
    })) return
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/comm/podium/calcul`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ du, au }),
      })
      const d = await r.json()
      if (!d.ok) { showToast(d.message || 'Erreur', 'error'); return }
      showToast(d.message || 'Calcul terminé', 'success')
    } finally { setLoading(false) }
  }

  return (
    <div className="space-y-4">
      {/* Filtres */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-end gap-3 flex-wrap">
          <label className="flex flex-col text-xs gap-1 min-w-[220px]">
            <span className="text-[#8B7355] font-medium">Type Podium</span>
            <select value={idType} onChange={(e) => setIdType(e.target.value)}
                    className="px-2 py-1.5 border border-[#E5E0D5] rounded">
              <option value="">Choisir...</option>
              {types.map((t) => (
                <option key={t.id} value={t.id}>{t.lib}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col text-xs gap-1">
            <span className="text-[#8B7355] font-medium">Mois</span>
            <input type="number" min={1} max={12}
                   value={mois}
                   onChange={(e) => setMois(Number(e.target.value))}
                   className="px-2 py-1.5 border border-[#E5E0D5] rounded w-20" />
          </label>
          <label className="flex flex-col text-xs gap-1">
            <span className="text-[#8B7355] font-medium">Année</span>
            <input type="number" min={2020} max={2100}
                   value={annee}
                   onChange={(e) => setAnnee(Number(e.target.value))}
                   className="px-2 py-1.5 border border-[#E5E0D5] rounded w-24" />
          </label>
          <div className="flex gap-1 rounded overflow-hidden border border-[#E5E0D5]">
            <button
              onClick={() => setIsDistrib(false)}
              className={`px-3 py-1.5 text-sm ${
                !isDistrib ? 'bg-[#17494E] text-white' : 'bg-white text-[#17494E]'
              }`}
            >Interne</button>
            <button
              onClick={() => setIsDistrib(true)}
              className={`px-3 py-1.5 text-sm ${
                isDistrib ? 'bg-[#17494E] text-white' : 'bg-white text-[#17494E]'
              }`}
            >Distributeur</button>
          </div>
          {isDistrib && (
            <label className="flex flex-col text-xs gap-1 min-w-[220px]">
              <span className="text-[#8B7355] font-medium">Distrib</span>
              <select value={idDistrib} onChange={(e) => setIdDistrib(e.target.value)}
                      className="px-2 py-1.5 border border-[#E5E0D5] rounded">
                <option value="">Choisir...</option>
                {distribs.map((d) => (
                  <option key={d.id} value={d.id}>{d.lib}</option>
                ))}
              </select>
            </label>
          )}
          <button
            onClick={doRechercher}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white disabled:opacity-40 hover:bg-[#0F3438]"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Rechercher
          </button>
          <button
            onClick={doTelecharger}
            disabled={loading || lignes.length === 0}
            title="Télécharger XLSX"
            className="p-2 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] disabled:opacity-40"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
        {idPodiumMois && (
          <div className="mt-3 flex items-center gap-2 border-t border-[#F0EDE5] pt-3">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={scoreVisible}
                     onChange={(e) => setScoreVisible(e.target.checked)}
                     className="accent-[#17494E]" />
              <span className="text-[#8B7355]">Score Visible</span>
            </label>
            <button
              onClick={doSaveScoreVisible}
              title="Enregistrer"
              className="p-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]"
            >
              <Save className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Tableau */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="overflow-x-auto max-h-[60vh] overflow-y-auto">
          <table className="text-xs w-full">
            <thead className="sticky top-0 bg-[#17494E] text-white z-10">
              <tr>
                <th className="py-2 px-2 text-left">Nom</th>
                <th className="py-2 px-2 text-left">Date ancienneté</th>
                <th className="py-2 px-2 text-left">Équipe</th>
                <th className="py-2 px-2 text-right">Valeur</th>
                {isQualite && <th className="py-2 px-2 text-right">Taux</th>}
              </tr>
            </thead>
            <tbody>
              {lignes.filter((l) => l.visible).map((l, i) => (
                <tr key={i} className="border-b border-[#F0EDE5] hover:bg-[#ECF1F2]">
                  <td className="py-1.5 px-2 font-medium">{l.nom}</td>
                  <td className="py-1.5 px-2 tabular-nums">{shortDate(l.date_anciennete)}</td>
                  <td className="py-1.5 px-2">{l.equipe_lib}</td>
                  <td className="py-1.5 px-2 text-right tabular-nums">{l.valeur}</td>
                  {isQualite && (
                    <td className="py-1.5 px-2 text-right tabular-nums">
                      {(l.taux * 100).toFixed(1)}%
                    </td>
                  )}
                </tr>
              ))}
              {lignes.length === 0 && (
                <tr><td colSpan={5} className="py-8 text-center text-gray-400">
                  Aucun résultat - Lance une recherche
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Calcul podium */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-end gap-3 flex-wrap">
          <label className="flex flex-col text-xs gap-1">
            <span className="text-[#8B7355] font-medium">Du</span>
            <input type="date" value={du} onChange={(e) => setDu(e.target.value)}
                   className="px-2 py-1.5 border border-[#E5E0D5] rounded" />
          </label>
          <label className="flex flex-col text-xs gap-1">
            <span className="text-[#8B7355] font-medium">Au</span>
            <input type="date" value={au} onChange={(e) => setAu(e.target.value)}
                   className="px-2 py-1.5 border border-[#E5E0D5] rounded" />
          </label>
          <button
            onClick={doCalcul}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded bg-[#8B7355] text-white disabled:opacity-40 hover:bg-[#725e46]"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calculator className="w-4 h-4" />}
            Calcul Podium
          </button>
        </div>
      </div>
    </div>
  )
}

// =====================================================================
// Onglet 2 - Paramètres
// =====================================================================

const EMPTY_TYPE: Omit<PodiumType, 'id_podium_type'> = {
  lib_podium_type: '', lib_court: '', prod_groupe: false, qualite: false,
  espoir: false, is_actif: true, ordre_affichage: 0,
}
const EMPTY_PART: Omit<PodiumTypePart, 'id_podium_type_part' | 'id_podium_type'> = {
  famille: 'Tous', sous_fam: 'Tous', prefixe_bdd: '', type_prod: 'Paye',
  option_vente: '', jour_cial_deb: 1, jour_cial_fin: 31,
}

function OngletParametres() {
  const [types, setTypes] = useState<PodiumType[]>([])
  const [parts, setParts] = useState<PodiumTypePart[]>([])
  const [selTypeIdx, setSelTypeIdx] = useState<number>(-1)
  const [selPartIdx, setSelPartIdx] = useState<number>(-1)
  const [typeModal, setTypeModal] = useState<{ mode: 'new' | 'edit'; data: PodiumType } | null>(null)
  const [partModal, setPartModal] = useState<{ mode: 'new' | 'edit'; data: PodiumTypePart } | null>(null)
  const [loading, setLoading] = useState(false)

  const loadTypes = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/comm/podium/types`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      const d: PodiumType[] = await r.json()
      setTypes(d || [])
    } finally { setLoading(false) }
  }, [])
  useEffect(() => { void loadTypes() }, [loadTypes])

  const loadParts = useCallback(async (idType: string) => {
    if (!idType) { setParts([]); return }
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/comm/podium/types/${idType}/parts`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      const d: PodiumTypePart[] = await r.json()
      setParts(d || [])
    } finally { setLoading(false) }
  }, [])

  useEffect(() => {
    if (selTypeIdx >= 0 && types[selTypeIdx]) {
      void loadParts(types[selTypeIdx].id_podium_type)
    } else {
      setParts([])
    }
  }, [selTypeIdx, types, loadParts])

  const saveType = async () => {
    if (!typeModal) return
    const url = typeModal.mode === 'new'
      ? `${API_BASE}/comm/podium/types`
      : `${API_BASE}/comm/podium/types/${typeModal.data.id_podium_type}`
    const method = typeModal.mode === 'new' ? 'POST' : 'PUT'
    const { id_podium_type: _, ...payload } = typeModal.data
    const r = await fetch(url, {
      method,
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    const d = await r.json()
    if (d.ok) {
      showToast('Enregistré', 'success')
      setTypeModal(null)
      await loadTypes()
    } else showToast('Erreur', 'error')
  }

  const deleteType = async (idx: number) => {
    if (!await showConfirm({
      title: 'Supprimer',
      message: `Supprimer le type "${types[idx].lib_podium_type}" ?`,
    })) return
    await fetch(`${API_BASE}/comm/podium/types/${types[idx].id_podium_type}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    await loadTypes()
    setSelTypeIdx(-1)
  }

  const savePart = async () => {
    if (!partModal) return
    const url = partModal.mode === 'new'
      ? `${API_BASE}/comm/podium/parts`
      : `${API_BASE}/comm/podium/parts/${partModal.data.id_podium_type_part}`
    const method = partModal.mode === 'new' ? 'POST' : 'PUT'
    const { id_podium_type_part: _, ...payload } = partModal.data
    const r = await fetch(url, {
      method,
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    const d = await r.json()
    if (d.ok) {
      showToast('Enregistré', 'success')
      setPartModal(null)
      if (selTypeIdx >= 0) await loadParts(types[selTypeIdx].id_podium_type)
    } else showToast('Erreur', 'error')
  }

  const deletePart = async (idx: number) => {
    if (!await showConfirm({
      title: 'Supprimer',
      message: 'Supprimer ce critère ?',
    })) return
    await fetch(`${API_BASE}/comm/podium/parts/${parts[idx].id_podium_type_part}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (selTypeIdx >= 0) await loadParts(types[selTypeIdx].id_podium_type)
    setSelPartIdx(-1)
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Colonne gauche : PodiumType */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-2 mb-3">
          <h3 className="text-sm font-semibold text-[#17494E] flex-1">Types de podium</h3>
          <button onClick={() => setTypeModal({
            mode: 'new', data: { id_podium_type: '', ...EMPTY_TYPE },
          })} title="Ajouter"
                  className="p-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438]">
            <Plus className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => selTypeIdx >= 0 && setTypeModal({
            mode: 'edit', data: { ...types[selTypeIdx] },
          })} disabled={selTypeIdx < 0} title="Modifier"
                  className="p-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] disabled:opacity-40">
            <Pencil className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => selTypeIdx >= 0 && deleteType(selTypeIdx)}
                  disabled={selTypeIdx < 0} title="Supprimer"
                  className="p-1.5 rounded border border-[#B91C1C] text-[#B91C1C] hover:bg-red-50 disabled:opacity-40">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="overflow-y-auto max-h-[60vh]">
          <table className="text-xs w-full">
            <thead className="bg-[#F5F5F0]">
              <tr>
                <th className="py-1.5 px-2 text-left">Lib Podium</th>
                <th className="py-1.5 px-2 text-center">PG</th>
                <th className="py-1.5 px-2 text-center">Qual</th>
                <th className="py-1.5 px-2 text-center">Esp</th>
                <th className="py-1.5 px-2 text-center">Actif</th>
                <th className="py-1.5 px-2 text-right">Ordre</th>
              </tr>
            </thead>
            <tbody>
              {types.map((t, i) => (
                <tr key={i} onClick={() => setSelTypeIdx(i)}
                    className={`cursor-pointer border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${
                      selTypeIdx === i ? 'bg-[#FFF5E0] ring-1 ring-[#8B7355]' : ''
                    }`}>
                  <td className="py-1.5 px-2 font-medium">{t.lib_podium_type}</td>
                  <td className="py-1.5 px-2 text-center">{t.prod_groupe ? '✓' : ''}</td>
                  <td className="py-1.5 px-2 text-center">{t.qualite ? '✓' : ''}</td>
                  <td className="py-1.5 px-2 text-center">{t.espoir ? '✓' : ''}</td>
                  <td className="py-1.5 px-2 text-center">{t.is_actif ? '✓' : ''}</td>
                  <td className="py-1.5 px-2 text-right tabular-nums">{t.ordre_affichage}</td>
                </tr>
              ))}
              {types.length === 0 && !loading && (
                <tr><td colSpan={6} className="py-6 text-center text-gray-400">
                  Aucun type - Ajoute avec +
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Colonne droite : PodiumTypePart */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-2 mb-3">
          <h3 className="text-sm font-semibold text-[#17494E] flex-1">
            Critères
            {selTypeIdx >= 0 && ` — ${types[selTypeIdx]?.lib_podium_type}`}
          </h3>
          <button onClick={() => selTypeIdx >= 0 && setPartModal({
            mode: 'new',
            data: {
              id_podium_type_part: '',
              id_podium_type: types[selTypeIdx].id_podium_type,
              ...EMPTY_PART,
            },
          })} disabled={selTypeIdx < 0} title="Ajouter"
                  className="p-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] disabled:opacity-40">
            <Plus className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => selPartIdx >= 0 && setPartModal({
            mode: 'edit', data: { ...parts[selPartIdx] },
          })} disabled={selPartIdx < 0} title="Modifier"
                  className="p-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] disabled:opacity-40">
            <Pencil className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => selPartIdx >= 0 && deletePart(selPartIdx)}
                  disabled={selPartIdx < 0} title="Supprimer"
                  className="p-1.5 rounded border border-[#B91C1C] text-[#B91C1C] hover:bg-red-50 disabled:opacity-40">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="overflow-y-auto max-h-[60vh]">
          <table className="text-xs w-full">
            <thead className="bg-[#F5F5F0]">
              <tr>
                <th className="py-1.5 px-2 text-left">Partenaire</th>
                <th className="py-1.5 px-2 text-left">Famille</th>
                <th className="py-1.5 px-2 text-left">SousFam</th>
                <th className="py-1.5 px-2 text-left">Type Prod</th>
                <th className="py-1.5 px-2 text-left">Option Vente</th>
                <th className="py-1.5 px-2 text-right">Du</th>
                <th className="py-1.5 px-2 text-right">Au</th>
              </tr>
            </thead>
            <tbody>
              {parts.map((p, i) => (
                <tr key={i} onClick={() => setSelPartIdx(i)}
                    className={`cursor-pointer border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${
                      selPartIdx === i ? 'bg-[#FFF5E0] ring-1 ring-[#8B7355]' : ''
                    }`}>
                  <td className="py-1.5 px-2 font-medium">{p.prefixe_bdd}</td>
                  <td className="py-1.5 px-2">{p.famille}</td>
                  <td className="py-1.5 px-2">{p.sous_fam}</td>
                  <td className="py-1.5 px-2">{p.type_prod}</td>
                  <td className="py-1.5 px-2">{p.option_vente}</td>
                  <td className="py-1.5 px-2 text-right tabular-nums">{p.jour_cial_deb}</td>
                  <td className="py-1.5 px-2 text-right tabular-nums">{p.jour_cial_fin}</td>
                </tr>
              ))}
              {selTypeIdx < 0 && (
                <tr><td colSpan={7} className="py-6 text-center text-gray-400">
                  Sélectionne un type
                </td></tr>
              )}
              {selTypeIdx >= 0 && parts.length === 0 && !loading && (
                <tr><td colSpan={7} className="py-6 text-center text-gray-400">
                  Aucun critère
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {typeModal && (
        <ModalPodiumType
          data={typeModal.data}
          onChange={(d) => setTypeModal({ ...typeModal, data: d })}
          onSave={saveType}
          onClose={() => setTypeModal(null)}
        />
      )}
      {partModal && (
        <ModalPodiumTypePart
          data={partModal.data}
          onChange={(d) => setPartModal({ ...partModal, data: d })}
          onSave={savePart}
          onClose={() => setPartModal(null)}
        />
      )}
    </div>
  )
}

// Modales -------------------------------------------------------------

function ModalPodiumType({
  data, onChange, onSave, onClose,
}: {
  data: PodiumType
  onChange: (d: PodiumType) => void
  onSave: () => void
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-[#17494E]">Type de podium</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="space-y-3">
          <label className="block text-xs">
            <span className="text-[#8B7355] font-medium">Libellé</span>
            <input type="text" value={data.lib_podium_type}
                   onChange={(e) => onChange({ ...data, lib_podium_type: e.target.value })}
                   className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
          </label>
          <label className="block text-xs">
            <span className="text-[#8B7355] font-medium">Libellé court</span>
            <input type="text" value={data.lib_court}
                   onChange={(e) => onChange({ ...data, lib_court: e.target.value })}
                   className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
          </label>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={data.prod_groupe}
                     onChange={(e) => onChange({ ...data, prod_groupe: e.target.checked })}
                     className="accent-[#17494E]" />
              <span>Prod Groupe (équipe)</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={data.qualite}
                     onChange={(e) => onChange({ ...data, qualite: e.target.checked })}
                     className="accent-[#17494E]" />
              <span>Qualité (taux payé/brut)</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={data.espoir}
                     onChange={(e) => onChange({ ...data, espoir: e.target.checked })}
                     className="accent-[#17494E]" />
              <span>Espoir (anciens)</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={data.is_actif}
                     onChange={(e) => onChange({ ...data, is_actif: e.target.checked })}
                     className="accent-[#17494E]" />
              <span>Actif</span>
            </label>
          </div>
          <label className="block text-xs">
            <span className="text-[#8B7355] font-medium">Ordre affichage</span>
            <input type="number" value={data.ordre_affichage}
                   onChange={(e) => onChange({ ...data, ordre_affichage: Number(e.target.value) })}
                   className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
          </label>
        </div>
        <div className="flex gap-2 mt-4">
          <button onClick={onSave}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white hover:bg-[#0F3438]">
            <Check className="w-4 h-4" />
            Enregistrer
          </button>
          <button onClick={onClose}
                  className="flex-1 px-3 py-2 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]">
            Annuler
          </button>
        </div>
      </div>
    </div>
  )
}

function ModalPodiumTypePart({
  data, onChange, onSave, onClose,
}: {
  data: PodiumTypePart
  onChange: (d: PodiumTypePart) => void
  onSave: () => void
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-[#17494E]">Critère de podium</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="space-y-3">
          <label className="block text-xs">
            <span className="text-[#8B7355] font-medium">Partenaire (PréfixeBDD)</span>
            <select value={data.prefixe_bdd}
                    onChange={(e) => onChange({ ...data, prefixe_bdd: e.target.value })}
                    className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded">
              <option value="">Choisir...</option>
              <option value="ENI">ENI</option>
              <option value="SFR">SFR</option>
              <option value="IAG">IAG</option>
              <option value="STR">STR (Strato)</option>
              <option value="VAL">VAL (Valandre)</option>
              <option value="PRO">PRO (Protected)</option>
              <option value="OEN">OEN (Ohm Énergie)</option>
              <option value="TLC">TLC</option>
              <option value="Coopt">Coopt (Cooptation)</option>
            </select>
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Famille</span>
              <input type="text" value={data.famille}
                     onChange={(e) => onChange({ ...data, famille: e.target.value })}
                     placeholder="Tous ou valeur"
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Sous-famille</span>
              <input type="text" value={data.sous_fam}
                     onChange={(e) => onChange({ ...data, sous_fam: e.target.value })}
                     placeholder="Tous ou valeur"
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
          </div>
          <label className="block text-xs">
            <span className="text-[#8B7355] font-medium">Type Prod</span>
            <select value={data.type_prod}
                    onChange={(e) => onChange({ ...data, type_prod: e.target.value })}
                    className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded">
              <option value="Brut">Brut</option>
              <option value="HorsRejet">Hors Rejet</option>
              <option value="Paye">Payé</option>
            </select>
          </label>
          <label className="block text-xs">
            <span className="text-[#8B7355] font-medium">Option Vente</span>
            <select value={data.option_vente}
                    onChange={(e) => onChange({ ...data, option_vente: e.target.value })}
                    className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded">
              <option value="">Toutes</option>
              <option value="CQ-">Conquêtes seulement</option>
              <option value="MIG-">Migrations seulement</option>
              <option value="CQ-MIG-">Conquêtes + Migrations</option>
            </select>
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Jour début</span>
              <input type="number" min={1} max={31} value={data.jour_cial_deb}
                     onChange={(e) => onChange({ ...data, jour_cial_deb: Number(e.target.value) })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Jour fin</span>
              <input type="number" min={1} max={31} value={data.jour_cial_fin}
                     onChange={(e) => onChange({ ...data, jour_cial_fin: Number(e.target.value) })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
          </div>
        </div>
        <div className="flex gap-2 mt-4">
          <button onClick={onSave}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white hover:bg-[#0F3438]">
            <Check className="w-4 h-4" />
            Enregistrer
          </button>
          <button onClick={onClose}
                  className="flex-1 px-3 py-2 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]">
            Annuler
          </button>
        </div>
      </div>
    </div>
  )
}

// =====================================================================
// Onglet 3 - Année Podium
// =====================================================================

function OngletAnnee() {
  const [annee, setAnnee] = useState(currentYear)
  const [loading, setLoading] = useState(false)

  const doValider = async () => {
    if (!await showConfirm({
      title: 'Valider l\'année',
      message: `Créer les 12 mois de podium pour l'année ${annee} (pour tous les types actifs) ?`,
    })) return
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/comm/podium/valider-annee`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ annee }),
      })
      const d = await r.json()
      if (!d.ok) { showToast(d.message || 'Erreur', 'error'); return }
      showToast(d.message || '', 'success')
    } finally { setLoading(false) }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 max-w-md">
      <div className="flex items-end gap-3">
        <label className="flex flex-col text-xs gap-1">
          <span className="text-[#8B7355] font-medium">Année</span>
          <input type="number" min={2020} max={2100} value={annee}
                 onChange={(e) => setAnnee(Number(e.target.value))}
                 className="px-2 py-1.5 border border-[#E5E0D5] rounded w-28 text-lg" />
        </label>
        <button
          onClick={doValider}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white disabled:opacity-40 hover:bg-[#0F3438]"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
          Valider l'année
        </button>
      </div>
      <p className="mt-3 text-xs text-gray-500 italic">
        Crée 12 lignes PodiumMois (score_visible=true par défaut) pour chaque
        type de podium actif. Idempotent : les mois déjà créés sont ignorés.
      </p>
    </div>
  )
}
