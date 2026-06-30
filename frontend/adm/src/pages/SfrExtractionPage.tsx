/**
 * Fen_ExtractionSFR - Suivi SFR > Extraction SFR.
 *
 * 2 onglets : Contrats (fonctionnel) / Tickets (vide cf WinDev).
 *
 * Filtres :
 *   - Du / Au
 *   - Bouton segmenté : Date Racc / RDV Tech / Churn
 *   - Combo État vente SFR (désactivée en mode Churn)
 *
 * Tableau résultats : checkbox + nombreuses colonnes, fond colore
 * selon TypeEtatContrat (R,V,B). Filtre + tri + export XLSX.
 *
 * 2 boutons d'action en bas : 'Convertir en Ticket Call RET RDV TECH'
 * et 'Convertir en Ticket Call RET Racc'.
 */
import { useEffect, useState } from 'react'
import {
  Search, Loader2, ArrowLeft, Download as DownloadIcon, FileDown,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  useTableSortFilter, SortableTh, FilterInput,
} from '@shared/production/_tableHelpers'

const API_BASE = '/api/adm'

interface EtatSfr { id_etat: number; lib_etat: string }
interface Row {
  id_contrat: string; num_bs: string; lib_produit: string
  type_prod: string; type_vente: number
  date_signature: string; type_etat: string
  etat_contrat: string; etat_sfr: number
  couleur_hex: string
  nom_vendeur: string; agence: string; equipe: string
  client_nom: string; client_adr: string; client_cp: string
  client_ville: string; client_mail: string; client_mobile: string
  box8: boolean; box8_verif: boolean
  cluster_code: string; cluster_nom: string
  date_portabilite: string; date_racc_valid: string
  date_rdv_tech: string; date_resil: string; date_validation: string
  internet_garanti: boolean; remise: number; self_install: string
  technologie: number
  infos_internes: string; infos_partagees: string
}

type Mode = 'date_racc' | 'rdv_tech' | 'churn'
type Onglet = 'contrats' | 'tickets'

const todayIso = (): string => new Date().toISOString().slice(0, 10)
const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? '' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function SfrExtractionPage() {
  useDocumentTitle('Extraction SFR')
  const [du, setDu] = useState(todayIso())
  const [au, setAu] = useState(todayIso())
  const [mode, setMode] = useState<Mode>('date_racc')
  const [etats, setEtats] = useState<EtatSfr[]>([])
  const [idEtatSfr, setIdEtatSfr] = useState<number>(0)
  const [rows, setRows] = useState<Row[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [onglet, setOnglet] = useState<Onglet>('contrats')

  useEffect(() => {
    fetch(`${API_BASE}/suivi-sfr/extraction-sfr/etats`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then((d: EtatSfr[]) => setEtats(Array.isArray(d) ? d : []))
  }, [])

  const rechercher = async () => {
    if (du > au) { showToast('Dates incohérentes', 'error'); return }
    setLoading(true); setSelected(new Set())
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/extraction-sfr/search?du=${du}&au=${au}&mode=${mode}&id_etat_sfr=${idEtatSfr}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d: Row[] = await r.json()
      setRows(d)
      // Pre-coche tout (cf WinDev Choix=Vrai par defaut)
      setSelected(new Set(d.map(x => x.id_contrat)))
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }

  const tsf = useTableSortFilter(
    rows as unknown as Array<Record<string, unknown>>,
    { key: 'date_signature', dir: 'desc' },
    (r) => [
      r.num_bs, r.lib_produit, r.client_nom, r.nom_vendeur,
      r.cluster_nom, r.etat_contrat, r.type_etat,
    ].map((v) => String(v ?? '')).join(' '),
  )
  const visible = tsf.rows as unknown as Row[]

  const toggleAll = () => {
    if (visible.every(r => selected.has(r.id_contrat))) {
      const s = new Set(selected); for (const r of visible) s.delete(r.id_contrat); setSelected(s)
    } else {
      const s = new Set(selected); for (const r of visible) s.add(r.id_contrat); setSelected(s)
    }
  }
  const toggle = (id: string) => {
    const s = new Set(selected); if (s.has(id)) s.delete(id); else s.add(id); setSelected(s)
  }

  const doConvert = async (kind: 'rdv-tech' | 'racc') => {
    const ids = Array.from(selected).map(id => parseInt(id, 10))
    if (ids.length === 0) return
    const label = kind === 'rdv-tech' ? 'RET RDV TECH' : 'RET Racc'
    const ok = await showConfirm({
      title: `Convertir en Ticket Call ${label}`,
      message: `Créer ${ids.length} ticket(s) ${label} ?`,
    })
    if (!ok) return
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/extraction-sfr/convert-${kind}`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ id_contrats: ids }),
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      const res: { nb_ok: number; nb_ko: number } = await r.json()
      showToast(`${res.nb_ok}/${res.nb_ok + res.nb_ko} ticket(s) créé(s)`,
        res.nb_ko === 0 ? 'success' : 'info')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const exportXlsx = async () => {
    const { exportRowsToXlsx } = await import('@shared/production/_tableHelpers')
    exportRowsToXlsx(
      [
        { key: 'num_bs', label: 'Num BS' },
        { key: 'lib_produit', label: 'Lib Produit' },
        { key: 'type_prod', label: 'Type Prod' },
        { key: 'type_vente', label: 'Type vente' },
        { key: 'date_signature', label: 'Date Signature' },
        { key: 'type_etat', label: 'Type Etat' },
        { key: 'etat_contrat', label: 'Etat contrat' },
        { key: 'nom_vendeur', label: 'Vendeur' },
        { key: 'client_nom', label: 'Client' },
        { key: 'client_adr', label: 'Adresse' },
        { key: 'client_cp', label: 'CP' },
        { key: 'client_ville', label: 'Ville' },
        { key: 'client_mail', label: 'Mail' },
        { key: 'client_mobile', label: 'Mobile' },
        { key: 'cluster_code', label: 'Cluster Code' },
        { key: 'cluster_nom', label: 'Cluster Nom' },
        { key: 'date_portabilite', label: 'Date Portabilité' },
        { key: 'date_racc_valid', label: 'Date Racc' },
        { key: 'date_rdv_tech', label: 'Date RDV Tech' },
        { key: 'date_resil', label: 'Date Résil' },
        { key: 'date_validation', label: 'Date Validation' },
        { key: 'box8', label: 'Box8' },
        { key: 'box8_verif', label: 'Box8 Vérif' },
        { key: 'internet_garanti', label: 'Internet Garanti' },
        { key: 'remise', label: 'Remise' },
        { key: 'self_install', label: 'Self Install' },
        { key: 'technologie', label: 'Techno' },
        { key: 'infos_internes', label: 'Infos Internes' },
        { key: 'infos_partagees', label: 'Infos Partagées' },
      ],
      visible as unknown as Array<Record<string, unknown>>,
      'extraction-sfr', 'Extraction SFR',
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
          <DownloadIcon className="w-4 h-4 text-c-brand" /> Extraction SFR
        </h1>
      </div>

      {/* Onglets */}
      <div className="flex gap-1 border-b border-c-line mb-3">
        {(['contrats', 'tickets'] as const).map(t => (
          <button key={t} type="button" onClick={() => setOnglet(t)}
            className={`px-4 py-1.5 text-sm font-medium rounded-t ${
              onglet === t
                ? 'bg-white border border-c-line border-b-white text-c-brand'
                : 'text-c-ink-faint hover:bg-c-surface-soft'
            }`}>
            {t === 'contrats' ? 'Contrats' : 'Tickets'}
          </button>
        ))}
      </div>

      {onglet === 'tickets' && (
        <div className="bg-white rounded-xl border border-c-line p-12 text-center text-sm text-c-ink-faint italic">
          Onglet Tickets vide (cf WinDev).
        </div>
      )}

      {onglet === 'contrats' && (
        <>
          {/* Filtres */}
          <div className="flex items-center gap-3 mb-3 bg-white p-3 rounded-xl border border-c-line text-sm flex-wrap">
            <label className="text-c-ink-faint text-xs">Du</label>
            <input type="date" value={du} onChange={e => setDu(e.target.value)}
              className="px-2 py-1 border border-c-line rounded text-xs h-7" />
            <label className="text-c-ink-faint text-xs">Au</label>
            <input type="date" value={au} onChange={e => setAu(e.target.value)}
              className="px-2 py-1 border border-c-line rounded text-xs h-7" />

            <div className="flex gap-0 ml-2">
              {([
                ['date_racc', 'Date Racc'],
                ['rdv_tech', 'RDV Tech'],
                ['churn', 'Churn'],
              ] as const).map(([k, l], i) => (
                <button key={k} type="button" onClick={() => setMode(k)}
                  className={`px-3 h-7 text-xs border border-c-line ${
                    i === 0 ? 'rounded-l' : ''
                  } ${i === 2 ? 'rounded-r' : ''} ${
                    mode === k ? 'bg-c-brand text-white border-c-brand' : 'bg-white text-c-ink-soft'
                  }`}>
                  {l}
                </button>
              ))}
            </div>

            <button type="button" onClick={rechercher} disabled={loading}
              className="flex items-center gap-2 px-4 bg-c-brand text-white rounded text-sm font-medium hover:opacity-90 disabled:opacity-50 h-7">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" />
                       : <Search className="w-4 h-4" />}
              Rechercher
            </button>

            <div className="flex-1" />

            {rows.length > 0 && (
              <button type="button" onClick={exportXlsx}
                className="flex items-center gap-1.5 px-2.5 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft h-7">
                <FileDown className="w-3.5 h-3.5" /> XLSX
              </button>
            )}
          </div>

          {/* Combo Etat (désactivée en mode Churn) */}
          <div className="flex items-center gap-3 mb-3 bg-white px-3 py-2 rounded-xl border border-c-line text-sm flex-wrap">
            <label className="text-c-ink-faint text-xs">État vente SFR</label>
            <select value={idEtatSfr}
              onChange={e => setIdEtatSfr(parseInt(e.target.value, 10) || 0)}
              disabled={mode === 'churn'}
              className="flex-1 px-2 py-1 border border-c-line rounded text-xs h-7 disabled:opacity-50">
              <option value={0}>— Tous —</option>
              {etats.map(e => (
                <option key={e.id_etat} value={e.id_etat}>{e.lib_etat}</option>
              ))}
            </select>
            <FilterInput value={tsf.filter} onChange={tsf.setFilter}
              placeholder="Filtrer…" />
          </div>

          {/* Tableau */}
          <div className="bg-white rounded-xl border border-c-line overflow-hidden flex-1 flex flex-col">
            <div className="px-3 py-1.5 border-b border-c-line-soft text-xs text-c-ink-faint">
              {visible.length} / {rows.length} contrat(s) | {selected.size} sélectionné(s)
            </div>
            <div className="flex-1 overflow-auto">
              <table className="w-full text-xs">
                <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0 z-10">
                  <tr>
                    <th className="px-2 py-2 text-center w-8">
                      <input type="checkbox"
                        checked={visible.length > 0 && visible.every(r => selected.has(r.id_contrat))}
                        onChange={toggleAll} />
                    </th>
                    <SortableTh label="Num BS" sortKey="num_bs" sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Lib Produit" sortKey="lib_produit" sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Type Prod" sortKey="type_prod" sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Type vente" sortKey="type_vente" sort={tsf.sort} onSort={tsf.toggleSort} align="center" />
                    <SortableTh label="Signature" sortKey="date_signature" sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Type Etat" sortKey="type_etat" sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="État" sortKey="etat_contrat" sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Vendeur" sortKey="nom_vendeur" sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Client" sortKey="client_nom" sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="CP" sortKey="client_cp" sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Ville" sortKey="client_ville" sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Cluster" sortKey="cluster_nom" sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Date Racc" sortKey="date_racc_valid" sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="RDV Tech" sortKey="date_rdv_tech" sort={tsf.sort} onSort={tsf.toggleSort} />
                    <SortableTh label="Résil" sortKey="date_resil" sort={tsf.sort} onSort={tsf.toggleSort} />
                  </tr>
                </thead>
                <tbody className="divide-y divide-c-line-soft">
                  {visible.length === 0 ? (
                    <tr>
                      <td colSpan={16} className="text-center py-12 text-c-ink-faint-2 italic">
                        Aucun contrat — choisis filtres puis Rechercher.
                      </td>
                    </tr>
                  ) : visible.map(r => (
                    <tr key={r.id_contrat}
                      onClick={() => toggle(r.id_contrat)}
                      className="cursor-pointer hover:bg-c-surface-soft"
                      style={r.couleur_hex ? { background: r.couleur_hex } : {}}>
                      <td className="px-2 py-1.5 text-center">
                        <input type="checkbox" checked={selected.has(r.id_contrat)}
                          onChange={() => toggle(r.id_contrat)}
                          onClick={(e) => e.stopPropagation()} />
                      </td>
                      <td className="px-2 py-1.5 tabular-nums">{r.num_bs}</td>
                      <td className="px-2 py-1.5">{r.lib_produit}</td>
                      <td className="px-2 py-1.5">{r.type_prod}</td>
                      <td className="px-2 py-1.5 text-center">{r.type_vente || ''}</td>
                      <td className="px-2 py-1.5">{shortDate(r.date_signature)}</td>
                      <td className="px-2 py-1.5">{r.type_etat}</td>
                      <td className="px-2 py-1.5">{r.etat_contrat}</td>
                      <td className="px-2 py-1.5">{r.nom_vendeur}</td>
                      <td className="px-2 py-1.5">{r.client_nom}</td>
                      <td className="px-2 py-1.5">{r.client_cp}</td>
                      <td className="px-2 py-1.5">{r.client_ville}</td>
                      <td className="px-2 py-1.5">{r.cluster_nom}</td>
                      <td className="px-2 py-1.5">{shortDate(r.date_racc_valid)}</td>
                      <td className="px-2 py-1.5">{shortDate(r.date_rdv_tech)}</td>
                      <td className="px-2 py-1.5">{shortDate(r.date_resil)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex gap-3 mt-3">
            <button type="button" onClick={() => doConvert('rdv-tech')}
              disabled={selected.size === 0}
              className="flex-1 px-4 py-2 bg-c-brand text-white rounded text-sm font-medium hover:opacity-90 disabled:opacity-50">
              Convertir en Ticket Call RET RDV TECH ({selected.size})
            </button>
            <button type="button" onClick={() => doConvert('racc')}
              disabled={selected.size === 0}
              className="flex-1 px-4 py-2 bg-c-brand text-white rounded text-sm font-medium hover:opacity-90 disabled:opacity-50">
              Convertir en Ticket Call RET Racc ({selected.size})
            </button>
          </div>
        </>
      )}
    </div>
  )
}
