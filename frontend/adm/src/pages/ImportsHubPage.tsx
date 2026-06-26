/**
 * Fen_ChoixImports — Hub des imports manuels par partenaire +
 * suivi des imports automatiques (polling 5s).
 *
 * Combo Partenaire : redirige vers /imports/{prefixe_bdd} (a coder
 * par partenaire). Si la page n'existe pas encore -> showToast info
 * (cf WinDev 'Il n'existe pas encore de fenêtre d'importation...').
 */

import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CheckCircle2, Database, FileDown, Loader2, Play, RefreshCw,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface Partenaire {
  id_partenaire: string
  prefixe_bdd: string
  lib_partenaire: string
  is_actif: boolean
}

interface AutoSuivi {
  type: string
  total: number
  avancement: number
  pourcent: number
  date_import: string
  modif_date: string
}

const API_BASE = '/api/adm'

// Pages d'import deja codees (ajoute ici quand tu codes une Fen_ImportXXX)
const IMPLEMENTED_IMPORTS: Set<string> = new Set([
  'ENI',  // -> /imports/eni (Plenitude)
  'IAG',  // -> /imports/iag
  'OEN',  // -> /imports/oen (OHM Énergie)
  'PRO',  // -> /imports/pro (PROTECTED)
  'SFR',  // -> /imports/sfr (10 types : BJ Fibre/Mobile/CALL, Hebdo, Options, RUN, CallRET x4)
])

const fmtDateTime = (iso: string): string => {
  if (!iso) return ''
  const [d, t] = iso.split(' ')
  if (!d) return iso
  const [y, m, day] = d.split('-')
  return `${day}/${m}/${y} ${(t || '').slice(0, 5)}`
}

export default function ImportsHubPage() {
  useDocumentTitle('Imports')
  const navigate = useNavigate()
  const [partenaires, setPartenaires] = useState<Partenaire[]>([])
  const [selPart, setSelPart] = useState('')
  const [suivi, setSuivi] = useState<AutoSuivi[]>([])
  const [loading, setLoading] = useState(true)

  // Combos
  useEffect(() => {
    fetch(`${API_BASE}/imports/partenaires`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(d => setPartenaires(Array.isArray(d) ? d : []))
  }, [])

  // Suivi avec polling
  const loadSuivi = useCallback(() => {
    fetch(`${API_BASE}/imports/auto-suivi`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(d => setSuivi(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadSuivi()
    const id = window.setInterval(loadSuivi, 5000)
    return () => window.clearInterval(id)
  }, [loadSuivi])

  const valider = () => {
    if (!selPart) {
      showToast('Choisis un partenaire.', 'info'); return
    }
    const p = partenaires.find(x => x.prefixe_bdd === selPart)
    if (!p) return
    if (IMPLEMENTED_IMPORTS.has(p.prefixe_bdd)) {
      navigate(`/imports/${p.prefixe_bdd.toLowerCase()}`)
    } else {
      showToast(
        `Il n'existe pas encore de fenêtre d'importation pour le partenaire ${p.lib_partenaire}. Contacte ton administrateur.`,
        'info',
      )
    }
  }

  return (
    <div className="p-6 max-w-4xl" style={{ color: COL_BRUN }}>
      <h1 className="text-xl font-bold mb-4 flex items-center gap-2">
        <FileDown className="w-5 h-5" style={{ color: COL_PRIMARY }} />
        Choix du partenaire pour l'import
      </h1>

      {/* Imports manuels */}
      <div className="border rounded p-4 mb-4"
           style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
        <h2 className="text-xs font-bold mb-3 uppercase"
            style={{ color: COL_PRIMARY }}>
          Imports manuels
        </h2>
        <div className="flex items-center gap-2">
          <label className="text-sm w-24" style={{ color: COL_BRUN }}>
            Partenaire
          </label>
          <select value={selPart} onChange={e => setSelPart(e.target.value)}
                  className="flex-1 px-2 py-1.5 rounded border text-sm"
                  style={{ borderColor: COL_BORDER }}>
            <option value="">—</option>
            {partenaires.map(p => (
              <option key={p.id_partenaire} value={p.prefixe_bdd}
                      disabled={!p.is_actif}>
                {p.lib_partenaire}{!p.is_actif ? ' (inactif)' : ''}
              </option>
            ))}
          </select>
          <button type="button" onClick={valider} disabled={!selPart}
                  className="flex items-center gap-1 px-4 py-1.5 rounded text-white text-sm disabled:opacity-40"
                  style={{ backgroundColor: COL_PRIMARY }}>
            <Play className="w-3.5 h-3.5" />
            Ouvrir
          </button>
        </div>
      </div>

      {/* Suivi automatiques */}
      <div className="border rounded p-4"
           style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
        <div className="flex items-center mb-3">
          <h2 className="text-xs font-bold flex-1 uppercase"
              style={{ color: COL_PRIMARY }}>
            Suivi des imports automatiques
          </h2>
          <RefreshCw className="w-3 h-3 animate-pulse"
                     style={{ color: COL_PRIMARY_LIGHT }} />
          <span className="text-[10px] ml-1 italic" style={{ color: '#A68D8A' }}>
            polling 5s
          </span>
        </div>

        {loading ? (
          <Loader2 className="w-5 h-5 animate-spin mx-auto"
                   style={{ color: COL_PRIMARY }} />
        ) : suivi.length === 0 ? (
          <p className="italic text-sm text-center py-4"
             style={{ color: '#A68D8A' }}>
            Aucun import automatique en cours.
          </p>
        ) : (
          <div className="space-y-3">
            {suivi.map(s => {
              const isDone = s.avancement >= s.total && s.total > 0
              return (
                <div key={s.type} className="bg-white rounded border p-3"
                     style={{ borderColor: COL_BORDER }}>
                  <div className="flex items-center gap-2 text-sm">
                    <Database className="w-4 h-4"
                              style={{ color: COL_PRIMARY }} />
                    <strong className="flex-1">{s.type}</strong>
                    <span className="text-xs"
                          style={{ color: isDone ? '#16a34a' : COL_PRIMARY }}>
                      {s.pourcent.toFixed(1)}%
                    </span>
                    {isDone && (
                      <CheckCircle2 className="w-4 h-4"
                                    style={{ color: '#16a34a' }} />
                    )}
                  </div>
                  {/* Jauge */}
                  <div className="mt-2 h-2 rounded overflow-hidden"
                       style={{ backgroundColor: COL_BORDER }}>
                    <div className="h-full transition-all"
                         style={{
                           width: `${Math.min(s.pourcent, 100)}%`,
                           backgroundColor: isDone ? '#16a34a' : COL_PRIMARY_LIGHT,
                         }} />
                  </div>
                  <div className="flex justify-between text-[10px] mt-1"
                       style={{ color: '#A68D8A' }}>
                    <span>{s.avancement.toLocaleString('fr-FR')} / {s.total.toLocaleString('fr-FR')}</span>
                    <span>MAJ : {fmtDateTime(s.modif_date)}</span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
