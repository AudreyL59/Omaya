/**
 * Fen_DPAE_Recherche (transposition WinDev) - ADM, section Salaries.
 *
 * 3 champs : Nom, Prenom, Mobile (si Mobile rempli, prio sur les telephones,
 * sinon match Nom+Prenom).
 *
 * Resultats fusionnes : registre RH (salaries) + cvtheque (candidats).
 * - Lignes CV avec un RDV existant : fond vert pale (RVB 168,220,168)
 * - Lignes registre RH avec en_activite=true : message "ATTENTION, toujours
 *   en activite" en colonne "Infos cplt"
 *
 * Actions :
 *  - DPAE vierge : ouvre Fen_DPAE_Nouvelle avec TypeDpae=0 (sans pre-remplir)
 *  - Demarrer la DPAE : sur la ligne selectionnee
 *     - CV       -> TypeDpae=1, IdElement=id_cvtheque, IdcvSuiv=id_cv_suivi
 *     - Reg RH actif  -> TypeDpae=3
 *     - Reg RH sorti  -> TypeDpae=2
 *  - Vider le tableau : reset les resultats
 */

import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Eraser, Loader2, Play, Search, UserPlus } from 'lucide-react'

import { getToken } from '@/api'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'
import { showToast } from '@shared/ui/dialog'

interface DpaeRow {
  origine: 'CV' | 'Registre RH'
  id_elem: string
  id_cv_suivi: string
  identite: string
  cp: string
  ville: string
  date_entree_rdv: string
  en_activite: boolean
  infos_cplt: string
  ligne_rdv: boolean
}

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_VERT_RDV = '#A8DCA8' // RVB(168,220,168)
const COL_BORDER = '#E5DDDC'

function isoToFr(s: string): string {
  if (!s || s.length < 10) return ''
  return `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}`
}

export default function DpaeRecherchePage() {
  useDocumentTitle('DPAE — Recherche')
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const idTicket = searchParams.get('id_ticket') || '0'

  // Pre-remplissage depuis les query params (cas : btn 'Demarrer la DPAE'
  // d'un ticket FI_DPAE - cf. WinDev qui injecte GSM ou NOM+PRENOM puis
  // declenche la recherche).
  const [nom, setNom] = useState(searchParams.get('nom') || '')
  const [prenom, setPrenom] = useState(searchParams.get('prenom') || '')
  const [gsm, setGsm] = useState(searchParams.get('gsm') || '')
  const [rows, setRows] = useState<DpaeRow[]>([])
  const [selected, setSelected] = useState<number>(-1)
  const [loading, setLoading] = useState(false)
  const autoSearchedRef = useRef(false)

  const doSearch = async () => {
    if (!nom.trim() && !prenom.trim() && !gsm.trim()) {
      showToast('Saisis au moins un critère.', 'info')
      return
    }
    setLoading(true)
    try {
      const r = await fetch('/api/adm/dpae/recherche', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ nom, prenom, gsm }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const data = (await r.json()) as DpaeRow[]
      setRows(data)
      setSelected(data.length > 0 ? 0 : -1)
    } catch (e) {
      showToast(`Échec recherche : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  // Recherche automatique au mount si les query params contiennent deja
  // des criteres (cas : btn 'Demarrer la DPAE' d'un ticket).
  useEffect(() => {
    if (autoSearchedRef.current) return
    if (nom.trim() || prenom.trim() || gsm.trim()) {
      autoSearchedRef.current = true
      doSearch()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleStartDpae = (typeDpae: number, idElem: string, idCvSuiv: string) => {
    const q = new URLSearchParams({
      id_ticket: idTicket,
      type_dpae: String(typeDpae),
      id_elem: idElem,
      id_cv_suivi: idCvSuiv,
    }).toString()
    navigate(`/salaries/dpae/nouvelle?${q}`)
  }

  const handleDpaeVierge = () => handleStartDpae(0, '0', '0')

  const handleStartFromSelection = () => {
    if (selected < 0) {
      showToast('Sélectionne une ligne ou clique sur "DPAE vierge".', 'info')
      return
    }
    const row = rows[selected]
    let typeDpae = 0
    let idCvSuiv = '0'
    if (row.origine === 'CV') {
      typeDpae = 1
      idCvSuiv = row.id_cv_suivi || '0'
    } else {
      typeDpae = row.en_activite ? 3 : 2
    }
    handleStartDpae(typeDpae, row.id_elem, idCvSuiv)
  }

  return (
    <div className="p-6 max-w-7xl mx-auto font-normal">
      <PageHeader icon={Search} title="DPAE - Recherche" />

      {/* Toolbar : 3 inputs + Loupe + DPAE vierge + Demarrer la DPAE */}
      <div
        className="bg-white rounded-lg shadow-sm p-4 mb-4 border"
        style={{ borderColor: COL_BORDER }}
      >
        <div className="flex flex-wrap items-end gap-3">
          <input
            type="text"
            placeholder="Nom"
            value={nom}
            onChange={(e) => setNom(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && doSearch()}
            className="flex-1 min-w-[180px] px-3 py-2 border rounded-md text-sm"
            style={{ borderColor: COL_BORDER, color: COL_BRUN }}
          />
          <input
            type="text"
            placeholder="Prénom"
            value={prenom}
            onChange={(e) => setPrenom(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && doSearch()}
            className="flex-1 min-w-[180px] px-3 py-2 border rounded-md text-sm"
            style={{ borderColor: COL_BORDER, color: COL_BRUN }}
          />
          <input
            type="text"
            placeholder="Mobile"
            value={gsm}
            onChange={(e) => setGsm(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && doSearch()}
            className="flex-1 min-w-[180px] px-3 py-2 border rounded-md text-sm"
            style={{ borderColor: COL_BORDER, color: COL_BRUN }}
          />
          <button
            type="button"
            onClick={doSearch}
            disabled={loading}
            className="p-2 border rounded-md hover:bg-[#EFE9E7] disabled:opacity-50"
            style={{ borderColor: COL_BORDER, color: COL_BRUN }}
            title="Rechercher"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Search className="w-5 h-5" />
            )}
          </button>
          <button
            type="button"
            onClick={handleDpaeVierge}
            className="flex items-center gap-2 px-4 py-2 border rounded-md text-sm hover:bg-[#EFE9E7]"
            style={{ borderColor: COL_BORDER, color: COL_BRUN }}
          >
            <UserPlus className="w-4 h-4" />
            DPAE vierge
          </button>
          <button
            type="button"
            onClick={handleStartFromSelection}
            disabled={rows.length === 0}
            className="flex items-center gap-2 px-4 py-2 rounded-md text-sm text-white disabled:opacity-50"
            style={{ backgroundColor: COL_PRIMARY }}
          >
            <Play className="w-4 h-4" />
            Démarrer la DPAE
          </button>
        </div>
        <p className="mt-3 text-xs text-[#A68D8A]">
          Si aucun résultat ne correspond à votre recherche, cliquez sur "Vider le
          tableau" et ensuite sur "Démarrer la DPAE" pour en démarrer une vierge.
        </p>
      </div>

      {/* Tableau */}
      <div
        className="bg-white rounded-lg shadow-sm overflow-hidden border"
        style={{ borderColor: COL_BORDER }}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
              <tr>
                <Th>Identité</Th>
                <Th>Origine</Th>
                <Th>Adresse</Th>
                <Th>CP</Th>
                <Th>Ville</Th>
                <Th>Date entrée / RDV</Th>
                <Th>Infos cplt</Th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="text-center py-10 text-[#A68D8A] italic"
                  >
                    {loading
                      ? 'Recherche en cours...'
                      : 'Aucun résultat — saisis un critère et clique sur la loupe.'}
                  </td>
                </tr>
              ) : (
                rows.map((r, i) => {
                  const bg =
                    selected === i
                      ? COL_PRIMARY
                      : r.ligne_rdv
                        ? COL_VERT_RDV
                        : 'white'
                  const color = selected === i ? 'white' : COL_BRUN
                  return (
                    <tr
                      key={i}
                      onClick={() => setSelected(i)}
                      onDoubleClick={handleStartFromSelection}
                      className="cursor-pointer border-b"
                      style={{
                        backgroundColor: bg,
                        color,
                        borderColor: COL_BORDER,
                      }}
                    >
                      <Td>{r.identite}</Td>
                      <Td>{r.origine}</Td>
                      <Td>—</Td>
                      <Td>{r.cp}</Td>
                      <Td>{r.ville}</Td>
                      <Td>{isoToFr(r.date_entree_rdv)}</Td>
                      <Td>{r.infos_cplt}</Td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Footer : Vider le tableau */}
        {rows.length > 0 && (
          <div
            className="flex justify-end p-3 border-t"
            style={{ borderColor: COL_BORDER }}
          >
            <button
              type="button"
              onClick={() => {
                setRows([])
                setSelected(-1)
              }}
              className="flex items-center gap-2 px-3 py-1.5 border rounded-md text-sm hover:bg-[#EFE9E7]"
              style={{ borderColor: COL_BORDER, color: COL_BRUN }}
            >
              <Eraser className="w-4 h-4" />
              Vider le tableau
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide">
      {children}
    </th>
  )
}

function Td({ children }: { children: React.ReactNode }) {
  return <td className="px-3 py-2 whitespace-nowrap">{children}</td>
}
