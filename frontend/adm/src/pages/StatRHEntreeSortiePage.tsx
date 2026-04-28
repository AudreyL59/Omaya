import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  ChevronLeft,
  Calendar as CalendarIcon,
  Network,
  Building2,
  Play,
  Loader2,
  AlertCircle,
  X,
} from 'lucide-react'
import { getToken } from '@/api'
import { useAuth } from '@/hooks/useAuth'
import OrgaPicker, { type OrgaItem } from '@/components/OrgaPicker'
import ExportButton from '@/components/ExportButton'
import StatDetailModal from '@/components/StatDetailModal'
import { exportToCSV, csvDate } from '@/utils/csvExport'
import { Eye } from 'lucide-react'

type TabKey = 'resume' | 'dpae' | 'sorties'
type TypeRecherche = 'reseau' | 'orga'

interface DpaeRow {
  id_salarie: string
  id_ste: number
  nom: string
  prenom: string
  adresse: string
  cp: string
  ville: string
  date_entree: string
  en_activite: boolean
  date_sortie: string
  fin_demandee: string
  origine: string
  detail_origine: string
  id_orga: string
  prod: boolean
}

interface SortieRow {
  id_salarie: string
  id_ste: number
  nom: string
  prenom: string
  adresse: string
  cp: string
  ville: string
  date_entree: string
  date_sortie_reelle: string
  fin_demandee: string
  id_type_sortie: number
  type_sortie_lib: string
  id_orga: string
  prod: boolean
}

interface OrgaResumeRow {
  id_orga: string
  lib_orga: string
  lib_parent: string
  id_parent: number
  nb_dpae: number
  nb_sortants_non_prod: number
  nb_jour_non_prod: number
  nb_sortants_prod: number
  nb_jour_prod: number
}

interface StatEntreeSortieResponse {
  dpae: DpaeRow[]
  sorties: SortieRow[]
  resume: OrgaResumeRow[]
}

function toYmd(d: Date): string {
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
}

function formatShortDate(raw: string): string {
  if (!raw) return ''
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (iso) return `${iso[3]}/${iso[2]}/${iso[1]}`
  if (raw.length >= 8 && /^\d+$/.test(raw.slice(0, 8))) {
    return `${raw.slice(6, 8)}/${raw.slice(4, 6)}/${raw.slice(0, 4)}`
  }
  return raw
}

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

export default function StatRHEntreeSortiePage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const hasDroitGr = (user?.droits || []).includes('StatsRHGr')

  const today = toYmd(new Date())
  const [typeRecherche, setTypeRecherche] = useState<TypeRecherche>('reseau')
  const [dateDu, setDateDu] = useState<string>(today)
  const [dateAu, setDateAu] = useState<string>(today)
  const [tab, setTab] = useState<TabKey>('resume')
  const [selectedOrgas, setSelectedOrgas] = useState<OrgaItem[]>([])
  const [showPicker, setShowPicker] = useState(false)

  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<StatEntreeSortieResponse | null>(null)
  const [error, setError] = useState<string>('')
  const [detail, setDetail] = useState<{ title: string; orgaIds: string[] } | null>(null)

  const labelOrga =
    selectedOrgas.length === 0
      ? "Un bloc d'orga ..."
      : selectedOrgas.length === 1
        ? selectedOrgas[0].lib_orga
        : `${selectedOrgas.length} blocs`

  const onToggleType = (v: TypeRecherche) => {
    if (v === 'reseau') {
      setTypeRecherche('reseau')
      setSelectedOrgas([])
    } else {
      setShowPicker(true)
    }
  }

  const removeOrga = (id: string) => {
    const next = selectedOrgas.filter((o) => o.id_orga !== id)
    setSelectedOrgas(next)
    if (next.length === 0) setTypeRecherche('reseau')
  }

  const runCalcul = () => {
    setError('')
    setLoading(true)
    const params = new URLSearchParams()
    params.set('date_du', dateDu)
    params.set('date_au', dateAu)
    params.set('type_recherche', typeRecherche)
    if (typeRecherche === 'orga') {
      for (const o of selectedOrgas) {
        params.append('id_orga', String(o.id_orga))
      }
    }
    fetch(`/api/adm/stat-rh/entree-sortie?${params.toString()}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Erreur API (${r.status})`)
        return r.json()
      })
      .then((res: StatEntreeSortieResponse) => setData(res))
      .catch((e) => setError(e.message || 'Erreur'))
      .finally(() => setLoading(false))
  }

  return (
    <div className="p-8">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <button
          onClick={() => navigate('/stat-rh')}
          className="flex items-center gap-1.5 text-sm text-[#A68D8A] hover:text-[#4E1D17] mb-3"
        >
          <ChevronLeft className="w-4 h-4" />
          Retour Stats RH
        </button>
        <h1 className="text-2xl font-bold text-[#4E1D17]">Stats DPAE / Sortie</h1>
        <p className="text-[#A68D8A] mt-1">
          Entrees et sorties par agence/equipe sur la periode.
        </p>
      </motion.div>

      {/* Filtres */}
      <div className="bg-white rounded-[10px] border border-[#E5DDDC] p-4 mt-6 flex flex-wrap items-center gap-3">
        {hasDroitGr && (
          <Toggle
            value={typeRecherche}
            options={[
              { v: 'reseau', label: 'Reseau complet', icon: <Network className="w-3.5 h-3.5" /> },
              { v: 'orga', label: labelOrga, icon: <Building2 className="w-3.5 h-3.5" /> },
            ]}
            onChange={(v) => onToggleType(v as TypeRecherche)}
          />
        )}

        <div className="h-6 w-px bg-[#E5DDDC]" />

        <DateField label="Du" value={dateDu} onChange={setDateDu} />
        <DateField label="Au" value={dateAu} onChange={setDateAu} />

        <div className="flex-1" />

        <button
          onClick={runCalcul}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-[#17494E] text-white rounded-lg text-sm font-medium hover:bg-[#17494E]/90 disabled:opacity-50 shadow-sm"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          Demarrer le calcul
        </button>
      </div>

      {/* Chips de la selection multi-orga */}
      {typeRecherche === 'orga' && selectedOrgas.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] uppercase tracking-wide text-[#A68D8A] font-semibold mr-1">
            Blocs :
          </span>
          {selectedOrgas.map((o) => (
            <span
              key={o.id_orga}
              className="inline-flex items-center gap-1 bg-white border border-[#E5DDDC] rounded-full px-2.5 py-1 text-xs"
            >
              <Building2 className="w-3 h-3 text-[#A68D8A]/80" />
              {o.lib_orga}
              <button
                onClick={() => removeOrga(o.id_orga)}
                className="text-[#A68D8A]/80 hover:text-[#4E1D17]"
                title="Retirer"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
          <button
            onClick={() => setShowPicker(true)}
            className="text-xs text-[#A68D8A] hover:text-[#4E1D17] px-2 py-0.5 rounded-full border border-dashed border-[#E5DDDC] hover:border-[#A68D8A]"
          >
            + Modifier
          </button>
        </div>
      )}

      {/* Erreur */}
      {error && (
        <div className="mt-3 flex items-center gap-2 bg-red-50 border border-red-200 text-[#993636] px-4 py-2.5 rounded-lg text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Onglets */}
      <div className="mt-4 border-b border-[#E5DDDC] flex gap-1">
        <TabButton active={tab === 'resume'} onClick={() => setTab('resume')} label="Resume" />
        <TabButton active={tab === 'dpae'} onClick={() => setTab('dpae')} label={`DPAE${data ? ` (${data.dpae.length})` : ''}`} />
        <TabButton active={tab === 'sorties'} onClick={() => setTab('sorties')} label={`Sorties${data ? ` (${data.sorties.length})` : ''}`} />
      </div>

      {/* Contenu onglets */}
      <div className="mt-4">
        <AnimatePresence mode="wait">
          {tab === 'resume' && (
            <motion.div key="resume" initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }}>
              <ResumeTable
                rows={data?.resume || []}
                loading={loading}
                onDetailEquipe={(r) =>
                  setDetail({
                    title: r.lib_orga,
                    orgaIds: [r.id_orga],
                  })
                }
                onDetailAgence={(agence, equipes) =>
                  setDetail({
                    title: `${agence}`,
                    orgaIds: equipes.map((e) => e.id_orga),
                  })
                }
                onDetailTotal={() =>
                  setDetail({
                    title: 'Total',
                    orgaIds: (data?.resume || []).map((r) => r.id_orga),
                  })
                }
              />
            </motion.div>
          )}
          {tab === 'dpae' && (
            <motion.div key="dpae" initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }}>
              <DpaeTable rows={data?.dpae || []} loading={loading} />
            </motion.div>
          )}
          {tab === 'sorties' && (
            <motion.div key="sorties" initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -5 }}>
              <SortieTable rows={data?.sorties || []} loading={loading} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {showPicker && (
          <OrgaPicker
            initialSelected={selectedOrgas}
            onClose={() => setShowPicker(false)}
            onSelect={(orgas) => {
              setSelectedOrgas(orgas)
              setTypeRecherche(orgas.length > 0 ? 'orga' : 'reseau')
              setShowPicker(false)
            }}
          />
        )}
        {detail && data && (
          <StatDetailModal
            title={detail.title}
            orgaIds={detail.orgaIds}
            dpaeRows={data.dpae}
            sortieRows={data.sorties}
            onClose={() => setDetail(null)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// --- Sous-composants -----------------------------------------------------

function Toggle<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: { v: T; label: string; icon?: React.ReactNode }[]
  onChange: (v: T) => void
}) {
  return (
    <div className="inline-flex bg-[#EFE9E7] rounded-lg p-0.5">
      {options.map((o) => (
        <button
          key={o.v}
          onClick={() => onChange(o.v)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            value === o.v ? 'bg-white text-[#17494E] shadow-sm' : 'text-[#A68D8A] hover:text-[#4E1D17]'
          }`}
        >
          {o.icon}
          {o.label}
        </button>
      ))}
    </div>
  )
}

function DateField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const inputValue = value.length === 8
    ? `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`
    : value
  return (
    <label className="flex items-center gap-2 px-3 py-1.5 border border-[#E5DDDC] rounded-lg text-sm">
      <CalendarIcon className="w-4 h-4 text-[#A68D8A]/80" />
      <span className="text-[#A68D8A]">{label}</span>
      <input
        type="date"
        value={inputValue}
        onChange={(e) => onChange(e.target.value.replace(/-/g, ''))}
        className="outline-none bg-transparent font-medium text-[#4E1D17] w-32"
      />
    </label>
  )
}

function DetailIconButton({
  title,
  onClick,
}: {
  title: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="p-1.5 rounded-md text-[#A68D8A]/80 hover:text-[#4E1D17] hover:bg-white border border-transparent hover:border-[#E5DDDC] transition-colors"
    >
      <Eye className="w-3.5 h-3.5" />
    </button>
  )
}

function TabButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
        active ? 'border-[#17494E] text-[#4E1D17]' : 'border-transparent text-[#A68D8A] hover:text-[#4E1D17]'
      }`}
    >
      {label}
    </button>
  )
}

function ResumeTable({
  rows,
  loading,
  onDetailEquipe,
  onDetailAgence,
  onDetailTotal,
}: {
  rows: OrgaResumeRow[]
  loading: boolean
  onDetailEquipe: (r: OrgaResumeRow) => void
  onDetailAgence: (agence: string, equipes: OrgaResumeRow[]) => void
  onDetailTotal: () => void
}) {
  if (loading) return <TableLoader />
  if (rows.length === 0) return <EmptyState label="Pas de donnees. Demarre le calcul." />

  // Grouper par agence parent
  const groups = new Map<string, OrgaResumeRow[]>()
  for (const r of rows) {
    const key = r.lib_parent || 'Sans parent'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(r)
  }

  const total = rows.reduce(
    (acc, r) => ({
      dpae: acc.dpae + r.nb_dpae,
      nonProd: acc.nonProd + r.nb_sortants_non_prod,
      jourNonProd: acc.jourNonProd + r.nb_jour_non_prod,
      prod: acc.prod + r.nb_sortants_prod,
      jourProd: acc.jourProd + r.nb_jour_prod,
    }),
    { dpae: 0, nonProd: 0, jourNonProd: 0, prod: 0, jourProd: 0 }
  )

  const moy = (num: number, den: number) => (den > 0 ? (num / den).toFixed(1) : '0.0')

  // Classes des 2 groupes : cadre visuel + tonalite
  const grpNonProd = 'bg-orange-50/60 border-l border-orange-200'
  const grpNonProdLast = 'bg-orange-50/60 border-r border-orange-200'
  const grpProd = 'bg-[#17494E]/5 border-l border-[#17494E]/25'
  const grpProdLast = 'bg-[#17494E]/5 border-r border-[#17494E]/25'

  const handleExport = () => {
    const rowsCsv: (string | number)[][] = []
    for (const [agence, equipes] of groups.entries()) {
      const sub = equipes.reduce(
        (acc, r) => ({
          dpae: acc.dpae + r.nb_dpae,
          nonProd: acc.nonProd + r.nb_sortants_non_prod,
          jourNonProd: acc.jourNonProd + r.nb_jour_non_prod,
          prod: acc.prod + r.nb_sortants_prod,
          jourProd: acc.jourProd + r.nb_jour_prod,
        }),
        { dpae: 0, nonProd: 0, jourNonProd: 0, prod: 0, jourProd: 0 }
      )
      rowsCsv.push([agence, '', '', '', '', ''])
      for (const r of equipes) {
        rowsCsv.push([
          r.lib_orga,
          r.nb_dpae,
          r.nb_sortants_non_prod,
          moy(r.nb_jour_non_prod, r.nb_sortants_non_prod),
          r.nb_sortants_prod,
          moy(r.nb_jour_prod, r.nb_sortants_prod),
        ])
      }
      rowsCsv.push([
        `Sous-total ${agence}`,
        sub.dpae,
        sub.nonProd,
        moy(sub.jourNonProd, sub.nonProd),
        sub.prod,
        moy(sub.jourProd, sub.prod),
      ])
    }
    rowsCsv.push([
      'TOTAL',
      total.dpae,
      total.nonProd,
      moy(total.jourNonProd, total.nonProd),
      total.prod,
      moy(total.jourProd, total.prod),
    ])
    exportToCSV(
      'stats-entree-sortie-resume',
      ['Equipe', 'DPAE', 'Sortants non Prod (Nb)', 'Non Prod (Moy j)', 'Sortants Prod (Nb)', 'Prod (Moy j)'],
      rowsCsv,
    )
  }

  return (
    <div className="bg-white rounded-[10px] border border-[#E5DDDC] overflow-hidden">
      <div className="px-4 py-2 bg-white border-b border-[#E5DDDC] flex items-center justify-end">
        <ExportButton onClick={handleExport} />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-white border-b border-[#E5DDDC]">
            {/* Rangee 1 : groupes */}
            <tr>
              <th rowSpan={2} className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase align-bottom">Equipe</th>
              <th rowSpan={2} className="text-right py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase align-bottom">DPAE</th>
              <th colSpan={2} className={`text-center py-2 px-3 text-xs font-semibold text-orange-700 uppercase ${grpNonProd} ${grpNonProdLast.replace('bg-orange-50/60 border-l border-orange-200', 'border-r border-orange-200')}`}>
                Sortants non Prod
              </th>
              <th colSpan={2} className={`text-center py-2 px-3 text-xs font-semibold text-[#17494E] uppercase ${grpProd} ${grpProdLast.replace('bg-[#17494E]/5 border-l border-[#17494E]/25', 'border-r border-[#17494E]/25')}`}>
                Sortants Prod
              </th>
              <th rowSpan={2} className="py-2 px-2 text-xs font-medium text-[#A68D8A] uppercase align-bottom w-12 text-center">Detail</th>
            </tr>
            {/* Rangee 2 : sous-colonnes */}
            <tr>
              <th className={`text-right py-1.5 px-3 text-[10px] font-medium text-orange-600 uppercase ${grpNonProd}`}>Nb</th>
              <th className={`text-right py-1.5 px-3 text-[10px] font-medium text-orange-600 uppercase ${grpNonProdLast}`}>Moy j</th>
              <th className={`text-right py-1.5 px-3 text-[10px] font-medium text-[#17494E] uppercase ${grpProd}`}>Nb</th>
              <th className={`text-right py-1.5 px-3 text-[10px] font-medium text-[#17494E] uppercase ${grpProdLast}`}>Moy j</th>
            </tr>
          </thead>
          <tbody>
            {[...groups.entries()].map(([agence, equipes]) => {
              // Sous-total du groupe
              const sub = equipes.reduce(
                (acc, r) => ({
                  dpae: acc.dpae + r.nb_dpae,
                  nonProd: acc.nonProd + r.nb_sortants_non_prod,
                  jourNonProd: acc.jourNonProd + r.nb_jour_non_prod,
                  prod: acc.prod + r.nb_sortants_prod,
                  jourProd: acc.jourProd + r.nb_jour_prod,
                }),
                { dpae: 0, nonProd: 0, jourNonProd: 0, prod: 0, jourProd: 0 }
              )

              return (
                <>
                  <tr key={`h-${agence}`} className="bg-[#EFE9E7]">
                    <td colSpan={6} className="py-1.5 px-3 text-xs font-semibold text-[#4E1D17] uppercase tracking-wide">
                      {agence}
                    </td>
                    <td className="py-1 px-2 text-center">
                      <DetailIconButton
                        title={`Detail ${agence}`}
                        onClick={() => onDetailAgence(agence, equipes)}
                      />
                    </td>
                  </tr>
                  {equipes.map((r) => (
                    <tr key={r.id_orga} className="border-b border-[#E5DDDC] last:border-0 hover:bg-[#EFE9E7]">
                      <td className="py-2 px-3 font-medium text-[#4E1D17]">{r.lib_orga}</td>
                      <td className="py-2 px-3 text-right tabular-nums">{r.nb_dpae}</td>
                      <td className={`py-2 px-3 text-right tabular-nums ${grpNonProd}`}>{r.nb_sortants_non_prod}</td>
                      <td className={`py-2 px-3 text-right tabular-nums text-[#A68D8A] ${grpNonProdLast}`}>{moy(r.nb_jour_non_prod, r.nb_sortants_non_prod)}</td>
                      <td className={`py-2 px-3 text-right tabular-nums ${grpProd}`}>{r.nb_sortants_prod}</td>
                      <td className={`py-2 px-3 text-right tabular-nums text-[#A68D8A] ${grpProdLast}`}>{moy(r.nb_jour_prod, r.nb_sortants_prod)}</td>
                      <td className="py-1 px-2 text-center">
                        <DetailIconButton
                          title={`Detail ${r.lib_orga}`}
                          onClick={() => onDetailEquipe(r)}
                        />
                      </td>
                    </tr>
                  ))}
                  {/* Sous-total du bloc */}
                  <tr key={`sub-${agence}`} className="bg-white border-y border-[#E5DDDC] font-medium">
                    <td className="py-2 px-3 text-right text-[11px] text-[#A68D8A] uppercase tracking-wide italic">
                      Sous-total
                    </td>
                    <td className="py-2 px-3 text-right tabular-nums text-[#4E1D17]">{sub.dpae}</td>
                    <td className={`py-2 px-3 text-right tabular-nums text-[#4E1D17] ${grpNonProd}`}>{sub.nonProd}</td>
                    <td className={`py-2 px-3 text-right tabular-nums text-[#4E1D17]/80 ${grpNonProdLast}`}>{moy(sub.jourNonProd, sub.nonProd)}</td>
                    <td className={`py-2 px-3 text-right tabular-nums text-[#4E1D17] ${grpProd}`}>{sub.prod}</td>
                    <td className={`py-2 px-3 text-right tabular-nums text-[#4E1D17]/80 ${grpProdLast}`}>{moy(sub.jourProd, sub.prod)}</td>
                    <td />
                  </tr>
                </>
              )
            })}
            <tr className="bg-white font-semibold border-t-2 border-[#E5DDDC]">
              <td className="py-2 px-3 text-[#4E1D17]">TOTAL</td>
              <td className="py-2 px-3 text-right tabular-nums">{total.dpae}</td>
              <td className={`py-2 px-3 text-right tabular-nums ${grpNonProd}`}>{total.nonProd}</td>
              <td className={`py-2 px-3 text-right tabular-nums text-[#4E1D17]/80 ${grpNonProdLast}`}>{moy(total.jourNonProd, total.nonProd)}</td>
              <td className={`py-2 px-3 text-right tabular-nums ${grpProd}`}>{total.prod}</td>
              <td className={`py-2 px-3 text-right tabular-nums text-[#4E1D17]/80 ${grpProdLast}`}>{moy(total.jourProd, total.prod)}</td>
              <td className="py-1 px-2 text-center">
                <DetailIconButton title="Detail Total" onClick={onDetailTotal} />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

function DpaeTable({ rows, loading }: { rows: DpaeRow[]; loading: boolean }) {
  if (loading) return <TableLoader />
  if (rows.length === 0) return <EmptyState label="Pas de DPAE sur cette periode." />

  const handleExport = () => {
    exportToCSV(
      'stats-entree-sortie-dpae',
      ['Entite', 'Nom', 'Prenom', 'Adresse', 'CP', 'Ville', "Date d'entree", 'Actif', 'Date Sortie', 'Fin demandee'],
      rows.map((r) => [
        r.id_ste || '',
        r.nom,
        capitalize(r.prenom),
        r.adresse,
        r.cp,
        r.ville,
        csvDate(r.date_entree),
        r.en_activite,
        csvDate(r.date_sortie),
        csvDate(r.fin_demandee),
      ]),
    )
  }

  return (
    <div className="bg-white rounded-[10px] border border-[#E5DDDC] overflow-hidden">
      <div className="px-4 py-2 bg-white border-b border-[#E5DDDC] flex items-center justify-end">
        <ExportButton onClick={handleExport} />
      </div>
      <div className="overflow-x-auto max-h-[calc(100vh-400px)] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-white border-b border-[#E5DDDC] sticky top-0">
            <tr>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Entite</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Nom</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Prenom</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Adresse</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">CP</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Ville</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Date d'entree</th>
              <th className="text-center py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Actif</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Date Sortie</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Fin demandee</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id_salarie} className="border-b border-[#E5DDDC] last:border-0 hover:bg-[#EFE9E7]">
                <td className="py-2 px-3 text-[#4E1D17]/80">{r.id_ste || '—'}</td>
                <td className="py-2 px-3 font-medium text-[#4E1D17]">{r.nom}</td>
                <td className="py-2 px-3 text-[#4E1D17]">{capitalize(r.prenom)}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80 truncate max-w-xs">{r.adresse}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{r.cp}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{r.ville}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{formatShortDate(r.date_entree)}</td>
                <td className="py-2 px-3 text-center">
                  <input type="checkbox" checked={r.en_activite} readOnly className="accent-gray-900" />
                </td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{formatShortDate(r.date_sortie)}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{formatShortDate(r.fin_demandee)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SortieTable({ rows, loading }: { rows: SortieRow[]; loading: boolean }) {
  if (loading) return <TableLoader />
  if (rows.length === 0) return <EmptyState label="Pas de sortie sur cette periode." />

  const handleExport = () => {
    exportToCSV(
      'stats-entree-sortie-sorties',
      ['Entite', 'Nom', 'Prenom', 'Adresse', 'CP', 'Ville', 'Date entree', 'Date sortie', 'Fin demandee', 'Type sortie'],
      rows.map((r) => [
        r.id_ste || '',
        r.nom,
        capitalize(r.prenom),
        r.adresse,
        r.cp,
        r.ville,
        csvDate(r.date_entree),
        csvDate(r.date_sortie_reelle),
        csvDate(r.fin_demandee),
        r.type_sortie_lib || r.id_type_sortie || '',
      ]),
    )
  }

  return (
    <div className="bg-white rounded-[10px] border border-[#E5DDDC] overflow-hidden">
      <div className="px-4 py-2 bg-white border-b border-[#E5DDDC] flex items-center justify-end">
        <ExportButton onClick={handleExport} />
      </div>
      <div className="overflow-x-auto max-h-[calc(100vh-400px)] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-white border-b border-[#E5DDDC] sticky top-0">
            <tr>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Entite</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Nom</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Prenom</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Adresse</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">CP</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Ville</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Date entree</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Date sortie</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Fin demandee</th>
              <th className="text-left py-2 px-3 text-xs font-medium text-[#A68D8A] uppercase">Type sortie</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id_salarie} className="border-b border-[#E5DDDC] last:border-0 hover:bg-[#EFE9E7]">
                <td className="py-2 px-3 text-[#4E1D17]/80">{r.id_ste || '—'}</td>
                <td className="py-2 px-3 font-medium text-[#4E1D17]">{r.nom}</td>
                <td className="py-2 px-3 text-[#4E1D17]">{capitalize(r.prenom)}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80 truncate max-w-xs">{r.adresse}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{r.cp}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{r.ville}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{formatShortDate(r.date_entree)}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{formatShortDate(r.date_sortie_reelle)}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{formatShortDate(r.fin_demandee)}</td>
                <td className="py-2 px-3 text-[#4E1D17]/80">{r.type_sortie_lib || r.id_type_sortie || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function TableLoader() {
  return (
    <div className="flex items-center justify-center py-20 bg-white rounded-[10px] border border-[#E5DDDC]">
      <Loader2 className="w-6 h-6 text-[#E5DDDC] animate-spin" />
    </div>
  )
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="text-center py-20 text-[#A68D8A]/80 text-sm italic bg-white rounded-[10px] border border-[#E5DDDC]">
      {label}
    </div>
  )
}
