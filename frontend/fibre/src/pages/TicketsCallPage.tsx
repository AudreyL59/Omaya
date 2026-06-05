/**
 * Page principale Call Fibre (transposition de la fenetre WinDev Call SFR).
 *
 * Architecture :
 * - Header : 4 stats globales du jour (Paniers Valides / Offres Fibre THD /
 *   CQ Fibre Valides / Mobiles Valides)
 * - Tableau du HAUT : tickets a traiter (live update via long polling)
 * - Tableau du BAS : tickets traites du jour
 * - Footer : stats par agence (interne + Power + Fox)
 *
 * Long polling : appel a /tickets/live?since=<last_modif>. Si pas de changement
 * en 25s, le serveur repond changed=false, on relance immediatement. Sinon il
 * renvoie la page complete et on met a jour.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Loader2,
  FileSpreadsheet,
  Eye,
  Search,
  Phone,
  User,
  Smartphone,
  Router,
  ChevronLeft,
  ChevronRight,
  Check,
} from 'lucide-react'
import { getToken } from '@/api'
import FicheTicketModal from '@/components/FicheTicketModal'

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
  nb_fibre_valide: number
  nb_mobile_valide: number
  col_offres_fibre: string
  vendeur_distrib: boolean
  premier_contrat: boolean
  delai_depasse: boolean
}

interface StatAgence {
  id_orga: string
  lib_orga: string
  nb_fibre: number
  nb_mobile: number
  gimmick_url: string
}

interface Stats {
  paniers_valides: number
  offres_fibre_thd: number
  cq_fibre_valides: number
  mobiles_valides: number
  agences_internes: StatAgence[]
  nb_fibre_power: number
  nb_mobile_power: number
  nb_fibre_fox: number
  nb_mobile_fox: number
}

interface EnCoursPayload {
  tickets_en_cours: TicketEnCours[]
  serveur_now: string
  last_modif: string
}

interface TraitesPayload {
  tickets_traites: TicketTraite[]
  stats: Stats
}

const API_BASE = '/api/call/fibre'

// Intervalle de refresh auto (en ms). On utilise un simple polling court a la
// place du long polling /tickets/live (qui timeout sur MAX(ModifDate) en
// HFSQL sans index adequat). A reactiver au cutover PG si besoin.
// Long polling : /tickets/live attend max 25s qu'un ticket bouge cote
// serveur, puis renvoie la page complete. Detection ~instantanee.
// Si timeout sans changement -> on relance immediatement.
// Pas d'interval cote client (juste une boucle qui relance des qu'elle
// recoit une reponse).

// Resout quand l'onglet redevient visible (ou tout de suite s'il l'est deja).
// Sert a mettre le long-poll en pause quand l'onglet est en arriere-plan :
// le navigateur limite a 6 connexions par domaine, partagees entre onglets ;
// un long-poll d'onglet cache tiendrait une connexion ~25s et pourrait
// retarder l'ouverture d'une fiche dans l'onglet actif.
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

export default function TicketsCallPage() {
  // 2 etats separes : on affiche les "en cours" des qu'on les a, sans
  // attendre les "traites" + stats (chargement plus long).
  const [enCours, setEnCours] = useState<EnCoursPayload | null>(null)
  const [traites, setTraites] = useState<TraitesPayload | null>(null)
  const [loadingTraites, setLoadingTraites] = useState(true)
  const [clientNow, setClientNow] = useState('')
  const [jourBas, setJourBas] = useState(() => new Date().toISOString().slice(0, 10))
  // Selection courante pour ouvrir la fiche : on stocke un id par tableau
  // (haut = en cours, bas = traites) + l'id actuellement ouvert dans la modal.
  const [selectedHautId, setSelectedHautId] = useState<string>('')
  const [selectedBasId, setSelectedBasId] = useState<string>('')
  const [ficheOpenId, setFicheOpenId] = useState<string | null>(null)
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
      // Onglet en arriere-plan -> on suspend le long-poll (libere la connexion
      // HTTP pour que l'onglet actif puisse ouvrir une fiche sans faire la queue).
      if (document.hidden) {
        await waitUntilVisible()
        if (stoppedRef.current) break
      }
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

  const stats = traites?.stats
  const traitesRows = traites?.tickets_traites || []

  return (
    <div className="p-6 space-y-4">
      {/* DASHBOARD EN HAUT : titre + 4 stats + agences (Interne/Power/Fox + carrousel) */}
      <DashboardCard
        clientNow={clientNow}
        serveurNow={enCours.serveur_now}
        stats={stats}
      />

      {/* Tableau du HAUT : tickets à traiter */}
      <SectionHeader
        title="Tickets Call à traiter"
        right={<HautActions disabled={!selectedHautId} onClick={() => selectedHautId && setFicheOpenId(selectedHautId)} />}
      />
      <TableEnCours
        rows={enCours.tickets_en_cours}
        selectedId={selectedHautId}
        onSelect={setSelectedHautId}
        onOpenFiche={(id) => setFicheOpenId(id)}
      />

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
            ficheDisabled={!selectedBasId}
            onOpenFiche={() => selectedBasId && setFicheOpenId(selectedBasId)}
          />
        }
      />
      {loadingTraites && !traites ? (
        <div className="border border-c-line rounded-md p-6 text-center text-c-ink-faint text-sm flex items-center justify-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" />
          Chargement des tickets traités...
        </div>
      ) : (
        <TableTraites
          rows={traitesRows}
          selectedId={selectedBasId}
          onSelect={setSelectedBasId}
          onOpenFiche={(id) => setFicheOpenId(id)}
        />
      )}

      {/* Popup fiche ticket */}
      <FicheTicketModal
        idTicket={ficheOpenId}
        onClose={() => setFicheOpenId(null)}
        onAfterAction={async () => {
          // Apres une action panier (valider/annuler/renvoyer) : refetch les
          // 2 tableaux pour que le ticket disparaisse du haut et apparaisse
          // dans le bas (ou inversement).
          const p = await fetchEnCours()
          if (p) {
            setEnCours(p)
            lastModifRef.current = p.last_modif
          }
          await fetchTraites(jourBasRef.current)
        }}
      />
    </div>
  )
}

// --- Dashboard (haut de page : titre + stats globales + stats agences) -----

function DashboardCard({
  clientNow,
  serveurNow,
  stats,
}: {
  clientNow: string
  serveurNow: string
  stats: Stats | undefined
}) {
  const totInterneFibre = stats?.agences_internes.reduce((s, a) => s + a.nb_fibre, 0) ?? 0
  const totInterneMobile = stats?.agences_internes.reduce((s, a) => s + a.nb_mobile, 0) ?? 0
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const scrollBy = (dir: 1 | -1) => {
    if (!scrollRef.current) return
    scrollRef.current.scrollBy({ left: dir * 240, behavior: 'smooth' })
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-c-line p-5 space-y-5">
      {/* Header : Logo + titre + 4 cercles de stats */}
      <div className="flex items-center flex-wrap gap-8">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center shadow">
            <Phone className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-c-ink leading-tight">Call SFR</h1>
            <p className="text-[11px] text-c-ink-faint">
              Dernière vérif {clientNow || '—'} · serveur {serveurNow || '—'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-10">
          <StatCircle label="Paniers validés" value={stats?.paniers_valides ?? 0} />
          <StatCircle label="Offres Fibre THD" value={stats?.offres_fibre_thd ?? 0} />
          <StatCircle label="CQ Fibre Validés" value={stats?.cq_fibre_valides ?? 0} />
          <StatCircle label="Mobiles Validés" value={stats?.mobiles_valides ?? 0} />
        </div>
      </div>

      {/* Séparateur */}
      <div className="border-t border-c-line-soft" />

      {/* Bloc agences : 3 totaux à gauche + carrousel à droite */}
      {stats ? (
        <div className="flex items-center gap-8">
          <div className="flex flex-col gap-2.5 shrink-0 pr-6 border-r border-c-line-soft">
            <TotalRow label="Tot Interne" fibre={totInterneFibre} mobile={totInterneMobile} />
            <TotalRow label="Tot Power" fibre={stats.nb_fibre_power} mobile={stats.nb_mobile_power} />
            <TotalRow label="Tot Fox" fibre={stats.nb_fibre_fox} mobile={stats.nb_mobile_fox} />
          </div>
          <button
            onClick={() => scrollBy(-1)}
            className="shrink-0 text-c-ink-soft hover:text-c-ink p-1"
            aria-label="Defiler à gauche"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div
            ref={scrollRef}
            className="flex items-center gap-16 overflow-x-auto flex-1 px-4 py-1 scroll-smooth"
            style={{ scrollbarWidth: 'thin' }}
          >
            {stats.agences_internes.map((a) => (
              <AgenceCard key={a.id_orga} agence={a} />
            ))}
          </div>
          <button
            onClick={() => scrollBy(1)}
            className="shrink-0 text-c-ink-soft hover:text-c-ink p-1"
            aria-label="Defiler à droite"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      ) : (
        <div className="flex items-center justify-center gap-2 text-c-ink-faint text-xs py-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          Chargement des stats agences...
        </div>
      )}
    </div>
  )
}

// --- Sous-composants -------------------------------------------------------

function StatCircle({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col items-center min-w-[80px]">
      <div className="w-16 h-16 rounded-full border border-c-ink flex items-center justify-center text-xl font-bold text-c-ink bg-white">
        {value}
      </div>
      <div className="text-[11px] text-c-ink-soft mt-1 text-center font-medium uppercase tracking-wide">
        {label}
      </div>
    </div>
  )
}

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

function HautActions({ disabled, onClick }: { disabled: boolean; onClick: () => void }) {
  return (
    <>
      <button
        onClick={onClick}
        disabled={disabled}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed"
        title={disabled ? 'Sélectionne un ticket dans la table' : 'Ouvrir la fiche'}
      >
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
  ficheDisabled,
  onOpenFiche,
}: {
  date: string
  onChangeDate: (d: string) => void
  onApply: () => void
  rows: TicketTraite[]
  loading: boolean
  ficheDisabled: boolean
  onOpenFiche: () => void
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
      a.download = `tickets_call_fibre_${date.replace(/-/g, '')}.xlsx`
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
      <button
        onClick={onOpenFiche}
        disabled={ficheDisabled}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed"
        title={ficheDisabled ? 'Sélectionne un ticket dans la table' : 'Ouvrir la fiche'}
      >
        <Eye className="w-4 h-4" />
        Voir la fiche
      </button>
    </>
  )
}

function TableEnCours({
  rows,
  selectedId,
  onSelect,
  onOpenFiche,
}: {
  rows: TicketEnCours[]
  selectedId: string
  onSelect: (id: string) => void
  onOpenFiche: (id: string) => void
}) {
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
            const isSel = t.id === selectedId
            const bg = isSel
              ? 'bg-c-brand-soft'
              : t.appel_en_cours
                ? 'bg-orange-100'
                : 'bg-white'
            const textColor =
              t.id_tk_statut === 34
                ? 'text-blue-600'
                : t.ticket_diff
                  ? 'text-red-600'
                  : 'text-c-ink'
            return (
              <tr
                key={t.id}
                onClick={() => onSelect(t.id)}
                onDoubleClick={() => onOpenFiche(t.id)}
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

function TableTraites({
  rows,
  selectedId,
  onSelect,
  onOpenFiche,
}: {
  rows: TicketTraite[]
  selectedId: string
  onSelect: (id: string) => void
  onOpenFiche: (id: string) => void
}) {
  const [filters, setFilters] = useState({
    date: '', client: '', cp: '', ville: '', commercial: '', agence: '', etat: '', ref: '',
  })
  const setF = (k: keyof typeof filters) => (v: string) => setFilters((f) => ({ ...f, [k]: v }))
  // Valeurs distinctes pour les colonnes a liste deroulante.
  const agences = useMemo(
    () => [...new Set(rows.map((r) => r.agence).filter(Boolean))].sort(),
    [rows],
  )
  const etats = useMemo(
    () => [...new Set(rows.map((r) => r.lib_statut).filter(Boolean))].sort(),
    [rows],
  )
  const ct = (val: string, f: string) => !f || (val || '').toLowerCase().includes(f.toLowerCase())
  const filtered = useMemo(
    () =>
      rows.filter(
        (t) =>
          ct(shortDateTime(t.date_crea), filters.date) &&
          ct(t.nom_client, filters.client) &&
          ct(t.cp, filters.cp) &&
          ct(t.ville, filters.ville) &&
          ct(t.nom_vendeur, filters.commercial) &&
          (!filters.agence || t.agence === filters.agence) &&
          (!filters.etat || t.lib_statut === filters.etat) &&
          ct(t.ref_appel, filters.ref),
      ),
    [rows, filters],
  )
  const hasFilter = Object.values(filters).some((v) => v)

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
            <Th className="text-center">NB Offres</Th>
            <Th className="text-center">NB Fibre Valide</Th>
            <Th className="text-center">NB Mobile Valide</Th>
            <Th>Réf Appel</Th>
          </tr>
          {/* Ligne de filtres par colonne */}
          <tr className="bg-white border-b border-c-line">
            <FilterCell><FilterInput value={filters.date} onChange={setF('date')} /></FilterCell>
            <FilterCell><FilterInput value={filters.client} onChange={setF('client')} /></FilterCell>
            <FilterCell><FilterInput value={filters.cp} onChange={setF('cp')} /></FilterCell>
            <FilterCell><FilterInput value={filters.ville} onChange={setF('ville')} /></FilterCell>
            <FilterCell><FilterInput value={filters.commercial} onChange={setF('commercial')} /></FilterCell>
            <FilterCell><FilterSelect value={filters.agence} onChange={setF('agence')} options={agences} /></FilterCell>
            <FilterCell><FilterSelect value={filters.etat} onChange={setF('etat')} options={etats} /></FilterCell>
            <FilterCell />
            <FilterCell />
            <FilterCell />
            <FilterCell><FilterInput value={filters.ref} onChange={setF('ref')} /></FilterCell>
          </tr>
        </thead>
        <tbody>
          {hasFilter && filtered.length === 0 && (
            <tr>
              <td colSpan={11} className="px-3 py-4 text-center text-c-ink-faint italic">
                Aucun ticket ne correspond aux filtres.
              </td>
            </tr>
          )}
          {filtered.map((t) => {
            // Coloration ligne (WinDev) :
            //  - delai NUM >= 1h apres Datecrea : fond ROUGE (priorite max)
            //  - VendeurDistrib : fond GRIS (vendeur du reseau distrib externe)
            //  - 1er contrat du vendeur : fond VERT
            //  - ligne selectionnee : override avec un fond bleu doux
            const isSel = t.id === selectedId
            const bg = isSel
              ? 'bg-c-brand-soft'
              : t.delai_depasse
                ? 'bg-red-100'
                : t.vendeur_distrib
                  ? 'bg-gray-100'
                  : t.premier_contrat
                    ? 'bg-green-100'
                    : 'bg-white'
            return (
              <tr
                key={t.id}
                onClick={() => onSelect(t.id)}
                onDoubleClick={() => onOpenFiche(t.id)}
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
                <Td className="text-center"><CountBadge value={t.nb_fibre_valide} variant="brand" /></Td>
                <Td className="text-center"><CountBadge value={t.nb_mobile_valide} variant="brand" /></Td>
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

function TotalRow({ label, fibre, mobile }: { label: string; fibre: number; mobile: number }) {
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="font-semibold text-c-ink w-20 text-right">{label}</span>
      <Router className="w-4 h-4 text-c-ink-soft" aria-label="Fibre" />
      <span className="font-bold text-c-ink min-w-[20px] text-center" title="Fibre">{fibre}</span>
      <Smartphone className="w-4 h-4 text-c-ink-soft" aria-label="Mobile" />
      <span className="font-bold text-c-ink min-w-[20px] text-center" title="Mobile">{mobile}</span>
    </div>
  )
}

function AgenceCard({ agence }: { agence: StatAgence }) {
  return (
    <div className="flex flex-col items-center shrink-0">
      <div className="flex items-center gap-3">
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
        {/* Compteurs Fibre / Mobile en colonne verticale */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2" title="Fibre">
            <Router className="w-3.5 h-3.5 text-c-ink-soft" />
            <span className="text-xs font-bold text-c-ink min-w-[16px]">{agence.nb_fibre}</span>
          </div>
          <div className="flex items-center gap-2" title="Mobile">
            <Smartphone className="w-3.5 h-3.5 text-c-ink-soft" />
            <span className="text-xs font-bold text-c-ink min-w-[16px]">{agence.nb_mobile}</span>
          </div>
        </div>
      </div>
      <div className="text-[11px] text-c-ink-soft mt-2 text-center font-medium whitespace-nowrap">
        {agence.lib_orga}
      </div>
    </div>
  )
}

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <th className={`px-3 py-2 font-semibold ${className}`}>{children}</th>
}

function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2 ${className}`}>{children}</td>
}

// --- Filtres de colonne (tableau des traites) ---------------------------

function FilterCell({ children }: { children?: React.ReactNode }) {
  return <th className="px-2 pb-2 align-top font-normal">{children}</th>
}

function FilterInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Filtrer…"
      className="w-full px-1.5 py-1 border border-c-line rounded text-xs font-normal bg-white focus:border-c-brand focus:ring-1 focus:ring-c-brand focus:outline-none"
    />
  )
}

function FilterSelect({
  value,
  onChange,
  options,
}: {
  value: string
  onChange: (v: string) => void
  options: string[]
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-1.5 py-1 border border-c-line rounded text-xs font-normal bg-white focus:border-c-brand focus:ring-1 focus:ring-c-brand focus:outline-none"
    >
      <option value="">Tous</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  )
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
