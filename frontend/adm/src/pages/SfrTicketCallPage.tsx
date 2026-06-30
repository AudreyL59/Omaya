/**
 * Fen_TicketCallSFR - Suivi SFR > Ticket CALL SFR.
 *
 * 4 onglets :
 *   1. Liste des Tickets : tableau tickets avec resume panier + état
 *   2. Analyse : tranches horaires + compteurs <3m / 3-5m / 5-7m / >7m
 *   3. Analyse des Appels : planning visuel (placeholder cette étape)
 *   4. Analyse des ventes : compteurs + graphique SVG barres
 *
 * Filtres communs : Du / Au + radio Ouverts / Clôturés / Tous.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Search, Loader2, ArrowLeft, PhoneCall, FileDown,
  CalendarClock, BarChart3, Eye,
} from 'lucide-react'
import { showConfirm } from '@shared/ui/dialog'
import {
  useTableSortFilter, SortableTh, FilterInput,
} from '@shared/production/_tableHelpers'
import TicketCallPlanning from '@/components/sfr/TicketCallPlanning'
import TicketCallContenuModal from '@/components/sfr/TicketCallContenuModal'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const API_BASE = '/api/adm'

interface Ticket {
  id_tk_call_sfr: string; id_tk_liste: string
  nb_ctt: number; nb_num_rens: number; nb_ctt_avec_num: number
  contenu_panier: string
  date_crea: string; nom_vendeur: string
  nom_client: string; prenom_client: string; cp: string; ville: string
  nom_operateur: string
  date_deb_prise_en_charge: string; date_fin_prise_en_charge: string
  delai_av_prise_charge_min: number
  duree_appel_min: number
  parcours_chaines: boolean
  row_color_alert: boolean
  lib_statut: string; cloturee: boolean; nb_valide: number
}
interface AnalyseVentes {
  pas_encore_statuees: number; ventes_validees: number; ventes_annulees: number
  par_delai: Array<{ delai: string; ventes_valides: number; ventes_annulees: number }>
}
interface PlanningRdv {
  titre: string; contenu: string
  date_debut: string; date_fin: string
  ressource: string; couleur: string
  delai_label: string; delai_min: number
  nb_valide: number
}

type Etat = 'ouverts' | 'clotures' | 'tous'
type Onglet = 'liste' | 'appels' | 'ventes'

const todayIso = (): string => new Date().toISOString().slice(0, 10)
const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? '' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function SfrTicketCallPage() {
  useDocumentTitle('Ticket Call SFR')
  const [du, setDu] = useState(todayIso())
  const [au, setAu] = useState(todayIso())
  const [etat, setEtat] = useState<Etat>('tous')
  const [onglet, setOnglet] = useState<Onglet>('liste')
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [ventes, setVentes] = useState<AnalyseVentes | null>(null)
  const [planning, setPlanning] = useState<PlanningRdv[]>([])
  const [contenuTicketId, setContenuTicketId] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const rechercher = useCallback(async () => {
    if (du > au) { showToast('Dates incohérentes', 'error'); return }
    setLoading(true)
    setSelected(new Set())
    try {
      const h = { Authorization: `Bearer ${getToken()}` }
      const params = `du=${du}&au=${au}&etat=${etat}`
      const [t, ven, pl] = await Promise.all([
        fetch(`${API_BASE}/suivi-sfr/ticket-call?${params}`, { headers: h }).then(r => r.json()),
        fetch(`${API_BASE}/suivi-sfr/ticket-call/analyse-ventes?${params}`, { headers: h }).then(r => r.json()),
        fetch(`${API_BASE}/suivi-sfr/ticket-call/planning?${params}`, { headers: h }).then(r => r.json()),
      ])
      setTickets(Array.isArray(t) ? t : [])
      setVentes(ven)
      setPlanning(Array.isArray(pl) ? pl : [])
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [du, au, etat])

  useEffect(() => { void rechercher() }, [])

  const toggleAll = () => {
    if (selected.size === tickets.length) setSelected(new Set())
    else setSelected(new Set(tickets.map(t => t.id_tk_call_sfr)))
  }
  const toggle = (id: string) => {
    const s = new Set(selected); if (s.has(id)) s.delete(id); else s.add(id); setSelected(s)
  }

  const exportXlsx = async () => {
    const { exportRowsToXlsx } = await import('@shared/production/_tableHelpers')
    exportRowsToXlsx(
      [
        { key: 'date_crea', label: 'Fiche créée le' },
        { key: 'nb_ctt', label: 'NB Ctt panier' },
        { key: 'nb_num_rens', label: 'NB Num Rens' },
        { key: 'contenu_panier', label: 'Contenu Panier' },
        { key: 'nom_vendeur', label: 'Vendeur' },
        { key: 'nom_operateur', label: 'Opérateur' },
        { key: 'nom_client', label: 'Nom Client' },
        { key: 'prenom_client', label: 'Prénom Client' },
        { key: 'cp', label: 'CP' },
        { key: 'ville', label: 'Ville' },
        { key: 'date_deb_prise_en_charge', label: 'Début prise en charge' },
        { key: 'date_fin_prise_en_charge', label: 'Fin prise en charge' },
        { key: 'delai_av_prise_charge_min', label: 'Délai (min)' },
        { key: 'duree_appel_min', label: 'Durée appel (min)' },
        { key: 'parcours_chaines', label: 'Parcours chaînés' },
        { key: 'lib_statut', label: 'Statut' },
        { key: 'cloturee', label: 'Clôturé' },
      ],
      tickets as unknown as Array<Record<string, unknown>>,
      'tickets-call-sfr', 'Tickets',
    )
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-110px)] text-c-ink">
      <div className="flex items-center gap-2 mb-3">
        <Link to=".." relative="path"
          className="p-1.5 hover:bg-c-surface-soft rounded text-c-ink-faint-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-lg font-bold flex items-center gap-2">
          <PhoneCall className="w-4 h-4 text-c-brand" /> Ticket Call SFR
        </h1>
      </div>

      {/* Filtres */}
      <div className="flex items-center gap-3 mb-3 bg-white p-3 rounded-xl border border-c-line text-sm flex-wrap">
        <label className="text-c-ink-faint text-xs">Du</label>
        <input type="date" value={du} onChange={e => setDu(e.target.value)}
          className="px-2 py-1 border border-c-line rounded text-xs h-7" />
        <label className="text-c-ink-faint text-xs">Au</label>
        <input type="date" value={au} onChange={e => setAu(e.target.value)}
          className="px-2 py-1 border border-c-line rounded text-xs h-7" />
        <div className="flex gap-3 items-center text-xs ml-2">
          {(['ouverts', 'clotures', 'tous'] as const).map(e => (
            <label key={e} className="flex items-center gap-1 cursor-pointer">
              <input type="radio" checked={etat === e} onChange={() => setEtat(e)} />
              {e === 'ouverts' ? 'Ouverts' : e === 'clotures' ? 'Clôturés' : 'Tous'}
            </label>
          ))}
        </div>
        <button type="button" onClick={rechercher} disabled={loading}
          className="flex items-center gap-2 px-4 bg-c-brand text-white rounded text-sm font-medium hover:opacity-90 disabled:opacity-50 h-7">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" />
                   : <Search className="w-4 h-4" />}
          Rechercher
        </button>
        <div className="flex-1" />
        {tickets.length > 0 && (
          <button type="button" onClick={exportXlsx}
            className="flex items-center gap-1.5 px-2.5 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft h-7">
            <FileDown className="w-3.5 h-3.5" /> XLSX
          </button>
        )}
      </div>

      {/* Onglets */}
      <div className="flex gap-1 border-b border-c-line mb-3">
        {([
          ['liste', 'Liste des Tickets', null],
          ['appels', 'Analyse des Appels', CalendarClock],
          ['ventes', 'Analyse des ventes', BarChart3],
        ] as const).map(([key, label, Icon]) => (
          <button key={key} type="button" onClick={() => setOnglet(key)}
            className={`px-4 py-1.5 text-sm font-medium rounded-t flex items-center gap-1.5 ${
              onglet === key
                ? 'bg-white border border-c-line border-b-white text-c-brand'
                : 'text-c-ink-faint hover:bg-c-surface-soft'
            }`}>
            {Icon && <Icon className="w-3.5 h-3.5" />}
            {label}
          </button>
        ))}
      </div>

      {/* Contenu onglet */}
      <div className="flex-1 overflow-hidden bg-white rounded-xl border border-c-line">
        {onglet === 'liste' && (
          <OngletListe tickets={tickets} selected={selected}
            toggle={toggle} toggleAll={toggleAll}
            onVoirTicket={(id) => setContenuTicketId(id)}
            onConvertir={async () => {
              const ids = tickets
                .filter(t => selected.has(t.id_tk_call_sfr))
                .map(t => parseInt(t.id_tk_liste, 10))
              if (ids.length === 0) return
              const ok = await showConfirm({
                title: 'Convertir la sélection en contrat',
                message: `Vous êtes sur le point de convertir ${ids.length} ticket(s) en contrat(s). Voulez-vous continuer ?`,
              })
              if (!ok) return
              try {
                const r = await fetch(
                  `${API_BASE}/suivi-sfr/ticket-call/convert-selection`,
                  {
                    method: 'POST',
                    headers: {
                      Authorization: `Bearer ${getToken()}`,
                      'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ ids_tk_liste: ids }),
                  },
                )
                if (!r.ok) throw new Error(String(r.status))
                const res: Array<{ nb_crees: number; nb_existants: number; nb_erreurs: number }> = await r.json()
                const totals = res.reduce((acc, x) => ({
                  c: acc.c + x.nb_crees,
                  e: acc.e + x.nb_existants,
                  k: acc.k + x.nb_erreurs,
                }), { c: 0, e: 0, k: 0 })
                showToast(`Conversion : ${totals.c} créé(s), ${totals.e} existant(s)${totals.k ? `, ${totals.k} erreur(s)` : ''}`, 'success')
                await rechercher()
              } catch (e) {
                showToast(`Erreur : ${(e as Error).message}`, 'error')
              }
            }}
            onClore={async () => {
              const ids = tickets
                .filter(t => selected.has(t.id_tk_call_sfr))
                .map(t => parseInt(t.id_tk_liste, 10))
              if (ids.length === 0) return
              const ok = await showConfirm({
                title: 'Clôturer sans convertir',
                message: `Vous êtes sur le point de clôturer ${ids.length} ticket(s) SANS convertir en contrat. Continuer ?`,
              })
              if (!ok) return
              try {
                const r = await fetch(
                  `${API_BASE}/suivi-sfr/ticket-call/cloture-selection`,
                  {
                    method: 'POST',
                    headers: {
                      Authorization: `Bearer ${getToken()}`,
                      'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ ids_tk_liste: ids }),
                  },
                )
                if (!r.ok) throw new Error(String(r.status))
                const res: Array<{ cloture_ok: boolean }> = await r.json()
                const ok_count = res.filter(x => x.cloture_ok).length
                showToast(`${ok_count}/${res.length} ticket(s) clôturé(s)`, 'success')
                await rechercher()
              } catch (e) {
                showToast(`Erreur : ${(e as Error).message}`, 'error')
              }
            }}
          />
        )}
        {onglet === 'appels' && (
          <TicketCallPlanning rdvs={planning} initialDate={du} />
        )}
        {onglet === 'ventes' && ventes && <OngletVentes ventes={ventes} />}
      </div>

      {contenuTicketId && (
        <TicketCallContenuModal
          idTkListe={contenuTicketId}
          onClose={() => setContenuTicketId('')}
          onChanged={rechercher}
        />
      )}
    </div>
  )
}

// =================== Onglet 1 : Liste ===========================
function OngletListe({
  tickets, selected, toggle, toggleAll,
  onVoirTicket, onConvertir, onClore,
}: {
  tickets: Ticket[]; selected: Set<string>
  toggle: (id: string) => void; toggleAll: () => void
  onVoirTicket: (idTkListe: string) => void
  onConvertir: () => void
  onClore: () => void
}) {
  const tsf = useTableSortFilter(
    tickets as unknown as Array<Record<string, unknown>>,
    { key: 'date_crea', dir: 'desc' },
    (r) => [
      r.nom_client, r.prenom_client, r.cp, r.ville,
      r.nom_vendeur, r.lib_statut, r.contenu_panier,
    ].map((v) => String(v ?? '')).join(' '),
  )
  const rows = tsf.rows as unknown as Ticket[]

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1.5 border-b border-c-line-soft flex items-center gap-2 text-xs flex-wrap">
        <button type="button"
          className="flex items-center gap-1 px-2 py-1 rounded text-c-brand hover:bg-c-brand/10 disabled:opacity-30"
          disabled={selected.size !== 1}
          onClick={() => {
            const id = Array.from(selected)[0]
            const t = tickets.find(x => x.id_tk_call_sfr === id)
            if (t) onVoirTicket(t.id_tk_liste)
          }}>
          <Eye className="w-3.5 h-3.5" /> Voir le ticket
        </button>
        <button type="button"
          className="px-2 py-1 rounded bg-c-brand text-white disabled:opacity-30"
          disabled={selected.size === 0}
          onClick={onConvertir}>
          Convertir la sélection
        </button>
        <button type="button"
          className="px-2 py-1 rounded text-red-600 hover:bg-red-50 disabled:opacity-30"
          disabled={selected.size === 0}
          onClick={onClore}>
          Clôturer sans convertir
        </button>
        <span className="ml-3 text-c-ink-faint">
          {rows.length} / {tickets.length} ticket(s) | {selected.size} sélectionné(s)
        </span>
        <div className="flex-1" />
        <FilterInput value={tsf.filter} onChange={tsf.setFilter}
          placeholder="Filtrer (client, vendeur, BS…)" />
      </div>
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs">
          <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0 z-10">
            <tr>
              <th className="px-2 py-2 text-center w-8">
                <input type="checkbox" onChange={toggleAll}
                  checked={tickets.length > 0 && selected.size === tickets.length} />
              </th>
              <SortableTh label="NB Ctt" sortKey="nb_ctt" sort={tsf.sort} onSort={tsf.toggleSort} align="center" />
              <SortableTh label="NB Num Rens" sortKey="nb_num_rens" sort={tsf.sort} onSort={tsf.toggleSort} align="center" />
              <SortableTh label="Contenu Panier" sortKey="contenu_panier" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Fiche créée le" sortKey="date_crea" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Vendeur" sortKey="nom_vendeur" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Opérateur" sortKey="nom_operateur" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Nom Client" sortKey="nom_client" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Prénom" sortKey="prenom_client" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="CP" sortKey="cp" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Ville" sortKey="ville" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Délai (min)" sortKey="delai_av_prise_charge_min" sort={tsf.sort} onSort={tsf.toggleSort} align="right" />
              <SortableTh label="Durée appel (min)" sortKey="duree_appel_min" sort={tsf.sort} onSort={tsf.toggleSort} align="right" />
              <SortableTh label="Parc. chaînés" sortKey="parcours_chaines" sort={tsf.sort} onSort={tsf.toggleSort} align="center" />
              <SortableTh label="Statut" sortKey="lib_statut" sort={tsf.sort} onSort={tsf.toggleSort} />
            </tr>
          </thead>
          <tbody className="divide-y divide-c-line-soft">
            {rows.length === 0 ? (
              <tr>
                <td colSpan={14} className="text-center py-12 text-c-ink-faint-2 italic">
                  Aucun ticket — choisis dates puis Rechercher.
                </td>
              </tr>
            ) : rows.map(t => {
              const selBg = selected.has(t.id_tk_call_sfr) ? 'bg-c-brand/10' : ''
              // Alerte rouge si au moins 1 panier saisi > 1h après crea
              const alertBg = t.row_color_alert ? 'bg-red-50' : ''
              return (
              <tr key={t.id_tk_call_sfr}
                onClick={() => toggle(t.id_tk_call_sfr)}
                onDoubleClick={() => onVoirTicket(t.id_tk_liste)}
                className={`cursor-pointer hover:bg-c-surface-soft ${selBg || alertBg}`}>
                <td className="px-2 py-1.5 text-center align-top">
                  <input type="checkbox" checked={selected.has(t.id_tk_call_sfr)}
                    onChange={() => toggle(t.id_tk_call_sfr)}
                    onClick={(e) => e.stopPropagation()} />
                </td>
                <td className="px-2 py-1.5 text-center align-top">{t.nb_ctt}</td>
                <td className="px-2 py-1.5 text-center align-top">{t.nb_num_rens}</td>
                {/* Multi-ligne : chaque BS sur sa ligne */}
                <td className="px-2 py-1.5 align-top text-c-ink-faint whitespace-pre-line">
                  {t.contenu_panier}
                </td>
                <td className="px-2 py-1.5 align-top">{shortDate(t.date_crea)}</td>
                <td className="px-2 py-1.5 align-top">{t.nom_vendeur}</td>
                <td className="px-2 py-1.5 align-top">{t.nom_operateur}</td>
                <td className="px-2 py-1.5 align-top">{t.nom_client}</td>
                <td className="px-2 py-1.5 align-top">{t.prenom_client}</td>
                <td className="px-2 py-1.5 align-top">{t.cp}</td>
                <td className="px-2 py-1.5 align-top">{t.ville}</td>
                <td className="px-2 py-1.5 text-right tabular-nums align-top">
                  {t.delai_av_prise_charge_min.toFixed(1)}
                </td>
                <td className="px-2 py-1.5 text-right tabular-nums align-top">
                  {t.duree_appel_min > 0 ? t.duree_appel_min.toFixed(1) : ''}
                </td>
                <td className="px-2 py-1.5 text-center align-top">
                  {t.parcours_chaines ? '✓' : ''}
                </td>
                <td className="px-2 py-1.5 align-top">{t.lib_statut}</td>
              </tr>
            )})}
          </tbody>
        </table>
      </div>
    </div>
  )
}


// =================== Onglet 4 : Analyse des ventes ==============
function OngletVentes({ ventes }: { ventes: AnalyseVentes }) {
  const maxVal = Math.max(1,
    ...ventes.par_delai.map(d => Math.max(d.ventes_valides, d.ventes_annulees)))

  return (
    <div className="p-4 h-full flex flex-col">
      <div className="flex items-center gap-6 mb-4 text-sm">
        <span><b>Pas encore statuées :</b> <span className="text-c-ink-faint">{ventes.pas_encore_statuees}</span></span>
        <span><b>Ventes validées :</b> <span className="text-c-brand">{ventes.ventes_validees}</span></span>
        <span><b>Ventes annulées :</b> <span className="text-red-600">{ventes.ventes_annulees}</span></span>
      </div>

      <h3 className="text-sm font-semibold text-center mb-3">
        Ventes par délai de prise en charge
      </h3>

      {/* Graphique SVG en barres */}
      <div className="flex-1 flex justify-center items-center">
        <svg viewBox="0 0 600 380" className="w-full max-w-3xl">
          {/* Axe Y */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
            const v = Math.round(maxVal * pct)
            const y = 320 - 280 * pct
            return (
              <g key={pct}>
                <line x1={50} y1={y} x2={580} y2={y} stroke="#e5e7eb" strokeDasharray="3 3" />
                <text x={45} y={y + 4} fontSize={10} fill="#9ca3af" textAnchor="end">{v}</text>
              </g>
            )
          })}

          {ventes.par_delai.map((d, i) => {
            const groupX = 80 + i * 130
            const hVal = (d.ventes_valides / maxVal) * 280
            const hAnn = (d.ventes_annulees / maxVal) * 280
            return (
              <g key={d.delai}>
                {/* Barre validees */}
                <rect x={groupX} y={320 - hVal} width={45} height={hVal}
                  rx={5} fill="#86efac" />
                <text x={groupX + 22} y={320 - hVal - 6} fontSize={11}
                  textAnchor="middle" fill="#16a34a" fontWeight="600">
                  {d.ventes_valides}
                </text>
                {/* Barre annulees */}
                <rect x={groupX + 55} y={320 - hAnn} width={45} height={hAnn}
                  rx={5} fill="#fca5a5" />
                <text x={groupX + 77} y={320 - hAnn - 6} fontSize={11}
                  textAnchor="middle" fill="#dc2626" fontWeight="600">
                  {d.ventes_annulees}
                </text>
                {/* Label X */}
                <text x={groupX + 48} y={340} fontSize={11}
                  textAnchor="middle" fill="#4b5563">
                  {d.delai}
                </text>
              </g>
            )
          })}

          {/* Legende */}
          <g transform="translate(220, 360)">
            <rect x={0} y={0} width={14} height={10} fill="#86efac" rx={2} />
            <text x={20} y={9} fontSize={11} fill="#4b5563">Ventes validées</text>
            <rect x={130} y={0} width={14} height={10} fill="#fca5a5" rx={2} />
            <text x={150} y={9} fontSize={11} fill="#4b5563">Ventes annulées</text>
          </g>
        </svg>
      </div>
    </div>
  )
}
