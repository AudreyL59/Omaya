import { useEffect, useMemo, useState } from 'react'
import {
  Banknote,
  Building2,
  Calendar,
  Car,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  Coins,
  CreditCard,
  FilePen,
  FileSignature,
  FileText,
  HeartHandshake,
  IdCard,
  Loader2,
  Package,
  PhoneCall,
  Plane,
  Receipt,
  Scale,
  Search,
  ShoppingCart,
  Ticket,
  UserMinus,
  UserPlus,
  Wrench,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import type {
  TicketListResponse,
  TicketRow,
  TicketSidebarItem,
  TicketTypeDemande,
} from './types'

// Mapping IDTK_TypeDemande → icône lucide. Les valeurs viennent du switch
// WinDev DonneInfoTicket / des libellés vus dans le screenshot.
const TICKET_ICON_BY_ID: Record<string, LucideIcon> = {
  '1':  Package,           // Commande Fourniture
  '2':  IdCard,            // Carte PRO
  '3':  UserPlus,          // DPAE
  '4':  FileSignature,     // Contrat W - Signature
  '9':  Plane,             // Réservation
  '10': Coins,             // Avance
  '11': PhoneCall,         // SOS BO
  '12': UserMinus,         // Sorties RH
  '13': Calendar,          // Congés
  '14': Car,               // Relève Kilométrique
  '15': Car,               // Mise à dispo / Restitution Véhicule
  '17': Scale,             // SOS Pôle JURI
  '18': PhoneCall,         // SOS Info
  '19': Wrench,            // Retour RDV Tech
  '20': PhoneCall,         // Call SFR
  '21': UserPlus,          // DPAE à venir
  '22': PhoneCall,         // Call energie
  '23': FileText,          // Contrat de courtage
  '24': ShoppingCart,      // Commande ExoCash
  '25': Banknote,          // Attribution ExoCash
  '26': PhoneCall,         // Call SFR RET RDV Tech
  '27': HeartHandshake,    // Mutuelle
  '28': Receipt,           // Facturation Distrib
  '29': UserPlus,          // DPAE Distributeur
  '30': Building2,         // Intégration Distributeur
  '31': FileText,          // Demande Doc Distributeur
  '33': Receipt,           // Demande facturation
  '35': Car,               // PV Liv/Rest Ulease
  '36': UserMinus,         // Sorties FPE
  '37': UserMinus,         // Sorties Licenciement
  '38': CreditCard,        // Demande code Vendeur
  '39': CreditCard,        // Désactivation code Vendeur
  '40': FilePen,           // Contrat W - Demande
}

function TicketTypeIcon({ idType }: { idType: string }) {
  const Icon = TICKET_ICON_BY_ID[idType] || ClipboardList
  // text-c-brand = vert charter en ADM, emerald en Vendeur
  return <Icon className="w-5 h-5 shrink-0 text-c-brand" />
}

interface TicketsPageProps {
  apiBase: string                 // ex: '/api/vendeur' ou '/api/adm'
  getToken: () => string
}

function shortDateTime(raw: string | undefined | null): string {
  if (!raw) return ''
  const m = String(raw).match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/)
  if (!m) return raw || ''
  return `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}`
}

function capitalize(s: string): string {
  if (!s) return ''
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase()
}

export default function TicketsPage({ apiBase, getToken }: TicketsPageProps) {
  const [sidebar, setSidebar] = useState<TicketSidebarItem[]>([])
  const [loadingSidebar, setLoadingSidebar] = useState(true)
  const [selectedType, setSelectedType] = useState<TicketTypeDemande | null>(null)
  const [data, setData] = useState<TicketListResponse | null>(null)
  const [loadingList, setLoadingList] = useState(false)
  const [openServices, setOpenServices] = useState<Set<string>>(new Set())
  const [selected, setSelected] = useState<Set<string>>(new Set())
  // Filtres popup (déclenchée par la loupe)
  const [showFiltersPopup, setShowFiltersPopup] = useState(false)
  const [filterCloturee, setFilterCloturee] = useState(false)
  const [filterDateDu, setFilterDateDu] = useState('')   // YYYY-MM-DD ou ''
  const [filterDateAu, setFilterDateAu] = useState('')   // YYYY-MM-DD ou ''

  // Charge la sidebar (services + types accessibles)
  useEffect(() => {
    setLoadingSidebar(true)
    fetch(`${apiBase}/tickets/sidebar`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: TicketSidebarItem[]) => {
        setSidebar(Array.isArray(d) ? d : [])
        // Premier service ouvert par défaut
        if (Array.isArray(d) && d.length > 0) {
          setOpenServices(new Set([d[0].service]))
        }
      })
      .catch(() => setSidebar([]))
      .finally(() => setLoadingSidebar(false))
  }, [apiBase])

  // Charge les tickets quand le type sélectionné OU les filtres changent.
  useEffect(() => {
    if (!selectedType) return
    setLoadingList(true)
    setSelected(new Set())
    const params = new URLSearchParams({ id_type_demande: selectedType.id_type_demande })
    if (filterCloturee) params.set('cloturee', '1')
    if (filterDateDu) params.set('date_du', filterDateDu.replace(/-/g, ''))
    if (filterDateAu) params.set('date_au', filterDateAu.replace(/-/g, ''))
    fetch(`${apiBase}/tickets?${params}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: TicketListResponse) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoadingList(false))
  }, [apiBase, selectedType, filterCloturee, filterDateDu, filterDateAu])

  const toggleService = (svc: string) => {
    setOpenServices((prev) => {
      const next = new Set(prev)
      if (next.has(svc)) next.delete(svc)
      else next.add(svc)
      return next
    })
  }

  // Groupage par statut (les rows sont déjà filtrées côté backend)
  const groupedByStatut = useMemo(() => {
    if (!data) return new Map<number, TicketRow[]>()
    const map = new Map<number, TicketRow[]>()
    for (const r of data.rows) {
      if (!map.has(r.id_statut)) map.set(r.id_statut, [])
      map.get(r.id_statut)!.push(r)
    }
    return map
  }, [data])

  const toggleRow = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="flex h-[calc(100vh-100px)] gap-4 p-4">
      {/* Sidebar — style WinDev : services en bandes pleines, types en lignes blanches */}
      <aside className="w-64 shrink-0 bg-transparent overflow-y-auto flex flex-col">
        {/* En-tête "Tickets" avec icône */}
        <div className="px-4 py-3 flex items-center gap-2">
          <Ticket className="w-5 h-5 text-c-brand" />
          <span className="text-base font-semibold text-c-brand">Tickets</span>
        </div>
        {/* Sous-titre "Demande" */}
        <div className="px-4 py-2 text-xs font-medium text-c-ink-soft uppercase tracking-wide">
          Demande
        </div>

        {loadingSidebar ? (
          <div className="p-4 flex justify-center">
            <Loader2 className="w-4 h-4 text-c-ink-icon animate-spin" />
          </div>
        ) : sidebar.length === 0 ? (
          <div className="p-4 text-xs text-c-ink-faint">Aucun type accessible.</div>
        ) : (
          <nav className="flex-1">
            {sidebar.map((svc) => {
              const isOpen = openServices.has(svc.service)
              return (
                <div key={svc.service} className="px-2 mb-1">
                  {/* Bande Service en couleur pleine, arrondi 10px */}
                  <button
                    onClick={() => toggleService(svc.service)}
                    className="w-full flex items-center gap-2 px-3 py-2.5 bg-c-brand text-white text-sm font-semibold rounded-[10px] hover:brightness-110 transition-all"
                  >
                    {isOpen
                      ? <ChevronDown className="w-4 h-4" />
                      : <ChevronRight className="w-4 h-4" />}
                    {svc.service}
                  </button>
                  {/* Liste des types (rendu uniquement si ouvert) */}
                  {isOpen && (
                    <ul>
                      {svc.types.map((t) => {
                        const active = selectedType?.id_type_demande === t.id_type_demande
                        return (
                          <li key={t.id_type_demande}>
                            <button
                              onClick={() => setSelectedType(t)}
                              className={`w-full text-left px-4 py-2 text-sm flex items-center gap-3 transition-colors text-c-ink ${
                                active
                                  ? 'bg-c-brand-soft rounded-[10px]'
                                  : 'hover:bg-c-surface-soft hover:rounded-[10px]'
                              }`}
                            >
                              {t.icone_data_url ? (
                                <img src={t.icone_data_url} alt="" className="w-5 h-5 shrink-0" />
                              ) : (
                                <TicketTypeIcon idType={t.id_type_demande} />
                              )}
                              <span className="truncate font-normal">{t.lib_type_demande}</span>
                            </button>
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </div>
              )
            })}
          </nav>
        )}
      </aside>

      {/* Main — pas d'overflow-hidden ici (sinon clipping de la popup filtres) */}
      <main className="flex-1 min-w-0 flex flex-col bg-white border border-c-line rounded-xl">
        {/* Toolbar */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-c-line bg-c-surface-soft relative">
          <h1 className="text-base font-semibold text-c-ink">
            {selectedType ? selectedType.lib_type_demande : 'Sélectionne un type'}
          </h1>
          <button
            onClick={() => setShowFiltersPopup((v) => !v)}
            className={`p-2 rounded-lg transition-colors ${
              filterCloturee || filterDateDu || filterDateAu
                ? 'bg-c-brand-soft text-c-brand-strong'
                : 'text-c-ink-faint hover:bg-c-surface-medium'
            }`}
            title="Filtres"
          >
            <Search className="w-4 h-4" />
          </button>
          {showFiltersPopup && (
            <FiltersPopup
              cloturee={filterCloturee}
              dateDu={filterDateDu}
              dateAu={filterDateAu}
              onChangeCloturee={setFilterCloturee}
              onChangeDateDu={setFilterDateDu}
              onChangeDateAu={setFilterDateAu}
              onClose={() => setShowFiltersPopup(false)}
            />
          )}
        </header>

        {/* Table */}
        <div className="flex-1 overflow-auto">
          {!selectedType ? (
            <div className="h-full flex items-center justify-center text-c-ink-faint text-sm">
              Choisis un type de demande dans la sidebar.
            </div>
          ) : loadingList ? (
            <div className="p-12 flex justify-center">
              <Loader2 className="w-5 h-5 text-c-ink-icon animate-spin" />
            </div>
          ) : !data || data.rows.length === 0 ? (
            <div className="p-12 text-center text-c-ink-faint-2 text-sm">Aucun ticket.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-c-surface-soft text-xs text-c-ink-faint uppercase tracking-wide">
                <tr>
                  <th className="px-3 py-2.5 text-center w-10">
                    <input type="checkbox" disabled className="w-4 h-4 opacity-40" />
                  </th>
                  <th className="px-3 py-2.5 text-left w-44">Date Créa</th>
                  <th className="px-3 py-2.5 text-left">Opérateur</th>
                  <th className="px-3 py-2.5 text-left">Info</th>
                  <th className="px-3 py-2.5 text-left">Opé Staff</th>
                </tr>
              </thead>
              <tbody>
                {data.statuts.map((statut) => {
                  const rows = groupedByStatut.get(statut.id_statut) || []
                  if (rows.length === 0) return null
                  return (
                    <RowGroup
                      key={statut.id_statut}
                      label={statut.lib_statut}
                      count={rows.length}
                      rows={rows}
                      selected={selected}
                      onToggle={toggleRow}
                    />
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        {data && data.rows.length > 0 && (
          <footer className="px-4 py-2 border-t border-c-line bg-c-surface-soft text-xs text-c-ink-faint flex items-center justify-between">
            <span>{data.total} ticket{data.total > 1 ? 's' : ''}</span>
            {selected.size > 0 && (
              <span className="text-c-ink-soft">{selected.size} sélectionné{selected.size > 1 ? 's' : ''}</span>
            )}
          </footer>
        )}
      </main>
    </div>
  )
}

function FiltersPopup({
  cloturee, dateDu, dateAu,
  onChangeCloturee, onChangeDateDu, onChangeDateAu, onClose,
}: {
  cloturee: boolean
  dateDu: string
  dateAu: string
  onChangeCloturee: (v: boolean) => void
  onChangeDateDu: (v: string) => void
  onChangeDateAu: (v: string) => void
  onClose: () => void
}) {
  return (
    <>
      <div
        className="fixed inset-0 z-30"
        onClick={onClose}
      />
      <div className="absolute right-3 top-full mt-2 z-40 bg-white rounded-xl border border-c-line shadow-lg p-4 w-72">
        <div className="flex items-center gap-2 text-sm font-semibold text-c-ink mb-3">
          <Search className="w-4 h-4 text-c-brand" />
          Affichage Façon Trello
        </div>
        <label className="flex items-center gap-2 text-sm text-c-ink mb-3 cursor-pointer">
          <input
            type="checkbox"
            checked={cloturee}
            onChange={(e) => onChangeCloturee(e.target.checked)}
            className="w-4 h-4 cursor-pointer accent-c-brand"
          />
          Afficher les tickets clôturés
        </label>
        <div className="text-xs text-c-ink-soft mb-1">Créés entre le</div>
        <input
          type="date"
          value={dateDu}
          onChange={(e) => onChangeDateDu(e.target.value)}
          className="w-full px-2 py-1 mb-2 border border-c-line-strong rounded-md text-xs focus:outline-none focus:ring-1 focus:ring-c-brand-line"
        />
        <div className="text-xs text-c-ink-soft mb-1">et le</div>
        <input
          type="date"
          value={dateAu}
          onChange={(e) => onChangeDateAu(e.target.value)}
          className="w-full px-2 py-1 border border-c-line-strong rounded-md text-xs focus:outline-none focus:ring-1 focus:ring-c-brand-line"
        />
        {(dateDu || dateAu || cloturee) && (
          <button
            onClick={() => {
              onChangeCloturee(false)
              onChangeDateDu('')
              onChangeDateAu('')
            }}
            className="mt-3 text-xs text-c-ink-faint hover:text-c-ink underline"
          >Réinitialiser</button>
        )}
      </div>
    </>
  )
}


function RowGroup({
  label, count, rows, selected, onToggle,
}: {
  label: string
  count: number
  rows: TicketRow[]
  selected: Set<string>
  onToggle: (id: string) => void
}) {
  return (
    <>
      <tr className="bg-c-surface-medium text-c-ink-soft text-xs">
        <td colSpan={5} className="px-4 py-1.5 font-semibold sticky left-0">
          {label}
          <span className="ml-2 text-c-ink-faint font-normal">{count}</span>
        </td>
      </tr>
      {rows.map((r) => {
        const isSelected = selected.has(r.id_ticket)
        return (
          <tr
            key={r.id_ticket}
            className={`border-t border-c-line-soft hover:bg-c-surface-soft ${
              isSelected ? 'bg-c-surface-medium' : ''
            }`}
          >
            <td className="px-3 py-2 text-center">
              <input
                type="checkbox"
                className="w-4 h-4 cursor-pointer accent-c-brand"
                checked={isSelected}
                onChange={() => onToggle(r.id_ticket)}
              />
            </td>
            <td className="px-3 py-2 tabular-nums text-c-ink-soft whitespace-nowrap">
              {shortDateTime(r.date_crea)}
            </td>
            <td className="px-3 py-2 text-c-ink whitespace-nowrap">
              {r.op_dest_nom} {capitalize(r.op_dest_prenom)}
            </td>
            <td className="px-3 py-2 text-c-ink-soft">{r.info}</td>
            <td className="px-3 py-2 text-c-ink whitespace-nowrap">
              {r.op_staff_nom
                ? `${capitalize(r.op_staff_prenom)} ${r.op_staff_nom.charAt(0).toUpperCase()}`
                : ''}
            </td>
          </tr>
        )
      })}
    </>
  )
}
