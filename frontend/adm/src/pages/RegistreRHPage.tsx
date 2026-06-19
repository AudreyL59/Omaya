import { useState, useEffect, useMemo, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Loader2, AlertCircle, ExternalLink, FileText, FileSpreadsheet } from 'lucide-react'
import { getToken } from '@/api'
import FicheSalarieModal from '@/components/FicheSalarieModal'

// --- Types ---------------------------------------------------------------

interface SocieteOption {
  id_ste: string
  rs_interne: string
}

interface RefOption {
  id: number
  label: string
}

interface RegistreRefs {
  type_ctt: RefOption[]
  type_horaire: RefOption[]
  type_sortie: RefOption[]
}

interface SalarieRegistre {
  id_salarie: string
  civilite: number
  nom: string
  prenom: string
  sexe: string
  nationalite: string
  date_naiss: string
  lieu_naiss: string
  dep_naiss: number
  num_ss: string
  cpam: string
  num_cin: string
  travailleur_handi: boolean
  adresse1: string
  adresse2: string
  cp: string
  ville: string
  tel_mob: string
  mail: string
  iban: string
  urg_nom: string
  urg_lien: string
  urg_tel: string
  id_ste: string
  date_debut: string
  date_fin_per_essai: string
  dpae_num: string
  dpae_date: string
  id_type_poste: number
  lib_poste: string
  id_type_ctt: number
  id_type_horaire: number
  en_activite: boolean
  coopte: boolean
  coopteur: string
  date_sortie_demandee: string
  date_sortie_reelle: string
  demandeur_sortie: string
  id_type_sortie: number
}

// --- Helpers -------------------------------------------------------------

function formatShortDate(iso: string): string {
  if (!iso) return ''
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/)
  return m ? `${m[3]}/${m[2]}/${m[1]}` : iso
}

const CIVILITE_LIBS: Record<number, string> = { 1: 'M.', 2: 'Mme', 3: 'Mlle' }

function refLabel(refs: RefOption[], id: number): string {
  if (!id) return ''
  const found = refs.find((r) => r.id === id)
  return found ? found.label : ''
}

// --- Page ----------------------------------------------------------------

export default function RegistreRHPage() {
  const [searchParams] = useSearchParams()
  const [ficheOpen, setFicheOpen] = useState<{ id: string; nom: string; prenom: string } | null>(null)
  const autoOpenedRef = useRef(false)

  // Auto-ouverture de la fiche depuis ?ouvrir=<id>&nom=<nom>&prenom=<prenom>
  // (ex: navigation depuis Fen_DPAE_Nouvelle apres 'Terminer ma DPAE').
  useEffect(() => {
    if (autoOpenedRef.current) return
    const id = searchParams.get('ouvrir')
    if (!id) return
    autoOpenedRef.current = true
    setFicheOpen({
      id,
      nom: searchParams.get('nom') || '',
      prenom: searchParams.get('prenom') || '',
    })
  }, [searchParams])
  const [societes, setSocietes] = useState<SocieteOption[]>([])
  const [refs, setRefs] = useState<RegistreRefs | null>(null)
  const [selectedSte, setSelectedSte] = useState<string>('')
  const [salaries, setSalaries] = useState<SalarieRegistre[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [loadingSte, setLoadingSte] = useState(false)
  const [loadingList, setLoadingList] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string>('')

  // Charge societes + refs en parallele au mount
  useEffect(() => {
    let cancelled = false
    setLoadingSte(true)
    Promise.all([
      fetch('/api/adm/registre-rh/societes', {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) => (r.ok ? r.json() : Promise.reject(r.status))),
      fetch('/api/adm/registre-rh/refs', {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) => (r.ok ? r.json() : Promise.reject(r.status))),
    ])
      .then(([stes, rfs]) => {
        if (cancelled) return
        setSocietes(stes)
        setRefs(rfs)
        // Auto-selectionne la 1re societe pour eviter l'ecran vide
        if (stes.length > 0 && !selectedSte) {
          setSelectedSte(stes[0].id_ste)
        }
      })
      .catch((e) => !cancelled && setError(`Chargement initial : ${e}`))
      .finally(() => !cancelled && setLoadingSte(false))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Charge la liste des salaries quand la societe change
  useEffect(() => {
    if (!selectedSte) {
      setSalaries([])
      return
    }
    let cancelled = false
    setLoadingList(true)
    setError('')
    fetch(`/api/adm/registre-rh?id_ste=${encodeURIComponent(selectedSte)}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data: SalarieRegistre[]) => {
        if (cancelled) return
        setSalaries(data)
        setSelectedId('')
      })
      .catch((e) => !cancelled && setError(`Chargement salaries : ${e}`))
      .finally(() => !cancelled && setLoadingList(false))
    return () => {
      cancelled = true
    }
  }, [selectedSte])

  const selectedSalarie = useMemo(
    () => salaries.find((s) => s.id_salarie === selectedId) || null,
    [salaries, selectedId],
  )

  const openFiche = (s: SalarieRegistre) =>
    setFicheOpen({ id: s.id_salarie, nom: s.nom, prenom: s.prenom })

  // Export Excel : telecharge le .xlsx genere par le backend
  const handleExport = async () => {
    if (!selectedSte) return
    setExporting(true)
    try {
      const r = await fetch(
        `/api/adm/registre-rh/export.xlsx?id_ste=${encodeURIComponent(selectedSte)}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        alert(`Export Excel : echec (${j?.detail || r.status})`)
        return
      }
      // Recupere le filename depuis Content-Disposition si dispo, sinon fallback
      const cd = r.headers.get('Content-Disposition') || ''
      const m = cd.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/)
      const filename = m ? decodeURIComponent(m[1]) : `Registre_RH_${selectedSte}.xlsx`

      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="px-6 py-4 border-b border-c-line flex items-center gap-4">
        <FileText className="w-5 h-5 text-c-brand" />
        <h1 className="text-lg font-semibold text-c-ink">Registre RH</h1>

        <div className="flex-1" />

        {/* Combo Societe */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-c-ink-soft">Société :</label>
          <select
            value={selectedSte}
            onChange={(e) => setSelectedSte(e.target.value)}
            disabled={loadingSte || societes.length === 0}
            className="px-3 py-1.5 border border-c-line rounded text-sm bg-white min-w-[240px] focus:border-c-brand focus:outline-none disabled:opacity-50"
          >
            {societes.length === 0 ? (
              <option value="">Aucune société</option>
            ) : (
              societes.map((s) => (
                <option key={s.id_ste} value={s.id_ste}>
                  {s.rs_interne}
                </option>
              ))
            )}
          </select>
        </div>

        {/* Bouton "Exporter Excel" */}
        <button
          onClick={handleExport}
          disabled={!selectedSte || exporting || salaries.length === 0}
          className="flex items-center gap-2 px-3 py-1.5 border border-emerald-700 text-emerald-700 rounded text-sm hover:bg-emerald-50 disabled:opacity-40 disabled:cursor-not-allowed"
          title="Telecharger le registre au format Excel (.xlsx)"
        >
          {exporting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <FileSpreadsheet className="w-4 h-4" />
          )}
          Exporter Excel
        </button>

        {/* Bouton "Voir Fiche Salarie" - ouvre la popup */}
        <button
          onClick={() => selectedSalarie && openFiche(selectedSalarie)}
          disabled={!selectedSalarie}
          className="flex items-center gap-2 px-3 py-1.5 border border-c-brand text-c-brand rounded text-sm hover:bg-c-brand-soft disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <ExternalLink className="w-4 h-4" />
          Voir Fiche Salarié
        </button>
      </div>

      {/* Erreur */}
      {error && (
        <div className="px-6 py-2 bg-red-50 border-b border-red-200 text-red-700 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Tableau */}
      <div className="flex-1 overflow-auto">
        {loadingList ? (
          <div className="flex items-center justify-center h-40 text-c-ink-soft">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            Chargement…
          </div>
        ) : salaries.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-c-ink-faint italic text-sm">
            {selectedSte ? 'Aucun salarié pour cette société' : 'Sélectionne une société'}
          </div>
        ) : (
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-c-bg-soft z-10">
              <tr className="text-left text-c-ink-soft border-b border-c-line">
                <Th>Civilité</Th>
                <Th>Nom</Th>
                <Th>Prénom</Th>
                <Th>Nationalité</Th>
                <Th>Sexe</Th>
                <Th>N° Sécu Soc</Th>
                <Th>Date Naiss</Th>
                <Th>Lieu Naiss</Th>
                <Th>Dép Naiss</Th>
                <Th>Adresse 1</Th>
                <Th>Adresse 2</Th>
                <Th>CP</Th>
                <Th>Ville</Th>
                <Th>N° CIN</Th>
                <Th>DPAE n°</Th>
                <Th>En activité</Th>
                <Th>Date début</Th>
                <Th>Type contrat</Th>
                <Th>Poste</Th>
                <Th>Date sortie demandée</Th>
                <Th>Date sortie réelle</Th>
                <Th>Type sortie</Th>
                <Th>Type horaire</Th>
                <Th>RQTH</Th>
              </tr>
            </thead>
            <tbody>
              {salaries.map((s) => {
                const isSelected = s.id_salarie === selectedId
                return (
                  <tr
                    key={s.id_salarie}
                    onClick={() => setSelectedId(s.id_salarie)}
                    onDoubleClick={() => openFiche(s)}
                    className={`border-b border-c-line-soft cursor-pointer transition ${
                      isSelected ? 'bg-c-brand-soft' : 'hover:bg-c-bg-soft'
                    }`}
                  >
                    <Td>{CIVILITE_LIBS[s.civilite] || ''}</Td>
                    <Td className="font-medium">{s.nom}</Td>
                    <Td>{s.prenom}</Td>
                    <Td>{s.nationalite}</Td>
                    <Td>{s.sexe}</Td>
                    <Td className="font-mono">{s.num_ss}</Td>
                    <Td>{formatShortDate(s.date_naiss)}</Td>
                    <Td>{s.lieu_naiss}</Td>
                    <Td>{s.dep_naiss || ''}</Td>
                    <Td>{s.adresse1}</Td>
                    <Td>{s.adresse2}</Td>
                    <Td>{s.cp}</Td>
                    <Td>{s.ville}</Td>
                    <Td className="font-mono">{s.num_cin}</Td>
                    <Td className="font-mono">{s.dpae_num}</Td>
                    <Td>
                      {s.en_activite ? (
                        <span className="text-emerald-700 font-semibold">Oui</span>
                      ) : (
                        <span className="text-c-ink-faint">Non</span>
                      )}
                    </Td>
                    <Td>{formatShortDate(s.date_debut)}</Td>
                    <Td>{refs ? refLabel(refs.type_ctt, s.id_type_ctt) : ''}</Td>
                    <Td>{s.lib_poste}</Td>
                    <Td>{formatShortDate(s.date_sortie_demandee)}</Td>
                    <Td>{formatShortDate(s.date_sortie_reelle)}</Td>
                    <Td>{refs ? refLabel(refs.type_sortie, s.id_type_sortie) : ''}</Td>
                    <Td>{refs ? refLabel(refs.type_horaire, s.id_type_horaire) : ''}</Td>
                    <Td>{s.travailleur_handi ? 'Oui' : ''}</Td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Total bas */}
      {!loadingList && salaries.length > 0 && (
        <div className="px-6 py-2 border-t border-c-line text-xs text-c-ink-soft bg-c-bg-soft">
          {salaries.length} salarié{salaries.length > 1 ? 's' : ''} (
          {salaries.filter((s) => s.en_activite).length} en activité)
        </div>
      )}

      <AnimatePresence>
        {ficheOpen && (
          <FicheSalarieModal
            idSalarie={ficheOpen.id}
            nom={ficheOpen.nom}
            prenom={ficheOpen.prenom}
            onClose={() => setFicheOpen(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// --- Cellules de tableau -------------------------------------------------

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-2 py-1.5 font-semibold whitespace-nowrap">{children}</th>
}

function Td({
  children,
  className = '',
}: {
  children: React.ReactNode
  className?: string
}) {
  return <td className={`px-2 py-1.5 whitespace-nowrap ${className}`}>{children}</td>
}
