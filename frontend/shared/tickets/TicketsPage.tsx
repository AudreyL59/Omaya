import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Banknote,
  Building2,
  Calendar,
  Car,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  Coins,
  CreditCard,
  FilePen,
  FileSignature,
  FileText,
  HeartHandshake,
  History,
  IdCard,
  Loader2,
  Package,
  PhoneCall,
  Plane,
  Receipt,
  Save,
  Scale,
  Search,
  ShoppingCart,
  Ticket,
  Trash2,
  UserMinus,
  UserPlus,
  Wrench,
  X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { FI_COMPONENTS } from './forms'
import type {
  SalarieItem,
  TicketDetail,
  TicketListResponse,
  TicketRow,
  TicketSidebarItem,
  TicketStatut,
  TicketStreamPayload,
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
  getToken: () => string | null
}

function shortDateTime(raw: string | undefined | null): string {
  if (!raw) return ''
  const m = String(raw).match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/)
  if (!m) return raw || ''
  return `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}`
}

function shortDate(raw: string | undefined | null): string {
  if (!raw) return ''
  const m = String(raw).match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return raw || ''
  return `${m[3]}/${m[2]}/${m[1]}`
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
  // Action "Statuer la sélection"
  const [allStatuts, setAllStatuts] = useState<TicketStatut[]>([])
  const [showStatuerPopup, setShowStatuerPopup] = useState(false)
  const [reloadNonce, setReloadNonce] = useState(0)
  // Fen_TicketContenu (clic sur une ligne)
  const [detail, setDetail] = useState<TicketDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  // Live update (SSE)
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set())
  const [modifiedIds, setModifiedIds] = useState<Set<string>>(new Set())
  const addedIdsRef = useRef<Set<string>>(new Set())
  const presentIdsRef = useRef<Set<string>>(new Set())
  const streamAbortRef = useRef<AbortController | null>(null)
  // Refs synchros avec le state (lectures synchrones dans handleSSEBlock).
  useEffect(() => { addedIdsRef.current = addedIds }, [addedIds])
  useEffect(() => {
    presentIdsRef.current = new Set(data?.rows.map((r) => r.id_ticket) || [])
  }, [data])

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

  // Charge la liste complète des statuts (pour le combo "Statuer")
  useEffect(() => {
    fetch(`${apiBase}/tickets/statuts`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: TicketStatut[]) => setAllStatuts(Array.isArray(d) ? d : []))
      .catch(() => setAllStatuts([]))
  }, [apiBase])

  const applyEvents = useCallback((evts: TicketStreamPayload['events']) => {
    if (!evts || evts.length === 0) return

    // Pré-calcul : on a besoin des IDs déjà présents AVANT le merge.
    setData((prev) => {
      if (!prev) return prev
      const rowMap = new Map(prev.rows.map((r) => [r.id_ticket, r] as const))
      const seenStatuts = new Set(prev.statuts.map((s) => s.id_statut))
      const newStatuts: typeof prev.statuts = [...prev.statuts]
      for (const e of evts) {
        rowMap.set(e.row.id_ticket, e.row)
        if (!seenStatuts.has(e.row.id_statut)) {
          seenStatuts.add(e.row.id_statut)
          newStatuts.push({ id_statut: e.row.id_statut, lib_statut: e.row.lib_statut })
        }
      }
      const allRows = Array.from(rowMap.values()).sort((a, b) => {
        if (a.id_statut !== b.id_statut) return a.id_statut - b.id_statut
        return a.date_crea < b.date_crea ? 1 : a.date_crea > b.date_crea ? -1 : 0
      })
      newStatuts.sort((a, b) => a.id_statut - b.id_statut)
      return { rows: allRows, statuts: newStatuts, total: allRows.length }
    })

    // Marqueurs : added si pas déjà présent dans la liste, sinon modified.
    // On lit les IDs présents via une ref synchro pour éviter une race
    // avec le setData ci-dessus.
    const presentIds = presentIdsRef.current
    const newAdded = new Set<string>()
    const newModified = new Set<string>()
    for (const e of evts) {
      const id = e.row.id_ticket
      if (!presentIds.has(id)) newAdded.add(id)
      else newModified.add(id)
    }
    if (newAdded.size > 0) {
      setAddedIds((prevSet) => {
        const next = new Set(prevSet)
        for (const id of newAdded) next.add(id)
        return next
      })
    }
    if (newModified.size > 0) {
      setModifiedIds((prevSet) => {
        const next = new Set(prevSet)
        for (const id of newModified) {
          // si déjà dans added (premier coup), garder added
          if (!addedIdsRef.current.has(id)) next.add(id)
        }
        return next
      })
    }
  }, [])

  // Long-polling : boucle de fetch JSON (le SSE est bufferisé par IIS/ARR).
  // Chaque requête attend jusqu'à ~25 s côté serveur qu'un ticket bouge,
  // puis le client reboucle immédiatement.
  const startTicketsStream = useCallback(
    async (
      signal: AbortSignal,
      idTypeDemande: string,
      cloturee: boolean,
      dateDu: string,
      dateAu: string,
    ) => {
      let cursor = ''
      const sleep = (ms: number) =>
        new Promise<void>((res) => setTimeout(res, ms))
      while (!signal.aborted) {
        const sp = new URLSearchParams({ id_type_demande: idTypeDemande })
        if (cloturee) sp.set('cloturee', '1')
        if (dateDu) sp.set('date_du', dateDu.replace(/-/g, ''))
        if (dateAu) sp.set('date_au', dateAu.replace(/-/g, ''))
        if (cursor) sp.set('cursor', cursor)
        try {
          const resp = await fetch(`${apiBase}/tickets/poll?${sp}`, {
            headers: { Authorization: `Bearer ${getToken()}` },
            signal,
          })
          if (!resp.ok) {
            // 401/403/500 : on attend un peu avant de réessayer
            await sleep(5000)
            continue
          }
          const payload = (await resp.json()) as TicketStreamPayload
          if (payload.cursor) cursor = payload.cursor
          applyEvents(payload.events)
        } catch (err: any) {
          if (err?.name === 'AbortError') return
          await sleep(5000)
        }
      }
    },
    [apiBase, getToken, applyEvents],
  )

  // Charge les tickets quand le type sélectionné OU les filtres changent.
  // Puis lance la boucle de long-polling pour les ajouts/modifs en live.
  useEffect(() => {
    if (!selectedType) return
    setLoadingList(true)
    setSelected(new Set())
    setAddedIds(new Set())
    setModifiedIds(new Set())
    streamAbortRef.current?.abort()
    const controller = new AbortController()
    streamAbortRef.current = controller

    const params = new URLSearchParams({ id_type_demande: selectedType.id_type_demande })
    if (filterCloturee) params.set('cloturee', '1')
    if (filterDateDu) params.set('date_du', filterDateDu.replace(/-/g, ''))
    if (filterDateAu) params.set('date_au', filterDateAu.replace(/-/g, ''))

    let cancelled = false
    fetch(`${apiBase}/tickets?${params}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
      signal: controller.signal,
    })
      .then((r) => r.json())
      .then((d: TicketListResponse) => {
        if (cancelled) return
        setData(d)
        startTicketsStream(
          controller.signal,
          selectedType.id_type_demande,
          filterCloturee,
          filterDateDu,
          filterDateAu,
        )
      })
      .catch((err) => {
        if (err?.name === 'AbortError') return
        setData(null)
      })
      .finally(() => {
        if (!cancelled) setLoadingList(false)
      })

    return () => {
      cancelled = true
      controller.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, selectedType, filterCloturee, filterDateDu, filterDateAu, reloadNonce])

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

  // Clic sur la ligne (zone hors checkbox) : retire les marqueurs vert/jaune.
  const clearRowMarkers = (id: string) => {
    let changed = false
    if (addedIds.has(id)) {
      setAddedIds((prev) => {
        const next = new Set(prev); next.delete(id); return next
      })
      changed = true
    }
    if (modifiedIds.has(id)) {
      setModifiedIds((prev) => {
        const next = new Set(prev); next.delete(id); return next
      })
      changed = true
    }
    return changed
  }

  // Action "Statuer la sélection" (cf. WinDev Fen_TicketChoixStatut)
  const doStatuer = async (idStatut: number | null, cloturee: boolean) => {
    const ids = Array.from(selected)
    if (ids.length === 0) return
    const libStatut = cloturee
      ? 'Clôturer'
      : allStatuts.find((s) => s.id_statut === idStatut)?.lib_statut || ''
    if (
      !window.confirm(
        `Vous êtes sur le point de statuer la sélection en « ${libStatut} ».\nVoulez-vous continuer ?`,
      )
    )
      return
    try {
      const resp = await fetch(`${apiBase}/tickets/statuer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_tickets: ids,
          id_statut: cloturee ? null : idStatut,
          cloturee,
        }),
      })
      if (!resp.ok) {
        const e = await resp.json().catch(() => null)
        window.alert(`Erreur : ${e?.detail || resp.status}`)
        return
      }
      setShowStatuerPopup(false)
      setSelected(new Set())
      setReloadNonce((n) => n + 1)
    } catch {
      window.alert('Erreur réseau lors du changement de statut.')
    }
  }

  // Action "Supprimer la sélection" (soft-delete, cf. WinDev)
  const doSupprimer = async () => {
    const ids = Array.from(selected)
    if (ids.length === 0) return
    if (
      !window.confirm(
        'Vous êtes sur le point de supprimer cette sélection de ticket.\nVoulez-vous continuer ?',
      )
    )
      return
    try {
      const resp = await fetch(`${apiBase}/tickets/supprimer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ id_tickets: ids }),
      })
      if (!resp.ok) {
        const e = await resp.json().catch(() => null)
        window.alert(`Erreur : ${e?.detail || resp.status}`)
        return
      }
      setSelected(new Set())
      setReloadNonce((n) => n + 1)
    } catch {
      window.alert('Erreur réseau lors de la suppression.')
    }
  }

  // Clic sur une ligne → ouvre Fen_TicketContenu (applique aussi la
  // règle WinDev statut<2 → 2 côté backend).
  const openTicket = async (idTicket: string) => {
    setLoadingDetail(true)
    setDetail(null)
    try {
      const resp = await fetch(`${apiBase}/tickets/${idTicket}/ouvrir`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!resp.ok) {
        const e = await resp.json().catch(() => null)
        window.alert(`Erreur : ${e?.detail || resp.status}`)
        return
      }
      const d = (await resp.json()) as TicketDetail
      setDetail(d)
      // Le passage statut→2 modifie la liste : on resynchronise.
      setReloadNonce((n) => n + 1)
    } catch {
      window.alert('Erreur réseau (ouverture du ticket).')
    } finally {
      setLoadingDetail(false)
    }
  }

  // Enregistrer les infos générales (saveTicket WinDev)
  const saveInfos = async (payload: {
    id_statut: number
    op_dest: string
    op_traitement_staff: string
    cloturee: boolean
    date_cloture: string
    prendre_en_charge?: boolean
  }) => {
    if (!detail) return
    try {
      const resp = await fetch(`${apiBase}/tickets/${detail.id_ticket}/infos`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(payload),
      })
      if (!resp.ok) {
        const e = await resp.json().catch(() => null)
        window.alert(`Erreur : ${e?.detail || resp.status}`)
        return
      }
      const res = await resp.json()
      setReloadNonce((n) => n + 1)
      if (res.closed) {
        setDetail(null) // clôturé → ferme la fenêtre (cf. WinDev Ferme())
      } else {
        // recharge le détail à jour (libellés, noms…)
        openTicket(detail.id_ticket)
      }
    } catch {
      window.alert('Erreur réseau lors de l’enregistrement.')
    }
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
                      addedIds={addedIds}
                      modifiedIds={modifiedIds}
                      onClearMarkers={clearRowMarkers}
                      onOpen={openTicket}
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
            <div className="flex items-center gap-3">
              {selected.size > 0 && (
                <span className="text-c-ink-soft">
                  {selected.size} sélectionné{selected.size > 1 ? 's' : ''}
                </span>
              )}
              <button
                onClick={doSupprimer}
                disabled={selected.size === 0}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Supprimer
              </button>
              <button
                onClick={() => setShowStatuerPopup(true)}
                disabled={selected.size === 0}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-c-brand text-white hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                Statuer
              </button>
            </div>
          </footer>
        )}

        {showStatuerPopup && (
          <StatuerPopup
            statuts={allStatuts}
            count={selected.size}
            onValidate={doStatuer}
            onClose={() => setShowStatuerPopup(false)}
          />
        )}

        {(detail || loadingDetail) && (
          <TicketContenuModal
            apiBase={apiBase}
            getToken={getToken}
            detail={detail}
            loading={loadingDetail}
            statuts={allStatuts}
            onSave={saveInfos}
            onClose={() => setDetail(null)}
          />
        )}
      </main>
    </div>
  )
}

function SalariePicker({
  apiBase, getToken, onPick, onClose,
}: {
  apiBase: string
  getToken: () => string | null
  onPick: (s: SalarieItem) => void
  onClose: () => void
}) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<SalarieItem[]>([])
  const [searching, setSearching] = useState(false)
  useEffect(() => {
    const term = q.trim()
    if (term.length < 1) {
      setResults([])
      return
    }
    setSearching(true)
    const t = setTimeout(() => {
      fetch(`${apiBase}/tickets/salaries/search?q=${encodeURIComponent(term)}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
        .then((r) => r.json())
        .then((d: SalarieItem[]) => setResults(Array.isArray(d) ? d : []))
        .catch(() => setResults([]))
        .finally(() => setSearching(false))
    }, 300)
    return () => clearTimeout(t)
  }, [q, apiBase])
  return (
    <>
      <div className="fixed inset-0 z-[60] bg-black/30" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-[70] bg-white rounded-2xl shadow-xl border border-c-line w-96 p-5">
        <div className="flex items-center gap-2 text-base font-semibold text-c-ink mb-3">
          <UserPlus className="w-5 h-5 text-c-brand" />
          Recherche un salarié
        </div>
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Nom (début)…"
          className="w-full px-3 py-2 mb-3 border border-c-line-strong rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-c-brand-line"
        />
        <div className="max-h-72 overflow-auto -mx-1">
          {searching ? (
            <div className="p-4 flex justify-center">
              <Loader2 className="w-4 h-4 text-c-ink-icon animate-spin" />
            </div>
          ) : results.length === 0 ? (
            <div className="p-4 text-xs text-c-ink-faint text-center">
              {q.trim() ? 'Aucun résultat.' : 'Saisis un début de nom.'}
            </div>
          ) : (
            <ul>
              {results.map((s) => {
                const meta = [s.poste, s.lib_societe].filter(Boolean).join(' · ')
                return (
                  <li key={s.id_salarie}>
                    <button
                      onClick={() => onPick(s)}
                      className="w-full text-left px-3 py-2 rounded-lg hover:bg-c-brand-soft transition-colors"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium text-c-ink">
                          {s.nom} {capitalize(s.prenom)}
                        </span>
                        <span
                          className={`text-[10px] font-semibold px-1.5 py-0.5 rounded shrink-0 ${
                            s.actif
                              ? 'bg-emerald-100 text-emerald-700'
                              : 'bg-red-100 text-red-700'
                          }`}
                        >
                          {s.actif ? 'En activité' : 'Hors effectifs'}
                        </span>
                      </div>
                      {meta && (
                        <div className="text-xs text-c-ink-soft truncate">{meta}</div>
                      )}
                      {s.date_embauche && (
                        <div className="text-[11px] text-c-ink-faint">
                          Emb. le {shortDate(s.date_embauche)}
                        </div>
                      )}
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>
    </>
  )
}

function TicketContenuModal({
  apiBase, getToken, detail, loading, statuts, onSave, onClose,
}: {
  apiBase: string
  getToken: () => string | null
  detail: TicketDetail | null
  loading: boolean
  statuts: TicketStatut[]
  onSave: (payload: {
    id_statut: number
    op_dest: string
    op_traitement_staff: string
    cloturee: boolean
    date_cloture: string
    prendre_en_charge?: boolean
  }) => void
  onClose: () => void
}) {
  const [statutId, setStatutId] = useState<number>(0)
  const [cloturee, setCloturee] = useState(false)
  const [dateCloture, setDateCloture] = useState('')
  const [opDest, setOpDest] = useState('')
  const [opDestLabel, setOpDestLabel] = useState('')
  const [opStaff, setOpStaff] = useState('')
  const [opStaffLabel, setOpStaffLabel] = useState('')
  const [picker, setPicker] = useState<'dest' | 'staff' | null>(null)

  // (Ré)initialise les champs quand le détail (re)charge
  useEffect(() => {
    if (!detail) return
    setStatutId(detail.id_statut)
    setCloturee(detail.cloturee)
    setDateCloture(detail.date_cloture ? detail.date_cloture.slice(0, 10) : '')
    setOpDest(detail.op_dest || '')
    setOpDestLabel(
      detail.op_dest_nom
        ? `${detail.op_dest_nom} ${capitalize(detail.op_dest_prenom)}`
        : '',
    )
    setOpStaff(detail.op_traitement_staff || '')
    setOpStaffLabel(
      detail.op_staff_nom
        ? `${detail.op_staff_nom} ${capitalize(detail.op_staff_prenom)}`
        : '',
    )
  }, [detail])

  const buildPayload = (over?: Partial<{ op_dest: string; op_traitement_staff: string }>) => ({
    id_statut: statutId,
    op_dest: over?.op_dest ?? opDest,
    op_traitement_staff: over?.op_traitement_staff ?? opStaff,
    cloturee,
    date_cloture: dateCloture,
  })

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/40" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 bg-white rounded-2xl shadow-2xl border border-c-line w-[1400px] max-w-[97vw] h-[88vh] flex flex-col overflow-hidden">
        <header className="flex items-center justify-between px-5 py-3 border-b border-c-line bg-c-surface-soft">
          <div className="flex items-center gap-2 text-base font-semibold text-c-ink">
            <Ticket className="w-5 h-5 text-c-brand" />
            {detail ? detail.lib_type_demande || 'Ticket' : 'Ticket'}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-c-ink-faint hover:bg-c-surface-medium transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </header>

        {loading || !detail ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-6 h-6 text-c-ink-icon animate-spin" />
          </div>
        ) : (
          <div className="flex-1 flex min-h-0">
            {/* Colonne gauche — Informations générales */}
            <div className="w-80 shrink-0 border-r border-c-line bg-c-surface-soft overflow-y-auto p-4 flex flex-col gap-3">
              <h3 className="text-sm font-semibold text-c-brand-strong">
                Informations générales
              </h3>

              <button
                onClick={() => setPicker('dest')}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong bg-white text-sm text-c-ink hover:bg-c-brand-soft transition-colors"
              >
                <UserPlus className="w-4 h-4 text-c-brand shrink-0" />
                <span className="truncate">
                  {opDestLabel || 'Choisir le destinataire'}
                </span>
              </button>

              <select
                value={statutId}
                onChange={(e) => setStatutId(Number(e.target.value))}
                className="w-full px-3 py-2 border border-c-line-strong rounded-lg text-sm bg-white focus:outline-none focus:ring-1 focus:ring-c-brand-line"
              >
                {statuts.map((s) => (
                  <option key={s.id_statut} value={s.id_statut}>
                    {s.lib_statut}
                  </option>
                ))}
              </select>

              <label className="flex items-center gap-2 text-sm text-c-ink cursor-pointer">
                <input
                  type="checkbox"
                  checked={cloturee}
                  onChange={(e) => setCloturee(e.target.checked)}
                  className="w-4 h-4 cursor-pointer accent-c-brand"
                />
                Clôturé le
                <input
                  type="date"
                  value={dateCloture}
                  onChange={(e) => setDateCloture(e.target.value)}
                  disabled={!cloturee}
                  className="flex-1 px-2 py-1 border border-c-line-strong rounded-md text-xs disabled:opacity-50"
                />
              </label>

              <div className="text-xs text-c-ink-soft border border-c-line rounded-lg p-3 bg-white space-y-1">
                <div>
                  <span className="text-c-ink-faint">Id Ticket : </span>
                  {detail.id_ticket}
                </div>
                <div>
                  <span className="text-c-ink-faint">Service : </span>
                  {detail.service}
                </div>
                <div>
                  <span className="text-c-ink-faint">Id Type Dem : </span>
                  {detail.id_type_demande}
                </div>
              </div>

              <button
                onClick={() => setPicker('staff')}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong bg-white text-sm text-c-ink hover:bg-c-brand-soft transition-colors"
              >
                <UserPlus className="w-4 h-4 text-c-brand shrink-0" />
                <span className="truncate">
                  {opStaffLabel || "Choisir l'Opé Staff"}
                </span>
              </button>

              <button
                onClick={() =>
                  onSave({ ...buildPayload(), prendre_en_charge: true })
                }
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-c-brand text-c-brand-strong text-sm font-medium hover:bg-c-brand-soft transition-colors"
              >
                <CheckCircle2 className="w-4 h-4" />
                Je m'occupe de ce ticket
              </button>

              <button
                onClick={() => onSave(buildPayload())}
                className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 transition-all"
              >
                <Save className="w-4 h-4" />
                Enregistrer les infos générales
              </button>

              <button
                disabled
                title="Historique — à venir"
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-c-ink-faint text-sm opacity-50 cursor-not-allowed"
              >
                <History className="w-4 h-4" />
                Voir l'historique
              </button>
            </div>

            {/* Colonne droite — Détail du ticket (fenêtre interne FI_*) */}
            <div className="flex-1 min-w-0 overflow-y-auto p-6 flex flex-col">
              <h3 className="text-sm font-semibold text-c-ink mb-4 shrink-0">
                Détail du ticket
              </h3>
              {(() => {
                const FI = FI_COMPONENTS[detail.id_type_demande]
                return FI ? (
                  <div className="flex-1 min-h-0 overflow-auto">
                    <FI
                      apiBase={apiBase}
                      getToken={getToken}
                      idTicket={detail.id_ticket}
                      onClose={onClose}
                    />
                  </div>
                ) : (
                  <div className="h-full flex items-center justify-center text-c-ink-faint text-sm text-center">
                    Formulaire spécifique au type «&nbsp;
                    {detail.lib_type_demande}&nbsp;»
                    <br />
                    (à venir)
                  </div>
                )
              })()}
            </div>
          </div>
        )}

        {picker && (
          <SalariePicker
            apiBase={apiBase}
            getToken={getToken}
            onClose={() => setPicker(null)}
            onPick={(s) => {
              const label = `${s.nom} ${capitalize(s.prenom)}`
              if (picker === 'dest') {
                setOpDest(s.id_salarie)
                setOpDestLabel(label)
                onSave(buildPayload({ op_dest: s.id_salarie }))
              } else {
                setOpStaff(s.id_salarie)
                setOpStaffLabel(label)
                onSave(buildPayload({ op_traitement_staff: s.id_salarie }))
              }
              setPicker(null)
            }}
          />
        )}
      </div>
    </>
  )
}

function StatuerPopup({
  statuts, count, onValidate, onClose,
}: {
  statuts: TicketStatut[]
  count: number
  onValidate: (idStatut: number | null, cloturee: boolean) => void
  onClose: () => void
}) {
  const [statutId, setStatutId] = useState<number | ''>('')
  const [cloturee, setCloturee] = useState(false)
  const canValidate = cloturee || statutId !== ''
  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 bg-white rounded-2xl shadow-xl border border-c-line w-80 p-5">
        <div className="flex items-center gap-2 text-base font-semibold text-c-ink mb-1">
          <CheckCircle2 className="w-5 h-5 text-c-brand" />
          Choisir un statut
        </div>
        <p className="text-xs text-c-ink-faint mb-4">
          {count} ticket{count > 1 ? 's' : ''} sélectionné{count > 1 ? 's' : ''}
        </p>
        <select
          value={statutId}
          onChange={(e) =>
            setStatutId(e.target.value === '' ? '' : Number(e.target.value))
          }
          disabled={cloturee}
          className="w-full px-3 py-2 mb-3 border border-c-line-strong rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-c-brand-line disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <option value="">Statut…</option>
          {statuts.map((s) => (
            <option key={s.id_statut} value={s.id_statut}>
              {s.lib_statut}
            </option>
          ))}
        </select>
        <label className="flex items-center justify-center gap-2 text-sm text-c-ink mb-4 cursor-pointer">
          <input
            type="checkbox"
            checked={cloturee}
            onChange={(e) => setCloturee(e.target.checked)}
            className="w-4 h-4 cursor-pointer accent-c-brand"
          />
          Clôturé
        </label>
        <button
          onClick={() =>
            onValidate(cloturee ? null : statutId === '' ? null : statutId, cloturee)
          }
          disabled={!canValidate}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          <Save className="w-4 h-4" />
          Je valide ce statut
        </button>
      </div>
    </>
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
  addedIds, modifiedIds, onClearMarkers, onOpen,
}: {
  label: string
  count: number
  rows: TicketRow[]
  selected: Set<string>
  onToggle: (id: string) => void
  addedIds: Set<string>
  modifiedIds: Set<string>
  onClearMarkers: (id: string) => void
  onOpen: (id: string) => void
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
        const isAdded = addedIds.has(r.id_ticket)
        const isModified = !isAdded && modifiedIds.has(r.id_ticket)
        // Priorité : added > modified > selected > base
        const rowBg = isAdded
          ? 'bg-emerald-50 hover:bg-emerald-100'
          : isModified
            ? 'bg-amber-50 hover:bg-amber-100'
            : isSelected
              ? 'bg-c-surface-medium'
              : 'hover:bg-c-surface-soft'
        return (
          <tr
            key={r.id_ticket}
            onClick={() => {
              if (isAdded || isModified) onClearMarkers(r.id_ticket)
              onOpen(r.id_ticket)
            }}
            className={`border-t border-c-line-soft transition-colors cursor-pointer ${rowBg}`}
            title="Ouvrir le ticket"
          >
            <td className="px-3 py-2 text-center" onClick={(e) => e.stopPropagation()}>
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
