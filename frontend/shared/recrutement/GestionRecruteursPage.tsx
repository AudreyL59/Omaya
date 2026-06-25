/**
 * Fen_Agenda_GestionRecruteur — gestion des recruteurs (agenda_actif).
 *
 * Toolbar : checkbox 'Salarié Actif' (filtre en_activite) +
 * bouton 'Activer/désactiver' (toggle agenda_actif sur lignes
 * selectionnees).
 */

import { useCallback, useEffect, useState } from 'react'
import {
  CheckCircle2, Loader2, Power, Users, XCircle,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '../ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface Recruteur {
  id_salarie: string
  nom_prenom: string
  agenda_actif: boolean
  en_activite: boolean
}

interface GestionRecruteursPageProps {
  apiBase: string
}

export default function GestionRecruteursPage({
  apiBase,
}: GestionRecruteursPageProps) {
  const [rows, setRows] = useState<Recruteur[]>([])
  const [loading, setLoading] = useState(true)
  const [salarieActif, setSalarieActif] = useState(true)
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const load = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/recrutement/cv/gestion-recruteurs?salarie_actif=${salarieActif}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(d => setRows(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }, [apiBase, salarieActif])

  useEffect(() => { load() }, [load])

  const toggleSel = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }
  const toggleAll = () => {
    if (selected.size === rows.length) setSelected(new Set())
    else setSelected(new Set(rows.map(r => r.id_salarie)))
  }

  const toggle = async () => {
    if (selected.size === 0) {
      showToast('Sélectionne au moins un recruteur.', 'info'); return
    }
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/gestion-recruteurs/toggle`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ ids: Array.from(selected) }),
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast(`${selected.size} recruteur(s) basculé(s).`, 'success')
      setSelected(new Set())
      load()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-120px)]"
         style={{ color: COL_BRUN }}>
      <h1 className="text-xl font-bold mb-3 flex items-center gap-2">
        <Users className="w-5 h-5" style={{ color: COL_PRIMARY }} />
        Gestion Recruteurs
      </h1>

      <div className="flex-1 flex flex-col min-h-0 border rounded"
           style={{ borderColor: COL_BORDER }}>
        <div className="px-3 py-2 flex items-center gap-3 border-b"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <button type="button" onClick={toggle} disabled={selected.size === 0}
                  className="flex items-center gap-1 px-3 py-1.5 rounded text-white text-xs disabled:opacity-40"
                  style={{ backgroundColor: COL_PRIMARY }}>
            <Power className="w-3.5 h-3.5" />
            Activer / désactiver
            {selected.size > 0 && <span className="ml-1">({selected.size})</span>}
          </button>
          <label className="flex items-center gap-1 text-sm" style={{ color: COL_BRUN }}>
            <input type="checkbox" checked={salarieActif}
                   onChange={e => { setSelected(new Set()); setSalarieActif(e.target.checked) }} />
            Salarié Actif
          </label>
          <div className="flex-1" />
          <span className="text-xs italic" style={{ color: '#A68D8A' }}>
            {rows.length} recruteur(s)
          </span>
        </div>

        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="p-8 flex justify-center">
              <Loader2 className="w-6 h-6 animate-spin"
                       style={{ color: COL_PRIMARY }} />
            </div>
          ) : rows.length === 0 ? (
            <p className="p-8 text-center italic" style={{ color: '#A68D8A' }}>
              Aucun recruteur.
            </p>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0"
                     style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                <tr>
                  <th className="px-2 py-2 w-8">
                    <input type="checkbox"
                           checked={selected.size === rows.length && rows.length > 0}
                           onChange={toggleAll} />
                  </th>
                  <th className="px-2 py-2 text-left">NomPrenom</th>
                  <th className="px-2 py-2 text-center">AgendaActif</th>
                  <th className="px-2 py-2 text-center">En Activité</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(r => {
                  const isSel = selected.has(r.id_salarie)
                  return (
                    <tr key={r.id_salarie}
                        onClick={() => toggleSel(r.id_salarie)}
                        className="border-b cursor-pointer"
                        style={{
                          borderColor: COL_BORDER,
                          backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                          color: isSel ? 'white' : COL_BRUN,
                        }}>
                      <td className="px-2 py-1.5 text-center">
                        <input type="checkbox" checked={isSel}
                               onChange={() => toggleSel(r.id_salarie)}
                               onClick={e => e.stopPropagation()} />
                      </td>
                      <td className="px-2 py-1.5 font-semibold">{r.nom_prenom}</td>
                      <td className="px-2 py-1.5 text-center">
                        <BoolIcon value={r.agenda_actif} on={isSel} />
                      </td>
                      <td className="px-2 py-1.5 text-center">
                        <BoolIcon value={r.en_activite} on={isSel} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

function BoolIcon({ value, on }: { value: boolean; on: boolean }) {
  if (value) {
    return <CheckCircle2 className="w-4 h-4 inline"
                         style={{ color: on ? 'white' : '#16a34a' }} />
  }
  return <XCircle className="w-4 h-4 inline"
                  style={{ color: on ? 'white' : '#B91C1C' }} />
}
