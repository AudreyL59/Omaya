/**
 * SDTCModal : popup partagee Solde De Tout Compte (transposition Fen_SDTC).
 *
 * Composant utilisable depuis n'importe quel intranet :
 *   <SDTCModal
 *     open={open}
 *     onClose={() => setOpen(false)}
 *     getToken={getToken}
 *     idSalarie="123456"
 *   />
 *
 * Scaffold pour cette etape : chargement des donnees de base + onglet
 * 'Resume' fonctionnel (bloc HTML façon WinDev avec nom / societe /
 * adresse / date naiss / num SS / sortie / mutuelle).
 *
 * Onglets restants en placeholder, branches dans des commits dedies :
 *   - Contrats deja traites (grille selection mois + qte)
 *   - Contrats SDTC (selection + valider)
 *   - Resume Solde de tout compte (NB Pts / Comm Pts / Bareme / Total)
 *   - Contrats a editer pour le salarie (grille)
 *   - Recap Ctts pour le BO (recap par produit)
 */

import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Check, CheckSquare, Loader2, Square, Wallet, X } from 'lucide-react'

import { showToast } from '../ui/dialog'

const COLOR_PRIMARY = '#17494E'
const COLOR_BRUN = '#4E1D17'
const COLOR_BG_SOFT = '#EFE9E7'

interface SalarieInfo {
  nom: string
  prenom: string
  lib_nom: string
  num_ss: string
  date_naiss: string
  lieu_naiss: string
  dep_naiss: string
  adresse1: string
  adresse2: string
  cp: string
  ville: string
  date_embauche: string
  date_anciennete: string
  id_ste: string
  lib_societe: string
}

interface SortieInfo {
  date_sortie_reelle: string
  lib_sortie_raw: string
  titre_sortie: string
  kind: string
  courrier_info: string
}

interface SDTCData {
  found: boolean
  id_salarie: string
  salarie: SalarieInfo
  sortie: SortieInfo
  info_mutuelle: string
  date_dernier_ctt: string
}

interface ContratItem {
  id_contrat: string
  partenaire: string
  num_bs: string
  info_interne: string
  lib_produit: string
  type_prod: string
  date_signature: string
  mois_paiement: string
  id_etat_contrat: number
  etat_contrat_lib: string
  id_type_etat: number
  type_etat_lib: string
  couleur_fond: string
  nb_points: number
  client_nom: string
  client_adresse: string
  client_cp: string
  client_ville: string
  client_mail: string
  client_gsm: string
}

interface ContratsData {
  traites: ContratItem[]
  a_traiter: ContratItem[]
  type_etats: Record<string, { lib_type: string; couleur: string }>
}

type Tab =
  | 'resume'
  | 'deja_traites'
  | 'contrats_sdtc'
  | 'resume_stc'
  | 'a_editer'
  | 'recap_bo'

const TABS: { key: Tab; label: string }[] = [
  { key: 'resume',        label: 'Résumé' },
  { key: 'deja_traites',  label: 'Contrats déjà traités' },
  { key: 'contrats_sdtc', label: 'Contrats SDTC' },
  { key: 'resume_stc',    label: 'Résumé Solde de tout compte' },
  { key: 'a_editer',      label: 'Contrats à éditer pour le salarié' },
  { key: 'recap_bo',      label: 'Récap Ctts pour le BO' },
]

interface Props {
  open: boolean
  onClose: () => void
  getToken: () => string | null
  idSalarie: string
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

export default function SDTCModal({ open, onClose, getToken, idSalarie }: Props) {
  const [data, setData] = useState<SDTCData | null>(null)
  const [contrats, setContrats] = useState<ContratsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingContrats, setLoadingContrats] = useState(false)
  const [tab, setTab] = useState<Tab>('resume')
  const [selectedSdtc, setSelectedSdtc] = useState<Set<string>>(new Set())
  const [selectedTraites, setSelectedTraites] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!open || !idSalarie) return
    let cancelled = false
    setLoading(true)
    setLoadingContrats(true)
    setData(null)
    setContrats(null)
    setSelectedSdtc(new Set())
    setSelectedTraites(new Set())
    setTab('resume')
    const auth = { Authorization: `Bearer ${getToken()}` }

    fetch(`/api/shared/sdtc/${idSalarie}/load`, { headers: auth })
      .then(async (r) => {
        if (!r.ok) {
          const j = await r.json().catch(() => ({}))
          throw new Error((j as { detail?: string })?.detail || String(r.status))
        }
        return r.json()
      })
      .then((j) => {
        if (cancelled) return
        setData(j as SDTCData)
      })
      .catch((e) => {
        if (cancelled) return
        showToast(`Échec chargement SDTC : ${e?.message || e}`, 'error')
      })
      .finally(() => !cancelled && setLoading(false))

    fetch(`/api/shared/sdtc/${idSalarie}/contrats`, { headers: auth })
      .then(async (r) => {
        if (!r.ok) {
          const j = await r.json().catch(() => ({}))
          throw new Error((j as { detail?: string })?.detail || String(r.status))
        }
        return r.json()
      })
      .then((j) => {
        if (cancelled) return
        setContrats(j as ContratsData)
      })
      .catch((e) => {
        if (cancelled) return
        showToast(`Échec chargement contrats SDTC : ${e?.message || e}`, 'error')
      })
      .finally(() => !cancelled && setLoadingContrats(false))

    return () => {
      cancelled = true
    }
  }, [open, idSalarie, getToken])

  if (!open) return null

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-[1300px] max-w-[97vw] h-[88vh] flex flex-col overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b" style={{ borderColor: COLOR_BG_SOFT }}>
          <div className="flex items-center gap-2">
            <Wallet className="w-5 h-5" style={{ color: COLOR_PRIMARY }} />
            <h2 className="text-base font-semibold" style={{ color: COLOR_BRUN }}>
              Solde de tout compte
            </h2>
            {data && (
              <span className="text-sm" style={{ color: COLOR_BRUN }}>
                — {data.salarie.lib_nom}
                {data.salarie.lib_societe && (
                  <span style={{ opacity: 0.7 }}> ({data.salarie.lib_societe})</span>
                )}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-[#EFE9E7]"
            style={{ color: COLOR_BRUN }}
            title="Fermer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 px-3 pt-2 border-b" style={{ borderColor: COLOR_BG_SOFT }}>
          {TABS.map((t) => {
            const active = t.key === tab
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                className="px-3 py-1.5 text-sm rounded-t transition"
                style={{
                  color: active ? COLOR_PRIMARY : COLOR_BRUN,
                  backgroundColor: active ? '#ECF1F2' : 'transparent',
                  borderBottom: active ? `2px solid ${COLOR_PRIMARY}` : '2px solid transparent',
                  fontWeight: active ? 600 : 400,
                }}
              >
                {t.label}
              </button>
            )
          })}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading && (
            <div className="flex items-center gap-2 text-sm" style={{ color: COLOR_BRUN }}>
              <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
            </div>
          )}
          {!loading && data && tab === 'resume' && <ResumeTab data={data} />}
          {!loading && data && tab === 'deja_traites' && (
            <DejaTraitesTab
              contrats={contrats}
              loading={loadingContrats}
              selected={selectedTraites}
              setSelected={setSelectedTraites}
            />
          )}
          {!loading && data && tab === 'contrats_sdtc' && (
            <ContratsSDTCTab
              contrats={contrats}
              loading={loadingContrats}
              selected={selectedSdtc}
              setSelected={setSelectedSdtc}
              onValidate={() => {
                showToast(
                  `${selectedSdtc.size} contrat(s) sélectionné(s) — calcul barème à implémenter`,
                  'info',
                )
              }}
            />
          )}
          {!loading && data &&
            tab !== 'resume' &&
            tab !== 'deja_traites' &&
            tab !== 'contrats_sdtc' && (
              <ComingSoon label={TABS.find((t) => t.key === tab)?.label || ''} />
            )}
        </div>
      </motion.div>
    </motion.div>
  )
}

// --- Onglet "Resume" ----------------------------------------------------

function ResumeTab({ data }: { data: SDTCData }) {
  const { salarie, sortie, info_mutuelle, date_dernier_ctt } = data
  return (
    <div className="max-w-3xl mx-auto">
      <div
        className="border rounded-lg p-5"
        style={{ borderColor: COLOR_BG_SOFT, backgroundColor: 'white' }}
      >
        <h3
          className="text-lg font-semibold text-center pb-2 border-b"
          style={{ color: COLOR_BRUN, borderColor: COLOR_BG_SOFT }}
        >
          SOLDE DE TOUT COMPTE
        </h3>
        <p className="text-center font-medium mt-3" style={{ color: COLOR_BRUN }}>
          {salarie.lib_nom}
          {salarie.lib_societe && <span> chez {salarie.lib_societe}</span>}
        </p>

        <p className="text-xs text-center mt-3" style={{ color: COLOR_BRUN }}>
          Entré(e) le {fmtDate(salarie.date_embauche) || '—'}
        </p>
        <p className="text-xs text-center" style={{ color: COLOR_BRUN }}>
          Sorti(e) le {fmtDate(sortie.date_sortie_reelle) || ':'} {sortie.courrier_info}
        </p>

        {sortie.titre_sortie && (
          <p className="text-sm font-semibold text-center mt-3" style={{ color: COLOR_BRUN }}>
            {sortie.titre_sortie}
          </p>
        )}

        <div className="mt-4 space-y-1 text-sm" style={{ color: COLOR_BRUN }}>
          {salarie.adresse1 && <div>{salarie.adresse1}</div>}
          {salarie.adresse2 && <div>{salarie.adresse2}</div>}
          <div>
            {salarie.cp} {salarie.ville}
          </div>
          <div>
            N° SS : {salarie.num_ss || '—'}
          </div>
          <div>
            Né(e) le : {fmtDate(salarie.date_naiss) || '—'} à {salarie.lieu_naiss}
            {salarie.dep_naiss && ` (${salarie.dep_naiss})`}
          </div>
        </div>

        <div className="mt-5 space-y-1 text-sm" style={{ color: COLOR_BRUN }}>
          <Placeholder label="COMM" value="MONTANT_COMM" />
          <Placeholder label="CP" value="MONTANT_CP" />
          <Placeholder label="DECO" value="MONTANT_DECO" />
          <Placeholder label="AVANCE" value="MONTANT_AVANCE" />
          <Placeholder label="Nombre de TR" value="NB_TR" />
          <div>
            Mutuelle Entreprise : <strong>{info_mutuelle}</strong>
          </div>
          <Placeholder label="Absence" value="DATEABS" />
        </div>

        {date_dernier_ctt && (
          <p className="mt-4 text-xs text-emerald-700">
            Dernier contrat signé le {fmtDate(date_dernier_ctt)}
          </p>
        )}

        <p className="mt-4 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
          Cordialement.
        </p>
      </div>

      <p className="mt-4 text-xs text-center" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
        Les montants COMM/CP/DECO/AVANCE/TR et les contrats seront calculés à partir
        des onglets suivants (à venir).
      </p>
    </div>
  )
}

function Placeholder({ label, value }: { label: string; value: string }) {
  return (
    <div>
      {label} :{' '}
      <span className="font-mono text-xs italic" style={{ opacity: 0.6 }}>
        {value}
      </span>
    </div>
  )
}

function ComingSoon({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center h-full text-sm italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
      « {label} » — à brancher dans un prochain commit.
    </div>
  )
}

// --- Helpers communs aux grilles contrats -------------------------------

function fmtFrenchDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

function fmtMoisFr(iso: string): string {
  // 'YYYY-MM' -> 'MM/YYYY'
  if (!iso || iso.length < 7) return ''
  return `${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

const COLS_WIDTHS = {
  select: '38px',
  partenaire: '70px',
  produit: '1fr',
  type_prod: '110px',
  num_bs: '120px',
  date: '90px',
  type_etat: '120px',
  etat: '160px',
  mois: '80px',
} as const

const GRID_TEMPLATE = `${COLS_WIDTHS.select} ${COLS_WIDTHS.partenaire} ${COLS_WIDTHS.produit} ${COLS_WIDTHS.type_prod} ${COLS_WIDTHS.num_bs} ${COLS_WIDTHS.date} ${COLS_WIDTHS.type_etat} ${COLS_WIDTHS.etat}`
const GRID_TEMPLATE_TRAITES = `${GRID_TEMPLATE} ${COLS_WIDTHS.mois}`

interface RowProps {
  ct: ContratItem
  checked: boolean
  onToggle: (id: string) => void
  showMois?: boolean
}

function ContratRow({ ct, checked, onToggle, showMois }: RowProps) {
  return (
    <div
      className="grid items-center gap-2 px-2 py-1 text-xs border-b cursor-pointer"
      style={{
        gridTemplateColumns: showMois ? GRID_TEMPLATE_TRAITES : GRID_TEMPLATE,
        backgroundColor: ct.couleur_fond || '#FFFFFF',
        borderColor: COLOR_BG_SOFT,
        color: COLOR_BRUN,
      }}
      onClick={() => onToggle(ct.id_contrat)}
    >
      <div className="flex justify-center">
        {checked ? (
          <CheckSquare className="w-4 h-4" style={{ color: COLOR_PRIMARY }} />
        ) : (
          <Square className="w-4 h-4" style={{ opacity: 0.4 }} />
        )}
      </div>
      <div className="font-semibold truncate" title={ct.partenaire}>
        {ct.partenaire}
      </div>
      <div className="truncate" title={ct.lib_produit}>
        {ct.lib_produit}
      </div>
      <div className="truncate" title={ct.type_prod}>
        {ct.type_prod}
      </div>
      <div className="truncate" title={ct.num_bs}>
        {ct.num_bs}
      </div>
      <div>{fmtFrenchDate(ct.date_signature)}</div>
      <div className="truncate" title={ct.type_etat_lib}>
        {ct.type_etat_lib}
      </div>
      <div className="truncate" title={ct.etat_contrat_lib}>
        {ct.etat_contrat_lib}
      </div>
      {showMois && <div>{fmtMoisFr(ct.mois_paiement)}</div>}
    </div>
  )
}

function GridHeader({ showMois }: { showMois?: boolean }) {
  return (
    <div
      className="grid items-center gap-2 px-2 py-2 text-xs font-semibold border-b sticky top-0 z-10"
      style={{
        gridTemplateColumns: showMois ? GRID_TEMPLATE_TRAITES : GRID_TEMPLATE,
        color: COLOR_BRUN,
        backgroundColor: COLOR_BG_SOFT,
        borderColor: COLOR_BG_SOFT,
      }}
    >
      <div></div>
      <div>Part.</div>
      <div>Libellé Produit</div>
      <div>Type Prod.</div>
      <div>N° BS</div>
      <div>Date Sign.</div>
      <div>Type État</div>
      <div>État Contrat</div>
      {showMois && <div>Mois Pmt</div>}
    </div>
  )
}

// --- Onglet "Contrats déjà traités" -------------------------------------

interface TabProps {
  contrats: ContratsData | null
  loading: boolean
  selected: Set<string>
  setSelected: (s: Set<string>) => void
}

function DejaTraitesTab({ contrats, loading, selected, setSelected }: TabProps) {
  // Liste distincte des mois de paiement présents (descendant)
  const moisDispos = useMemo(() => {
    if (!contrats) return [] as string[]
    const set = new Set<string>()
    for (const c of contrats.traites) {
      if (c.mois_paiement) set.add(c.mois_paiement)
    }
    return Array.from(set).sort((a, b) => b.localeCompare(a))
  }, [contrats])

  const [moisFiltre, setMoisFiltre] = useState<string>('')

  useEffect(() => {
    if (moisDispos.length > 0 && !moisFiltre) setMoisFiltre(moisDispos[0])
  }, [moisDispos, moisFiltre])

  const filtered = useMemo(() => {
    if (!contrats) return [] as ContratItem[]
    if (!moisFiltre) return contrats.traites
    return contrats.traites.filter((c) => c.mois_paiement === moisFiltre)
  }, [contrats, moisFiltre])

  const toggle = (id: string) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelected(next)
  }

  // "Valider" WinDev : coche toutes les lignes "VALID*" du mois sélectionné
  const validerMois = () => {
    if (!contrats || !moisFiltre) return
    const next = new Set(selected)
    let added = 0
    for (const c of contrats.traites) {
      if (
        c.mois_paiement === moisFiltre &&
        c.type_etat_lib.toUpperCase().includes('VALID')
      ) {
        if (!next.has(c.id_contrat)) {
          next.add(c.id_contrat)
          added++
        }
      }
    }
    setSelected(next)
    showToast(`${added} contrat(s) ajouté(s) à la sélection`, 'info')
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm" style={{ color: COLOR_BRUN }}>
        <Loader2 className="w-4 h-4 animate-spin" /> Chargement des contrats…
      </div>
    )
  }
  if (!contrats || contrats.traites.length === 0) {
    return (
      <div className="text-sm italic" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
        Aucun contrat déjà traité pour ce salarié.
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 pb-2">
        <label className="text-sm" style={{ color: COLOR_BRUN }}>
          Mois de paiement :
        </label>
        <select
          value={moisFiltre}
          onChange={(e) => setMoisFiltre(e.target.value)}
          className="text-sm px-2 py-1 border rounded"
          style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
        >
          <option value="">(tous)</option>
          {moisDispos.map((m) => (
            <option key={m} value={m}>
              {fmtMoisFr(m)}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={validerMois}
          disabled={!moisFiltre}
          className="ml-auto inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded text-white disabled:opacity-40"
          style={{ backgroundColor: COLOR_PRIMARY }}
        >
          <Check className="w-4 h-4" /> Valider (lignes VALID du mois)
        </button>
      </div>
      <div className="text-xs pb-2" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
        {filtered.length} contrat(s) — {selected.size} sélectionné(s)
      </div>
      <div className="flex-1 overflow-y-auto border rounded" style={{ borderColor: COLOR_BG_SOFT }}>
        <GridHeader showMois />
        {filtered.map((c) => (
          <ContratRow
            key={c.id_contrat}
            ct={c}
            checked={selected.has(c.id_contrat)}
            onToggle={toggle}
            showMois
          />
        ))}
      </div>
    </div>
  )
}

// --- Onglet "Contrats SDTC" --------------------------------------------

interface TabSDTCProps extends TabProps {
  onValidate: () => void
}

function ContratsSDTCTab({ contrats, loading, selected, setSelected, onValidate }: TabSDTCProps) {
  const toggle = (id: string) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelected(next)
  }

  const toggleAll = () => {
    if (!contrats) return
    if (selected.size === contrats.a_traiter.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(contrats.a_traiter.map((c) => c.id_contrat)))
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm" style={{ color: COLOR_BRUN }}>
        <Loader2 className="w-4 h-4 animate-spin" /> Chargement des contrats…
      </div>
    )
  }
  if (!contrats || contrats.a_traiter.length === 0) {
    return (
      <div className="text-sm italic" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
        Aucun contrat éligible au SDTC pour ce salarié.
      </div>
    )
  }

  const allSelected = selected.size === contrats.a_traiter.length

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 pb-2">
        <button
          type="button"
          onClick={toggleAll}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded border"
          style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
        >
          {allSelected ? <Square className="w-4 h-4" /> : <CheckSquare className="w-4 h-4" />}
          {allSelected ? 'Tout désélectionner' : 'Tout sélectionner'}
        </button>
        <div className="text-xs" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
          {contrats.a_traiter.length} contrat(s) à traiter — {selected.size} sélectionné(s)
        </div>
        <button
          type="button"
          onClick={onValidate}
          disabled={selected.size === 0}
          className="ml-auto inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded text-white disabled:opacity-40"
          style={{ backgroundColor: COLOR_PRIMARY }}
        >
          <Check className="w-4 h-4" /> Valider la sélection et passer à l'étape suivante
        </button>
      </div>
      <div className="flex-1 overflow-y-auto border rounded" style={{ borderColor: COLOR_BG_SOFT }}>
        <GridHeader />
        {contrats.a_traiter.map((c) => (
          <ContratRow
            key={c.id_contrat}
            ct={c}
            checked={selected.has(c.id_contrat)}
            onToggle={toggle}
          />
        ))}
      </div>
    </div>
  )
}
