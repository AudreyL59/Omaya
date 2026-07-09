/**
 * Fen_ScoolStagiaire_Fiche - Fiche detaillee d'un stagiaire dans une
 * formation S'Cool.
 *
 * URL : /scool/formations/:id_formation/stagiaires/:id_salarie
 *       ?type_prod=ENI|SFR
 *
 * Layout :
 * - Header : Nom, Du, Au, btn Enregistrer + refresh + Axes de travail
 * - 2 onglets : Declaratif de presence / Production (ENI ou SFR)
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
  Save, RefreshCw, FileText, Plus, Loader2, Check,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'

const API_BASE = '/api/adm'

interface PresenceRow {
  date: string
  type_journee: number
  presence: number       // 1 present, 0 absent, -1 demi
  id_motif: number
  motif_absence: string
  periode: number
  emarg_matin: boolean
  emarg_aprem: boolean
}

interface ProdEniRow {
  date: string; num_sem: number; sem_prod: string
  salle: number; terrain: number; duree: number
  absent: number; present: number
  objectif_bs_jour: number
  total_ctt: number; total_adf: number
  eni_gaz: number; eni_dual: number; eni_elec: number
  eni_gaz_vert: number; eni_elec_verte: number; eni_mail: number
  presse: number; assu: number; cooptation: number
  objectif: number
  pourcent_dual: number; pourcent_elec: number; pourcent_mail: number
  pourcent_gv: number; pourcent_ev: number
  pourcent_adf: number; pourcent_presse: number
}

interface ProdSfrRow {
  date: string; num_sem: number; sem_prod: string
  salle: number; terrain: number; duree: number
  absent: number; present: number
  objectif_bs_jour: number
  total_ctt: number; total_adf: number
  power8: number; premium: number; fibre8: number; power: number
  migration: number; mobile: number
  assu: number; presse: number; cooptation: number
  objectif: number
  pourcent_adf: number; pourcent_presse: number
}

interface Fiche {
  id_formation: string; id_salarie: string
  nom_prenom: string; lib_formation: string
  date_debut: string; date_fin: string
  niveau_form: string
  heure_jour_salle: number; heure_jour_terrain: number
  type_prod: string
  axe_travail_1: string; axe_travail_2: string
  livrable: boolean
  presence: PresenceRow[]
  recap_presence: {
    nb_jours_salle: number
    nb_jours_terrain: number
    total_jours: number
  }
  prod_eni: ProdEniRow[]
  prod_sfr: ProdSfrRow[]
  tot_salle: number; tot_terrain: number; tot_duree: number
  tot_absent: number; tot_present: number
  tot_obj_bs: number
  tot_ctt: number; tot_adf: number
  tot_presse: number; tot_assu: number; tot_coopt: number
}

interface MotifAbsence { id_type_absence: number; lib_absence: string }

const fmtDate = (d: string) => {
  if (!d) return ''
  const s = d.slice(0, 10)
  return `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}`
}
const fmtNum = (n: number, dec = 2) => n === 0 ? '' : n.toFixed(dec)
const fmtPct = (n: number) => n === 0 ? '' : (n * 100).toFixed(1) + '%'
const clsPct = (v: number, seuil: number, inverse = false) => {
  if (v === 0) return ''
  const bad = inverse ? v > seuil : v < seuil
  return bad
    ? 'text-red-800 bg-red-100 font-medium'
    : 'text-green-800 bg-green-100 font-medium'
}


export default function ScoolStagiaireFichePage() {
  useDocumentTitle('Fiche Stagiaire')
  const nav = useNavigate()
  const { id_formation, id_salarie } = useParams()
  const [sp] = useSearchParams()
  const typeProd = (sp.get('type_prod') || '').toUpperCase()

  const [fiche, setFiche] = useState<Fiche | null>(null)
  const [motifs, setMotifs] = useState<MotifAbsence[]>([])
  const [tab, setTab] = useState<'presence' | 'prod'>('presence')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(false)
  const [pdfLoading, setPdfLoading] = useState<string | null>(null)

  const [du, setDu] = useState('')
  const [au, setAu] = useState('')
  const [livrable, setLivrable] = useState(false)
  const [axe1, setAxe1] = useState('')
  const [axe2, setAxe2] = useState('')

  const load = useCallback(async () => {
    if (!id_formation || !id_salarie) return
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/scool/stagiaire-fiche/${id_formation}/${id_salarie}` +
        `?type_prod=${typeProd}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        showToast('Fiche introuvable', 'error')
        return
      }
      const d: Fiche = await r.json()
      setFiche(d)
      setDu(d.date_debut)
      setAu(d.date_fin)
      setLivrable(d.livrable)
      setAxe1(d.axe_travail_1)
      setAxe2(d.axe_travail_2)
    } finally { setLoading(false) }
  }, [id_formation, id_salarie, typeProd])

  useEffect(() => { void load() }, [load])
  useEffect(() => {
    void (async () => {
      const r = await fetch(
        `${API_BASE}/scool/stagiaire-fiche/motifs-absence`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (r.ok) setMotifs(await r.json())
    })()
  }, [])

  const onSave = async () => {
    if (!id_formation || !id_salarie) return
    setSaving(true)
    try {
      const r = await fetch(`${API_BASE}/scool/stagiaire-fiche/save`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_formation, id_salarie,
          date_debut: du, date_fin: au,
          livrable, axe_travail_1: axe1, axe_travail_2: axe2,
        }),
      })
      const d = await r.json()
      if (d.ok) {
        showToast('Enregistré', 'success')
        await load()
      } else {
        showToast("Echec de l'enregistrement", 'error')
      }
    } finally { setSaving(false) }
  }

  const openPdf = useCallback(async (kind: 'declpres' | 'prodeni' | 'prodsfr') => {
    if (!id_formation || !id_salarie) return
    setPdfLoading(kind)
    try {
      const r = await fetch(
        `${API_BASE}/scool/stagiaire-fiche/${id_formation}/${id_salarie}` +
        `/pdf-${kind}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) { showToast('Erreur PDF', 'error'); return }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } finally { setPdfLoading(null) }
  }, [id_formation, id_salarie])

  const onAjoutLigne = async () => {
    const dateStr = window.prompt('Date à ajouter (YYYY-MM-DD) :')
    if (!dateStr) return
    const r = await fetch(
      `${API_BASE}/scool/stagiaire-fiche/ajout-ligne-prod`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_formation, id_salarie, date: dateStr,
        }),
      })
    const d = await r.json()
    if (d.ok) { showToast('Ligne ajoutée', 'success'); await load() }
  }

  const motifLabel = useMemo(() => {
    const m = new Map<number, string>()
    motifs.forEach((mm) => m.set(mm.id_type_absence, mm.lib_absence))
    return m
  }, [motifs])

  if (!fiche && !loading) {
    return (
      <div className="min-h-screen bg-[#F5F1E8]">
        <PageHeader onBack={() => nav(-1)} />
        <div className="text-center text-gray-500 py-20">Chargement…</div>
      </div>
    )
  }

  // Groupement production par semaine
  const rowsProd = typeProd === 'ENI'
    ? (fiche?.prod_eni || [])
    : typeProd === 'SFR' ? (fiche?.prod_sfr || []) : []
  const groupedBySem = useMemo(() => {
    const out: Record<string, typeof rowsProd> = {}
    rowsProd.forEach((r) => {
      const k = r.sem_prod || `Semaine ${r.num_sem}`
      if (!out[k]) out[k] = []
      ;(out[k] as typeof rowsProd).push(r)
    })
    return out
  }, [rowsProd])

  return (
    <div className="min-h-screen bg-[#F5F1E8]">
      <PageHeader
        onBack={() => nav(`/scool/formations/${id_formation}`)}
      />

      <div className="max-w-[1600px] mx-auto px-4 py-4">
        {/* Header libelle + dates + livrable */}
        <div className="bg-white rounded-lg shadow p-4 mb-3">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex-1 min-w-[260px]">
              <div className="text-xs text-[#8B7355]">Stagiaire</div>
              <div className="text-lg font-bold text-[#17494E]">
                {fiche?.nom_prenom}
              </div>
              <div className="text-xs text-[#8B7355] mt-0.5">
                {fiche?.lib_formation}
                {fiche?.niveau_form ? ` · ${fiche.niveau_form}` : ''}
              </div>
            </div>
            <label className="text-xs">
              <div className="text-[#8B7355] mb-0.5">Du</div>
              <input type="date" value={du}
                     onChange={(e) => setDu(e.target.value)}
                     className="border border-[#D4C9A8] rounded px-2 py-1" />
            </label>
            <label className="text-xs">
              <div className="text-[#8B7355] mb-0.5">Au</div>
              <input type="date" value={au}
                     onChange={(e) => setAu(e.target.value)}
                     className="border border-[#D4C9A8] rounded px-2 py-1" />
            </label>
            <label className="flex items-center gap-2 text-xs">
              <input type="checkbox" checked={livrable}
                     onChange={(e) => setLivrable(e.target.checked)}
                     className="accent-[#17494E]" />
              Livrable
            </label>
            <button onClick={onSave} disabled={saving}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm disabled:opacity-50">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" />
                      : <Save className="w-4 h-4" />}
              Enregistrer
            </button>
            <button onClick={load}
                    className="p-1.5 rounded hover:bg-[#ECF1F2]"
                    title="Recharger">
              <RefreshCw className="w-4 h-4 text-[#17494E]" />
            </button>
          </div>
        </div>

        {/* Onglets */}
        <div className="flex gap-1 border-b border-[#D4C9A8] mb-3">
          <TabBtn active={tab === 'presence'}
                  onClick={() => setTab('presence')}>
            Déclaratif de présence
          </TabBtn>
          {typeProd === 'ENI' && (
            <TabBtn active={tab === 'prod'}
                    onClick={() => setTab('prod')}>
              Production ENI Jour/Jour
            </TabBtn>
          )}
          {typeProd === 'SFR' && (
            <TabBtn active={tab === 'prod'}
                    onClick={() => setTab('prod')}>
              Production SFR Jour/Jour
            </TabBtn>
          )}
        </div>

        {tab === 'presence' && fiche && (
          <PresenceTab fiche={fiche} motifLabel={motifLabel}
                       onPdf={() => openPdf('declpres')}
                       pdfLoading={pdfLoading === 'declpres'} />
        )}

        {tab === 'prod' && typeProd === 'ENI' && fiche && (
          <ProdEniTab
            rowsBySem={groupedBySem as Record<string, ProdEniRow[]>}
            fiche={fiche}
            onAjoutLigne={onAjoutLigne}
            axe1={axe1} axe2={axe2}
            setAxe1={setAxe1} setAxe2={setAxe2}
            onPdf={() => openPdf('prodeni')}
            pdfLoading={pdfLoading === 'prodeni'}
          />
        )}
        {tab === 'prod' && typeProd === 'SFR' && fiche && (
          <ProdSfrTab
            rowsBySem={groupedBySem as Record<string, ProdSfrRow[]>}
            fiche={fiche}
            onAjoutLigne={onAjoutLigne}
            axe1={axe1} axe2={axe2}
            setAxe1={setAxe1} setAxe2={setAxe2}
            onPdf={() => openPdf('prodsfr')}
            pdfLoading={pdfLoading === 'prodsfr'}
          />
        )}
      </div>
    </div>
  )
}


function TabBtn(
  { active, onClick, children }:
    { active: boolean; onClick: () => void; children: React.ReactNode },
) {
  return (
    <button onClick={onClick}
            className={
              `px-3 py-1.5 text-sm rounded-t border-b-2 transition-colors ${
                active
                  ? 'bg-white text-[#17494E] border-[#17494E] font-semibold'
                  : 'text-[#8B7355] border-transparent hover:bg-white/50'
              }`
            }>
      {children}
    </button>
  )
}


// =====================================================================
// Onglet Presence
// =====================================================================

function PresenceTab(
  { fiche, motifLabel, onPdf, pdfLoading }:
    {
      fiche: Fiche; motifLabel: Map<number, string>
      onPdf: () => void; pdfLoading: boolean
    },
) {
  const presLabel = (p: PresenceRow) => {
    if (p.presence === 1) return <Check className="inline w-4 h-4 text-green-700" />
    if (p.presence === -1) return <span className="text-orange-700">½</span>
    return <span className="text-red-700 font-bold">✗</span>
  }
  const periodeLabel = (p: number) => {
    if (p === 1) return 'Matin'
    if (p === 2) return 'Après-midi'
    if (p === 3) return 'Journée'
    return ''
  }
  const typeJourLabel = (t: number) => {
    if (t === 1) return 'Salle'
    if (t === 2) return 'Terrain'
    return ''
  }
  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-3">
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-2 mb-3">
          <button onClick={onPdf} disabled={pdfLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E]/10 hover:bg-[#17494E]/20 text-sm text-[#17494E] disabled:opacity-50"
                  title="Cf. WinDev : imprime EtatScool_DeclPres">
            {pdfLoading
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <FileText className="w-4 h-4" />}
            {pdfLoading ? 'Génération…' : 'Imprimer PDF'}
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="text-xs w-full">
            <thead className="bg-[#17494E] text-white">
              <tr>
                <th className="py-1.5 px-2 text-left">Date</th>
                <th className="py-1.5 px-2 text-left">Type Journée</th>
                <th className="py-1.5 px-2 text-center">Présence</th>
                <th className="py-1.5 px-2 text-left">Motif d'absence</th>
                <th className="py-1.5 px-2 text-left">Période d'absence</th>
                <th className="py-1.5 px-2 text-center">Émarg. matin</th>
                <th className="py-1.5 px-2 text-center">Émarg. aprem</th>
              </tr>
            </thead>
            <tbody>
              {fiche.presence.map((p) => (
                <tr key={p.date} className="border-b border-[#F0EDE5] hover:bg-[#ECF1F2]">
                  <td className="py-1 px-2 tabular-nums">{fmtDate(p.date)}</td>
                  <td className="py-1 px-2">{typeJourLabel(p.type_journee)}</td>
                  <td className="py-1 px-2 text-center">{presLabel(p)}</td>
                  <td className="py-1 px-2">
                    {p.motif_absence || motifLabel.get(p.id_motif) || ''}
                  </td>
                  <td className="py-1 px-2">{periodeLabel(p.periode)}</td>
                  <td className="py-1 px-2 text-center">
                    {p.emarg_matin
                      ? <Check className="inline w-3 h-3 text-green-700" />
                      : ''}
                  </td>
                  <td className="py-1 px-2 text-center">
                    {p.emarg_aprem
                      ? <Check className="inline w-3 h-3 text-green-700" />
                      : ''}
                  </td>
                </tr>
              ))}
              {fiche.presence.length === 0 && (
                <tr><td colSpan={7} className="py-6 text-center text-gray-400">Aucune présence</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recap */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-sm font-semibold text-[#17494E] mb-3">
          Récap Présence
        </div>
        <RecapRow label="nb Jours en salle"
                  value={fiche.recap_presence.nb_jours_salle} />
        <RecapRow label="nb Jours de terrain"
                  value={fiche.recap_presence.nb_jours_terrain} />
        <div className="border-t border-[#D4C9A8] mt-2 pt-2">
          <RecapRow label="TOTAL Jours"
                    value={fiche.recap_presence.total_jours}
                    bold />
        </div>
      </div>
    </div>
  )
}

function RecapRow(
  { label, value, bold = false }:
    { label: string; value: number; bold?: boolean },
) {
  return (
    <div className="flex items-center justify-between py-1 text-sm">
      <span className={bold
        ? 'font-semibold text-[#17494E]' : 'text-[#8B7355]'}>{label}</span>
      <span className={`tabular-nums ${bold ? 'font-bold' : ''}`}>
        {value.toFixed(2)}
      </span>
    </div>
  )
}


// =====================================================================
// Onglet Production ENI
// =====================================================================

interface ProdTabProps<T> {
  rowsBySem: Record<string, T[]>
  fiche: Fiche
  onAjoutLigne: () => void
  axe1: string; axe2: string
  setAxe1: (v: string) => void; setAxe2: (v: string) => void
  onPdf: () => void
  pdfLoading: boolean
}

function ProdEniTab(
  { rowsBySem, fiche, onAjoutLigne, axe1, axe2, setAxe1, setAxe2,
    onPdf, pdfLoading }:
    ProdTabProps<ProdEniRow>,
) {
  const semaines = Object.keys(rowsBySem).sort((a, b) => {
    const na = parseInt(a.replace(/\D/g, ''), 10) || 0
    const nb = parseInt(b.replace(/\D/g, ''), 10) || 0
    return na - nb
  })
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center gap-2 mb-3">
        <button onClick={onAjoutLigne}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm">
          <Plus className="w-4 h-4" /> Ajouter une ligne au tableau
        </button>
        <button onClick={onPdf} disabled={pdfLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E]/10 hover:bg-[#17494E]/20 text-sm text-[#17494E] disabled:opacity-50"
                title="Cf. WinDev : imprime EtatProdStagiareScool">
          {pdfLoading
            ? <Loader2 className="w-4 h-4 animate-spin" />
            : <FileText className="w-4 h-4" />}
          {pdfLoading ? 'Génération…' : 'Imprimer'}
        </button>
      </div>

      {semaines.map((sem, i) => {
        const rows = rowsBySem[sem] || []
        const sousTot = rows.reduce((acc, r) => ({
          salle: acc.salle + r.salle,
          terrain: acc.terrain + r.terrain,
          duree: acc.duree + r.duree,
          absent: acc.absent + r.absent,
          present: acc.present + r.present,
          objectif_bs_jour: acc.objectif_bs_jour + r.objectif_bs_jour,
          total_ctt: acc.total_ctt + r.total_ctt,
          total_adf: acc.total_adf + r.total_adf,
          eni_gaz: acc.eni_gaz + r.eni_gaz,
          eni_dual: acc.eni_dual + r.eni_dual,
          eni_elec: acc.eni_elec + r.eni_elec,
          eni_gaz_vert: acc.eni_gaz_vert + r.eni_gaz_vert,
          eni_elec_verte: acc.eni_elec_verte + r.eni_elec_verte,
          eni_mail: acc.eni_mail + r.eni_mail,
          presse: acc.presse + r.presse,
          assu: acc.assu + r.assu,
          cooptation: acc.cooptation + r.cooptation,
        }), {
          salle: 0, terrain: 0, duree: 0, absent: 0, present: 0,
          objectif_bs_jour: 0, total_ctt: 0, total_adf: 0,
          eni_gaz: 0, eni_dual: 0, eni_elec: 0,
          eni_gaz_vert: 0, eni_elec_verte: 0, eni_mail: 0,
          presse: 0, assu: 0, cooptation: 0,
        })
        return (
          <div key={sem} className="mb-6">
            <div className="text-sm font-semibold text-[#17494E] mb-1">
              {sem}
            </div>
            <div className="overflow-x-auto">
              <table className="text-xs w-full whitespace-nowrap">
                <thead>
                  <tr className="bg-[#17494E] text-white text-[10px]">
                    <th className="px-1 py-1 text-left">Date</th>
                    <th className="px-1 py-1" colSpan={3}>Programme</th>
                    <th className="px-1 py-1" colSpan={2}>Assiduité</th>
                    <th className="px-1 py-1">Obj BS</th>
                    <th className="px-1 py-1">Total*</th>
                    <th className="px-1 py-1">ADF</th>
                    <th className="px-1 py-1">%</th>
                    <th className="px-1 py-1" colSpan={10}>ENI</th>
                    <th className="px-1 py-1" colSpan={2}>Presse</th>
                    <th className="px-1 py-1">ASSU</th>
                    <th className="px-1 py-1">Coopt</th>
                  </tr>
                  <tr className="bg-[#17494E] text-white text-[10px]">
                    <th></th>
                    <th className="px-1 py-1">Salle</th>
                    <th className="px-1 py-1">Terrain</th>
                    <th className="px-1 py-1">Durée</th>
                    <th className="px-1 py-1">Abs</th>
                    <th className="px-1 py-1">Prés</th>
                    <th className="px-1 py-1">Obj</th>
                    <th className="px-1 py-1"></th>
                    <th className="px-1 py-1"></th>
                    <th className="px-1 py-1"></th>
                    <th className="px-1 py-1">Gaz</th>
                    <th className="px-1 py-1">Dual</th>
                    <th className="px-1 py-1">%</th>
                    <th className="px-1 py-1">Elec</th>
                    <th className="px-1 py-1">%</th>
                    <th className="px-1 py-1">GV</th>
                    <th className="px-1 py-1">%</th>
                    <th className="px-1 py-1">EV</th>
                    <th className="px-1 py-1">%</th>
                    <th className="px-1 py-1">Mail</th>
                    <th className="px-1 py-1">Nb</th>
                    <th className="px-1 py-1">%</th>
                    <th className="px-1 py-1"></th>
                    <th className="px-1 py-1"></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => {
                    const nbEni = r.eni_gaz + r.eni_dual + r.eni_elec
                    return (
                      <tr key={r.date}
                          className="border-b border-[#F0EDE5] hover:bg-[#ECF1F2]">
                        <td className="px-1 py-0.5 tabular-nums">{fmtDate(r.date)}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{fmtNum(r.salle, 1)}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{fmtNum(r.terrain, 1)}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{fmtNum(r.duree, 1)}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{fmtNum(r.absent, 1)}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{fmtNum(r.present, 1)}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{fmtNum(r.objectif_bs_jour, 0)}</td>
                        <td className={`px-1 py-0.5 text-right tabular-nums ${clsPct(r.objectif, 1)}`}>
                          {r.total_ctt || ''}
                        </td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{r.total_adf || ''}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{fmtPct(r.pourcent_adf)}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{r.eni_gaz || ''}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{r.eni_dual || ''}</td>
                        <td className={`px-1 py-0.5 text-right tabular-nums ${clsPct(r.pourcent_dual, 0.75)}`}>{fmtPct(r.pourcent_dual)}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{r.eni_elec || ''}</td>
                        <td className={`px-1 py-0.5 text-right tabular-nums ${clsPct(r.pourcent_elec, 0.74, true)}`}>{fmtPct(r.pourcent_elec)}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{r.eni_gaz_vert || ''}</td>
                        <td className={`px-1 py-0.5 text-right tabular-nums ${clsPct(r.pourcent_gv, 0.75)}`}>{fmtPct(r.pourcent_gv)}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{r.eni_elec_verte || ''}</td>
                        <td className={`px-1 py-0.5 text-right tabular-nums ${clsPct(r.pourcent_ev, 0.75)}`}>{fmtPct(r.pourcent_ev)}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{r.eni_mail || ''}</td>
                        <td className={`px-1 py-0.5 text-right tabular-nums ${clsPct(r.pourcent_mail, 0.75)}`}>{nbEni > 0 ? fmtPct(r.pourcent_mail) : ''}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{r.presse || ''}</td>
                        <td className={`px-1 py-0.5 text-right tabular-nums ${clsPct(r.pourcent_presse, 0.5)}`}>{fmtPct(r.pourcent_presse)}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{r.assu || ''}</td>
                        <td className="px-1 py-0.5 text-right tabular-nums">{r.cooptation || ''}</td>
                      </tr>
                    )
                  })}
                  <tr className="bg-[#F5F1E8] font-semibold border-t border-[#17494E]">
                    <td className="px-1 py-1">Sous-total {sem}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{fmtNum(sousTot.salle, 1)}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{fmtNum(sousTot.terrain, 1)}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{fmtNum(sousTot.duree, 1)}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{fmtNum(sousTot.absent, 1)}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{fmtNum(sousTot.present, 1)}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{fmtNum(sousTot.objectif_bs_jour, 0)}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.total_ctt || ''}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.total_adf || ''}</td>
                    <td className="px-1 py-1"></td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.eni_gaz || ''}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.eni_dual || ''}</td>
                    <td className="px-1 py-1"></td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.eni_elec || ''}</td>
                    <td className="px-1 py-1"></td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.eni_gaz_vert || ''}</td>
                    <td className="px-1 py-1"></td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.eni_elec_verte || ''}</td>
                    <td className="px-1 py-1"></td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.eni_mail || ''}</td>
                    <td className="px-1 py-1"></td>
                    <td className="px-1 py-1"></td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.presse || ''}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.assu || ''}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.cooptation || ''}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            {i === 0 && (
              <div className="grid grid-cols-2 gap-3 mt-3">
                <label className="text-xs">
                  <div className="text-[#8B7355] mb-0.5">Axe de travail 1</div>
                  <textarea rows={2} value={axe1}
                            onChange={(e) => setAxe1(e.target.value)}
                            className="w-full border border-[#D4C9A8] rounded px-2 py-1 text-xs" />
                </label>
                <label className="text-xs">
                  <div className="text-[#8B7355] mb-0.5">Axe de travail 2</div>
                  <textarea rows={2} value={axe2}
                            onChange={(e) => setAxe2(e.target.value)}
                            className="w-full border border-[#D4C9A8] rounded px-2 py-1 text-xs" />
                </label>
              </div>
            )}
          </div>
        )
      })}

      {/* Totaux formation */}
      <div className="mt-6 bg-[#17494E] text-white rounded-lg p-3 text-xs">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <TotItem label="Salle" v={fiche.tot_salle} dec={1} />
          <TotItem label="Terrain" v={fiche.tot_terrain} dec={1} />
          <TotItem label="Durée" v={fiche.tot_duree} dec={1} />
          <TotItem label="Absent" v={fiche.tot_absent} dec={1} />
          <TotItem label="Présent" v={fiche.tot_present} dec={1} />
          <TotItem label="Obj BS" v={fiche.tot_obj_bs} dec={0} />
          <TotItem label="Total Ctt" v={fiche.tot_ctt} dec={0} />
          <TotItem label="ADF" v={fiche.tot_adf} dec={0} />
          <TotItem label="Presse" v={fiche.tot_presse} dec={0} />
          <TotItem label="ASSU" v={fiche.tot_assu} dec={0} />
          <TotItem label="Coopt" v={fiche.tot_coopt} dec={0} />
        </div>
      </div>
    </div>
  )
}


function TotItem(
  { label, v, dec }: { label: string; v: number; dec: number },
) {
  return (
    <div>
      <div className="opacity-70">{label}</div>
      <div className="font-bold tabular-nums">{v.toFixed(dec)}</div>
    </div>
  )
}


// =====================================================================
// Onglet Production SFR
// =====================================================================

function ProdSfrTab(
  { rowsBySem, fiche, onAjoutLigne, axe1, axe2, setAxe1, setAxe2,
    onPdf, pdfLoading }:
    ProdTabProps<ProdSfrRow>,
) {
  const semaines = Object.keys(rowsBySem).sort((a, b) => {
    const na = parseInt(a.replace(/\D/g, ''), 10) || 0
    const nb = parseInt(b.replace(/\D/g, ''), 10) || 0
    return na - nb
  })
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center gap-2 mb-3">
        <button onClick={onAjoutLigne}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm">
          <Plus className="w-4 h-4" /> Ajouter une ligne au tableau
        </button>
        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E]/10 hover:bg-[#17494E]/20 text-sm text-[#17494E]"
                title="Cf. WinDev : imprime EtatProdStagiareScoolFibre">
          <FileText className="w-4 h-4" /> Imprimer
        </button>
      </div>

      {semaines.map((sem, i) => {
        const rows = rowsBySem[sem] || []
        const sousTot = rows.reduce((acc, r) => ({
          salle: acc.salle + r.salle,
          terrain: acc.terrain + r.terrain,
          duree: acc.duree + r.duree,
          absent: acc.absent + r.absent,
          present: acc.present + r.present,
          objectif_bs_jour: acc.objectif_bs_jour + r.objectif_bs_jour,
          total_ctt: acc.total_ctt + r.total_ctt,
          total_adf: acc.total_adf + r.total_adf,
          power8: acc.power8 + r.power8,
          premium: acc.premium + r.premium,
          fibre8: acc.fibre8 + r.fibre8,
          power: acc.power + r.power,
          migration: acc.migration + r.migration,
          mobile: acc.mobile + r.mobile,
          assu: acc.assu + r.assu,
          presse: acc.presse + r.presse,
          cooptation: acc.cooptation + r.cooptation,
        }), {
          salle: 0, terrain: 0, duree: 0, absent: 0, present: 0,
          objectif_bs_jour: 0, total_ctt: 0, total_adf: 0,
          power8: 0, premium: 0, fibre8: 0, power: 0,
          migration: 0, mobile: 0,
          assu: 0, presse: 0, cooptation: 0,
        })
        return (
          <div key={sem} className="mb-6">
            <div className="text-sm font-semibold text-[#17494E] mb-1">{sem}</div>
            <div className="overflow-x-auto">
              <table className="text-xs w-full whitespace-nowrap">
                <thead>
                  <tr className="bg-[#17494E] text-white text-[10px]">
                    <th className="px-1 py-1 text-left">Date</th>
                    <th className="px-1 py-1" colSpan={3}>Programme</th>
                    <th className="px-1 py-1" colSpan={2}>Assiduité</th>
                    <th className="px-1 py-1">Obj BS</th>
                    <th className="px-1 py-1">Total</th>
                    <th className="px-1 py-1">ADF</th>
                    <th className="px-1 py-1">%</th>
                    <th className="px-1 py-1" colSpan={6}>SFR</th>
                    <th className="px-1 py-1">ASSU</th>
                    <th className="px-1 py-1" colSpan={2}>Presse</th>
                    <th className="px-1 py-1">Coopt</th>
                  </tr>
                  <tr className="bg-[#17494E] text-white text-[10px]">
                    <th></th>
                    <th className="px-1 py-1">Salle</th>
                    <th className="px-1 py-1">Terrain</th>
                    <th className="px-1 py-1">Durée</th>
                    <th className="px-1 py-1">Abs</th>
                    <th className="px-1 py-1">Prés</th>
                    <th className="px-1 py-1"></th>
                    <th className="px-1 py-1"></th>
                    <th className="px-1 py-1"></th>
                    <th className="px-1 py-1"></th>
                    <th className="px-1 py-1">Power 8</th>
                    <th className="px-1 py-1">Premium</th>
                    <th className="px-1 py-1">Fibre 8</th>
                    <th className="px-1 py-1">Power</th>
                    <th className="px-1 py-1">Migration</th>
                    <th className="px-1 py-1">Mobile</th>
                    <th className="px-1 py-1"></th>
                    <th className="px-1 py-1">Nb</th>
                    <th className="px-1 py-1">%</th>
                    <th className="px-1 py-1"></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.date}
                        className="border-b border-[#F0EDE5] hover:bg-[#ECF1F2]">
                      <td className="px-1 py-0.5 tabular-nums">{fmtDate(r.date)}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{fmtNum(r.salle, 1)}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{fmtNum(r.terrain, 1)}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{fmtNum(r.duree, 1)}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{fmtNum(r.absent, 1)}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{fmtNum(r.present, 1)}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{fmtNum(r.objectif_bs_jour, 0)}</td>
                      <td className={`px-1 py-0.5 text-right tabular-nums ${clsPct(r.objectif, 1)}`}>{r.total_ctt || ''}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{r.total_adf || ''}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{fmtPct(r.pourcent_adf)}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{r.power8 || ''}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{r.premium || ''}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{r.fibre8 || ''}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{r.power || ''}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{r.migration || ''}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{r.mobile || ''}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{r.assu || ''}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{r.presse || ''}</td>
                      <td className={`px-1 py-0.5 text-right tabular-nums ${clsPct(r.pourcent_presse, 0.5)}`}>{fmtPct(r.pourcent_presse)}</td>
                      <td className="px-1 py-0.5 text-right tabular-nums">{r.cooptation || ''}</td>
                    </tr>
                  ))}
                  <tr className="bg-[#F5F1E8] font-semibold border-t border-[#17494E]">
                    <td className="px-1 py-1">Sous-total {sem}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{fmtNum(sousTot.salle, 1)}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{fmtNum(sousTot.terrain, 1)}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{fmtNum(sousTot.duree, 1)}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{fmtNum(sousTot.absent, 1)}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{fmtNum(sousTot.present, 1)}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{fmtNum(sousTot.objectif_bs_jour, 0)}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.total_ctt || ''}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.total_adf || ''}</td>
                    <td className="px-1 py-1"></td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.power8 || ''}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.premium || ''}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.fibre8 || ''}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.power || ''}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.migration || ''}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.mobile || ''}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.assu || ''}</td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.presse || ''}</td>
                    <td className="px-1 py-1"></td>
                    <td className="px-1 py-1 text-right tabular-nums">{sousTot.cooptation || ''}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            {i === 0 && (
              <div className="grid grid-cols-2 gap-3 mt-3">
                <label className="text-xs">
                  <div className="text-[#8B7355] mb-0.5">Axe de travail 1</div>
                  <textarea rows={2} value={axe1}
                            onChange={(e) => setAxe1(e.target.value)}
                            className="w-full border border-[#D4C9A8] rounded px-2 py-1 text-xs" />
                </label>
                <label className="text-xs">
                  <div className="text-[#8B7355] mb-0.5">Axe de travail 2</div>
                  <textarea rows={2} value={axe2}
                            onChange={(e) => setAxe2(e.target.value)}
                            className="w-full border border-[#D4C9A8] rounded px-2 py-1 text-xs" />
                </label>
              </div>
            )}
          </div>
        )
      })}

      <div className="mt-6 bg-[#17494E] text-white rounded-lg p-3 text-xs">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <TotItem label="Salle" v={fiche.tot_salle} dec={1} />
          <TotItem label="Terrain" v={fiche.tot_terrain} dec={1} />
          <TotItem label="Durée" v={fiche.tot_duree} dec={1} />
          <TotItem label="Absent" v={fiche.tot_absent} dec={1} />
          <TotItem label="Présent" v={fiche.tot_present} dec={1} />
          <TotItem label="Obj BS" v={fiche.tot_obj_bs} dec={0} />
          <TotItem label="Total Ctt" v={fiche.tot_ctt} dec={0} />
          <TotItem label="ADF" v={fiche.tot_adf} dec={0} />
          <TotItem label="Presse" v={fiche.tot_presse} dec={0} />
          <TotItem label="ASSU" v={fiche.tot_assu} dec={0} />
          <TotItem label="Coopt" v={fiche.tot_coopt} dec={0} />
        </div>
      </div>
    </div>
  )
}
