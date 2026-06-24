/**
 * Fen_RechercheCvMotsCle (WinDev) - Recherche CV par mots-cles.
 *
 * Variante simplifiee de Fen_RechercheCV :
 *  - Filtres : tokens mots-cles (AND) + periode
 *  - Tableau resultats classique
 *  - Panneau droite : preview mots-cles du CV selectionne avec highlight
 *    rouge gras des tokens cherches
 *  - Double-click : ouvre Fen_CVFiche (CVFicheModal)
 */

import { useEffect, useMemo, useState } from 'react'
import {
  Calendar, ChevronLeft, ChevronRight, Loader2, Plus, Search, X,
} from 'lucide-react'
import { getToken, getStoredUser } from '@/api'
import { showToast } from '../ui/dialog'
import CVFicheModal from './CVFicheModal'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface ComboItem { id: string; label: string }

interface CVRow {
  id_cvtheque: string
  identite: string
  nom: string
  prenom: string
  op_traitement: string
  statut_actuel: string
  source: string
  detail_source: string
  age: number
  tel: string
  localisation: string
  date_saisie: string
  agence: string
  equipe: string
  commentaire: string
  mots_cles: string
}

interface RechercheCvMotsClesPageProps {
  apiBase: string
}

export default function RechercheCvMotsClesPage({
  apiBase,
}: RechercheCvMotsClesPageProps) {
  const today = new Date().toISOString().slice(0, 10)
  const oneYearAgo = new Date(Date.now() - 365 * 86400000).toISOString().slice(0, 10)
  const user = getStoredUser()

  const [tokens, setTokens] = useState<string[]>([])
  const [tokenInput, setTokenInput] = useState('')
  const [dateDebut, setDateDebut] = useState(oneYearAgo)
  const [dateFin, setDateFin] = useState(today)
  const [results, setResults] = useState<CVRow[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedId, setSelectedId] = useState('')
  const [statuts, setStatuts] = useState<ComboItem[]>([])
  const [sources, setSources] = useState<ComboItem[]>([])
  const [openFicheId, setOpenFicheId] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)

  // Combos statuts/sources pour les libelles
  useEffect(() => {
    const h = { Authorization: `Bearer ${getToken()}` }
    fetch(`${apiBase}/recrutement/cv/statuts`, { headers: h })
      .then(r => r.json()).then(setStatuts)
    fetch(`${apiBase}/recrutement/cv/sources`, { headers: h })
      .then(r => r.json()).then(setSources)
  }, [apiBase])

  const statutsById = useMemo(() => {
    const m = new Map<string, string>()
    statuts.forEach(s => m.set(s.id, s.label))
    return m
  }, [statuts])
  const sourcesById = useMemo(() => {
    const m = new Map<string, string>()
    sources.forEach(s => m.set(s.id, s.label))
    return m
  }, [sources])

  const addToken = () => {
    const v = tokenInput.trim()
    if (!v) return
    if (tokens.includes(v)) { setTokenInput(''); return }
    setTokens([...tokens, v])
    setTokenInput('')
  }

  const removeToken = (t: string) => setTokens(tokens.filter(x => x !== t))

  const lancer = async () => {
    if (tokens.length === 0) {
      showToast('Saisis au moins 1 mot-clé.', 'info')
      return
    }
    setLoading(true)
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/search-mots-cles`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          mots_cles: tokens,
          date_debut: dateDebut,
          date_fin: dateFin,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d: CVRow[] = await r.json()
      setResults(d)
      setSelectedId(d[0]?.id_cvtheque || '')
      if (d.length === 0) showToast('Aucun résultat.', 'info')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }

  const selectedRow = useMemo(
    () => results.find(r => r.id_cvtheque === selectedId),
    [results, selectedId],
  )

  const highlightedMotsCles = useMemo(() => {
    if (!selectedRow?.mots_cles) return ''
    let html = escapeHtml(selectedRow.mots_cles)
    // Surligne les tokens en rouge gras (insensible casse)
    tokens.forEach(t => {
      const re = new RegExp(`(${escapeRegExp(t)})`, 'gi')
      html = html.replace(re, '<strong style="color:#DC2626">$1</strong>')
    })
    // Convertit \n en <br>
    html = html.replace(/\n/g, '<br>')
    return html
  }, [selectedRow, tokens])

  return (
    <div className="flex h-full">
      {/* SIDEBAR FILTRES */}
      {sidebarOpen && (
        <aside className="w-72 shrink-0 border-r bg-white p-3 space-y-4"
               style={{ borderColor: COL_BORDER }}>
          <div>
            <label className="text-xs font-semibold mb-1 block" style={{ color: COL_BRUN }}>
              Mots-clés (chaque mot doit être présent)
            </label>
            <div className="flex gap-1 mb-2">
              <input type="text" value={tokenInput}
                     onChange={e => setTokenInput(e.target.value)}
                     onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addToken() } }}
                     placeholder="Ajouter un mot-clé"
                     className="flex-1 px-2 py-1.5 rounded border text-sm"
                     style={{ borderColor: COL_BORDER }} />
              <button type="button" onClick={addToken}
                      className="px-2 rounded border"
                      style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>
            {tokens.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {tokens.map(t => (
                  <span key={t}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs"
                        style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                    {t}
                    <button type="button" onClick={() => removeToken(t)}>
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="text-xs font-semibold flex items-center gap-1 mb-1"
                   style={{ color: COL_BRUN }}>
              <Calendar className="w-3 h-3" /> Période
            </label>
            <div className="flex gap-1 items-center text-xs">
              <input type="date" value={dateDebut}
                     onChange={e => setDateDebut(e.target.value)}
                     className="flex-1 px-2 py-1.5 rounded border"
                     style={{ borderColor: COL_BORDER }} />
              <span style={{ color: COL_BRUN }}>au</span>
              <input type="date" value={dateFin}
                     onChange={e => setDateFin(e.target.value)}
                     className="flex-1 px-2 py-1.5 rounded border"
                     style={{ borderColor: COL_BORDER }} />
            </div>
          </div>

          <button type="button" onClick={lancer} disabled={loading}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded text-white text-sm font-semibold disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Lancer la recherche
          </button>
        </aside>
      )}

      {/* MAIN : tableau + preview */}
      <main className="flex-1 flex flex-col min-w-0 p-3 space-y-3">
        <div className="flex items-center gap-2 shrink-0">
          <button type="button" onClick={() => setSidebarOpen(o => !o)}
                  className="p-1.5 rounded border hover:bg-gray-50"
                  style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
            {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
          <h1 className="text-lg font-bold" style={{ color: COL_BRUN }}>
            Recherche CV par mots-clés
            {results.length > 0 && (
              <span className="ml-2 text-sm font-normal" style={{ color: COL_PRIMARY }}>
                ({results.length} résultats)
              </span>
            )}
          </h1>
        </div>

        <div className="flex-1 grid gap-3 min-h-0"
             style={{ gridTemplateColumns: results.length > 0 ? '1fr 380px' : '1fr' }}>
          {/* Tableau resultats */}
          <div className="border rounded-lg overflow-auto bg-white"
               style={{ borderColor: COL_BORDER }}>
            <table className="w-full text-xs">
              <thead className="sticky top-0 z-10"
                     style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                <tr>
                  <th className="px-2 py-2 text-left whitespace-nowrap">Identité</th>
                  <th className="px-2 py-2 text-left whitespace-nowrap">Op. Traitement</th>
                  <th className="px-2 py-2 text-left whitespace-nowrap">Statut</th>
                  <th className="px-2 py-2 text-left whitespace-nowrap">Source</th>
                  <th className="px-2 py-2 text-left whitespace-nowrap">Détail Source</th>
                  <th className="px-2 py-2 text-center whitespace-nowrap">Age</th>
                  <th className="px-2 py-2 text-left whitespace-nowrap">Tél</th>
                  <th className="px-2 py-2 text-left whitespace-nowrap">Localisation</th>
                  <th className="px-2 py-2 text-left whitespace-nowrap">Date Saisie</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={9} className="p-6 text-center">
                    <Loader2 className="w-5 h-5 animate-spin inline" /></td></tr>
                ) : results.length === 0 ? (
                  <tr><td colSpan={9} className="p-6 text-center italic"
                          style={{ color: '#A68D8A' }}>
                    Saisis des mots-clés et lance la recherche.
                  </td></tr>
                ) : (
                  results.map(r => {
                    const isSel = selectedId === r.id_cvtheque
                    return (
                      <tr key={r.id_cvtheque}
                          onClick={() => setSelectedId(r.id_cvtheque)}
                          onDoubleClick={() => setOpenFicheId(r.id_cvtheque)}
                          className="cursor-pointer border-b"
                          style={{
                            backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                            color: isSel ? 'white' : COL_BRUN,
                            borderColor: COL_BORDER,
                          }}>
                        <td className="px-2 py-1.5 font-semibold whitespace-nowrap">{r.identite}</td>
                        <td className="px-2 py-1.5">{r.op_traitement}</td>
                        <td className="px-2 py-1.5">{statutsById.get(r.statut_actuel) || ''}</td>
                        <td className="px-2 py-1.5">{sourcesById.get(r.source) || ''}</td>
                        <td className="px-2 py-1.5">{r.detail_source}</td>
                        <td className="px-2 py-1.5 text-center">{r.age || ''}</td>
                        <td className="px-2 py-1.5 whitespace-nowrap">{r.tel}</td>
                        <td className="px-2 py-1.5">{r.localisation}</td>
                        <td className="px-2 py-1.5 whitespace-nowrap">{r.date_saisie}</td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Preview mots-cles du CV selectionne */}
          {results.length > 0 && (
            <div className="border rounded-lg overflow-auto bg-white p-3"
                 style={{ borderColor: COL_BORDER }}>
              <h3 className="text-xs font-bold uppercase mb-2" style={{ color: COL_BRUN }}>
                Mots-clés {selectedRow && `— ${selectedRow.identite}`}
              </h3>
              {selectedRow ? (
                <div className="text-xs leading-relaxed"
                     style={{ color: COL_BRUN, fontFamily: 'monospace' }}
                     dangerouslySetInnerHTML={{ __html: highlightedMotsCles || '<em>(vide)</em>' }} />
              ) : (
                <p className="text-xs italic" style={{ color: '#A68D8A' }}>
                  Sélectionne une ligne pour afficher le contenu.
                </p>
              )}
            </div>
          )}
        </div>
      </main>

      {/* Modal Fen_CVFiche au double-click */}
      {openFicheId && (
        <CVFicheModal apiBase={apiBase} idCv={openFicheId}
                      userDroits={user?.droits || []}
                      onClose={() => setOpenFicheId('')} />
      )}
    </div>
  )
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
