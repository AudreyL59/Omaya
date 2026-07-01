/**
 * Picker de societe distributrice (id_type_orga=3, is_actif=true).
 * Cf Fen_RechercheSociete WinDev - version simplifiee : liste
 * des distrib actifs avec un input de filtre.
 */
import { useEffect, useMemo, useState } from 'react'
import { X, Search, Loader2, Building2 } from 'lucide-react'
import { getToken } from '@/api'

const API_BASE = '/api/adm'

interface Societe {
  id_societe_auto: string
  id_ste: string
  id_type_orga: number
  raison_sociale: string
  rs_interne: string
  siret: string
}

interface Props {
  onClose: () => void
  onSelect: (idSte: string, label: string) => void
  excludeIdSte?: string       // pour exclure le distrib courant
}

export default function SocieteDistribPicker({
  onClose, onSelect, excludeIdSte,
}: Props) {
  const [rows, setRows] = useState<Societe[]>([])
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_BASE}/societes?type_orga=3&archivees=false`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then((d: Societe[]) => setRows(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    const qq = q.trim().toLowerCase()
    let list = rows
    if (excludeIdSte) list = list.filter(r => r.id_ste !== excludeIdSte)
    if (qq) list = list.filter(r =>
      r.rs_interne.toLowerCase().includes(qq)
      || r.raison_sociale.toLowerCase().includes(qq)
      || r.siret.toLowerCase().includes(qq),
    )
    return list
  }, [rows, q, excludeIdSte])

  return (
    <div className="fixed inset-0 bg-black/40 z-[80] flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-[600px] max-w-full max-h-[80vh] flex flex-col"
           onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-c-line">
          <h3 className="text-sm font-bold flex items-center gap-2">
            <Building2 className="w-4 h-4 text-c-brand" />
            Choisir un distributeur
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-c-surface-soft rounded">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Filtre */}
        <div className="px-4 py-2 border-b border-c-line-soft flex items-center gap-2">
          <Search className="w-4 h-4 text-c-ink-faint" />
          <input type="text" value={q} onChange={e => setQ(e.target.value)}
            autoFocus
            placeholder="Filtrer par nom ou SIRET..."
            className="flex-1 px-2 py-1 border border-c-line rounded text-xs h-7" />
        </div>

        {/* Liste */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-c-brand" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-8 text-c-ink-faint-2 italic text-xs">
              Aucun distributeur.
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0">
                <tr>
                  <th className="px-2 py-2 text-left">Nom</th>
                  <th className="px-2 py-2 text-left">Raison sociale</th>
                  <th className="px-2 py-2 text-left w-40">SIRET</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-c-line-soft">
                {filtered.map(r => (
                  <tr key={r.id_societe_auto}
                    onClick={() => onSelect(r.id_ste, r.rs_interne)}
                    className="cursor-pointer hover:bg-c-brand/5">
                    <td className="px-2 py-1.5 font-medium">{r.rs_interne}</td>
                    <td className="px-2 py-1.5">{r.raison_sociale}</td>
                    <td className="px-2 py-1.5 tabular-nums">{r.siret}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
