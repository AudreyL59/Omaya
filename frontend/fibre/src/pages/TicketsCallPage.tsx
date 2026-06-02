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

import { useCallback, useEffect, useRef, useState } from 'react'
import { Loader2, FileSpreadsheet, Eye, Search } from 'lucide-react'
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

interface PageData {
  tickets_en_cours: TicketEnCours[]
  tickets_traites: TicketTraite[]
  stats: Stats
  serveur_now: string
  last_modif: string
}

const API_BASE = '/api/call/fibre'

// Intervalle de refresh auto (en ms). On utilise un simple polling court a la
// place du long polling /tickets/live (qui timeout sur MAX(ModifDate) en
// HFSQL sans index adequat). A reactiver au cutover PG si besoin.
const REFRESH_INTERVAL_MS = 10_000

export default function TicketsCallPage() {
  const [data, setData] = useState<PageData | null>(null)
  const [loading, setLoading] = useState(true)
  const [clientNow, setClientNow] = useState('')
  // Date du champ de saisie au-dessus du tableau du BAS (defaut = today).
  const [jourBas, setJourBas] = useState(() => new Date().toISOString().slice(0, 10))
  const stoppedRef = useRef(false)
  const jourBasRef = useRef(jourBas)

  useEffect(() => {
    jourBasRef.current = jourBas
  }, [jourBas])

  // Refresh : fait un GET /tickets avec la date actuelle.
  // Appele au mount + a chaque interval + sur action user (bouton Search).
  const refetch = useCallback(async () => {
    try {
      const jour = encodeURIComponent(jourBasRef.current)
      const r = await fetch(`${API_BASE}/tickets?jour=${jour}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (r.ok) {
        const page = await r.json()
        if (!stoppedRef.current) {
          setData(page)
          setClientNow(new Date().toLocaleString('fr-FR'))
        }
      }
    } catch {
      // ignore (next interval will retry)
    } finally {
      if (!stoppedRef.current) {
        setLoading(false)
      }
    }
  }, [])

  // Mount : refetch immediat + setInterval pour le refresh periodique
  useEffect(() => {
    stoppedRef.current = false
    refetch()
    const id = setInterval(refetch, REFRESH_INTERVAL_MS)
    return () => {
      stoppedRef.current = true
      clearInterval(id)
    }
  }, [refetch])

  const refetchNow = refetch

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-c-brand animate-spin" />
      </div>
    )
  }
  if (!data) {
    return (
      <div className="h-full flex items-center justify-center text-c-ink-faint">
        Aucune donnée.
      </div>
    )
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header : titre + 4 stats globales */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-c-ink">Call SFR</h1>
        <div className="flex items-center gap-3">
          <StatCircle label="Paniers validés" value={data.stats.paniers_valides} />
          <StatCircle label="Offres Fibre THD" value={data.stats.offres_fibre_thd} />
          <StatCircle label="CQ Fibre Validés" value={data.stats.cq_fibre_valides} />
          <StatCircle label="Mobiles Validés" value={data.stats.mobiles_valides} />
        </div>
      </div>

      {/* Bandeau dernière vérif */}
      <div className="text-xs text-c-ink-faint">
        Dernière vérif intranet le {clientNow}, dernier calcul serveur le{' '}
        {data.serveur_now}
      </div>

      {/* Tableau du HAUT : tickets à traiter */}
      <SectionHeader title="Tickets Call à traiter" right={<HautActions />} />
      <TableEnCours rows={data.tickets_en_cours} />

      {/* Tableau du BAS : tickets traités du jour */}
      <SectionHeader
        title="Tickets Call traités du jour"
        right={
          <BasActions
            date={jourBas}
            onChangeDate={setJourBas}
            onApply={refetchNow}
          />
        }
      />
      <TableTraites rows={data.tickets_traites} />

      {/* Footer : stats par agence */}
      <FooterAgences stats={data.stats} />
    </div>
  )
}

// --- Sous-composants -------------------------------------------------------

function StatCircle({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col items-center">
      <div className="w-16 h-16 rounded-full border-2 border-c-brand flex items-center justify-center text-lg font-bold text-c-brand">
        {value}
      </div>
      <div className="text-xs text-c-ink-soft mt-1 text-center max-w-[80px]">
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
}: {
  date: string
  onChangeDate: (d: string) => void
  onApply: () => void
}) {
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
        className="flex items-center gap-2 px-2 py-1 rounded-md border border-c-line-strong text-xs hover:bg-c-brand-soft"
        title="Appliquer la date"
      >
        <Search className="w-3.5 h-3.5" />
      </button>
      <button className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-red-600 text-white text-sm font-semibold hover:brightness-110">
        <FileSpreadsheet className="w-4 h-4" />
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
      <div className="border border-c-line rounded-md p-6 text-center text-c-ink-faint text-sm">
        Aucun ticket en cours.
      </div>
    )
  }
  return (
    <div className="border border-c-line rounded-md overflow-x-auto bg-white">
      <table className="w-full text-xs">
        <thead className="bg-c-surface-soft">
          <tr className="text-left text-c-ink-soft">
            <Th>Appel en cours par</Th>
            <Th>Commande faite le</Th>
            <Th>Client</Th>
            <Th>CP</Th>
            <Th>Ville</Th>
            <Th>Commercial</Th>
            <Th>Équipe</Th>
            <Th>Non Prod</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => {
            // Coloration ligne (cf. WinDev)
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
                className={`${bg} ${textColor} border-t border-c-line-soft hover:bg-c-brand-soft cursor-pointer`}
              >
                <Td>{t.ope_appel_nom}</Td>
                <Td>{shortDateTime(t.date_crea)}</Td>
                <Td>{t.nom_client}</Td>
                <Td>{t.cp}</Td>
                <Td>{t.ville}</Td>
                <Td>{t.nom_vendeur}</Td>
                <Td>{t.lib_equipe}</Td>
                <Td>
                  {t.non_prod && (
                    <span className="inline-block w-3 h-3 rounded-full bg-green-500" />
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

function TableTraites({ rows }: { rows: TicketTraite[] }) {
  if (!rows.length) {
    return (
      <div className="border border-c-line rounded-md p-6 text-center text-c-ink-faint text-sm">
        Aucun ticket traité aujourd'hui.
      </div>
    )
  }
  return (
    <div className="border border-c-line rounded-md overflow-x-auto bg-white">
      <table className="w-full text-xs">
        <thead className="bg-c-surface-soft">
          <tr className="text-left text-c-ink-soft">
            <Th>Commande faite le</Th>
            <Th>Client</Th>
            <Th>CP</Th>
            <Th>Ville</Th>
            <Th>Commercial</Th>
            <Th>Agence</Th>
            <Th>État</Th>
            <Th>NB Offres</Th>
            <Th>NB Fibre Valide</Th>
            <Th>NB Mobile Valide</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => {
            const bg = t.vendeur_distrib
              ? 'bg-gray-100'
              : t.premier_contrat
                ? 'bg-green-100'
                : t.delai_depasse
                  ? 'bg-red-100'
                  : 'bg-white'
            return (
              <tr
                key={t.id}
                className={`${bg} border-t border-c-line-soft hover:bg-c-brand-soft cursor-pointer`}
              >
                <Td>{shortDateTime(t.date_crea)}</Td>
                <Td>{t.nom_client}</Td>
                <Td>{t.cp}</Td>
                <Td>{t.ville}</Td>
                <Td>{t.nom_vendeur}</Td>
                <Td>{t.agence}</Td>
                <Td>{t.lib_statut}</Td>
                <Td className="text-right">{t.nb_offres}</Td>
                <Td className="text-right">{t.nb_fibre_valide}</Td>
                <Td className="text-right">{t.nb_mobile_valide}</Td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function FooterAgences({ stats }: { stats: Stats }) {
  return (
    <div className="border-t border-c-line pt-4 mt-2">
      <div className="text-xs text-c-ink-soft mb-2">Détail SFR Fibre par agence</div>
      <div className="flex items-center gap-4 overflow-x-auto">
        <AgenceTotal label="Tot Interne" fibre={stats.agences_internes.reduce((s, a) => s + a.nb_fibre, 0)} mobile={stats.agences_internes.reduce((s, a) => s + a.nb_mobile, 0)} />
        {stats.agences_internes.map((a) => (
          <AgenceCard key={a.id_orga} agence={a} />
        ))}
        <AgenceTotal label="Tot Power" fibre={stats.nb_fibre_power} mobile={stats.nb_mobile_power} />
        <AgenceTotal label="Tot Fox" fibre={stats.nb_fibre_fox} mobile={stats.nb_mobile_fox} />
      </div>
    </div>
  )
}

function AgenceTotal({ label, fibre, mobile }: { label: string; fibre: number; mobile: number }) {
  return (
    <div className="flex flex-col items-center shrink-0">
      <div className="text-xs text-c-ink-soft">{label}</div>
      <div className="flex items-center gap-2 text-xs">
        <span className="px-2 py-0.5 rounded-md bg-c-brand-soft text-c-brand font-semibold">
          F {fibre}
        </span>
        <span className="px-2 py-0.5 rounded-md bg-c-brand-soft text-c-brand font-semibold">
          M {mobile}
        </span>
      </div>
    </div>
  )
}

function AgenceCard({ agence }: { agence: StatAgence }) {
  return (
    <div className="flex flex-col items-center shrink-0 px-2">
      <div className="w-10 h-10 rounded-full bg-c-surface-soft border border-c-line flex items-center justify-center text-xs text-c-ink-soft">
        {agence.lib_orga.slice(0, 2).toUpperCase()}
      </div>
      <div className="text-[10px] text-c-ink-soft mt-1 max-w-[80px] truncate">
        {agence.lib_orga}
      </div>
      <div className="flex items-center gap-1 text-[10px] mt-0.5">
        <span className="text-c-brand font-semibold">F{agence.nb_fibre}</span>
        <span className="text-c-brand font-semibold">M{agence.nb_mobile}</span>
      </div>
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 font-semibold">{children}</th>
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
