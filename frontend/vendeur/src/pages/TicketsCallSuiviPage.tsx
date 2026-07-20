/**
 * Fen_TicketsCallSuivi (Vendeur) - vue unifiee Fibre + Energie.
 *
 * Regles :
 * - User avec droit ProdRezo : voit tous les tickets.
 * - Sinon : filtre auto par orga (backend).
 *
 * Fusion des pages Call Fibre + Call Energie. La colonne 'Partenaire'
 * indique quel ticket ouvrir au double-clic (SFR -> fiche Fibre,
 * sinon -> fiche Energie).
 *
 * Etape 4b : le double-clic ouvre soit FicheTicketModalFibre (SFR) soit
 * FicheTicketModalEnergie (autre partenaire). Les endpoints d'ecriture
 * (verrou / save / actions) ne sont pas encore tous portes cote Vendeur
 * (etape 4b-5+), la lecture fonctionne.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Loader2, RefreshCw, Search, Calendar as CalIcon,
  Package, Users,
} from 'lucide-react'
import { getToken } from '@/api'
import FicheTicketModalFibre from '@/components/FicheTicketModalFibre'
import FicheTicketModalEnergie from '@/components/FicheTicketModalEnergie'

const API_BASE = '/api/vendeur/tickets-call/suivi'
// Refresh secondaire (traites + dashboards) : les changements de statut
// coulent aussi via /live pour les en-cours, mais on rafraichit periodique-
// ment le bas pour couvrir les mises a jour de dashboards.
const REFRESH_MS = 30_000

// Onglet en arriere-plan : suspendre le long-poll pour liberer la connexion HTTP.
function waitUntilVisible(): Promise<void> {
  if (typeof document === 'undefined' || !document.hidden) return Promise.resolve()
  return new Promise((resolve) => {
    const onVis = () => {
      if (!document.hidden) {
        document.removeEventListener('visibilitychange', onVis)
        resolve()
      }
    }
    document.addEventListener('visibilitychange', onVis)
  })
}

// --- Types partages -------------------------------------------------------

interface TicketRow {
  id: string
  partenaire: string
  partenaire_lib?: string
  date_crea: string
  nom_client: string
  cp: string
  ville: string
  nom_vendeur: string
  agence: string
  lib_equipe?: string
  lib_agence?: string
  lib_statut: string
  ref_appel?: string
  id_tk_statut?: number
  appel_en_cours?: boolean
  ope_appel_nom?: string
  ticket_diff?: boolean
  nb_offres?: number
  nb_fibre_valide?: number
  nb_mobile_valide?: number
  col_offres_fibre?: string
  nb_offres_valides?: number
  nb_num_bs?: number
  nb_brut_par_partenaire?: Record<string, number>
  delai_depasse?: boolean
}

interface DashFibre {
  paniers_valides: number
  offres_fibre_thd: number
  cq_fibre_valides: number
  mobiles_valides: number
  agences_internes: {
    id_orga: string; lib_orga: string
    nb_fibre: number; nb_mobile: number; gimmick_url: string
  }[]
  nb_fibre_power: number; nb_mobile_power: number
  nb_fibre_fox: number; nb_mobile_fox: number
}

interface DashPartRow {
  prefix: string; lib: string; logo_url: string
  nb_offres: number; nb_clients: number
}

interface DashEnergie {
  tickets_valides: number
  partenaires: (DashPartRow & { id: string })[]
  agences_internes: {
    id_orga: string; lib_orga: string; gimmick_url: string
    par_partenaire: DashPartRow[]
  }[]
  multicom: { par_partenaire: DashPartRow[] }
  power: { par_partenaire: DashPartRow[] }
}

// --- Utils ---------------------------------------------------------------

const fmtDateTimeFr = (s: string) => {
  if (!s || s.length < 10) return ''
  const d = s.slice(0, 10)
  const t = s.length >= 16 ? s.slice(11, 16) : ''
  return `${d.slice(8, 10)}/${d.slice(5, 7)}/${d.slice(0, 4)}${t ? ' ' + t : ''}`
}

const fmtDateFr = (s: string) => fmtDateTimeFr(s).slice(0, 10)

// --- Page principale -----------------------------------------------------

export default function TicketsCallSuiviPage() {
  const [enCours, setEnCours] = useState<TicketRow[]>([])
  const [traites, setTraites] = useState<TicketRow[]>([])
  const [dashFibre, setDashFibre] = useState<DashFibre | null>(null)
  const [dashEnergie, setDashEnergie] = useState<DashEnergie | null>(null)
  const [dashTab, setDashTab] = useState<'fibre' | 'energie'>('fibre')
  const [jour, setJour] = useState(() => new Date().toISOString().slice(0, 10))
  const [loadingEC, setLoadingEC] = useState(true)
  const [loadingTR, setLoadingTR] = useState(true)
  const [lastRefresh, setLastRefresh] = useState('')
  const [filtre, setFiltre] = useState('')

  useEffect(() => {
    document.title = 'Tickets Call · Suivi · Omaya'
  }, [])

  const auth = { Authorization: `Bearer ${getToken()}` }

  const fetchEnCours = useCallback(async () => {
    setLoadingEC(true)
    try {
      const r = await fetch(`${API_BASE}/en-cours`, { headers: auth })
      if (r.ok) {
        const d = await r.json()
        setEnCours(Array.isArray(d.tickets_en_cours) ? d.tickets_en_cours : [])
      }
    } finally { setLoadingEC(false) }
  }, [])

  const fetchTraites = useCallback(async (j: string) => {
    setLoadingTR(true)
    try {
      const r = await fetch(`${API_BASE}/traites?jour=${j}`, { headers: auth })
      if (r.ok) {
        const d = await r.json()
        setTraites(Array.isArray(d.tickets_traites) ? d.tickets_traites : [])
      }
    } finally { setLoadingTR(false) }
  }, [])

  const fetchDashboard = useCallback(async (tab: 'fibre' | 'energie', j: string) => {
    const r = await fetch(`${API_BASE}/dashboard/${tab}?jour=${j}`, { headers: auth })
    if (!r.ok) return
    const d = await r.json()
    if (tab === 'fibre') setDashFibre(d as DashFibre)
    else setDashEnergie(d as DashEnergie)
  }, [])

  const refreshAll = useCallback(async () => {
    await Promise.all([
      fetchEnCours(),
      fetchTraites(jour),
      fetchDashboard('fibre', jour),
      fetchDashboard('energie', jour),
    ])
    setLastRefresh(new Date().toLocaleTimeString('fr-FR'))
  }, [fetchEnCours, fetchTraites, fetchDashboard, jour])

  const refreshBas = useCallback(async () => {
    await Promise.all([
      fetchTraites(jour),
      fetchDashboard('fibre', jour),
      fetchDashboard('energie', jour),
    ])
    setLastRefresh(new Date().toLocaleTimeString('fr-FR'))
  }, [fetchTraites, fetchDashboard, jour])

  // Load initial
  useEffect(() => { void refreshAll() }, [refreshAll])
  // Refresh periodique du bas (traites + dashboards)
  useEffect(() => {
    const id = setInterval(() => { void refreshBas() }, REFRESH_MS)
    return () => clearInterval(id)
  }, [refreshBas])

  // Long polling sur les en-cours : detecte instantanement les nouveaux
  // tickets + les changements de statut + les prises/lachers de verrou.
  const lastModifRef = useRef('')
  const stoppedRef = useRef(false)
  useEffect(() => {
    stoppedRef.current = false
    ;(async () => {
      while (!stoppedRef.current) {
        if (document.hidden) {
          await waitUntilVisible()
          if (stoppedRef.current) break
        }
        try {
          const since = encodeURIComponent(lastModifRef.current)
          const r = await fetch(`${API_BASE}/live?since=${since}`, { headers: auth })
          if (!r.ok) { await new Promise((res) => setTimeout(res, 5000)); continue }
          const body = await r.json()
          if (body.changed && body.page) {
            if (!stoppedRef.current) {
              setEnCours(Array.isArray(body.page) ? body.page : [])
              lastModifRef.current = body.last_modif || ''
              setLastRefresh(new Date().toLocaleTimeString('fr-FR'))
              // Un changement peut aussi affecter le bas (statut = 14/15/28)
              // -> re-fetch les traites/dashboards en tache de fond.
              void refreshBas()
            }
          } else {
            lastModifRef.current = body.last_modif || lastModifRef.current
          }
        } catch {
          await new Promise((res) => setTimeout(res, 3000))
        }
      }
    })()
    return () => { stoppedRef.current = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const [openedFiche, setOpenedFiche] = useState<{
    id: string; kind: 'fibre' | 'energie'
  } | null>(null)

  const openFiche = (row: TicketRow) => {
    setOpenedFiche({
      id: row.id,
      kind: row.partenaire === 'SFR' ? 'fibre' : 'energie',
    })
  }
  const closeFiche = () => setOpenedFiche(null)
  const afterFicheAction = () => { void refreshAll() }

  const filtrer = (rows: TicketRow[]) => {
    if (!filtre.trim()) return rows
    const q = filtre.toLowerCase()
    return rows.filter((r) =>
      (r.nom_client + ' ' + r.nom_vendeur + ' ' + r.ville + ' ' + r.agence)
        .toLowerCase().includes(q),
    )
  }

  const enCoursF = useMemo(() => filtrer(enCours), [enCours, filtre])
  const traitesF = useMemo(() => filtrer(traites), [traites, filtre])

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-c-ink">
            Suivi Tickets Call
          </h1>
          <p className="text-xs text-c-ink-faint">
            Fibre + Énergie · dernière maj {lastRefresh || '—'}
          </p>
        </div>
        <div className="flex-1" />
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-c-ink-faint" />
          <input value={filtre} onChange={(e) => setFiltre(e.target.value)}
                 placeholder="Filtrer nom / vendeur / ville / agence"
                 className="pl-8 pr-2 py-1.5 border border-c-line rounded-md text-sm w-64" />
        </div>
        <label className="text-xs flex items-center gap-1.5">
          <CalIcon className="w-3.5 h-3.5 text-c-ink-faint" />
          <input type="date" value={jour}
                 onChange={(e) => setJour(e.target.value)}
                 className="border border-c-line rounded px-2 py-1" />
        </label>
        <button onClick={() => void refreshAll()}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-c-brand text-white text-sm hover:brightness-110">
          <RefreshCw className="w-3.5 h-3.5" /> Rafraîchir
        </button>
      </div>

      {/* Dashboard onglets */}
      <div className="bg-white rounded-lg border border-c-line-soft">
        <div className="flex gap-1 border-b border-c-line-soft px-2 pt-2">
          <DashTab active={dashTab === 'fibre'} onClick={() => setDashTab('fibre')}>
            Dashboard Fibre
          </DashTab>
          <DashTab active={dashTab === 'energie'} onClick={() => setDashTab('energie')}>
            Dashboard Énergie
          </DashTab>
        </div>
        <div className="p-4">
          {dashTab === 'fibre' && (
            <DashboardFibreView data={dashFibre} />
          )}
          {dashTab === 'energie' && (
            <DashboardEnergieView data={dashEnergie} />
          )}
        </div>
      </div>

      {/* Section EN COURS */}
      <SectionCard
        title="Tickets à traiter"
        badge={enCoursF.length}
        loading={loadingEC}
      >
        <TicketsTable
          rows={enCoursF}
          onDoubleClick={openFiche}
          variant="encours"
        />
      </SectionCard>

      {/* Section TRAITES */}
      <SectionCard
        title="Tickets traités"
        badge={traitesF.length}
        loading={loadingTR}
      >
        <TicketsTable
          rows={traitesF}
          onDoubleClick={openFiche}
          variant="traites"
        />
      </SectionCard>

      {/* Modals fiche - un seul monte a la fois selon le partenaire */}
      {openedFiche?.kind === 'fibre' && (
        <FicheTicketModalFibre
          idTicket={openedFiche.id}
          onClose={closeFiche}
          onAfterAction={afterFicheAction}
        />
      )}
      {openedFiche?.kind === 'energie' && (
        <FicheTicketModalEnergie
          idTicket={openedFiche.id}
          onClose={closeFiche}
          onAfterAction={afterFicheAction}
        />
      )}
    </div>
  )
}


// --- Sous-composants -----------------------------------------------------

function DashTab({
  active, onClick, children,
}: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-sm rounded-t border-b-2 -mb-px transition-colors ${
        active
          ? 'text-c-brand border-c-brand font-semibold'
          : 'text-c-ink-faint border-transparent hover:text-c-ink'
      }`}>
      {children}
    </button>
  )
}


function SectionCard({
  title, badge, loading, children,
}: {
  title: string; badge: number; loading: boolean; children: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-lg border border-c-line-soft">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-c-line-soft">
        <h2 className="text-sm font-semibold text-c-ink uppercase tracking-wide">
          {title}
        </h2>
        <span className="text-xs bg-c-brand-soft text-c-brand rounded-full px-2 py-0.5 font-medium">
          {badge}
        </span>
        {loading && (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-c-ink-faint" />
        )}
      </div>
      <div className="overflow-x-auto">{children}</div>
    </div>
  )
}


function TicketsTable({
  rows, onDoubleClick, variant,
}: {
  rows: TicketRow[]
  onDoubleClick: (r: TicketRow) => void
  variant: 'encours' | 'traites'
}) {
  return (
    <table className="text-xs w-full">
      <thead className="bg-c-surface-soft text-c-ink-soft">
        <tr>
          {variant === 'encours' && (
            <th className="py-1.5 px-2 text-left">Appel</th>
          )}
          <th className="py-1.5 px-2 text-left">Partenaire</th>
          <th className="py-1.5 px-2 text-left">Date</th>
          <th className="py-1.5 px-2 text-left">Client</th>
          <th className="py-1.5 px-2 text-left">CP</th>
          <th className="py-1.5 px-2 text-left">Ville</th>
          <th className="py-1.5 px-2 text-left">Vendeur</th>
          <th className="py-1.5 px-2 text-left">Agence</th>
          <th className="py-1.5 px-2 text-left">Statut</th>
          {variant === 'traites' && (
            <>
              <th className="py-1.5 px-2 text-right">Nb offres</th>
              <th className="py-1.5 px-2 text-right">Fibre val.</th>
              <th className="py-1.5 px-2 text-right">Mob. val.</th>
              <th className="py-1.5 px-2 text-right">Off. val.</th>
              <th className="py-1.5 px-2 text-right">Num BS</th>
              <th className="py-1.5 px-2 text-left">Détail brut</th>
            </>
          )}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id}
              onDoubleClick={() => onDoubleClick(r)}
              className="border-b border-c-line-soft hover:bg-c-surface-soft cursor-pointer">
            {variant === 'encours' && (
              <td className="py-1 px-2 text-xs text-c-ink-faint whitespace-nowrap">
                {r.appel_en_cours ? `📞 ${r.ope_appel_nom || ''}` : ''}
                {r.ticket_diff && (
                  <span className="ml-1 text-red-600 font-bold">DIFF</span>
                )}
              </td>
            )}
            <td className="py-1 px-2">
              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold whitespace-nowrap ${
                r.partenaire === 'SFR'
                  ? 'bg-orange-100 text-orange-700'
                  : 'bg-emerald-100 text-emerald-700'
              }`}
                    title={r.partenaire}>
                {r.partenaire_lib || r.partenaire}
              </span>
            </td>
            <td className="py-1 px-2 tabular-nums whitespace-nowrap">
              {variant === 'encours'
                ? fmtDateTimeFr(r.date_crea)
                : fmtDateFr(r.date_crea)}
            </td>
            <td className="py-1 px-2 font-medium">{r.nom_client}</td>
            <td className="py-1 px-2 tabular-nums">{r.cp}</td>
            <td className="py-1 px-2">{r.ville}</td>
            <td className="py-1 px-2">{r.nom_vendeur}</td>
            <td className="py-1 px-2">{r.agence || r.lib_equipe || ''}</td>
            <td className="py-1 px-2">
              <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] ${
                r.appel_en_cours
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-700'
              }`}>
                {r.lib_statut}
              </span>
            </td>
            {variant === 'traites' && (
              <>
                <td className="py-1 px-2 text-right tabular-nums">
                  {r.nb_offres || ''}
                </td>
                <td className="py-1 px-2 text-right tabular-nums">
                  {r.nb_fibre_valide || ''}
                </td>
                <td className="py-1 px-2 text-right tabular-nums">
                  {r.nb_mobile_valide || ''}
                </td>
                <td className="py-1 px-2 text-right tabular-nums">
                  {r.nb_offres_valides || ''}
                </td>
                <td className="py-1 px-2 text-right tabular-nums">
                  {r.nb_num_bs || ''}
                </td>
                <td className="py-1 px-2 text-xs text-c-ink-faint whitespace-nowrap">
                  {r.nb_brut_par_partenaire
                    ? Object.entries(r.nb_brut_par_partenaire)
                        .map(([p, n]) => `${p}:${n}`).join(' · ')
                    : ''}
                </td>
              </>
            )}
          </tr>
        ))}
        {rows.length === 0 && (
          <tr>
            <td colSpan={variant === 'encours' ? 9 : 14}
                className="py-6 text-center text-c-ink-faint italic">
              Aucun ticket
            </td>
          </tr>
        )}
      </tbody>
    </table>
  )
}


function DashboardFibreView({ data }: { data: DashFibre | null }) {
  if (!data) return <div className="text-center text-c-ink-faint text-xs py-4">Chargement…</div>
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Paniers validés" value={data.paniers_valides} />
        <KpiCard label="Offres Fibre THD" value={data.offres_fibre_thd} />
        <KpiCard label="CQ Fibre validés" value={data.cq_fibre_valides} />
        <KpiCard label="Mobiles validés" value={data.mobiles_valides} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {data.agences_internes.map((a) => (
          <AgenceCardFibre key={a.id_orga} agence={a} />
        ))}
        <AgenceCardFibre agence={{
          id_orga: 'power', lib_orga: 'Power',
          nb_fibre: data.nb_fibre_power, nb_mobile: data.nb_mobile_power,
          gimmick_url: '',
        }} />
        <AgenceCardFibre agence={{
          id_orga: 'fox', lib_orga: 'Fox',
          nb_fibre: data.nb_fibre_fox, nb_mobile: data.nb_mobile_fox,
          gimmick_url: '',
        }} />
      </div>
    </div>
  )
}


function DashboardEnergieView({ data }: { data: DashEnergie | null }) {
  if (!data) return <div className="text-center text-c-ink-faint text-xs py-4">Chargement…</div>
  return (
    <div className="space-y-4">
      <div className="text-sm text-c-ink-soft mb-1">
        <span className="font-semibold text-c-ink text-lg">
          {data.tickets_valides}
        </span> tickets validés
      </div>
      <div className="flex flex-wrap gap-2">
        {data.partenaires.map((p) => (
          <div key={p.prefix}
               className="px-3 py-2 rounded border border-c-line-soft bg-white text-xs">
            <div className="font-semibold">{p.lib}</div>
            <div className="text-c-ink-faint">
              {p.nb_offres} offres · {p.nb_clients} clients
            </div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {data.agences_internes.map((a) => (
          <ZoneCard key={a.id_orga} title={a.lib_orga} rows={a.par_partenaire} />
        ))}
        <ZoneCard title="Multicom" rows={data.multicom.par_partenaire} />
        <ZoneCard title="Power" rows={data.power.par_partenaire} />
      </div>
    </div>
  )
}


function KpiCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white border border-c-line-soft rounded-lg p-3">
      <div className="text-2xl font-bold text-c-ink tabular-nums">{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-c-ink-faint mt-1">
        {label}
      </div>
    </div>
  )
}


function AgenceCardFibre({ agence }: {
  agence: { id_orga: string; lib_orga: string; nb_fibre: number; nb_mobile: number; gimmick_url: string }
}) {
  return (
    <div className="bg-white border border-c-line-soft rounded-lg p-3">
      <div className="text-xs font-semibold text-c-ink">{agence.lib_orga}</div>
      <div className="flex gap-3 mt-1 text-xs">
        <span>Fibre <b className="tabular-nums">{agence.nb_fibre}</b></span>
        <span>Mob <b className="tabular-nums">{agence.nb_mobile}</b></span>
      </div>
    </div>
  )
}


function ZoneCard({ title, rows }: { title: string; rows: DashPartRow[] }) {
  // Grid a 3 colonnes : partenaire (auto) + offres (fixed) + clients (fixed).
  // Le header et chaque ligne partagent exactement la meme grille -> les
  // chiffres tombent pile sous leurs en-tetes.
  return (
    <div className="bg-white border border-c-line-soft rounded-lg p-3">
      <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 items-baseline mb-1">
        <div className="text-xs font-semibold text-c-ink">{title}</div>
        {rows.length > 0 ? (
          <>
            <span
              className="w-14 justify-end flex items-center gap-1 text-[10px] uppercase tracking-wide text-c-ink-faint"
              title="Nombre d'offres validées">
              <Package className="w-3 h-3" /> Offres
            </span>
            <span
              className="w-14 justify-end flex items-center gap-1 text-[10px] uppercase tracking-wide text-c-ink-faint"
              title="Nombre de clients distincts">
              <Users className="w-3 h-3" /> Clients
            </span>
          </>
        ) : (
          <>
            <span />
            <span />
          </>
        )}
      </div>
      {rows.length === 0 ? (
        <div className="text-[10px] italic text-c-ink-faint">Aucune offre</div>
      ) : (
        <div className="space-y-0.5">
          {rows.map((r) => (
            <div key={r.prefix}
                 className="grid grid-cols-[1fr_auto_auto] gap-x-4 text-xs">
              <span>{r.lib}</span>
              <span className="w-14 text-right tabular-nums text-c-ink-faint">
                {r.nb_offres}
              </span>
              <span className="w-14 text-right tabular-nums text-c-ink-faint">
                {r.nb_clients}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
