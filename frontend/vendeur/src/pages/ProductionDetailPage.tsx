import { useEffect, useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  FileDown,
  Loader2,
  Search,
  BarChart3,
  Users as UsersIcon,
  Table as TableIcon,
  Check,
  Minus,
} from 'lucide-react'
import { getToken, getStoredUser } from '@/api'

// --- Types -------------------------------------------------------

interface ContratRow {
  id_contrat: string
  partenaire: string
  num_bs: string

  // dates / produit
  date_signature: string
  date_saisie: string
  mois_p: string
  heure_sign: string
  lib_produit: string
  type_prod: string

  // état
  id_type_etat: number
  lib_type_etat: string
  couleur_etat: string
  lib_etat: string
  lib_etat_vend: string
  id_type_etat_ope: number
  lib_type_etat_ope: string
  lib_etat_ope: string

  // vendeur
  id_salarie: string
  vendeur_nom: string
  vendeur_prenom: string
  agence: string
  equipe: string
  poste: string
  en_activite: boolean
  date_embauche: string
  date_sortie: string

  // client
  id_client: string
  client_nom: string
  client_prenom: string
  client_adresse1: string
  client_adresse2: string
  client_cp: string
  client_ville: string
  client_mail: string
  client_mobile: string
  client_age: number
  client_rap_part: boolean

  // valeurs / infos
  nb_points: number
  notation: number
  notation_info: string
  info_interne: string
  info_partagee: string
  code_enr: string

  // SFR
  sfr_type_vente: number
  sfr_technologie: number
  sfr_box8: boolean
  sfr_box8_verif: boolean
  sfr_hors_cible: boolean
  sfr_date_rdv_tech: string
  sfr_date_racc_activ: string
  sfr_date_validation: string
  sfr_date_resil: string
  sfr_portabilite: boolean
  sfr_date_portab: string
  sfr_cluster_code: string
  sfr_cluster_nom: string
  sfr_mois_p_distrib: string
  sfr_internet_garanti: boolean
  sfr_offre_speciale: boolean
  sfr_parcours_chaine: boolean
  sfr_prise_existante: boolean
  sfr_prise_saisie: boolean
  sfr_num_prise_sfr: string
  sfr_num_prise_vend: string

  // ENI/OEN
  car: number
  puissance: number
  gaz_actif: boolean
  elec_actif: boolean
  opt_demat: boolean
  opt_maintenance: boolean
  opt_energie_verte_gaz: boolean
  opt_reforestation: boolean
  opt_protection: boolean

  // STR/VAL
  opt_num: string
}

interface ContratPage {
  total: number
  page: number
  page_size: number
  rows: ContratRow[]
}

interface ProductionJob {
  id_job: string
  titre: string
  statut: string
  nb_lignes: number
  duree_s: number
}

interface RepartPartenaireRow {
  partenaire: string
  couleur_hex: string
  brut: number
  temporaire: number
  envoye: number
  rejet: number
  resil: number
  payé: number
  decomm: number
  racc_activ_ko: number
  racc_active: number
}

interface VendeurStatRow {
  id_salarie: string
  nom: string
  prenom: string
  agence: string
  equipe: string
  poste: string
  en_activite: boolean
  date_sortie: string
  nb_contrats: number
  nb_paye: number
  nb_hors_rejet: number
  nb_points: number
  par_partenaire: Record<string, number>
}

interface JobStats {
  total_contrats: number
  total_paye: number
  total_points: number
  repart_partenaires: RepartPartenaireRow[]
  vendeurs: VendeurStatRow[]
  dashboard_sfr: Record<string, number>
  dashboard_oen: Record<string, number>
  dashboard_eni: Record<string, number>
}

type TabKey = 'contrats' | 'analyse' | 'repart' | 'vendeurs'

// --- Helpers -----------------------------------------------------

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

// Date affichée dd/mm/yyyy (input ISO YYYY-MM-DD ou WinDev YYYYMMDD)
function shortDate(raw: string | undefined | null): string {
  if (!raw) return ''
  const iso = String(raw).match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (iso) return `${iso[3]}/${iso[2]}/${iso[1]}`
  const wd = String(raw).slice(0, 8)
  if (/^\d{8}$/.test(wd)) return `${wd.slice(6, 8)}/${wd.slice(4, 6)}/${wd.slice(0, 4)}`
  return String(raw)
}

// Mois YYYY-MM → MM/YYYY
function shortMonth(raw: string | undefined | null): string {
  if (!raw) return ''
  const iso = String(raw).match(/^(\d{4})-(\d{2})/)
  if (iso) return `${iso[2]}/${iso[1]}`
  const wd = String(raw).slice(0, 8)
  if (/^\d{8}$/.test(wd)) return `${wd.slice(4, 6)}/${wd.slice(0, 4)}`
  return String(raw)
}

// ConsoGaz calculée depuis Car (cf. WinDev StatsENI / StatsOEN)
function consoGaz(car: number): string {
  if (!car) return ''
  if (car <= 1000) return 'Base'
  if (car <= 6000) return 'B0'
  if (car <= 30000) return 'B1'
  return 'B2i'
}

function BoolBadge({ v }: { v: boolean }) {
  return v ? (
    <Check className="w-3.5 h-3.5 text-emerald-600 inline-block" />
  ) : (
    <Minus className="w-3.5 h-3.5 text-gray-300 inline-block" />
  )
}

// Couleur selon seuils — reproduit fidèlement les fonctions CoulSFR_Tx* WinDev.
type ColorKind =
  | 'racc'      // CoulSFR_TxRacc : ≥70 vert / 60-70 orange / <60 rouge
  | 'resil'     // CoulSFR_TxResil : ≤15 vert / >15 rouge
  | 'consent'   // CoulSFR_TxConsent : ≥80 vert / <80 rouge
  | 'prise'     // CoulSFR_TxPrise : ≤69 rouge / 70-79 orange / ≥80 vert
  | 'dual'      // OEN : <80 rouge / 80-90 orange / >90 vert
  | 'premium'   // CoulSFR_TxPrem : <80 rouge / 80-90 orange / ≥90 vert
  | 'cq'        // CoulSFR_TxConquete : <80 rouge / 80-90 orange / ≥90 vert
  | 'portab'    // CoulSFR_TxPort : <70 rouge / 70-79 orange / ≥80 vert
  | 'mob'       // CoulSFR_TxMob : <30 rouge / 30-49 orange / ≥49 vert
  | 'f200'      // CoulSFR_TxForfaitMini : <20 rouge / 20-29 orange / ≥29 vert
  | 'dg'        // CoulSFR_TxDG : ≤15 vert / >15 rouge
  | 'pc'        // CoulSFR_TxParcChaines : ≤69 rouge / 70-79 orange / ≥80 vert
  | 'note'      // CoulSFR_NoteMoy : ≤8.59 rouge / 8.6-8.99 orange / ≥9 vert (sur /10)
  | 'none'

function colorClass(value: number, kind: ColorKind = 'none'): string {
  if (kind === 'none') return 'text-gray-900'
  switch (kind) {
    case 'racc':
      return value >= 70 ? 'text-emerald-600'
        : value >= 60 ? 'text-amber-600' : 'text-red-600'
    case 'resil':
      return value <= 15 ? 'text-emerald-600' : 'text-red-600'
    case 'consent':
      return value >= 80 ? 'text-emerald-600' : 'text-red-600'
    case 'prise':
    case 'pc':
      return value >= 80 ? 'text-emerald-600'
        : value >= 70 ? 'text-amber-600' : 'text-red-600'
    case 'dual':
      return value > 90 ? 'text-emerald-600'
        : value >= 80 ? 'text-amber-600' : 'text-red-600'
    case 'premium':
    case 'cq':
      return value >= 90 ? 'text-emerald-600'
        : value >= 80 ? 'text-amber-600' : 'text-red-600'
    case 'portab':
      return value >= 80 ? 'text-emerald-600'
        : value >= 70 ? 'text-amber-600' : 'text-red-600'
    case 'mob':
      return value >= 49 ? 'text-emerald-600'
        : value >= 30 ? 'text-amber-600' : 'text-red-600'
    case 'f200':
      return value >= 29 ? 'text-emerald-600'
        : value >= 20 ? 'text-amber-600' : 'text-red-600'
    case 'dg':
      return value <= 15 ? 'text-emerald-600' : 'text-red-600'
    case 'note':
      return value >= 9 ? 'text-emerald-600'
        : value >= 8.6 ? 'text-amber-600' : 'text-red-600'
  }
}

function Kpi({
  label, value, suffix = '', sub, tint = 'none', small = false,
}: {
  label: string
  value: number | string
  suffix?: string
  sub?: string
  tint?: ColorKind
  small?: boolean
}) {
  const numVal = typeof value === 'number' ? value : parseFloat(String(value))
  const colored = typeof value === 'number' || !isNaN(numVal)
  return (
    <div className={`bg-white rounded-xl border border-gray-200 px-4 ${small ? 'py-2.5' : 'py-3'}`}>
      <div className="text-[11px] font-medium text-gray-500 uppercase tracking-wide truncate">
        {label}
      </div>
      <div className={`${small ? 'text-xl' : 'text-2xl'} font-bold tabular-nums mt-0.5 ${
        colored ? colorClass(numVal, tint) : 'text-gray-900'
      }`}>
        {typeof value === 'number'
          ? (Number.isInteger(value) ? value.toLocaleString('fr-FR') : value.toFixed(1))
          : value}
        {suffix && <span className="text-sm font-medium text-gray-500 ml-1">{suffix}</span>}
      </div>
      {sub && <div className="text-[11px] text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

function DashboardSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">{title}</h3>
      {children}
    </div>
  )
}

// --- Column definitions (ordre exact Excel WinDev) ---------------

interface ColDef {
  key: string                              // clé de tri + identifiant unique
  label: string
  align?: 'left' | 'right' | 'center'
  // Visibilité conditionnelle : si renseignée, doit retourner true pour afficher
  onlyIfPartenaire?: string[]              // ex ['SFR'] : visible seulement si ≥1 contrat SFR
  onlyIfDroit?: string                     // ex 'InfoClientCoord'
  render: (r: ContratRow) => React.ReactNode
}

const COLUMNS: ColDef[] = [
  { key: 'vendeur_nom', label: 'Vendeur', render: (r) => (
    <span>
      <span className="font-medium text-gray-900">{r.vendeur_nom}</span>{' '}
      <span className="text-gray-600">{capitalize(r.vendeur_prenom)}</span>
      {!r.en_activite && <span className="ml-1 text-xs text-red-500">(inactif)</span>}
    </span>
  )},
  { key: 'num_bs', label: 'Num BS', render: (r) => (
    <span className="font-mono text-xs">{r.num_bs}</span>
  )},
  { key: 'partenaire', label: 'Part.', render: (r) => (
    <span className="font-semibold text-gray-900">{r.partenaire}</span>
  )},
  { key: 'lib_produit', label: 'Produit', render: (r) => r.lib_produit },
  { key: 'type_prod', label: 'Type Prod', render: (r) => r.type_prod },
  { key: 'sfr_type_vente', label: 'Type vente', onlyIfPartenaire: ['SFR'],
    render: (r) => r.partenaire === 'SFR' ? String(r.sfr_type_vente || '') : '' },
  { key: 'date_signature', label: 'Date Signature', align: 'left',
    render: (r) => <span className="tabular-nums">{shortDate(r.date_signature)}</span> },
  { key: 'sfr_date_rdv_tech', label: 'Date RDV Tech', onlyIfPartenaire: ['SFR'],
    render: (r) => <span className="tabular-nums">{shortDate(r.sfr_date_rdv_tech)}</span> },
  { key: 'sfr_date_racc_activ', label: 'Date Racc / Activation',
    onlyIfPartenaire: ['SFR', 'OEN'],
    render: (r) => <span className="tabular-nums">{shortDate(r.sfr_date_racc_activ)}</span> },
  { key: 'lib_type_etat', label: 'Type Etat', render: (r) => r.lib_type_etat },
  { key: 'lib_etat_vend', label: 'Etat contrat', render: (r) => (
    r.lib_etat_vend ? (
      <span
        className="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
        style={{
          color: r.couleur_etat || '#6b7280',
          backgroundColor: `${r.couleur_etat}15`,
          border: `1px solid ${r.couleur_etat}40`,
        }}
      >{r.lib_etat_vend}</span>
    ) : ''
  )},
  { key: 'lib_type_etat_ope', label: 'Type Etat Opérateur',
    onlyIfPartenaire: ['SFR', 'OEN'], onlyIfDroit: 'ProdRezo',
    render: (r) => r.lib_type_etat_ope },
  { key: 'lib_etat_ope', label: 'Etat Opérateur',
    onlyIfPartenaire: ['SFR', 'OEN'], onlyIfDroit: 'ProdRezo',
    render: (r) => r.lib_etat_ope },
  { key: 'sfr_cluster_nom', label: 'Cluster Nom', onlyIfPartenaire: ['SFR'],
    render: (r) => r.sfr_cluster_nom },
  { key: 'poste', label: 'Poste', render: (r) => (
    <span className="text-xs text-gray-500">{r.poste}</span>
  )},
  { key: 'date_embauche', label: 'Date Embauche',
    render: (r) => <span className="tabular-nums">{shortDate(r.date_embauche)}</span> },
  { key: 'en_activite', label: 'En activité', align: 'center',
    render: (r) => <BoolBadge v={r.en_activite} /> },
  { key: 'date_sortie', label: 'Date Sortie',
    render: (r) => <span className="tabular-nums">{shortDate(r.date_sortie)}</span> },
  { key: 'agence', label: 'Agence', render: (r) => r.agence },
  { key: 'equipe', label: 'Equipe', render: (r) => r.equipe },
  { key: 'client_nom', label: 'Client Nom', render: (r) => (
    <span>{r.client_nom} {capitalize(r.client_prenom)}</span>
  )},
  { key: 'client_adresse1', label: 'Client Adr', onlyIfDroit: 'InfoClientCoord',
    render: (r) => r.client_adresse1 },
  { key: 'client_adresse2', label: 'Client Cplt Adr', onlyIfDroit: 'InfoClientCoord',
    render: (r) => r.client_adresse2 },
  { key: 'client_cp', label: 'CP', render: (r) => r.client_cp },
  { key: 'client_ville', label: 'Ville', render: (r) => r.client_ville },
  { key: 'client_mail', label: 'Mail', onlyIfDroit: 'InfoClientCoord',
    render: (r) => (
      <span className="text-xs text-gray-600">{r.client_mail}</span>
    )},
  { key: 'client_mobile', label: 'Mobile', onlyIfDroit: 'InfoClientCoord',
    render: (r) => <span className="tabular-nums">{r.client_mobile}</span> },
  { key: 'client_rap_part', label: 'Recueil consentement', align: 'center',
    render: (r) => <BoolBadge v={r.client_rap_part} /> },
  { key: 'opt_num', label: 'Opt Numérique', onlyIfPartenaire: ['STR', 'VAL'],
    render: (r) => r.opt_num },
  { key: 'mois_p', label: 'Mois Paiement',
    render: (r) => <span className="tabular-nums">{shortMonth(r.mois_p)}</span> },
  { key: 'sfr_mois_p_distrib', label: 'Mois Paiement Distrib',
    onlyIfPartenaire: ['SFR'], onlyIfDroit: 'InfoPaieDistrib',
    render: (r) => <span className="tabular-nums">{shortMonth(r.sfr_mois_p_distrib)}</span> },
  { key: 'nb_points', label: 'NB Points', align: 'right',
    render: (r) => <span className="tabular-nums">{r.nb_points}</span> },
  { key: 'info_partagee', label: 'Infos Contrats',
    render: (r) => (
      <span className="text-xs text-gray-600 line-clamp-2">{r.info_partagee}</span>
    )},
  { key: 'gaz_actif', label: 'Gaz Actif', align: 'center',
    onlyIfPartenaire: ['ENI'],
    render: (r) => <BoolBadge v={r.gaz_actif} /> },
  { key: 'elec_actif', label: 'Elec Actif', align: 'center',
    onlyIfPartenaire: ['ENI'],
    render: (r) => <BoolBadge v={r.elec_actif} /> },
  { key: 'conso_gaz', label: 'ConsoGaz', onlyIfPartenaire: ['ENI', 'OEN'],
    render: (r) => consoGaz(r.car) },
  { key: 'car', label: 'Car', align: 'right', onlyIfPartenaire: ['ENI', 'OEN'],
    render: (r) => <span className="tabular-nums">{r.car || ''}</span> },
  { key: 'puissance', label: 'Puissance', align: 'right',
    onlyIfPartenaire: ['ENI', 'OEN'],
    render: (r) => <span className="tabular-nums">{r.puissance || ''}</span> },
  { key: 'opt_demat', label: 'OPT Démat', align: 'center',
    onlyIfPartenaire: ['ENI', 'OEN'],
    render: (r) => <BoolBadge v={r.opt_demat} /> },
  { key: 'opt_maintenance', label: 'OPT Maintenance', align: 'center',
    onlyIfPartenaire: ['ENI', 'OEN'],
    render: (r) => <BoolBadge v={r.opt_maintenance} /> },
  { key: 'opt_energie_verte_gaz', label: 'OPT Energie Verte Gaz', align: 'center',
    onlyIfPartenaire: ['ENI', 'OEN'],
    render: (r) => <BoolBadge v={r.opt_energie_verte_gaz} /> },
  { key: 'opt_reforestation', label: 'OPT Reforestation', align: 'center',
    onlyIfPartenaire: ['ENI', 'OEN'],
    render: (r) => <BoolBadge v={r.opt_reforestation} /> },
  { key: 'opt_protection', label: 'OPT Protection', align: 'center',
    onlyIfPartenaire: ['ENI', 'OEN'],
    render: (r) => <BoolBadge v={r.opt_protection} /> },
  { key: 'sfr_portabilite', label: 'Portabilité', align: 'center',
    onlyIfPartenaire: ['SFR'],
    render: (r) => <BoolBadge v={r.sfr_portabilite} /> },
  { key: 'sfr_date_portab', label: 'Date Portabilité', onlyIfPartenaire: ['SFR'],
    render: (r) => <span className="tabular-nums">{shortDate(r.sfr_date_portab)}</span> },
  { key: 'sfr_date_resil', label: 'Date Résil', onlyIfPartenaire: ['SFR', 'PRO'],
    render: (r) => <span className="tabular-nums">{shortDate(r.sfr_date_resil)}</span> },
  { key: 'sfr_internet_garanti', label: 'Internet Garanti', align: 'center',
    onlyIfPartenaire: ['SFR'],
    render: (r) => <BoolBadge v={r.sfr_internet_garanti} /> },
  { key: 'sfr_offre_speciale', label: 'Offre Spéciale', align: 'center',
    onlyIfPartenaire: ['SFR'],
    render: (r) => <BoolBadge v={r.sfr_offre_speciale} /> },
  { key: 'sfr_parcours_chaine', label: 'Parcours Chainés', align: 'center',
    onlyIfPartenaire: ['SFR'],
    render: (r) => <BoolBadge v={r.sfr_parcours_chaine} /> },
  { key: 'sfr_prise_existante', label: 'Prise Existante', align: 'center',
    onlyIfPartenaire: ['SFR'],
    render: (r) => <BoolBadge v={r.sfr_prise_existante} /> },
  { key: 'sfr_num_prise_sfr', label: 'Num prise SFR',
    onlyIfPartenaire: ['SFR'], onlyIfDroit: 'InfoClientCoord',
    render: (r) => <span className="font-mono text-xs">{r.sfr_num_prise_sfr}</span> },
  { key: 'sfr_num_prise_vend', label: 'Num prise vendeur',
    onlyIfPartenaire: ['SFR'], onlyIfDroit: 'InfoClientCoord',
    render: (r) => <span className="font-mono text-xs">{r.sfr_num_prise_vend}</span> },
  { key: 'heure_sign', label: 'Heure Signature', align: 'center',
    render: (r) => <span className="tabular-nums text-xs">{r.heure_sign}</span> },
  { key: 'notation', label: 'Note / 5', align: 'right', onlyIfDroit: 'InfoNotation',
    render: (r) => r.notation > 0 ? (
      <span className="tabular-nums font-medium">{r.notation.toFixed(1)}</span>
    ) : '' },
  { key: 'notation_info', label: 'Notation Info', onlyIfDroit: 'InfoNotation',
    render: (r) => <span className="text-xs text-gray-600">{r.notation_info}</span> },
]

// --- Page --------------------------------------------------------

export default function ProductionDetailPage() {
  const { id: idJob } = useParams<{ id: string }>()
  const [job, setJob] = useState<ProductionJob | null>(null)
  const [stats, setStats] = useState<JobStats | null>(null)
  const [tab, setTab] = useState<TabKey>('contrats')

  useEffect(() => {
    if (!idJob) return
    const headers = { Authorization: `Bearer ${getToken()}` }
    fetch(`/api/vendeur/production/jobs/${idJob}`, { headers })
      .then((r) => r.json())
      .then(setJob)
      .catch(() => {})
    fetch(`/api/vendeur/production/jobs/${idJob}/stats`, { headers })
      .then((r) => r.json())
      .then(setStats)
      .catch(() => {})
  }, [idJob])

  const downloadCsv = async () => {
    const r = await fetch(`/api/vendeur/production/jobs/${idJob}/export.csv`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `production-job-${idJob}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const partenairesPresents = useMemo(() => {
    if (!stats) return new Set<string>()
    return new Set(stats.repart_partenaires.map((r) => r.partenaire))
  }, [stats])

  return (
    <div className="p-6">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between gap-4"
      >
        <div className="flex items-center gap-3 min-w-0">
          <Link
            to="/production"
            className="p-2 text-gray-400 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-gray-900 truncate">
              {job?.titre || 'Extraction'}
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {stats ? stats.total_contrats.toLocaleString('fr-FR') : '…'} contrats
              {stats && stats.total_paye > 0 && (
                <> · {stats.total_paye.toLocaleString('fr-FR')} payés</>
              )}
            </p>
          </div>
        </div>
        <button
          onClick={downloadCsv}
          className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <FileDown className="w-4 h-4" />
          Export CSV
        </button>
      </motion.div>

      <div className="mt-5 border-b border-gray-200 flex items-center gap-1">
        <TabButton
          icon={<TableIcon className="w-4 h-4" />}
          label="Contrats"
          active={tab === 'contrats'}
          onClick={() => setTab('contrats')}
        />
        <TabButton
          icon={<BarChart3 className="w-4 h-4" />}
          label="Analyse"
          active={tab === 'analyse'}
          onClick={() => setTab('analyse')}
        />
        <TabButton
          icon={<BarChart3 className="w-4 h-4" />}
          label="Répartition"
          active={tab === 'repart'}
          onClick={() => setTab('repart')}
        />
        <TabButton
          icon={<UsersIcon className="w-4 h-4" />}
          label={`Vendeurs${stats ? ` (${stats.vendeurs.length})` : ''}`}
          active={tab === 'vendeurs'}
          onClick={() => setTab('vendeurs')}
        />
      </div>

      <div className="mt-5">
        {tab === 'contrats' && (
          <ContratsTable idJob={idJob!} partenairesPresents={partenairesPresents} />
        )}
        {tab === 'analyse' && <AnalyseDashboard stats={stats} partenairesPresents={partenairesPresents} />}
        {tab === 'repart' && <RepartTable stats={stats} />}
        {tab === 'vendeurs' && <VendeursTable stats={stats} />}
      </div>
    </div>
  )
}

function TabButton({
  icon, label, active, onClick,
}: { icon: React.ReactNode; label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
        active
          ? 'border-gray-900 text-gray-900'
          : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      {icon}
      {label}
    </button>
  )
}

// --- Onglet Contrats ---------------------------------------------

function ContratsTable({
  idJob,
  partenairesPresents,
}: {
  idJob: string
  partenairesPresents: Set<string>
}) {
  const user = getStoredUser()
  const droits = new Set(user?.droits || [])
  const [data, setData] = useState<ContratPage | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(100)
  const [showAll, setShowAll] = useState(false)
  const [sort, setSort] = useState<string>('-date_signature')
  const [partenaireFilter, setPartenaireFilter] = useState('')
  const [vendeurFilter, setVendeurFilter] = useState('')
  const [clientFilter, setClientFilter] = useState('')
  const [numBsFilter, setNumBsFilter] = useState('')
  const [typeProdFilter, setTypeProdFilter] = useState('')

  // En mode "Totalité", on demande toutes les lignes d'un coup (capé à 1M)
  const effectivePageSize = showAll ? 1_000_000 : pageSize
  const effectivePage = showAll ? 1 : page

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({
      page: String(effectivePage),
      page_size: String(effectivePageSize),
      sort,
    })
    if (partenaireFilter) params.set('partenaire', partenaireFilter)
    if (vendeurFilter) params.set('vendeur', vendeurFilter)
    if (clientFilter) params.set('client', clientFilter)
    if (numBsFilter) params.set('num_bs', numBsFilter)
    if (typeProdFilter) params.set('type_prod', typeProdFilter)
    fetch(`/api/vendeur/production/jobs/${idJob}/contrats?${params}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [idJob, effectivePage, effectivePageSize, sort, partenaireFilter, vendeurFilter, clientFilter, numBsFilter, typeProdFilter])

  const totalPages = useMemo(() => {
    if (!data || showAll) return 1
    return Math.max(1, Math.ceil(data.total / pageSize))
  }, [data, pageSize, showAll])

  const partenairesUniques = useMemo(
    () => Array.from(partenairesPresents).sort(),
    [partenairesPresents],
  )

  // Colonnes visibles : selon partenaires présents + droits user
  const visibleColumns = useMemo(
    () => COLUMNS.filter((c) => {
      if (c.onlyIfPartenaire && c.onlyIfPartenaire.length > 0) {
        const match = c.onlyIfPartenaire.some((p) => partenairesPresents.has(p))
        if (!match) return false
      }
      if (c.onlyIfDroit && !droits.has(c.onlyIfDroit)) return false
      return true
    }),
    [partenairesPresents, droits],
  )

  const toggleSort = (col: string) => {
    if (sort === col) setSort(`-${col}`)
    else if (sort === `-${col}`) setSort(col)
    else setSort(col)
    setPage(1)
  }

  const sortKey = sort.startsWith('-') ? sort.slice(1) : sort
  const sortDesc = sort.startsWith('-')

  return (
    <>
      <div className="flex flex-wrap items-center gap-3 mb-4">
        {partenairesUniques.length > 1 && (
          <select
            value={partenaireFilter}
            onChange={(e) => { setPartenaireFilter(e.target.value); setPage(1) }}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
          >
            <option value="">Tous partenaires</option>
            {partenairesUniques.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        )}
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            placeholder="Vendeur…"
            value={vendeurFilter}
            onChange={(e) => { setVendeurFilter(e.target.value); setPage(1) }}
            className="pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-300 w-48"
          />
        </div>
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            placeholder="Client…"
            value={clientFilter}
            onChange={(e) => { setClientFilter(e.target.value); setPage(1) }}
            className="pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-300 w-40"
          />
        </div>
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            placeholder="Num BS…"
            value={numBsFilter}
            onChange={(e) => { setNumBsFilter(e.target.value); setPage(1) }}
            className="pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-300 w-36 font-mono"
          />
        </div>
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            placeholder="Type Prod…"
            value={typeProdFilter}
            onChange={(e) => { setTypeProdFilter(e.target.value); setPage(1) }}
            className="pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-300 w-36"
          />
        </div>
        <div className="text-xs text-gray-500 ml-auto">
          {visibleColumns.length} colonnes
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-auto max-h-[calc(100vh-320px)]">
          <table className="text-sm" style={{ minWidth: '100%' }}>
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide sticky top-0 z-10 shadow-[inset_0_-1px_0_rgb(229_231_235)]">
              <tr>
                {visibleColumns.map((c) => (
                  <th
                    key={c.key}
                    onClick={() => toggleSort(c.key)}
                    className={`${c.align === 'right' ? 'text-right' : c.align === 'center' ? 'text-center' : 'text-left'} px-3 py-2.5 font-medium cursor-pointer select-none whitespace-nowrap hover:bg-gray-100 bg-gray-50`}
                  >
                    <span className="inline-flex items-center gap-1">
                      {c.label}
                      {sortKey === c.key && (sortDesc ? (
                        <ChevronDown className="w-3 h-3" />
                      ) : (
                        <ChevronUp className="w-3 h-3" />
                      ))}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan={visibleColumns.length} className="text-center py-12">
                    <Loader2 className="w-5 h-5 text-gray-300 animate-spin mx-auto" />
                  </td>
                </tr>
              ) : !data || data.rows.length === 0 ? (
                <tr>
                  <td colSpan={visibleColumns.length} className="text-center py-12 text-gray-400">
                    Aucun contrat
                  </td>
                </tr>
              ) : (
                data.rows.map((r, idx) => (
                  <tr
                    key={`${r.partenaire}-${r.id_contrat}-${idx}`}
                    className="hover:bg-gray-50"
                  >
                    {visibleColumns.map((c) => (
                      <td
                        key={c.key}
                        className={`${c.align === 'right' ? 'text-right' : c.align === 'center' ? 'text-center' : 'text-left'} px-3 py-2 text-gray-700 whitespace-nowrap`}
                      >
                        {c.render(r)}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {data && data.total > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50 text-sm">
            <div className="text-gray-500">
              {showAll ? (
                <>Tous les {data.total.toLocaleString('fr-FR')} contrats</>
              ) : (
                <>
                  {(page - 1) * pageSize + 1} – {Math.min(page * pageSize, data.total)} sur{' '}
                  {data.total.toLocaleString('fr-FR')}
                </>
              )}
            </div>
            <div className="flex items-center gap-2">
              <select
                value={showAll ? 'all' : String(pageSize)}
                onChange={(e) => {
                  if (e.target.value === 'all') {
                    setShowAll(true)
                    setPage(1)
                  } else {
                    setShowAll(false)
                    setPageSize(parseInt(e.target.value))
                    setPage(1)
                  }
                }}
                className="px-2 py-1 border border-gray-300 rounded text-sm"
              >
                {[50, 100, 200, 500].map((s) => (
                  <option key={s} value={s}>{s}/page</option>
                ))}
                <option value="all">Totalité</option>
              </select>
              {!showAll && (
                <>
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="px-2.5 py-1 border border-gray-300 rounded disabled:opacity-40 hover:bg-white"
                  >
                    Précédent
                  </button>
                  <span className="tabular-nums text-gray-700">{page} / {totalPages}</span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="px-2.5 py-1 border border-gray-300 rounded disabled:opacity-40 hover:bg-white"
                  >
                    Suivant
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  )
}

// --- Onglet Répartition ------------------------------------------

function RepartTable({ stats }: { stats: JobStats | null }) {
  if (!stats) {
    return (
      <div className="flex items-center justify-center py-16 bg-white rounded-xl border border-gray-200">
        <Loader2 className="w-5 h-5 text-gray-300 animate-spin" />
      </div>
    )
  }

  const rows = stats.repart_partenaires
  if (rows.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400 text-sm border border-dashed border-gray-300 rounded-xl">
        Aucune donnée.
      </div>
    )
  }

  const totals = rows.reduce(
    (acc, r) => ({
      brut: acc.brut + r.brut,
      temporaire: acc.temporaire + r.temporaire,
      envoye: acc.envoye + r.envoye,
      rejet: acc.rejet + r.rejet,
      resil: acc.resil + r.resil,
      payé: acc.payé + r.payé,
      decomm: acc.decomm + r.decomm,
      racc_activ_ko: acc.racc_activ_ko + r.racc_activ_ko,
      racc_active: acc.racc_active + r.racc_active,
    }),
    { brut: 0, temporaire: 0, envoye: 0, rejet: 0, resil: 0, payé: 0, decomm: 0, racc_activ_ko: 0, racc_active: 0 },
  )

  const num = (n: number) => n.toLocaleString('fr-FR')

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-2.5 font-medium">Partenaire</th>
              <th className="text-right px-3 py-2.5 font-medium">Brut</th>
              <th className="text-right px-3 py-2.5 font-medium">Temp.</th>
              <th className="text-right px-3 py-2.5 font-medium">Envoyé</th>
              <th className="text-right px-3 py-2.5 font-medium">Rejet</th>
              <th className="text-right px-3 py-2.5 font-medium">Résil.</th>
              <th className="text-right px-3 py-2.5 font-medium">Payé</th>
              <th className="text-right px-3 py-2.5 font-medium">Decomm.</th>
              <th className="text-right px-3 py-2.5 font-medium">Racc/Act. KO</th>
              <th className="text-right px-3 py-2.5 font-medium">Raccordé/Activé</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((r) => (
              <tr key={r.partenaire} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium text-gray-900 flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: r.couleur_hex || '#9ca3af' }} />
                  {r.partenaire}
                </td>
                <td className="px-3 py-2 text-right tabular-nums font-semibold text-gray-900">{num(r.brut)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-600">{num(r.temporaire)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-600">{num(r.envoye)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-red-600">{num(r.rejet)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-orange-600">{num(r.resil)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-emerald-700 font-medium">{num(r.payé)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-gray-500">{num(r.decomm)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-red-500">{num(r.racc_activ_ko)}</td>
                <td className="px-3 py-2 text-right tabular-nums text-emerald-600">{num(r.racc_active)}</td>
              </tr>
            ))}
            <tr className="bg-gray-50 font-semibold border-t-2 border-gray-200">
              <td className="px-4 py-2 text-gray-900">TOTAL</td>
              <td className="px-3 py-2 text-right tabular-nums text-gray-900">{num(totals.brut)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-gray-700">{num(totals.temporaire)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-gray-700">{num(totals.envoye)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-red-700">{num(totals.rejet)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-orange-700">{num(totals.resil)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-emerald-800">{num(totals.payé)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-gray-600">{num(totals.decomm)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-red-600">{num(totals.racc_activ_ko)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-emerald-700">{num(totals.racc_active)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

// --- Onglet Vendeurs ---------------------------------------------

function VendeursTable({ stats }: { stats: JobStats | null }) {
  const [filter, setFilter] = useState('')

  const partenaires = useMemo(() => {
    if (!stats) return [] as string[]
    const s = new Set<string>()
    for (const v of stats.vendeurs) Object.keys(v.par_partenaire).forEach((p) => s.add(p))
    return Array.from(s).sort()
  }, [stats])

  if (!stats) {
    return (
      <div className="flex items-center justify-center py-16 bg-white rounded-xl border border-gray-200">
        <Loader2 className="w-5 h-5 text-gray-300 animate-spin" />
      </div>
    )
  }

  const filtered = stats.vendeurs.filter((v) => {
    if (!filter) return true
    const q = filter.toLowerCase()
    return (
      v.nom.toLowerCase().includes(q) ||
      v.prenom.toLowerCase().includes(q) ||
      v.agence.toLowerCase().includes(q) ||
      v.equipe.toLowerCase().includes(q)
    )
  })

  if (stats.vendeurs.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400 text-sm border border-dashed border-gray-300 rounded-xl">
        Aucun vendeur.
      </div>
    )
  }

  return (
    <>
      <div className="flex items-center gap-3 mb-4">
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            placeholder="Rechercher vendeur / agence / équipe…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-300 w-96"
          />
        </div>
        <span className="text-xs text-gray-500">
          {filtered.length} / {stats.vendeurs.length} vendeurs
        </span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
              <tr>
                <th className="text-left px-3 py-2.5 font-medium">Vendeur</th>
                <th className="text-left px-3 py-2.5 font-medium">Agence</th>
                <th className="text-left px-3 py-2.5 font-medium">Équipe</th>
                <th className="text-left px-3 py-2.5 font-medium">Poste</th>
                <th className="text-right px-3 py-2.5 font-medium">Contrats</th>
                <th className="text-right px-3 py-2.5 font-medium">Hors rejet</th>
                <th className="text-right px-3 py-2.5 font-medium">Payés</th>
                <th className="text-right px-3 py-2.5 font-medium">Points</th>
                {partenaires.map((p) => (
                  <th key={p} className="text-right px-3 py-2.5 font-medium">{p}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8 + partenaires.length} className="text-center py-12 text-gray-400">
                    Aucun résultat
                  </td>
                </tr>
              ) : (
                filtered.map((v) => (
                  <tr key={v.id_salarie} className="hover:bg-gray-50">
                    <td className="px-3 py-2 font-medium text-gray-900">
                      {v.nom} {capitalize(v.prenom)}
                      {!v.en_activite && (
                        <span className="ml-1.5 text-xs text-red-500">(inactif)</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-gray-600">{v.agence || '—'}</td>
                    <td className="px-3 py-2 text-gray-600">{v.equipe || '—'}</td>
                    <td className="px-3 py-2 text-gray-500 text-xs">{v.poste || '—'}</td>
                    <td className="px-3 py-2 text-right tabular-nums font-semibold text-gray-900">
                      {v.nb_contrats.toLocaleString('fr-FR')}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-700">
                      {v.nb_hors_rejet.toLocaleString('fr-FR')}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-emerald-700 font-medium">
                      {v.nb_paye.toLocaleString('fr-FR')}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-700">
                      {v.nb_points.toLocaleString('fr-FR')}
                    </td>
                    {partenaires.map((p) => (
                      <td key={p} className="px-3 py-2 text-right tabular-nums text-gray-500">
                        {v.par_partenaire[p] ? v.par_partenaire[p] : '—'}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}

// --- Onglet Analyse (dashboards SFR / OEN / ENI) -----------------

function AnalyseDashboard({
  stats, partenairesPresents,
}: {
  stats: JobStats | null
  partenairesPresents: Set<string>
}) {
  // Détermine les sous-onglets disponibles selon les partenaires présents
  const hasSFR = partenairesPresents.has('SFR')
  const hasOEN = partenairesPresents.has('OEN')
  const hasENI = partenairesPresents.has('ENI')
  const defaultSub = hasSFR ? 'sfr' : hasOEN ? 'oen' : hasENI ? 'eni' : 'sfr'
  const [sub, setSub] = useState<'sfr' | 'oen' | 'eni'>(defaultSub)

  useEffect(() => { setSub(defaultSub) }, [defaultSub])

  if (!stats) {
    return (
      <div className="flex items-center justify-center py-16 bg-white rounded-xl border border-gray-200">
        <Loader2 className="w-5 h-5 text-gray-300 animate-spin" />
      </div>
    )
  }

  if (!hasSFR && !hasOEN && !hasENI) {
    return (
      <div className="text-center py-16 text-gray-400 text-sm border border-dashed border-gray-300 rounded-xl">
        Aucune donnée d'analyse. Les dashboards sont disponibles pour SFR, OEN et ENI.
      </div>
    )
  }

  return (
    <>
      <div className="flex items-center gap-1 mb-4 bg-gray-100 rounded-lg p-0.5 w-fit">
        {hasSFR && (
          <button
            onClick={() => setSub('sfr')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              sub === 'sfr' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
            }`}
          >Analyse SFR</button>
        )}
        {hasOEN && (
          <button
            onClick={() => setSub('oen')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              sub === 'oen' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
            }`}
          >Analyse Ohm Energie</button>
        )}
        {hasENI && (
          <button
            onClick={() => setSub('eni')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              sub === 'eni' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
            }`}
          >Analyse ENI</button>
        )}
      </div>

      {sub === 'sfr' && hasSFR && <DashboardSFR d={stats.dashboard_sfr} />}
      {sub === 'oen' && hasOEN && <DashboardOEN d={stats.dashboard_oen} />}
      {sub === 'eni' && hasENI && <DashboardENI d={stats.dashboard_eni} />}
    </>
  )
}

function DashboardSFR({ d }: { d: Record<string, number> }) {
  const n = (k: string) => Number((d ?? {})[k] ?? 0)
  return (
    <div className="space-y-6">
      {/* Entête global */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="Note moyenne" value={n('note_moy')} suffix="/ 10" tint="note"
          sub={`${n('pct_notes').toFixed(1)} % de contrats notés`} />
        <Kpi label="% Consentement" value={n('tx_consent')} suffix="%"
          sub={`${n('nb_consent')} / ${n('nb_clients')}`} tint="consent" />
        <Kpi label="% Prise Saisie" value={n('tx_prise_saisie')} suffix="%"
          sub={`${n('nb_fibre_prise_saisie')} / ${n('nb_fibre_prise_existante')}`} tint="prise" />
        <Kpi label="% Portabilité" value={n('tx_portab')} suffix="%"
          sub={`${n('nb_fibre_porta')} CQ avec Porta / ${n('nb_fibre_cq')} CQ`} tint="portab" />
      </div>

      {/* --- Fibre --- */}
      <DashboardSection title={`Fibre — ${n('nb_fibre')} contrats Brut (hors TK)`}>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <Kpi label="% Conquête" value={n('tx_cq')} suffix="%" tint="cq"
            sub={`${n('nb_fibre_cq')} CQ / ${n('nb_fibre')} Fibre`} />
          <Kpi label="% Premium" value={n('tx_premium')} suffix="%" tint="premium"
            sub={`${n('nb_fibre_premium_lib')} Premium / ${n('nb_fibre')}`} />
          <Kpi label="% Racc" value={n('tx_racc')} suffix="%" tint="racc"
            sub={`${n('nb_fibre_ra')} Racc / ${n('nb_fibre_hors_att')} hors att.`} />
          <Kpi label="% Racc SFR" value={n('tx_racc_sfr')} suffix="%" tint="racc"
            sub={`${n('nb_fibre_ra_sfr')} Racc SFR`} />
          <Kpi label="% Résil" value={n('tx_resil')} suffix="%" tint="resil"
            sub={`${n('nb_fibre_resil')} Résil / ${n('nb_fibre')}`} />
          <Kpi label="% Mobile" value={n('tx_mobile')} suffix="%" tint="mob"
            sub={`${n('nb_mobile')} MOB / ${n('nb_fibre')} Fibre`} />
          <Kpi label="% Parcours Chaînés" value={n('tx_pc')} suffix="%" tint="pc"
            sub={`${n('nb_fibre_pc')} PC / ${n('nb_sfr_4p')} Clients 4P`} />
          <Kpi label="% DG (Dépôt Garantie)" value={n('tx_dg')} suffix="%" tint="dg"
            sub={`${n('nb_fibre_depot_gar')} DG / ${n('nb_fibre')}`} />
        </div>
      </DashboardSection>

      {/* --- Mobile --- */}
      {n('nb_mobile') > 0 && (
        <DashboardSection title={`Mobile — ${n('nb_mobile')} contrats Brut (hors TK)`}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Kpi label="% forfait > 200Go" value={n('tx_forfait_200go')} suffix="%" tint="f200"
              sub={`${n('nb_mobile_200go')} / ${n('nb_mobile')}`} />
            <Kpi label="% Activation" value={n('tx_mobile_activ')} suffix="%" tint="racc"
              sub={`${n('nb_mobile_activ')} activé / ${n('nb_mobile_hors_att')} hors att.`} />
            <Kpi label="% Activation SFR" value={n('tx_mobile_activ_sfr')} suffix="%" tint="racc"
              sub={`${n('nb_mobile_activ_sfr')} activé SFR`} />
            <Kpi label="% Churn Mobile" value={n('tx_churn_mob')} suffix="%" tint="resil"
              sub={`${n('nb_res30j_mob')} résil ≤30j / ${n('nb_cq_ra_mob')} CQ finalisées`} />
          </div>
        </DashboardSection>
      )}

      {/* --- Box 5G --- */}
      {n('nb_box5g') > 0 && (
        <DashboardSection title={`Box 5G — ${n('nb_box5g')} contrats Brut (hors TK)`}>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <Kpi label="% Conquête" value={n('tx_box5g_cq')} suffix="%" tint="cq"
              sub={`${n('nb_box5g_cq')} CQ / ${n('nb_box5g')}`} />
            <Kpi label="% Résil" value={n('tx_box5g_resil')} suffix="%" tint="resil"
              sub={`${n('nb_box5g_resil')} Résil / ${n('nb_box5g')}`} />
            <Kpi label="% Activ" value={n('tx_box5g_racc')} suffix="%" tint="racc"
              sub={`${n('nb_box5g_activ')} activé / ${n('nb_box5g_hors_att')} hors att.`} />
            <Kpi label="% Activ SFR" value={n('tx_box5g_racc_sfr')} suffix="%" tint="racc"
              sub={`${n('nb_box5g_activ_sfr')} activé SFR`} />
            <Kpi label="% B5G TV" value={n('tx_box5g_tv')} suffix="%"
              sub={`${n('nb_box5g_tv')} TV / ${n('nb_box5g')}`} />
            <Kpi label="% Churn B5G" value={n('tx_churn_b5g')} suffix="%" tint="resil"
              sub={`${n('nb_res30j_b5g')} résil ≤30j / ${n('nb_cq_ra_b5g')} CQ finalisées`} />
          </div>
        </DashboardSection>
      )}

      {/* --- Secu (optionnel) --- */}
      {n('nb_secu') > 0 && (
        <DashboardSection title="Maison Sécu">
          <div className="grid grid-cols-4 gap-3">
            <Kpi label="Nb Maison Sécu" value={n('nb_secu')} />
          </div>
        </DashboardSection>
      )}
    </div>
  )
}

function DashboardOEN({ d }: { d: Record<string, number> }) {
  const n = (k: string) => Number((d ?? {})[k] ?? 0)
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="Nb Ctt Brut" value={n('nb_ctt')}
          sub="Mono + Dual/2" />
        <Kpi label="Nb PDL Hors anomalie" value={n('nb_pdl_brut')} />
        <Kpi label="Nb Ctt Hors anomalie" value={n('nb_hors_anomalie')} />
        <Kpi label="Note moyenne" value={n('note_moy')} suffix="/ 10"
          sub={`${n('pct_notes').toFixed(1)} % de ctt notés`} />
      </div>

      <DashboardSection title="Ratios clés">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
          <Kpi label="% Valide" value={n('tx_valide')} suffix="%" tint="dual"
            sub={`${n('nb_valide')} / ${n('nb_hors_anomalie')}`} />
          <Kpi label="% Valide Opé" value={n('tx_valide_ope')} suffix="%" tint="dual"
            sub={`${n('nb_valide_ope')} / ${n('nb_hors_anomalie')}`} />
          <Kpi label="% Anomalie" value={n('tx_anomalie')} suffix="%" tint="resil"
            sub={`${n('nb_anomalie')} / ${n('nb_ctt')}`} />
          <Kpi label="% Résil" value={n('tx_resil')} suffix="%" tint="resil"
            sub={`${n('nb_resil')} / ${n('nb_hors_anomalie')}`} />
          <Kpi label="% Attente" value={n('tx_attente')} suffix="%"
            sub={`${n('nb_attente')} / ${n('nb_ctt')}`} />
          <Kpi label="% Dual" value={n('tx_dual')} suffix="%" tint="dual"
            sub={`${n('nb_ctt_dual')} / ${n('nb_ctt')}`} />
          <Kpi label="% Base" value={n('tx_base')} suffix="%"
            sub={`${n('nb_base')} ≤ 1000 KWh`} />
          <Kpi label="% 6kva et +" value={n('tx_6kva')} suffix="%" tint="dual"
            sub={`${n('nb_6kva')} Elec ≥ 6 kVA`} />
          <Kpi label="% Consentement" value={n('tx_consent')} suffix="%" tint="consent"
            sub={`${n('nb_consent')} / ${n('nb_clients')}`} />
          <Kpi label="Car moy" value={n('car_moy')} suffix="KWh"
            sub="Consommation gaz moyenne" />
        </div>
      </DashboardSection>
    </div>
  )
}

function DashboardENI({ d }: { d: Record<string, number> }) {
  const n = (k: string) => Number((d ?? {})[k] ?? 0)
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="Nb Brut" value={n('nb_brut')} />
        <Kpi label="Nb Hors anomalie" value={n('nb_hors_anomalie')} />
        <Kpi label="Note moyenne" value={n('note_moy')} suffix="/ 10"
          sub={`${n('pct_notes').toFixed(1)} % de ctt notés`} />
        <Kpi label="Car moy" value={n('car_moy')} suffix="KWh"
          sub="Conso gaz moyenne" />
      </div>

      <DashboardSection title="Répartition">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Kpi label="% Mono Gaz" value={n('tx_mono_gaz')} suffix="%"
            sub={`${n('nb_mono_gaz')} contrats`} />
          <Kpi label="% Mono Elec" value={n('tx_mono_elec')} suffix="%"
            sub={`${n('nb_mono_elec')} contrats`} />
          <Kpi label="% Dual" value={n('tx_dual')} suffix="%" tint="dual"
            sub={`${n('nb_dual')} contrats`} />
          <Kpi label="% Type B1+" value={n('tx_b1_plus')} suffix="%"
            sub={`${n('nb_b1_plus')} ctts > 6000 KWh`} />
        </div>
      </DashboardSection>

      <DashboardSection title="États">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <Kpi label="% Anomalie" value={n('tx_anomalie')} suffix="%" tint="resil"
            sub={`${n('nb_anomalie')} / ${n('nb_brut')}`} />
          <Kpi label="% Résil" value={n('tx_resil')} suffix="%" tint="resil"
            sub={`${n('nb_resil')} / ${n('nb_brut')}`} />
          <Kpi label="% Stand-By" value={n('tx_stand_by')} suffix="%"
            sub={`${n('nb_stand_by')} / ${n('nb_brut')}`} />
        </div>
      </DashboardSection>

      <DashboardSection title="Options (objectif 90 %)">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <Kpi label="Démat" value={n('tx_demat')} suffix="%" tint="dual"
            sub={`${n('nb_demat')}`} small />
          <Kpi label="Maintenance" value={n('tx_maintenance')} suffix="%" tint="dual"
            sub={`${n('nb_maintenance')}`} small />
          <Kpi label="Énergie Verte Gaz" value={n('tx_energie_verte')} suffix="%" tint="dual"
            sub={`${n('nb_energie_verte')}`} small />
          <Kpi label="Reforestation" value={n('tx_reforestation')} suffix="%" tint="dual"
            sub={`${n('nb_reforestation')}`} small />
          <Kpi label="Protection" value={n('tx_protection')} suffix="%" tint="dual"
            sub={`${n('nb_protection')}`} small />
        </div>
      </DashboardSection>
    </div>
  )
}
