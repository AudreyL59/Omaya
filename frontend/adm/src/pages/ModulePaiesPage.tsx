/**
 * Fen_PaiesBS - Module paies.
 *
 * Ecran principal :
 *  1. Choisir salarié + Mois paiement + Simu + Lister + Toggle inactifs
 *  2. Bloc partenaires (checkbox + Du/Au signé + Du/Au hors délai par partenaire)
 *  3. Bouton "Lister les contrats"
 *  4. Bloc résultats : Date Racc SFR limite + Valider les paies + NB TR
 *  5. 4 onglets : Contrats Signés / Décommission / Jours non Prod TR / Base PDF
 */
import { useCallback, useState } from 'react'
import {
  ArrowLeft, Wallet, Loader2, Check, Search, Play,
  Download,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PersonnePicker, { type SalarieItem } from '@/components/PersonnePicker'

const API_BASE = '/api/adm'

interface PartenaireCfg {
  prefixe: string
  lib: string        // libellé pour l'UI
  is_actif: boolean
}

const _PARTENAIRES: PartenaireCfg[] = [
  { prefixe: 'ENI', lib: 'PLENITUDE',  is_actif: true },
  { prefixe: 'SFR', lib: 'SFR',        is_actif: true },
  { prefixe: 'IAG', lib: 'IAG',        is_actif: true },
  { prefixe: 'OEN', lib: 'OHM ENERGIE', is_actif: true },
  { prefixe: 'PRO', lib: 'PROTECTED',  is_actif: true },
  { prefixe: 'STR', lib: 'STRATO',     is_actif: true },
  { prefixe: 'VAL', lib: 'VALANDRE',   is_actif: true },
]

interface PartenaireState {
  prefixe: string
  is_actif: boolean
  coche: boolean
  signe_du: string
  signe_au: string
  hors_delai_du: string
  hors_delai_au: string
}

interface ContratRow {
  id_contrat: string
  partenaire: string
  lib_produit: string
  type_prod: string
  num_bs: string
  date_signature: string
  id_type_etat: number
  type_etat: string
  id_etat: number
  etat_contrat: string
  vendeur_nom: string
  agence: string
  equipe: string
  client_nom: string
  client_cp: string
  client_ville: string
  mois_paiement: string
  nb_points: number
  couleur_fond: string
  car?: number
  elec_actif?: boolean
  gaz_actif?: boolean
  puissance?: number
  opt_e_verte_elec?: boolean
  opt_e_verte_gaz?: boolean
  opt_mail?: boolean
  opt_reforestation?: boolean
  opt_protection?: boolean
  opt_entretien?: boolean
  date_racc_valid?: string
  date_rdv_tech?: string
  date_validation?: string
  id_etat_sfr?: number
  techno?: number
  type_vente?: number
  portabilite?: boolean
  notation_client?: number
  prise_saisie?: boolean
  pts_porta?: number
  pts_prises?: number
  pts_notation?: number
}

interface JourNonProd {
  jour: string
  eni: boolean
  fibre: boolean
}

interface NbCttParJourRow {
  date_ctt: string
  nb_ctt: number
  type_ctt: number
}

type Tab = 'signes' | 'decomm' | 'non_prod' | 'base_pdf'

const shortDate = (iso: string): string =>
  !iso || iso.length < 10
    ? ''
    : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

const firstOfMonth = (): string => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}
const lastOfMonth = (): string => {
  const d = new Date()
  const last = new Date(d.getFullYear(), d.getMonth() + 1, 0)
  return `${last.getFullYear()}-${String(last.getMonth() + 1).padStart(2, '0')}-${String(last.getDate()).padStart(2, '0')}`
}

const currentMoisPaie = (): string => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

// ---------------------------------------------------------------------

function PartenaireCell({
  p, onChange,
}: {
  p: PartenaireState
  onChange: (v: PartenaireState) => void
}) {
  const isSFR = p.prefixe === 'SFR'
  const inputCls =
    'w-full min-w-0 px-2 py-1 border border-[#E5E0D5] rounded text-xs bg-white disabled:bg-[#F5F5F0] disabled:cursor-not-allowed'
  return (
    <div
      className={`border rounded-lg p-3 ${
        p.coche ? 'border-[#8B7355] bg-white' : 'border-[#E5E0D5] bg-[#FCFAF5] opacity-60'
      }`}
    >
      <label className="flex items-center gap-2 mb-3 cursor-pointer">
        <input
          type="checkbox"
          checked={p.coche}
          onChange={(e) => onChange({ ...p, coche: e.target.checked })}
          className="accent-[#8B7355]"
        />
        <span className="font-semibold text-[#8B7355]">{p.prefixe}</span>
      </label>

      {/* Signé */}
      <div className="mb-2">
        <div className="text-[10px] uppercase tracking-wider text-[#8B7355] font-semibold mb-1">
          Signé
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          <div className="flex flex-col">
            <span className="text-[10px] text-gray-500 mb-0.5">Du</span>
            <input
              type="date"
              value={p.signe_du}
              onChange={(e) => onChange({ ...p, signe_du: e.target.value })}
              className={inputCls}
              disabled={!p.coche}
            />
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] text-gray-500 mb-0.5">Au</span>
            <input
              type="date"
              value={p.signe_au}
              onChange={(e) => onChange({ ...p, signe_au: e.target.value })}
              className={inputCls}
              disabled={!p.coche}
            />
          </div>
        </div>
      </div>

      {/* Hors Délai (pas pour SFR) */}
      {!isSFR && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-[#8B7355] font-semibold mb-1">
            Hors Délai
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            <div className="flex flex-col">
              <span className="text-[10px] text-gray-500 mb-0.5">Du</span>
              <input
                type="date"
                value={p.hors_delai_du}
                onChange={(e) => onChange({ ...p, hors_delai_du: e.target.value })}
                className={inputCls}
                disabled={!p.coche}
              />
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-gray-500 mb-0.5">Au</span>
              <input
                type="date"
                value={p.hors_delai_au}
                onChange={(e) => onChange({ ...p, hors_delai_au: e.target.value })}
                className={inputCls}
                disabled={!p.coche}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------

export default function ModulePaiesPage() {
  useDocumentTitle('Module Paies')
  const [salarie, setSalarie] = useState<SalarieItem | null>(null)
  const [showPicker, setShowPicker] = useState(false)
  const [moisPaie, setMoisPaie] = useState<string>(currentMoisPaie())
  const [simu, setSimu] = useState(true)
  const [afficherInactifs, setAfficherInactifs] = useState(false)

  const [parts, setParts] = useState<PartenaireState[]>(
    _PARTENAIRES.map((p) => ({
      prefixe: p.prefixe,
      is_actif: p.is_actif,
      coche: p.prefixe === 'ENI' || p.prefixe === 'SFR',
      signe_du: firstOfMonth(),
      signe_au: lastOfMonth(),
      hors_delai_du: firstOfMonth(),
      hors_delai_au: lastOfMonth(),
    })),
  )

  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)

  const [contratsSignes, setContratsSignes] = useState<ContratRow[]>([])
  const [contratsDecomm, setContratsDecomm] = useState<ContratRow[]>([])
  const [joursNonProd, setJoursNonProd] = useState<JourNonProd[]>([])
  const [nbCttParJour, setNbCttParJour] = useState<NbCttParJourRow[]>([])
  const [nbTr, setNbTr] = useState(0)
  const [hasEni, setHasEni] = useState(false)
  const [hasSfr, setHasSfr] = useState(false)
  const [dateRaccLimite, setDateRaccLimite] = useState(lastOfMonth())

  const [tab, setTab] = useState<Tab>('signes')

  const partsVisibles = afficherInactifs
    ? parts
    : parts.filter((p) => p.is_actif)

  // ------ Btn Lister les contrats ------
  const doLister = useCallback(async () => {
    if (!salarie) {
      showToast('Choisis un salarié', 'info')
      return
    }
    if (!moisPaie.match(/^\d{4}-\d{2}$/)) {
      showToast('Mois paiement invalide (YYYY-MM)', 'error')
      return
    }
    setLoading(true)
    setContratsSignes([])
    setContratsDecomm([])
    setJoursNonProd([])
    setNbCttParJour([])
    setNbTr(0)
    try {
      const r = await fetch(`${API_BASE}/paies/lister-contrats`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_salarie: salarie.id_salarie,
          mois_paiement: moisPaie,
          partenaires: parts
            .filter((p) => p.coche)
            .map((p) => ({
              prefixe: p.prefixe,
              is_actif: true,
              signe_du: p.signe_du,
              signe_au: p.signe_au,
              hors_delai_du: p.hors_delai_du,
              hors_delai_au: p.hors_delai_au,
            })),
          afficher_part_inactifs: afficherInactifs,
        }),
      })
      const d = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur', 'error')
        return
      }
      setContratsSignes(d.contrats_signes || [])
      setContratsDecomm(d.contrats_decomm || [])
      setJoursNonProd(d.jours_non_prod || [])
      setHasEni(!!d.has_eni)
      setHasSfr(!!d.has_sfr)
      showToast(d.message || 'Recherche terminée', 'success')
      setTab('signes')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [salarie, moisPaie, parts, afficherInactifs])

  // ------ Btn Valider les paies ------
  const doValider = useCallback(async () => {
    if (contratsSignes.length === 0) {
      showToast('Aucun contrat à valider (lance d\'abord la recherche)', 'info')
      return
    }
    if (!salarie) return
    const ok1 = await showConfirm({
      title: 'Valider la paie',
      message: `Voulez-vous valider la paye pour ${salarie.nom} ${salarie.prenom} ?\nMois : ${moisPaie}`,
    })
    if (!ok1) return
    if (!simu) {
      const ok2 = await showConfirm({
        title: 'Confirmation',
        message: 'Ceci n\'est pas une simulation, souhaitez-vous continuer ?',
        variant: 'danger',
      })
      if (!ok2) return
    }
    setValidating(true)
    try {
      const r = await fetch(`${API_BASE}/paies/valider-paies`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_salarie: salarie.id_salarie,
          mois_paiement: moisPaie,
          date_racc_limite: dateRaccLimite,
          simulation: simu,
          contrats: contratsSignes.map((c) => ({
            id_contrat: c.id_contrat,
            partenaire: c.partenaire,
            id_type_etat: c.id_type_etat,
            id_etat: c.id_etat,
            type_etat: c.type_etat,
            etat_contrat: c.etat_contrat,
            type_prod: c.type_prod,
            date_signature: c.date_signature,
            mois_paiement: c.mois_paiement,
            nb_points: c.nb_points,
            date_racc_valid: c.date_racc_valid || '',
          })),
        }),
      })
      const d = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur', 'error')
        return
      }
      // Applique le résultat aux contrats affichés
      const majMap = new Map(
        (d.contrats_maj || []).map((m: {
          id_contrat: string
          id_etat: number
          id_type_etat: number
          etat_contrat: string
          type_etat: string
          mois_paiement: string
        }) => [m.id_contrat, m]),
      )
      setContratsSignes((rows) =>
        rows.map((r) => {
          const m = majMap.get(r.id_contrat) as {
            id_etat: number
            id_type_etat: number
            etat_contrat: string
            type_etat: string
            mois_paiement: string
          } | undefined
          return m
            ? {
                ...r,
                id_etat: m.id_etat,
                id_type_etat: m.id_type_etat,
                etat_contrat: m.etat_contrat,
                type_etat: m.type_etat,
                mois_paiement: m.mois_paiement,
              }
            : r
        }),
      )
      setNbCttParJour(d.nb_ctt_par_jour || [])
      setNbTr(d.nb_tr || 0)
      showToast(d.message || 'Paies validées', 'success')
      // Lance la génération PDF
      void doGeneratePdf()
    } finally {
      setValidating(false)
    }
  }, [salarie, moisPaie, dateRaccLimite, simu, contratsSignes])

  // ------ Génération PDF ------
  const doGeneratePdf = useCallback(async () => {
    if (!salarie) return
    setPdfLoading(true)
    try {
      const r = await fetch(`${API_BASE}/paies/generation-base-pdf`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_salarie: salarie.id_salarie,
          mois_paiement: moisPaie,
          contrats: contratsSignes.map((c) => ({
            vendeur: c.vendeur_nom,
            num_bs: c.num_bs,
            signe_le: c.date_signature,
            nom_produit: c.lib_produit,
            etat: c.etat_contrat,
            mois_paiement: c.mois_paiement,
            car: c.car ? String(c.car) : '',
            date_racc_activ: c.date_racc_valid || '',
            type_vente: c.type_vente ? String(c.type_vente) : '',
            portabilite: !!c.portabilite,
            prise_saisie: !!c.prise_saisie,
            note: c.notation_client || 0,
            nb_pts: c.nb_points || 0,
          })),
          has_eni: hasEni,
          has_sfr: hasSfr,
        }),
      })
      const d = await r.json()
      if (!d.ok) {
        showToast(d.message || 'Erreur PDF', 'error')
        return
      }
      // Ouvre le PDF dans un nouvel onglet
      const bytes = atob(d.pdf_b64)
      const buf = new Uint8Array(bytes.length)
      for (let i = 0; i < bytes.length; i++) buf[i] = bytes.charCodeAt(i)
      const blob = new Blob([buf], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
      showToast(d.message || 'PDF généré', 'success')
    } finally {
      setPdfLoading(false)
    }
  }, [salarie, moisPaie, contratsSignes, hasEni, hasSfr])

  const bgFromCouleur = (c: string): string => {
    if (c === 'hors_delai') return 'bg-[#F8EDA5]'
    if (c === 'rejet_resil') return 'bg-[#FED2D2]'
    return ''
  }

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-[1600px] mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <Link to="/" className="p-2 rounded hover:bg-white/50" title="Retour">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <Wallet className="w-6 h-6 text-[#8B7355]" />
          <h1 className="text-2xl font-semibold text-[#8B7355]">Module Paies</h1>
        </div>

        {/* Bloc header : salarié + mois + toggles */}
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <div className="flex items-center gap-4 flex-wrap">
            <button
              onClick={() => setShowPicker(true)}
              className="flex items-center gap-2 px-3 py-2 rounded bg-[#8B7355] text-white hover:bg-[#725e46]"
            >
              <Search className="w-4 h-4" />
              {salarie
                ? `${salarie.nom} ${salarie.prenom}`
                : 'Choisir le salarié'}
            </button>
            <label className="flex flex-col text-xs gap-1">
              <span className="text-[#8B7355] font-medium">
                Mois Paiement (MM-AAAA)
              </span>
              <input
                type="month"
                value={moisPaie}
                onChange={(e) => setMoisPaie(e.target.value)}
                className="px-2 py-1 border border-[#E5E0D5] rounded"
              />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={simu}
                onChange={(e) => setSimu(e.target.checked)}
                className="accent-[#8B7355]"
              />
              <span className="text-[#8B7355] font-medium">
                Faire une simulation
              </span>
            </label>
            <label className="ml-auto flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={afficherInactifs}
                onChange={(e) => setAfficherInactifs(e.target.checked)}
                className="accent-[#8B7355]"
              />
              <span className="text-[#8B7355] font-medium">
                Afficher Part. inactifs
              </span>
            </label>
          </div>
        </div>

        {/* Bloc partenaires */}
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <h2 className="text-sm font-semibold text-[#8B7355] uppercase tracking-wider mb-3">
            Choisir les partenaires
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {partsVisibles.map((p) => (
              <PartenaireCell
                key={p.prefixe}
                p={p}
                onChange={(v) =>
                  setParts((ps) =>
                    ps.map((x) => (x.prefixe === p.prefixe ? v : x)),
                  )
                }
              />
            ))}
          </div>
          <div className="mt-4 flex justify-end">
            <button
              onClick={doLister}
              disabled={loading || !salarie}
              className="flex items-center gap-2 px-4 py-2 rounded bg-[#059669] text-white disabled:opacity-40 hover:bg-[#047857]"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Lister les contrats
            </button>
          </div>
        </div>

        {/* Bloc résultats */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-4 flex-wrap mb-4">
            <h2 className="text-sm font-semibold text-[#8B7355] uppercase tracking-wider">
              Liste des contrats trouvés
            </h2>
            <label className="flex flex-col text-xs gap-1 ml-4">
              <span className="text-[#8B7355] font-medium">
                Date Racc SFR limite
              </span>
              <input
                type="date"
                value={dateRaccLimite}
                onChange={(e) => setDateRaccLimite(e.target.value)}
                className="px-2 py-1 border border-[#E5E0D5] rounded"
              />
            </label>
            <button
              onClick={doValider}
              disabled={validating || contratsSignes.length === 0}
              className="flex items-center gap-2 px-4 py-2 rounded bg-[#8B7355] text-white disabled:opacity-40 hover:bg-[#725e46]"
            >
              {validating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Check className="w-4 h-4" />
              )}
              Valider les paies
            </button>
            <button
              onClick={doGeneratePdf}
              disabled={pdfLoading || contratsSignes.length === 0}
              className="flex items-center gap-2 px-4 py-2 rounded border border-[#8B7355] text-[#8B7355] disabled:opacity-40 hover:bg-[#ECF1F2]"
            >
              {pdfLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              Base PDF
            </button>
            <div className="ml-auto text-xs">
              <span className="text-[#8B7355] font-medium">NB TR :</span>{' '}
              <span className="font-semibold text-lg text-[#059669] tabular-nums">
                {nbTr}
              </span>
            </div>
          </div>

          {/* Onglets */}
          <div className="flex gap-1 border-b border-[#E5E0D5] mb-3">
            {(
              [
                { key: 'signes', label: `Contrats Signés (${contratsSignes.length})` },
                { key: 'decomm', label: `Décommission (${contratsDecomm.length})` },
                { key: 'non_prod', label: `Jours non Prod & TR (${joursNonProd.length + nbCttParJour.length})` },
                { key: 'base_pdf', label: 'Base PDF' },
              ] as { key: Tab; label: string }[]
            ).map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`px-3 py-1.5 text-sm font-medium border-b-2 -mb-px ${
                  tab === t.key
                    ? 'border-[#8B7355] text-[#8B7355]'
                    : 'border-transparent text-gray-500 hover:text-[#8B7355]'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Tables des onglets */}
          {tab === 'signes' && (
            <ContratsTable rows={contratsSignes} bgFn={bgFromCouleur} />
          )}
          {tab === 'decomm' && (
            <ContratsTable rows={contratsDecomm} bgFn={bgFromCouleur} />
          )}
          {tab === 'non_prod' && (
            <JoursTable jours={joursNonProd} nbParJour={nbCttParJour} />
          )}
          {tab === 'base_pdf' && (
            <BasePdfTable rows={contratsSignes} />
          )}
        </div>
      </div>

      {showPicker && (
        <PersonnePicker
          title="Choisir le salarié"
          onClose={() => setShowPicker(false)}
          onSelect={(s) => {
            setSalarie(s)
            setShowPicker(false)
          }}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------
// Tables des onglets
// ---------------------------------------------------------------------

function ContratsTable({
  rows, bgFn,
}: {
  rows: ContratRow[]
  bgFn: (c: string) => string
}) {
  if (rows.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-gray-400">
        Aucun contrat.
      </p>
    )
  }
  const totalPts = rows.reduce((s, r) => s + (r.nb_points || 0), 0)
  return (
    <div className="overflow-x-auto max-h-[600px]">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-[#F5F5F0]">
          <tr className="text-left text-[#8B7355] border-b border-[#E5E0D5]">
            <th className="py-1 px-2">Partenaire</th>
            <th className="py-1 px-2">Lib Produit</th>
            <th className="py-1 px-2">Type Prod</th>
            <th className="py-1 px-2">Num BS</th>
            <th className="py-1 px-2">Date Sign</th>
            <th className="py-1 px-2">Type État</th>
            <th className="py-1 px-2">État contrat</th>
            <th className="py-1 px-2">Vendeur</th>
            <th className="py-1 px-2">Agence</th>
            <th className="py-1 px-2">Équipe</th>
            <th className="py-1 px-2">Client</th>
            <th className="py-1 px-2">CP</th>
            <th className="py-1 px-2">Ville</th>
            <th className="py-1 px-2">Mois Paiement</th>
            <th className="py-1 px-2 text-right">NB Pts</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.id_contrat}
              className={`border-b border-[#F0EDE5] ${bgFn(r.couleur_fond)}`}
            >
              <td className="py-1 px-2 font-semibold">{r.partenaire}</td>
              <td className="py-1 px-2">{r.lib_produit}</td>
              <td className="py-1 px-2">{r.type_prod}</td>
              <td className="py-1 px-2 font-mono">{r.num_bs}</td>
              <td className="py-1 px-2 tabular-nums">
                {shortDate(r.date_signature)}
              </td>
              <td className="py-1 px-2">{r.type_etat}</td>
              <td className="py-1 px-2">{r.etat_contrat}</td>
              <td className="py-1 px-2">{r.vendeur_nom}</td>
              <td className="py-1 px-2">{r.agence}</td>
              <td className="py-1 px-2">{r.equipe}</td>
              <td className="py-1 px-2">{r.client_nom}</td>
              <td className="py-1 px-2">{r.client_cp}</td>
              <td className="py-1 px-2">{r.client_ville}</td>
              <td className="py-1 px-2 tabular-nums">
                {shortDate(r.mois_paiement)}
              </td>
              <td className="py-1 px-2 text-right tabular-nums">
                {(r.nb_points || 0).toFixed(2)}
              </td>
            </tr>
          ))}
          <tr className="bg-[#F5F5F0] font-semibold border-t-2 border-[#8B7355]">
            <td colSpan={14} className="py-1 px-2 text-right text-[#8B7355]">
              Total pts :
            </td>
            <td className="py-1 px-2 text-right tabular-nums text-[#8B7355]">
              {totalPts.toFixed(2)}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

function JoursTable({
  jours, nbParJour,
}: {
  jours: JourNonProd[]
  nbParJour: NbCttParJourRow[]
}) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <h3 className="text-xs font-semibold text-[#8B7355] mb-2 uppercase">
          Jours non productifs
        </h3>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-[#8B7355] border-b border-[#E5E0D5]">
              <th className="py-1 px-2">Jour</th>
              <th className="py-1 px-2 text-center">ENI</th>
              <th className="py-1 px-2 text-center">Fibre</th>
            </tr>
          </thead>
          <tbody>
            {jours.map((j) => (
              <tr key={j.jour} className="border-b border-[#F0EDE5]">
                <td className="py-1 px-2 tabular-nums">{shortDate(j.jour)}</td>
                <td className="py-1 px-2 text-center">
                  {j.eni ? <Check className="w-3 h-3 text-red-500 inline" /> : ''}
                </td>
                <td className="py-1 px-2 text-center">
                  {j.fibre ? <Check className="w-3 h-3 text-red-500 inline" /> : ''}
                </td>
              </tr>
            ))}
            {jours.length === 0 && (
              <tr>
                <td colSpan={3} className="py-4 text-center text-gray-400">
                  Aucun jour non productif.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div>
        <h3 className="text-xs font-semibold text-[#8B7355] mb-2 uppercase">
          NB Contrats / jour (base TR)
        </h3>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-[#8B7355] border-b border-[#E5E0D5]">
              <th className="py-1 px-2">Date Ctt</th>
              <th className="py-1 px-2 text-right">nb Ctt</th>
              <th className="py-1 px-2 text-center">Type</th>
            </tr>
          </thead>
          <tbody>
            {nbParJour.map((r) => {
              const eligible =
                (r.type_ctt === 1 && r.nb_ctt >= 3)
                || (r.type_ctt === 2 && r.nb_ctt >= 1)
              return (
                <tr
                  key={r.date_ctt}
                  className={`border-b border-[#F0EDE5] ${
                    eligible ? 'bg-[#DEF7EC]' : ''
                  }`}
                >
                  <td className="py-1 px-2 tabular-nums">
                    {shortDate(r.date_ctt)}
                  </td>
                  <td className="py-1 px-2 text-right tabular-nums font-semibold">
                    {r.nb_ctt}
                  </td>
                  <td className="py-1 px-2 text-center">
                    {r.type_ctt === 1 ? 'ENI/IAG/STR' : 'SFR-Fibre'}
                  </td>
                </tr>
              )
            })}
            {nbParJour.length === 0 && (
              <tr>
                <td colSpan={3} className="py-4 text-center text-gray-400">
                  Aucun calcul TR (valide les paies d'abord).
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function BasePdfTable({ rows }: { rows: ContratRow[] }) {
  if (rows.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-gray-400">
        Aucun contrat.
      </p>
    )
  }
  const totalPts = rows.reduce((s, r) => s + (r.nb_points || 0), 0)
  return (
    <div className="overflow-x-auto max-h-[600px]">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-[#F5F5F0]">
          <tr className="text-left text-[#8B7355] border-b border-[#E5E0D5]">
            <th className="py-1 px-2">Vendeur</th>
            <th className="py-1 px-2">Num BS</th>
            <th className="py-1 px-2">Signé le</th>
            <th className="py-1 px-2">Nom Produit</th>
            <th className="py-1 px-2">État</th>
            <th className="py-1 px-2">Mois Paiement</th>
            <th className="py-1 px-2 text-right">Note /10</th>
            <th className="py-1 px-2 text-right">NB Pts</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id_contrat} className="border-b border-[#F0EDE5]">
              <td className="py-1 px-2">{r.vendeur_nom}</td>
              <td className="py-1 px-2 font-mono">{r.num_bs}</td>
              <td className="py-1 px-2 tabular-nums">
                {shortDate(r.date_signature)}
              </td>
              <td className="py-1 px-2">{r.lib_produit}</td>
              <td className="py-1 px-2">{r.etat_contrat}</td>
              <td className="py-1 px-2 tabular-nums">
                {shortDate(r.mois_paiement)}
              </td>
              <td className="py-1 px-2 text-right tabular-nums">
                {(r.notation_client || 0).toFixed(1)}
              </td>
              <td className="py-1 px-2 text-right tabular-nums">
                {(r.nb_points || 0).toFixed(2)}
              </td>
            </tr>
          ))}
          <tr className="bg-[#F5F5F0] font-semibold border-t-2 border-[#8B7355]">
            <td colSpan={7} className="py-1 px-2 text-right text-[#8B7355]">
              Somme :
            </td>
            <td className="py-1 px-2 text-right tabular-nums text-[#8B7355]">
              {totalPts.toFixed(2)}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
