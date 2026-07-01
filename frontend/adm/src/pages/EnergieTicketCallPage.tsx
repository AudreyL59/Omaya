/**
 * Fen_TicketCall Énergie - Suivi Énergie > Ticket CALL.
 *
 * Similaire a SfrTicketCallPage mais pour Energie (partenaires
 * multiples : OEN, ENI, VAL, STR, PRO...).
 *
 * 3 onglets :
 *   - Liste     : tableau des tickets Call Energie
 *   - Planning  : calendrier visuel jour x ressources
 *   - Analyse ventes : bar chart par tranche de delai
 *
 * Le modal 'Voir le ticket' + bouton 'Convertir la selection'
 * arrivent en commits suivants.
 */
import { useState } from 'react'
import {
  Search, Loader2, ArrowLeft, PhoneCall, FileText, FileDown, CalendarClock,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  useTableSortFilter, SortableTh, FilterInput,
} from '@shared/production/_tableHelpers'
import TicketCallPlanning from '@/components/sfr/TicketCallPlanning'
import TicketCallEnergieContenuModal from '@/components/energie/TicketCallEnergieContenuModal'

const API_BASE = '/api/adm'

interface Ticket {
  id_tk_liste: string; id_tk_call: string; id_salarie: number
  date_crea: string; date_h_appel: string
  date_deb_prise_en_charge: string; date_fin_prise_en_charge: string
  lib_statut: string
  nom_client: string; prenom_client: string
  cp: string; ville: string
  adr_mail: string; mobile1: string
  ref_appel: string; ope_appel: number; nom_operateur: string
  nb_ctt: number; liste_num_ctt: string; num_cm: string
  delai_prise_charge_min: number; duree_appel_sec: number
  partenaires: string[]
  row_color_alert: boolean
}
interface AnalyseVentesTranche {
  delai: string; ventes_validees: number; ventes_annulees: number
}
interface AnalyseVentesTotaux {
  tranches: AnalyseVentesTranche[]
  nb_ventes_validees: number
  nb_ventes_annulees: number
  nb_ventes_pas_statuees: number
}
interface PlanningRdv {
  id_tk_call: string; id_tk_liste: string; id_salarie: number
  titre: string; contenu: string; ressource: string
  date_debut: string; date_fin: string
  couleur_hex: string; nb_valide: number
}

type Onglet = 'liste' | 'planning' | 'ventes'

const todayIso = (): string => new Date().toISOString().slice(0, 10)
const fmtDuree = (sec: number): string => {
  if (!sec) return ''
  const m = Math.floor(sec / 60); const s = Math.floor(sec % 60)
  return `${m}m ${s.toString().padStart(2, '0')}s`
}

export default function EnergieTicketCallPage() {
  useDocumentTitle('Ticket CALL Énergie')
  const [du, setDu] = useState(todayIso())
  const [au, setAu] = useState(todayIso())
  const [etat, setEtat] = useState<'ouverts' | 'clotures' | 'tous'>('tous')
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [ventes, setVentes] = useState<AnalyseVentesTotaux | null>(null)
  const [planning, setPlanning] = useState<PlanningRdv[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [onglet, setOnglet] = useState<Onglet>('liste')
  const [contenuTicketId, setContenuTicketId] = useState<string>('')

  const rechercher = async () => {
    if (du > au) { showToast('Dates incohérentes', 'error'); return }
    setLoading(true); setSelected(new Set())
    try {
      const q = `du=${du}&au=${au}&etat=${etat}`
      const [t, v, p] = await Promise.all([
        fetch(`${API_BASE}/suivi-energie/ticket-call?${q}`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        }).then(r => r.ok ? r.json() : []),
        fetch(`${API_BASE}/suivi-energie/ticket-call/analyse-ventes?${q}`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        }).then(r => r.ok ? r.json() : null),
        fetch(`${API_BASE}/suivi-energie/ticket-call/planning?${q}`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        }).then(r => r.ok ? r.json() : []),
      ])
      setTickets(t); setVentes(v); setPlanning(p)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }

  const toggleAll = () => {
    if (tickets.every(t => selected.has(t.id_tk_call))) {
      const s = new Set(selected); for (const t of tickets) s.delete(t.id_tk_call); setSelected(s)
    } else setSelected(new Set(tickets.map(t => t.id_tk_call)))
  }
  const toggle = (id: string) => {
    const s = new Set(selected); if (s.has(id)) s.delete(id); else s.add(id); setSelected(s)
  }

  const rdvs = planning.map(p => ({
    titre: p.titre, contenu: p.contenu,
    date_debut: p.date_debut, date_fin: p.date_fin,
    ressource: p.ressource, couleur: p.couleur_hex,
    delai_label: '', delai_min: 0,
    nb_valide: p.nb_valide,
  }))

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-110px)] text-c-ink">
      <div className="flex items-center gap-2 mb-3">
        <Link to=".." relative="path"
          className="p-1.5 hover:bg-c-surface-soft rounded text-c-ink-faint-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-lg font-bold flex items-center gap-2">
          <PhoneCall className="w-4 h-4 text-c-brand" /> Ticket CALL Énergie
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
      </div>

      {/* Onglets */}
      <div className="flex gap-1 border-b border-c-line mb-3">
        {(['liste', 'planning', 'ventes'] as const).map(t => (
          <button key={t} type="button" onClick={() => setOnglet(t)}
            className={`px-4 py-1.5 text-sm font-medium rounded-t flex items-center gap-1.5 ${
              onglet === t
                ? 'bg-white border border-c-line border-b-white text-c-brand'
                : 'text-c-ink-faint hover:bg-c-surface-soft'
            }`}>
            {t === 'liste' && <><FileText className="w-3.5 h-3.5" /> Liste</>}
            {t === 'planning' && <><CalendarClock className="w-3.5 h-3.5" /> Planning visuel</>}
            {t === 'ventes' && <><FileDown className="w-3.5 h-3.5" /> Analyse ventes</>}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-hidden">
        {onglet === 'liste' && (
          <OngletListe tickets={tickets} selected={selected}
            toggle={toggle} toggleAll={toggleAll}
            onVoirTicket={(id) => setContenuTicketId(id)}
            onConvertir={async () => {
              const ids = tickets
                .filter(t => selected.has(t.id_tk_call))
                .map(t => parseInt(t.id_tk_liste, 10))
              if (ids.length === 0) return
              const ok = await showConfirm({
                title: 'Convertir la sélection en contrat',
                message: `Vous êtes sur le point de convertir ${ids.length} ticket(s) en contrat. Voulez-vous continuer ?`,
              })
              if (!ok) return
              try {
                const r = await fetch(
                  `${API_BASE}/suivi-energie/ticket-call/convert-selection-tickets`,
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
                const res: Array<{ nb_updates: number; nb_skipped: number; nb_erreurs: number }> = await r.json()
                const totals = res.reduce((acc, x) => ({
                  u: acc.u + x.nb_updates,
                  s: acc.s + x.nb_skipped,
                  e: acc.e + x.nb_erreurs,
                }), { u: 0, s: 0, e: 0 })
                showToast(`Conversion : ${totals.u} maj, ${totals.s} skip${totals.e ? `, ${totals.e} erreur(s)` : ''}`, 'success')
                await rechercher()
              } catch (e) {
                showToast(`Erreur : ${(e as Error).message}`, 'error')
              }
            }}
            onClore={async () => {
              const ids = tickets
                .filter(t => selected.has(t.id_tk_call))
                .map(t => parseInt(t.id_tk_liste, 10))
              if (ids.length === 0) return
              const ok = await showConfirm({
                title: 'Clôturer sans convertir',
                message: `Vous êtes sur le point de clôturer ${ids.length} ticket(s) SANS convertir en contrat. Continuer ?`,
              })
              if (!ok) return
              try {
                const r = await fetch(
                  `${API_BASE}/suivi-energie/ticket-call/cloture-selection-tickets`,
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
        {onglet === 'planning' && (
          <TicketCallPlanning rdvs={rdvs} initialDate={du} />
        )}
        {onglet === 'ventes' && (
          <OngletVentes ventes={ventes} />
        )}
      </div>

      {contenuTicketId && (
        <TicketCallEnergieContenuModal idTkListe={contenuTicketId}
          onClose={() => setContenuTicketId('')}
          onChanged={() => { void rechercher() }} />
      )}
    </div>
  )
}

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
      r.nom_client, r.prenom_client, r.num_cm, r.nom_operateur,
      r.liste_num_ctt, r.ref_appel, r.lib_statut, r.ville, r.cp,
    ].join(' '),
  )
  const visible = tsf.rows as unknown as Ticket[]

  return (
    <div className="bg-white rounded-xl border border-c-line overflow-hidden flex flex-col h-full">
      <div className="flex items-center gap-3 px-3 py-2 border-b border-c-line-soft text-xs">
        <span className="text-c-ink-faint">
          {visible.length} / {tickets.length} ticket(s) | {selected.size} sélectionné(s)
        </span>
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
        <div className="flex-1" />
        <FilterInput value={tsf.filter} onChange={tsf.setFilter}
          placeholder="Filtrer…" />
      </div>
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs">
          <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0 z-10">
            <tr>
              <th className="px-2 py-2 text-center w-8">
                <input type="checkbox"
                  checked={visible.length > 0 && visible.every(r => selected.has(r.id_tk_call))}
                  onChange={toggleAll} />
              </th>
              <SortableTh label="NB Ctt" sortKey="nb_ctt" sort={tsf.sort} onSort={tsf.toggleSort} align="center" />
              <SortableTh label="Num CM" sortKey="num_cm" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Contenu Panier" sortKey="liste_num_ctt" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Fiche créée le" sortKey="date_crea" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Vendeur" sortKey="id_salarie" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Opérateur" sortKey="nom_operateur" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Nom Client" sortKey="nom_client" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Prénom" sortKey="prenom_client" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="CP" sortKey="cp" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Ville" sortKey="ville" sort={tsf.sort} onSort={tsf.toggleSort} />
              <SortableTh label="Délai (min)" sortKey="delai_prise_charge_min" sort={tsf.sort} onSort={tsf.toggleSort} align="right" />
              <SortableTh label="Durée appel" sortKey="duree_appel_sec" sort={tsf.sort} onSort={tsf.toggleSort} align="right" />
              <SortableTh label="Statut" sortKey="lib_statut" sort={tsf.sort} onSort={tsf.toggleSort} />
            </tr>
          </thead>
          <tbody className="divide-y divide-c-line-soft">
            {visible.length === 0 ? (
              <tr>
                <td colSpan={14} className="text-center py-12 text-c-ink-faint-2 italic">
                  {tickets.length === 0
                    ? 'Choisis filtres puis Rechercher.'
                    : 'Aucun résultat avec ce filtre.'}
                </td>
              </tr>
            ) : visible.map(r => {
              const isSel = selected.has(r.id_tk_call)
              return (
                <tr key={r.id_tk_call}
                  onClick={() => toggle(r.id_tk_call)}
                  onDoubleClick={() => onVoirTicket(r.id_tk_liste)}
                  className={`cursor-pointer ${
                    r.row_color_alert ? 'bg-red-50 hover:bg-red-100'
                                       : isSel ? 'bg-c-brand/10' : 'hover:bg-c-surface-soft'
                  }`}>
                  <td className="px-2 py-1.5 text-center">
                    <input type="checkbox" checked={isSel}
                      onChange={() => toggle(r.id_tk_call)}
                      onClick={(e) => e.stopPropagation()} />
                  </td>
                  <td className="px-2 py-1.5 text-center tabular-nums">{r.nb_ctt}</td>
                  <td className="px-2 py-1.5 tabular-nums">{r.num_cm}</td>
                  <td className="px-2 py-1.5 whitespace-pre-line text-[10px]">
                    {r.liste_num_ctt}
                  </td>
                  <td className="px-2 py-1.5">{r.date_crea?.slice(0, 16).replace('T', ' ')}</td>
                  <td className="px-2 py-1.5 tabular-nums">{r.id_salarie || ''}</td>
                  <td className="px-2 py-1.5">{r.nom_operateur}</td>
                  <td className="px-2 py-1.5">{r.nom_client}</td>
                  <td className="px-2 py-1.5">{r.prenom_client}</td>
                  <td className="px-2 py-1.5 tabular-nums">{r.cp}</td>
                  <td className="px-2 py-1.5">{r.ville}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">
                    {r.delai_prise_charge_min.toFixed(1)}
                  </td>
                  <td className="px-2 py-1.5 text-right tabular-nums">
                    {fmtDuree(r.duree_appel_sec)}
                  </td>
                  <td className="px-2 py-1.5">{r.lib_statut}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function OngletVentes({ ventes }: { ventes: AnalyseVentesTotaux | null }) {
  if (!ventes || ventes.tranches.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-c-line p-12 text-center text-sm text-c-ink-faint italic">
        Aucune donnée — lance une recherche.
      </div>
    )
  }
  const maxVal = Math.max(
    ...ventes.tranches.flatMap(t => [t.ventes_validees, t.ventes_annulees]),
    1,
  )
  const BAR_H = 260
  const BAR_W = 70
  const GAP = 10

  return (
    <div className="bg-white rounded-xl border border-c-line overflow-hidden h-full flex flex-col">
      <div className="px-4 py-3 border-b border-c-line-soft flex items-center gap-6 text-sm">
        <div>
          <span className="text-c-ink-faint text-xs">Validées : </span>
          <span className="font-bold text-green-700 tabular-nums">{ventes.nb_ventes_validees}</span>
        </div>
        <div>
          <span className="text-c-ink-faint text-xs">Annulées : </span>
          <span className="font-bold text-red-700 tabular-nums">{ventes.nb_ventes_annulees}</span>
        </div>
        <div>
          <span className="text-c-ink-faint text-xs">Pas statuées : </span>
          <span className="font-bold text-c-ink-faint-2 tabular-nums">{ventes.nb_ventes_pas_statuees}</span>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-6">
        <svg width={ventes.tranches.length * (BAR_W * 2 + GAP * 3)} height={BAR_H + 60}>
          {ventes.tranches.map((t, i) => {
            const x = i * (BAR_W * 2 + GAP * 3) + GAP
            const hv = (t.ventes_validees / maxVal) * BAR_H
            const ha = (t.ventes_annulees / maxVal) * BAR_H
            return (
              <g key={t.delai}>
                <rect x={x} y={BAR_H - hv} width={BAR_W} height={hv} fill="#4ade80" />
                <text x={x + BAR_W / 2} y={BAR_H - hv - 4}
                  textAnchor="middle" className="text-xs fill-c-ink font-bold">
                  {t.ventes_validees}
                </text>
                <rect x={x + BAR_W + GAP} y={BAR_H - ha} width={BAR_W} height={ha} fill="#f87171" />
                <text x={x + BAR_W + GAP + BAR_W / 2} y={BAR_H - ha - 4}
                  textAnchor="middle" className="text-xs fill-c-ink font-bold">
                  {t.ventes_annulees}
                </text>
                <text x={x + BAR_W + GAP / 2} y={BAR_H + 20}
                  textAnchor="middle" className="text-xs fill-c-ink-faint">
                  {t.delai}
                </text>
              </g>
            )
          })}
        </svg>
        <div className="mt-4 flex gap-4 text-xs">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 bg-[#4ade80]" /> Validées
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 bg-[#f87171]" /> Annulées
          </span>
        </div>
      </div>
    </div>
  )
}
