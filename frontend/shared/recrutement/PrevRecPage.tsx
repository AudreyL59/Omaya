/**
 * Fen_PrevRec — Prevision de Recrutement.
 *
 * Layout split : arbre orga gauche (lazy chargement enfants) +
 * tableau previsions droite. Date de reference filtre sur date_butoire >=.
 *
 * Etape 1 : juste la lecture + selection orga + refresh.
 * Boutons d'action (Nouvelle / Editer / Supprimer / Imprimer) viendront ensuite.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Calendar, ChevronDown, ChevronRight, Edit, Loader2, MapPin, Plus,
  Printer, RefreshCw, Search, Trash2, Users,
} from 'lucide-react'
import { getToken } from '@/api'
import { showConfirm, showToast } from '../ui/dialog'
import PrevRecAjoutModal from './PrevRecAjoutModal'
import PrevRecFicheModal from './PrevRecFicheModal'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface OrgaNode {
  idorganigramme: string
  lib_orga: string
  has_children: boolean
}

interface PrevRecRow {
  id_prevision_recrut: string
  id_prev_recrut_etat: string
  lib_etat: string
  idorganigramme: string
  lib_orga: string
  id_cv_lieu_rdv: string
  lib_lieu: string
  id_communes_france: string
  localisation: string
  date_session: string
  date_butoire: string
  date_debut: string
  date_fin: string
  commentaire: string
  taille_session: number
  potentiel_accueil: number
  nb_prod: number
  nb_coopt_mini: number
  nb_sourcing_mini: number
  obj_coopt: number
  obj_sourcing: number
  coopt_smoins1: number
  coopt_jmoins2: number
  sourcing_smoins1: number
  sourcing_jmoins2: number
}

interface PrevRecPageProps {
  apiBase: string
}

const fmtDate = (iso: string): string => {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

// Date de ref par defaut : DateSys() - 7 (cf. WinDev)
const defaultDateRef = (): string => {
  const d = new Date()
  d.setDate(d.getDate() - 7)
  return d.toISOString().slice(0, 10)
}

export default function PrevRecPage({ apiBase }: PrevRecPageProps) {
  const [dateRef, setDateRef] = useState(defaultDateRef())
  const [selectedOrga, setSelectedOrga] = useState<{ id: string; lib: string }>({
    id: '0', lib: 'Racine',
  })
  const [previsions, setPrevisions] = useState<PrevRecRow[]>([])
  const [loading, setLoading] = useState(false)
  const [showAjout, setShowAjout] = useState(false)
  const [editId, setEditId] = useState('')
  const [selectedRowId, setSelectedRowId] = useState('')

  const loadPrevisions = useCallback(() => {
    setLoading(true)
    fetch(
      `${apiBase}/recrutement/cv/prev-rec?id_orga=${selectedOrga.id}&date_ref=${dateRef}`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
      .then(r => r.ok ? r.json() : [])
      .then(setPrevisions)
      .catch(() => showToast('Erreur chargement.', 'error'))
      .finally(() => setLoading(false))
  }, [apiBase, selectedOrga.id, dateRef])

  useEffect(() => { loadPrevisions() }, [loadPrevisions])

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-120px)]"
         style={{ color: COL_BRUN }}>
      <div className="flex items-center gap-3 mb-3">
        <h1 className="text-xl font-bold flex-1">
          Prévision de recrutement
          {selectedOrga.id !== '0' && (
            <span className="text-sm font-normal ml-2"
                  style={{ color: COL_PRIMARY }}>
              — {selectedOrga.lib}
            </span>
          )}
        </h1>
        <label className="text-sm flex items-center gap-2">
          <Calendar className="w-4 h-4" style={{ color: COL_PRIMARY }} />
          Date Réf :
          <input type="date" value={dateRef}
                 onChange={e => setDateRef(e.target.value)}
                 className="px-2 py-1 rounded border text-sm"
                 style={{ borderColor: COL_BORDER }} />
        </label>
        <button type="button" onClick={loadPrevisions}
                title="Rafraîchir"
                className="p-2 rounded border"
                style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
          <Search className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 flex gap-3 min-h-0">
        {/* Arbre organigramme */}
        <div className="w-64 shrink-0 border rounded overflow-auto"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <OrgaTree apiBase={apiBase}
                    selectedId={selectedOrga.id}
                    onSelect={(id, lib) => setSelectedOrga({ id, lib })} />
        </div>

        {/* Toolbar + tableau */}
        <div className="flex-1 flex flex-col min-w-0 border rounded"
             style={{ borderColor: COL_BORDER }}>
          <div className="px-3 py-2 flex items-center gap-2 border-b"
               style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
            <BtnTb onClick={() => {
                     if (selectedOrga.id === '0') {
                       showToast('Sélectionne un organigramme.', 'info')
                       return
                     }
                     setShowAjout(true)
                   }}
                   icon={Plus} primary>Nouvelle session</BtnTb>
            <BtnTb onClick={() => {
                     if (!selectedRowId) {
                       showToast('Sélectionne une session à éditer.', 'info')
                       return
                     }
                     setEditId(selectedRowId)
                   }}
                   icon={Edit}>Éditer</BtnTb>
            <BtnTb onClick={() => showToast('Imprimer : à venir', 'info')}
                   icon={Printer}>Imprimer</BtnTb>
            <BtnTb onClick={async () => {
                     if (!selectedRowId) {
                       showToast('Sélectionne une session à supprimer.', 'info')
                       return
                     }
                     const ok = await showConfirm({
                       title: 'Supprimer cette session ?',
                       message: 'Vous êtes sur le point de supprimer cette session. Voulez-vous continuer ?',
                       confirmLabel: 'Supprimer',
                     })
                     if (!ok) return
                     try {
                       const r = await fetch(
                         `${apiBase}/recrutement/cv/prev-rec/session/${selectedRowId}`,
                         {
                           method: 'DELETE',
                           headers: { Authorization: `Bearer ${getToken()}` },
                         },
                       )
                       if (!r.ok) throw new Error(String(r.status))
                       showToast('Session supprimée.', 'success')
                       setSelectedRowId('')
                       loadPrevisions()
                     } catch (e) {
                       showToast(`Erreur : ${(e as Error).message}`, 'error')
                     }
                   }}
                   icon={Trash2} variant="danger">Supprimer</BtnTb>
            <div className="flex-1" />
            <button type="button" onClick={loadPrevisions}
                    className="p-1.5 rounded hover:bg-gray-100">
              <RefreshCw className="w-4 h-4"
                         style={{ color: COL_PRIMARY }} />
            </button>
          </div>

          <div className="flex-1 overflow-auto">
            {loading ? (
              <div className="p-8 flex justify-center">
                <Loader2 className="w-6 h-6 animate-spin"
                         style={{ color: COL_PRIMARY }} />
              </div>
            ) : previsions.length === 0 ? (
              <p className="p-8 text-center italic"
                 style={{ color: '#A68D8A' }}>
                Aucune session pour cette sélection.
              </p>
            ) : (
              <table className="w-full text-xs">
                <thead className="sticky top-0"
                       style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                  <tr>
                    <th className="px-2 py-2 text-left">Du</th>
                    <th className="px-2 py-2 text-left">Au</th>
                    <th className="px-2 py-2 text-left">Session</th>
                    <th className="px-2 py-2 text-left">Butoir</th>
                    <th className="px-2 py-2 text-left">Lieu</th>
                    <th className="px-2 py-2 text-left">Localisation</th>
                    <th className="px-2 py-2 text-left">État</th>
                    <th className="px-2 py-2 text-right">Potentiel</th>
                    <th className="px-2 py-2 text-right">Productifs</th>
                    <th className="px-2 py-2 text-right">Taille</th>
                  </tr>
                </thead>
                <tbody>
                  {previsions.map(p => {
                    const isSel = selectedRowId === p.id_prevision_recrut
                    return (
                    <tr key={p.id_prevision_recrut}
                        className="border-b cursor-pointer"
                        onClick={() => setSelectedRowId(p.id_prevision_recrut)}
                        onDoubleClick={() => setEditId(p.id_prevision_recrut)}
                        style={{
                          borderColor: COL_BORDER,
                          backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                          color: isSel ? 'white' : COL_BRUN,
                        }}>
                      <td className="px-2 py-1.5">{fmtDate(p.date_debut)}</td>
                      <td className="px-2 py-1.5">{fmtDate(p.date_fin)}</td>
                      <td className="px-2 py-1.5 font-semibold">
                        {fmtDate(p.date_session)}
                      </td>
                      <td className="px-2 py-1.5">{fmtDate(p.date_butoire)}</td>
                      <td className="px-2 py-1.5">{p.lib_lieu}</td>
                      <td className="px-2 py-1.5">
                        <MapPin className="w-3 h-3 inline mr-1"
                                style={{ color: COL_PRIMARY }} />
                        {p.localisation}
                      </td>
                      <td className="px-2 py-1.5">
                        <span className="px-1.5 py-0.5 rounded text-[10px]"
                              style={{
                                backgroundColor: COL_PRIMARY_LIGHT,
                                color: 'white',
                              }}>
                          {p.lib_etat}
                        </span>
                      </td>
                      <td className="px-2 py-1.5 text-right">
                        {p.potentiel_accueil || ''}
                      </td>
                      <td className="px-2 py-1.5 text-right">
                        {p.nb_prod || ''}
                      </td>
                      <td className="px-2 py-1.5 text-right font-semibold">
                        <Users className="w-3 h-3 inline mr-1" />
                        {p.taille_session || ''}
                      </td>
                    </tr>
                  )})}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {showAjout && selectedOrga.id !== '0' && (
        <PrevRecAjoutModal apiBase={apiBase} idOrga={selectedOrga.id}
                           onClose={(createdId) => {
                             setShowAjout(false)
                             if (createdId) loadPrevisions()
                           }} />
      )}

      {editId && (
        <PrevRecFicheModal apiBase={apiBase} idPrev={editId}
                           onClose={(modified) => {
                             setEditId('')
                             if (modified) loadPrevisions()
                           }} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Arbre orga (lazy chargement enfants au click chevron)
// ---------------------------------------------------------------------------

function OrgaTree({ apiBase, selectedId, onSelect }: {
  apiBase: string
  selectedId: string
  onSelect: (id: string, lib: string) => void
}) {
  const [racines, setRacines] = useState<OrgaNode[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${apiBase}/recrutement/cv/prev-rec/orgas/racine`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(setRacines)
      .finally(() => setLoading(false))
  }, [apiBase])

  if (loading) return (
    <div className="p-3">
      <Loader2 className="w-4 h-4 animate-spin" style={{ color: COL_PRIMARY }} />
    </div>
  )

  return (
    <div className="p-1 text-sm">
      <RowOrga node={{ idorganigramme: '0', lib_orga: 'Racine', has_children: true }}
               selectedId={selectedId} onSelect={onSelect} apiBase={apiBase}
               isRacine
               racines={racines} />
    </div>
  )
}

function RowOrga({
  node, selectedId, onSelect, apiBase,
  isRacine = false, racines,
}: {
  node: OrgaNode
  selectedId: string
  onSelect: (id: string, lib: string) => void
  apiBase: string
  isRacine?: boolean
  racines?: OrgaNode[]
}) {
  const [expanded, setExpanded] = useState(isRacine)
  const [enfants, setEnfants] = useState<OrgaNode[] | null>(
    isRacine && racines ? racines : null,
  )
  const [loadingChildren, setLoadingChildren] = useState(false)

  const toggle = () => {
    const next = !expanded
    setExpanded(next)
    if (next && enfants === null && !isRacine && node.has_children) {
      setLoadingChildren(true)
      fetch(
        `${apiBase}/recrutement/cv/prev-rec/orgas/${node.idorganigramme}/enfants`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
        .then(r => r.ok ? r.json() : [])
        .then(setEnfants)
        .finally(() => setLoadingChildren(false))
    }
  }

  const isSel = selectedId === node.idorganigramme
  const showChevron = isRacine || node.has_children

  return (
    <div>
      <div
        className="flex items-center gap-1 px-1 py-1 rounded cursor-pointer"
        style={{
          backgroundColor: isSel ? COL_PRIMARY : 'transparent',
          color: isSel ? 'white' : COL_BRUN,
        }}
        onClick={() => onSelect(node.idorganigramme, node.lib_orga)}
      >
        <button type="button"
                onClick={e => { e.stopPropagation(); if (showChevron) toggle() }}
                className="p-0.5"
                style={{ visibility: showChevron ? 'visible' : 'hidden' }}>
          {expanded
            ? <ChevronDown className="w-3 h-3" />
            : <ChevronRight className="w-3 h-3" />}
        </button>
        <span className="truncate text-xs">{node.lib_orga}</span>
      </div>
      {expanded && (
        <div className="ml-3 border-l pl-1"
             style={{ borderColor: COL_BORDER }}>
          {loadingChildren && (
            <Loader2 className="w-3 h-3 animate-spin mx-2"
                     style={{ color: COL_PRIMARY }} />
          )}
          {enfants && enfants.map(c => (
            <RowOrga key={c.idorganigramme} node={c}
                     selectedId={selectedId} onSelect={onSelect}
                     apiBase={apiBase} />
          ))}
        </div>
      )}
    </div>
  )
}

function BtnTb({ onClick, icon: Icon, children, primary, variant }: {
  onClick: () => void
  icon: React.ComponentType<{ className?: string }>
  children: React.ReactNode
  primary?: boolean
  variant?: 'danger'
}) {
  const bg = variant === 'danger' ? '#B91C1C' : primary ? COL_PRIMARY : 'white'
  const fg = primary || variant === 'danger' ? 'white' : COL_BRUN
  return (
    <button type="button" onClick={onClick}
            className="flex items-center gap-1 px-3 py-1.5 rounded border text-xs"
            style={{ borderColor: COL_BORDER, backgroundColor: bg, color: fg }}>
      <Icon className="w-3.5 h-3.5" />
      {children}
    </button>
  )
}
