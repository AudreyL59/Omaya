/**
 * Page principale Call Energie (transposition de la fenetre WinDev Call ENI).
 *
 * Architecture (MVP sans dashboard 4-stats - a definir avec le user) :
 * - Header simple : titre + timestamps
 * - Tableau du HAUT : tickets a traiter (live update via long polling)
 * - Tableau du BAS : tickets traites du jour
 *
 * Long polling : appel a /tickets/live?since=<last_modif>. Si pas de changement
 * en 25s, le serveur repond changed=false, on relance immediatement. Sinon il
 * renvoie la page complete et on met a jour.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Loader2,
  FileSpreadsheet,
  Eye,
  Search,
  Zap,
  Package,
  User,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  Check,
} from 'lucide-react'
import { getToken } from '@/api'

interface TicketEnCours {
  id: string
  date_crea: string
  nom_client: string
  cp: string
  ville: string
  nom_vendeur: string
  lib_equipe: string
  lib_statut: string
  id_tk_statut: number
  fdv_interne: boolean
  non_prod: boolean
  appel_en_cours: boolean
  ope_appel_nom: string
  ticket_diff: boolean
}

interface TicketTraite {
  id: string
  date_crea: string
  nom_client: string
  cp: string
  ville: string
  nom_vendeur: string
  agence: string
  lib_statut: string
  ref_appel: string
  nb_offres: number
  nb_offres_valides: number
  nb_num_bs: number
  nb_brut_par_partenaire: Record<string, number>
  vendeur_distrib: boolean
  premier_contrat: boolean
  delai_depasse: boolean
}

interface StatPartenaire {
  id: string
  prefix: string
  lib: string
  logo_url: string
  nb_offres: number
  nb_clients: number
}

interface StatPartenaireZone {
  prefix: string
  lib: string
  logo_url: string
  nb_offres: number
  nb_clients: number
}

interface StatAgenceEnergie {
  id_orga: string
  lib_orga: string
  gimmick_url: string
  par_partenaire: StatPartenaireZone[]
}

interface StatZoneDistrib {
  par_partenaire: StatPartenaireZone[]
}

interface StatsEnergie {
  tickets_valides: number
  partenaires: StatPartenaire[]
  agences_internes: StatAgenceEnergie[]
  multicom: StatZoneDistrib
  power: StatZoneDistrib
}

interface EnCoursPayload {
  tickets_en_cours: TicketEnCours[]
  serveur_now: string
  last_modif: string
}

interface TraitesPayload {
  tickets_traites: TicketTraite[]
  stats: StatsEnergie
}

const API_BASE = '/api/call/energie'

// Intervalle de refresh auto (en ms). On utilise un simple polling court a la
// place du long polling /tickets/live (qui timeout sur MAX(ModifDate) en
// HFSQL sans index adequat). A reactiver au cutover PG si besoin.
// Long polling : /tickets/live attend max 25s qu'un ticket bouge cote
// serveur, puis renvoie la page complete. Detection ~instantanee.
// Si timeout sans changement -> on relance immediatement.
// Pas d'interval cote client (juste une boucle qui relance des qu'elle
// recoit une reponse).

export default function TicketsCallPage() {
  // 2 etats separes : on affiche les "en cours" des qu'on les a, sans
  // attendre les "traites" + stats (chargement plus long).
  const [enCours, setEnCours] = useState<EnCoursPayload | null>(null)
  const [traites, setTraites] = useState<TraitesPayload | null>(null)
  const [loadingTraites, setLoadingTraites] = useState(true)
  const [clientNow, setClientNow] = useState('')
  const [jourBas, setJourBas] = useState(() => new Date().toISOString().slice(0, 10))
  const lastModifRef = useRef('')
  const stoppedRef = useRef(false)
  const jourBasRef = useRef(jourBas)

  useEffect(() => {
    jourBasRef.current = jourBas
  }, [jourBas])

  // Helper: fetch les en-cours (initial + long polling)
  const fetchEnCours = useCallback(async () => {
    const r = await fetch(`${API_BASE}/tickets/en-cours`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!r.ok) return null
    return (await r.json()) as EnCoursPayload
  }, [])

  // Helper: fetch les traites + stats (background + sur changement de date)
  const fetchTraites = useCallback(async (jour: string) => {
    setLoadingTraites(true)
    try {
      const r = await fetch(`${API_BASE}/tickets/traites?jour=${encodeURIComponent(jour)}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (r.ok) {
        const data = (await r.json()) as TraitesPayload
        if (!stoppedRef.current) setTraites(data)
      }
    } finally {
      if (!stoppedRef.current) setLoadingTraites(false)
    }
  }, [])

  // Long polling sur les EN COURS uniquement (le bas est rafraichi separement).
  const poll = useCallback(async () => {
    while (!stoppedRef.current) {
      try {
        const since = encodeURIComponent(lastModifRef.current)
        const r = await fetch(`${API_BASE}/tickets/live?since=${since}`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        if (!r.ok) {
          await new Promise((res) => setTimeout(res, 5000))
          continue
        }
        const body = await r.json()
        if (body.changed && body.page) {
          if (!stoppedRef.current) {
            setEnCours(body.page)
            lastModifRef.current = body.last_modif
            setClientNow(new Date().toLocaleString('fr-FR'))
            // Quand un ticket bouge cote serveur, rafraichir aussi les traites
            // (un ticket peut etre passe de "en cours" a "traite").
            fetchTraites(jourBasRef.current)
          }
        } else {
          lastModifRef.current = body.last_modif || lastModifRef.current
        }
      } catch {
        await new Promise((res) => setTimeout(res, 3000))
      }
    }
  }, [fetchTraites])

  // Refetch traites a la demande (changement de date par l'user)
  const refetchNow = useCallback(async () => {
    await fetchTraites(jourBasRef.current)
  }, [fetchTraites])

  // Mount : 1. fetch en-cours en priorite (affichage immediat),
  //         2. fetch traites en parallele,
  //         3. demarre le long polling.
  useEffect(() => {
    stoppedRef.current = false
    ;(async () => {
      const p1 = fetchEnCours().then((p) => {
        if (p && !stoppedRef.current) {
          setEnCours(p)
          lastModifRef.current = p.last_modif
          setClientNow(new Date().toLocaleString('fr-FR'))
        }
      })
      const p2 = fetchTraites(jourBasRef.current)
      // Demarre le polling apres que l'en-cours soit charge (pour avoir un last_modif)
      await p1
      poll()
      await p2
    })()
    return () => {
      stoppedRef.current = true
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Affichage progressif :
  // - Tant qu'on n'a pas les en-cours, on montre un loader plein ecran.
  // - Des qu'on les a, on affiche le haut + un placeholder pour le bas.
  if (!enCours) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-c-brand animate-spin" />
      </div>
    )
  }

  const traitesRows = traites?.tickets_traites || []
  const stats = traites?.stats
  // Partenaires connus (pour les colonnes dynamiques du tableau du bas
  // "NB Offres <lib> (Brut)" et l'access aux compteurs via prefix).
  const partenaires = stats?.partenaires || []

  return (
    <div className="p-6 space-y-4">
      {/* DASHBOARD : Tickets validés + cercles par Partenaire (Offres + Clients) */}
      <DashboardEnergie
        clientNow={clientNow}
        serveurNow={enCours.serveur_now}
        stats={stats}
      />

      {/* Tableau du HAUT : tickets à traiter */}
      <SectionHeader title="Tickets Call à traiter" right={<HautActions />} />
      <TableEnCours rows={enCours.tickets_en_cours} />

      {/* Tableau du BAS : tickets traités du jour (placeholder pendant chargement) */}
      <SectionHeader
        title="Tickets Call traités du jour"
        right={
          <BasActions
            date={jourBas}
            onChangeDate={setJourBas}
            onApply={refetchNow}
            rows={traitesRows}
            loading={loadingTraites}
          />
        }
      />
      {loadingTraites && !traites ? (
        <div className="border border-c-line rounded-md p-6 text-center text-c-ink-faint text-sm flex items-center justify-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" />
          Chargement des tickets traités...
        </div>
      ) : (
        <TableTraites rows={traitesRows} partenaires={partenaires} />
      )}
    </div>
  )
}

// --- Dashboard Energie (haut de page) -------------------------------------

function DashboardEnergie({
  clientNow,
  serveurNow,
  stats,
}: {
  clientNow: string
  serveurNow: string
  stats: StatsEnergie | undefined
}) {
  const [expanded, setExpanded] = useState(false)
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const scrollBy = (dir: 1 | -1) => {
    if (!scrollRef.current) return
    scrollRef.current.scrollBy({ left: dir * 240, behavior: 'smooth' })
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-c-line overflow-hidden">
      {/* Ligne 1 : titre + tickets validés + carrousel partenaires */}
      <div className="p-5">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-emerald-600 flex items-center justify-center shadow">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-c-ink leading-tight">Call ENI</h1>
              <p className="text-[11px] text-c-ink-faint">
                Dernière vérif {clientNow || '—'} · serveur {serveurNow || '—'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-8">
            {/* Tickets validés - gros cercle vert */}
            <div className="flex flex-col items-center min-w-[90px]">
              <div className="w-16 h-16 rounded-full border border-emerald-600 flex items-center justify-center text-xl font-bold text-emerald-700 bg-white">
                {stats?.tickets_valides ?? 0}
              </div>
              <div className="text-[11px] text-c-ink-soft mt-1 text-center font-medium uppercase tracking-wide">
                Tickets validés
              </div>
            </div>

            {/* Séparateur vertical + libellé "Détail Panier" */}
            <div className="hidden md:block self-stretch border-l border-c-line-soft" />
            <div className="hidden lg:block text-[11px] text-c-ink-soft uppercase tracking-wide font-medium max-w-[120px] leading-snug">
              Détail panier : Offres validées par Opérateur
            </div>

            {/* Carrousel de partenaires (logo + 2 cercles) */}
            {stats ? (
              <div className="flex items-center gap-7 overflow-x-auto" style={{ scrollbarWidth: 'thin' }}>
                {stats.partenaires.map((p) => (
                  <PartenaireBlock key={p.id} partenaire={p} />
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-2 text-c-ink-faint text-xs">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Stats...
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Section dépliable : Totaux a gauche + Carrousel agences a droite. */}
      {expanded && stats && (
        <div className="border-t border-c-line-soft p-5">
          <div className="flex items-start gap-8">
            <div className="flex flex-col gap-4 shrink-0 pr-6 border-r border-c-line-soft">
              <TotalRow label="Tot Interne" par_partenaire={mergeInternes(stats.agences_internes)} />
              <TotalRow label="Tot Multicom" par_partenaire={stats.multicom.par_partenaire} />
              <TotalRow label="Tot Power" par_partenaire={stats.power.par_partenaire} />
            </div>
            <button
              onClick={() => scrollBy(-1)}
              className="shrink-0 text-c-ink-soft hover:text-c-ink p-1 mt-6"
              aria-label="Défiler à gauche"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <div
              ref={scrollRef}
              className="flex items-start gap-10 overflow-x-auto flex-1 px-3 py-1 scroll-smooth"
              style={{ scrollbarWidth: 'thin' }}
            >
              {stats.agences_internes.map((a) => (
                <AgenceEnergieCard key={a.id_orga} agence={a} />
              ))}
            </div>
            <button
              onClick={() => scrollBy(1)}
              className="shrink-0 text-c-ink-soft hover:text-c-ink p-1 mt-6"
              aria-label="Défiler à droite"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {/* Bouton flèche full-width en bas, juste la flèche */}
      {stats && stats.agences_internes.length > 0 && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="w-full border-t border-c-line-soft flex items-center justify-center py-2 text-c-ink-soft hover:bg-c-brand-soft/30 transition-colors"
          title={expanded ? 'Masquer le détail par agence' : 'Afficher le détail par agence'}
          aria-label={expanded ? 'Masquer le détail' : 'Afficher le détail'}
        >
          {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
      )}
    </div>
  )
}

/** Aggrege les par_partenaire de toutes les agences internes en une liste
 *  unique (somme Offres + Clients par partenaire) pour la ligne "Tot Interne". */
function mergeInternes(agences: StatAgenceEnergie[]): StatPartenaireZone[] {
  const acc: Record<string, StatPartenaireZone> = {}
  for (const a of agences) {
    for (const pp of a.par_partenaire) {
      const cur = acc[pp.prefix]
      if (cur) {
        cur.nb_offres += pp.nb_offres
        cur.nb_clients += pp.nb_clients
      } else {
        acc[pp.prefix] = { ...pp }
      }
    }
  }
  return Object.values(acc)
}

function TotalRow({ label, par_partenaire }: { label: string; par_partenaire: StatPartenaireZone[] }) {
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="font-semibold text-c-ink w-24 text-right shrink-0">{label}</span>
      {par_partenaire.length === 0 ? (
        <span className="text-c-ink-faint italic">—</span>
      ) : (
        <div className="flex items-end gap-4">
          {par_partenaire.map((pp) => (
            <PartenaireMiniBlock key={pp.prefix} pp={pp} />
          ))}
        </div>
      )}
    </div>
  )
}

function AgenceEnergieCard({ agence }: { agence: StatAgenceEnergie }) {
  return (
    <div className="flex flex-col items-center shrink-0">
      <div className="flex items-center gap-4">
        {/* Logo agence (gimmick) ou fallback User icon */}
        <div className="w-14 h-14 rounded-full border border-c-line bg-white overflow-hidden flex items-center justify-center shrink-0">
          {agence.gimmick_url ? (
            <img
              src={agence.gimmick_url}
              alt={agence.lib_orga}
              className="w-full h-full object-cover"
            />
          ) : (
            <User className="w-6 h-6 text-c-ink-soft" />
          )}
        </div>
        {/* Mini-blocs par partenaire (logo + Offres + Clients) */}
        {agence.par_partenaire.length === 0 ? (
          <span className="text-xs text-c-ink-faint italic">aucune offre</span>
        ) : (
          <div className="flex items-end gap-4">
            {agence.par_partenaire.map((pp) => (
              <PartenaireMiniBlock key={pp.prefix} pp={pp} />
            ))}
          </div>
        )}
      </div>
      <div className="text-[11px] text-c-ink-soft mt-2 text-center font-medium whitespace-nowrap">
        {agence.lib_orga}
      </div>
    </div>
  )
}

function PartenaireMiniBlock({ pp }: { pp: StatPartenaireZone }) {
  const label = pp.lib || pp.prefix
  return (
    <div className="flex flex-col items-center gap-1 shrink-0" title={label}>
      {/* Logo partenaire en haut (petit) */}
      <div className="w-8 h-6 flex items-center justify-center">
        {pp.logo_url ? (
          <img src={pp.logo_url} alt={label} className="max-w-full max-h-full object-contain" />
        ) : (
          <span className="text-[9px] font-bold text-c-ink-soft">{pp.prefix}</span>
        )}
      </div>
      {/* Compteurs Offres + Clients */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-1.5" title="Offres">
          <Package className="w-3.5 h-3.5 text-c-ink-soft" />
          <span className="text-xs font-bold text-c-ink min-w-[14px]">{pp.nb_offres}</span>
        </div>
        <div className="flex items-center gap-1.5" title="Clients">
          <User className="w-3.5 h-3.5 text-c-ink-soft" />
          <span className="text-xs font-bold text-c-ink min-w-[14px]">{pp.nb_clients}</span>
        </div>
      </div>
    </div>
  )
}

function PartenaireBlock({ partenaire }: { partenaire: StatPartenaire }) {
  const label = partenaire.lib || partenaire.prefix
  return (
    <div className="flex items-center gap-3 shrink-0">
      {/* Logo partenaire sans contour, taille reduite (moitie de l'ancien w-14) */}
      <div className="w-8 h-8 overflow-hidden flex items-center justify-center shrink-0" title={label}>
        {partenaire.logo_url ? (
          <img
            src={partenaire.logo_url}
            alt={label}
            className="w-full h-full object-contain"
          />
        ) : (
          <span className="text-[10px] font-bold text-c-ink-soft">{partenaire.prefix}</span>
        )}
      </div>
      {/* 2 cercles : Offres et Clients */}
      <StatCircle value={partenaire.nb_offres} label="Offres" />
      <StatCircle value={partenaire.nb_clients} label="Clients" />
    </div>
  )
}

function StatCircle({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex flex-col items-center min-w-[60px]">
      <div className="w-12 h-12 rounded-full border border-c-ink flex items-center justify-center text-base font-bold text-c-ink bg-white">
        {value}
      </div>
      <div className="text-[10px] text-c-ink-soft mt-1 text-center font-medium uppercase tracking-wide">
        {label}
      </div>
    </div>
  )
}

// --- Sous-composants -------------------------------------------------------

function SectionHeader({
  title,
  right,
}: {
  title: string
  right?: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between mt-4 mb-1">
      <h2 className="text-sm font-semibold text-c-ink uppercase tracking-wide">
        {title}
      </h2>
      <div className="flex items-center gap-2">{right}</div>
    </div>
  )
}

function HautActions() {
  return (
    <>
      <button className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-c-brand text-white text-sm font-semibold hover:brightness-110">
        <Eye className="w-4 h-4" />
        Voir la fiche
      </button>
    </>
  )
}

function BasActions({
  date,
  onChangeDate,
  onApply,
  rows,
  loading,
}: {
  date: string
  onChangeDate: (d: string) => void
  onApply: () => void
  rows: TicketTraite[]
  loading: boolean
}) {
  const [exporting, setExporting] = useState(false)
  const handleExport = async () => {
    setExporting(true)
    try {
      const r = await fetch(`${API_BASE}/tickets/traites/export?jour=${encodeURIComponent(date)}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ tickets: rows }),
      })
      if (!r.ok) {
        alert("Export Excel : échec (" + r.status + ")")
        return
      }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `tickets_call_energie_${date.replace(/-/g, '')}.xlsx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } finally {
      setExporting(false)
    }
  }
  return (
    <>
      <span className="text-xs text-c-ink-soft">Date</span>
      <input
        type="date"
        value={date}
        onChange={(e) => onChangeDate(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && onApply()}
        className="px-2 py-1 border border-c-line-strong rounded-md text-xs"
      />
      <button
        onClick={onApply}
        disabled={loading}
        className="flex items-center gap-2 px-2 py-1 rounded-md border border-c-line-strong text-xs hover:bg-c-brand-soft disabled:opacity-60"
        title="Appliquer la date"
      >
        {loading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <Search className="w-3.5 h-3.5" />
        )}
      </button>
      <button
        onClick={handleExport}
        disabled={exporting}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-red-600 text-white text-sm font-semibold hover:brightness-110 disabled:opacity-60"
      >
        {exporting ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <FileSpreadsheet className="w-4 h-4" />
        )}
        Export Excel
      </button>
      <button className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-c-brand text-white text-sm font-semibold hover:brightness-110">
        <Eye className="w-4 h-4" />
        Voir la fiche
      </button>
    </>
  )
}

function TableEnCours({ rows }: { rows: TicketEnCours[] }) {
  if (!rows.length) {
    return (
      <div className="border border-c-line rounded-md p-6 text-center text-c-ink-faint text-sm bg-white">
        Aucun ticket en cours.
      </div>
    )
  }
  return (
    <div className="border border-c-line rounded-md overflow-x-auto bg-white">
      <table className="w-full text-xs">
        <thead className="bg-gray-50 border-b border-c-line">
          <tr className="text-left text-c-ink-soft">
            <Th>Appel en cours par</Th>
            <Th>Commande faite le</Th>
            <Th>Client</Th>
            <Th>CP</Th>
            <Th>Ville</Th>
            <Th>Commercial</Th>
            <Th>Équipe</Th>
            <Th className="text-center">FDV Int</Th>
            <Th className="text-center">Non Prod</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => {
            // Coloration ligne (transposition exacte WinDev) :
            //  - Si AppelEnCours : fond ORANGE PASTEL (un opé a pris le ticket)
            //  - Si IDTK_Statut = 34 : texte BLEU RVB(0,102,254)
            //  - Si TicketDiff : texte ROUGE
            const bg = t.appel_en_cours ? 'bg-orange-100' : 'bg-white'
            const textColor =
              t.id_tk_statut === 34
                ? 'text-blue-600'
                : t.ticket_diff
                  ? 'text-red-600'
                  : 'text-c-ink'
            return (
              <tr
                key={t.id}
                className={`${bg} ${textColor} border-t border-c-line-soft hover:bg-c-brand-soft/50 cursor-pointer transition-colors`}
              >
                <Td>{t.ope_appel_nom}</Td>
                <Td>{shortDateTime(t.date_crea)}</Td>
                <Td className="font-medium">{t.nom_client}</Td>
                <Td>{t.cp}</Td>
                <Td>{t.ville}</Td>
                <Td>{t.nom_vendeur}</Td>
                <Td className="text-c-ink-soft">{t.lib_equipe}</Td>
                <Td className="text-center">
                  {t.fdv_interne && <Check className="w-4 h-4 text-c-brand inline" />}
                </Td>
                <Td className="text-center">
                  {t.non_prod && (
                    <span
                      className="inline-block w-3 h-3 rounded-full bg-green-500"
                      title="Premier contrat du vendeur"
                    />
                  )}
                </Td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function TableTraites({ rows, partenaires }: { rows: TicketTraite[]; partenaires: StatPartenaire[] }) {
  if (!rows.length) {
    return (
      <div className="border border-c-line rounded-md p-6 text-center text-c-ink-faint text-sm bg-white">
        Aucun ticket traité aujourd'hui.
      </div>
    )
  }
  return (
    <div className="border border-c-line rounded-md overflow-x-auto bg-white">
      <table className="w-full text-xs">
        <thead className="bg-gray-50 border-b border-c-line">
          <tr className="text-left text-c-ink-soft">
            <Th>Commande faite le</Th>
            <Th>Client</Th>
            <Th>CP</Th>
            <Th>Ville</Th>
            <Th>Commercial</Th>
            <Th>Agence</Th>
            <Th>État</Th>
            <Th className="text-center">NB Offres (brut)</Th>
            {partenaires.map((p) => (
              <Th key={p.prefix} className="text-center">NB Offres {p.lib || p.prefix} (Brut)</Th>
            ))}
            <Th>Réf Appel</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => {
            // Coloration ligne (WinDev) :
            //  - delai NUM >= 1h apres Datecrea : fond ROUGE (priorite max)
            //  - VendeurDistrib : fond GRIS (vendeur du reseau distrib externe)
            //  - 1er contrat du vendeur : fond VERT
            const bg = t.delai_depasse
              ? 'bg-red-100'
              : t.vendeur_distrib
                ? 'bg-gray-100'
                : t.premier_contrat
                  ? 'bg-green-100'
                  : 'bg-white'
            return (
              <tr
                key={t.id}
                className={`${bg} border-t border-c-line-soft hover:bg-c-brand-soft/50 cursor-pointer transition-colors`}
              >
                <Td>{shortDateTime(t.date_crea)}</Td>
                <Td className="font-medium">{t.nom_client}</Td>
                <Td>{t.cp}</Td>
                <Td>{t.ville}</Td>
                <Td>{t.nom_vendeur}</Td>
                <Td className="text-c-ink-soft">{t.agence}</Td>
                <Td>{t.lib_statut}</Td>
                <Td className="text-center"><CountBadge value={t.nb_offres} /></Td>
                {partenaires.map((p) => (
                  <Td key={p.prefix} className="text-center">
                    <CountBadge value={t.nb_brut_par_partenaire?.[p.prefix] || 0} variant="brand" />
                  </Td>
                ))}
                <Td className="text-c-ink-soft">{t.ref_appel}</Td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function CountBadge({ value, variant = 'neutral' }: { value: number; variant?: 'neutral' | 'brand' }) {
  if (!value) {
    return <span className="text-c-ink-faint">—</span>
  }
  const cls =
    variant === 'brand'
      ? 'bg-c-brand text-white'
      : 'bg-gray-100 text-c-ink'
  return (
    <span className={`inline-block min-w-[28px] px-1.5 py-0.5 rounded-md text-xs font-semibold ${cls}`}>
      {value}
    </span>
  )
}

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <th className={`px-3 py-2 font-semibold ${className}`}>{children}</th>
}

function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2 ${className}`}>{children}</td>
}

function shortDateTime(iso: string): string {
  if (!iso) return ''
  const d = iso.slice(0, 16).replace('T', ' ')
  // 'YYYY-MM-DD HH:MM' -> 'DD/MM HH:MM'
  const [date, time] = d.split(' ')
  if (!date) return d
  const parts = date.split('-')
  if (parts.length !== 3) return d
  return `${parts[2]}/${parts[1]} ${time || ''}`.trim()
}
