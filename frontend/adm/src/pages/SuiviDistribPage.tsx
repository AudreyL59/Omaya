/**
 * Fen_SuiviDistrib - Suivi des Distributeurs.
 *
 * Tableau des distributeurs (id_type_orga=3) avec :
 *   - Toggle 'Afficher les distrib inactifs'
 *   - Colonnes : Raison Sociale / SIRET / Date Creation / Num Orias / Nom Gerant
 *   - Ligne rouge si pas de gerant associe
 *   - Cliquer une ligne ouvre FI_DetailDistributeurModal (4 blocs)
 *
 * Cf. WinDev Table_ListeSTE + FI_DétailDistributeur.
 */
import { useCallback, useEffect, useState } from 'react'
import { Building2, Loader2 } from 'lucide-react'
import PageHeader from '@/components/PageHeader'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  useTableSortFilter, SortableTh, FilterInput,
} from '@shared/production/_tableHelpers'
import FI_DetailDistributeurModal from '@/components/distrib/FI_DetailDistributeurModal'

const API_BASE = '/api/adm'

interface Distrib {
  id_ste: string
  raison_sociale: string
  rs_interne: string
  siret: string
  is_actif: boolean
  id_gerant: string
  nom_gerant: string
  num_orias: string
  date_creation: string
}

const shortDate = (iso: string): string =>
  !iso || iso.length < 10
    ? ''
    : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function SuiviDistribPage() {
  useDocumentTitle('Suivi Distributeurs')
  const [showInactifs, setShowInactifs] = useState(false)
  const [rows, setRows] = useState<Distrib[]>([])
  const [loading, setLoading] = useState(false)
  const [detail, setDetail] = useState<{ open: boolean; id_ste: string | null }>({
    open: false,
    id_ste: null,
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/distributeurs?actif=${!showInactifs}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setRows(d.items || [])
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [showInactifs])

  useEffect(() => {
    void load()
  }, [load])

  const tsf = useTableSortFilter(
    rows as unknown as Array<Record<string, unknown>>,
    { key: 'rs_interne', dir: 'asc' },
    (r) =>
      [r.rs_interne, r.raison_sociale, r.siret, r.num_orias, r.nom_gerant]
        .join(' '),
  )
  const visible = tsf.rows as unknown as Distrib[]

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-7xl mx-auto">
        <PageHeader icon={Building2} title="Suivi Distributeurs" />

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between mb-4">
            <FilterInput
              value={tsf.filter}
              onChange={tsf.setFilter}
              placeholder="Rechercher..."
            />
            <label className="flex items-center gap-2 text-sm text-[#8B7355] cursor-pointer">
              <input
                type="checkbox"
                checked={showInactifs}
                onChange={(e) => setShowInactifs(e.target.checked)}
                className="accent-[#8B7355]"
              />
              Afficher les distrib inactifs
            </label>
          </div>

          {loading ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="w-6 h-6 animate-spin text-[#8B7355]" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[#8B7355] border-b border-[#E5E0D5]">
                    <SortableTh label="Raison Sociale" sortKey="raison_sociale"
                      sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="SIRET" sortKey="siret"
                      sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Date Création" sortKey="date_creation"
                      sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Num Orias" sortKey="num_orias"
                      sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Nom Gérant" sortKey="nom_gerant"
                      sort={tsf.sort} onSort={tsf.toggleSort} />
                  </tr>
                </thead>
                <tbody>
                  {visible.map((r) => (
                    <tr
                      key={r.id_ste}
                      onClick={() =>
                        setDetail({ open: true, id_ste: r.id_ste })
                      }
                      className={`cursor-pointer border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${
                        !r.nom_gerant ? 'bg-[#FEE2E2]' : ''
                      }`}
                    >
                      <td className="py-2 px-2">{r.raison_sociale}</td>
                      <td className="py-2 px-2 font-mono text-xs">
                        {r.siret}
                      </td>
                      <td className="py-2 px-2">
                        {shortDate(r.date_creation)}
                      </td>
                      <td className="py-2 px-2">{r.num_orias}</td>
                      <td className="py-2 px-2">
                        {r.nom_gerant || (
                          <span className="text-red-700 italic">
                            PAS DE GERANT ASSOCIE
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {visible.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-gray-400">
                        Aucun distributeur.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          <div className="mt-3 text-xs text-gray-500">
            {visible.length} distributeur{visible.length > 1 ? 's' : ''}
          </div>
        </div>
      </div>

      {detail.open && detail.id_ste && (
        <FI_DetailDistributeurModal
          idSte={detail.id_ste}
          onClose={() => {
            setDetail({ open: false, id_ste: null })
            void load()
          }}
        />
      )}
    </div>
  )
}
