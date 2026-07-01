/**
 * Fen_OffresEZY - Suivi SFR > Offres EZY.
 *
 * 2 onglets : 'Liste des offres' (implemente) et 'Import' (a venir).
 *
 * Onglet Liste des offres :
 *   - Toggle Part / Pro (cf glissiere Type_OffresSFR WinDev)
 *   - 2 tableaux cote a cote : Fibres (gauche) / Mobile (droite)
 *   - Colonnes editables : Produit associe (combo) + Online (checkbox)
 *   - Save au blur/change de chaque ligne
 */
import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, ShoppingBag, Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const API_BASE = '/api/adm'

interface Offre {
  id_offres_sfr: string; type: string; lib_offre: string
  debit_down: string; debit_up: string
  prix_offre: number; recurrence: string
  prix_pro_ttc: string; engagement: string
  en_promo: boolean; info_promo: string; service_inclus: string
  id_produit: number; lib_produit: string; online: boolean
}
interface Produit { id_produit: number; lib_produit: string; famille: string }

type Onglet = 'liste' | 'import'
type Famille = 'FIBRE' | 'MOBILE'

export default function SfrOffresEzyPage() {
  useDocumentTitle('Offres EZY')
  const [onglet, setOnglet] = useState<Onglet>('liste')
  const [pro, setPro] = useState(false)
  const [fibres, setFibres] = useState<Offre[]>([])
  const [mobile, setMobile] = useState<Offre[]>([])
  const [prodFib, setProdFib] = useState<Produit[]>([])
  const [prodMob, setProdMob] = useState<Produit[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [f, m] = await Promise.all([
        fetch(`${API_BASE}/suivi-sfr/offres-ezy?cat=FIBRE&pro=${pro}`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        }).then(r => r.ok ? r.json() : []),
        fetch(`${API_BASE}/suivi-sfr/offres-ezy?cat=MOBILE&pro=${pro}`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        }).then(r => r.ok ? r.json() : []),
      ])
      setFibres(f); setMobile(m)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [pro])

  useEffect(() => { void load() }, [load])

  useEffect(() => {
    // Combos produits (chargees 1x)
    Promise.all([
      fetch(`${API_BASE}/suivi-sfr/offres-ezy/produits?famille=FIBRE`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then(r => r.ok ? r.json() : []),
      fetch(`${API_BASE}/suivi-sfr/offres-ezy/produits?famille=MOBILE`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then(r => r.ok ? r.json() : []),
    ]).then(([f, m]: [Produit[], Produit[]]) => {
      setProdFib(f); setProdMob(m)
    })
  }, [])

  const saveOffre = async (o: Offre) => {
    try {
      const r = await fetch(`${API_BASE}/suivi-sfr/offres-ezy/${o.id_offres_sfr}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id_produit: o.id_produit, online: o.online }),
      })
      if (!r.ok) throw new Error(String(r.status))
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const updateOffre = (
    rows: Offre[], setRows: (r: Offre[]) => void,
    id: string, patch: Partial<Offre>,
  ) => {
    setRows(rows.map(o => o.id_offres_sfr === id ? { ...o, ...patch } : o))
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-110px)] text-c-ink">
      <div className="flex items-center gap-2 mb-3">
        <Link to=".." relative="path"
          className="p-1.5 hover:bg-c-surface-soft rounded text-c-ink-faint-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-lg font-bold flex items-center gap-2">
          <ShoppingBag className="w-4 h-4 text-c-brand" /> Offres EZY
        </h1>
      </div>

      {/* Onglets */}
      <div className="flex gap-1 border-b border-c-line mb-3">
        {(['liste', 'import'] as const).map(o => (
          <button key={o} type="button" onClick={() => setOnglet(o)}
            className={`px-4 py-1.5 text-sm font-medium rounded-t ${
              onglet === o
                ? 'bg-white border border-c-line border-b-white text-c-brand'
                : 'text-c-ink-faint hover:bg-c-surface-soft'
            }`}>
            {o === 'liste' ? 'Liste des offres' : 'Import'}
          </button>
        ))}
      </div>

      {onglet === 'import' && (
        <div className="bg-white rounded-xl border border-c-line p-12 text-center text-sm text-c-ink-faint italic">
          Onglet Import : à venir.
        </div>
      )}

      {onglet === 'liste' && (
        <>
          {/* Toggle Part / Pro (glissiere Type_OffresSFR) */}
          <div className="flex items-center gap-3 mb-3 bg-white p-3 rounded-xl border border-c-line text-sm">
            <div className="flex gap-0">
              {([['Offres Part', false], ['Offres PRO', true]] as const).map(([label, val], i) => (
                <button key={label} type="button" onClick={() => setPro(val)}
                  className={`px-4 h-8 text-xs font-medium border border-c-line ${
                    i === 0 ? 'rounded-l' : 'rounded-r'
                  } ${
                    pro === val
                      ? 'bg-c-brand text-white border-c-brand'
                      : 'bg-white text-c-ink-soft hover:bg-c-surface-soft'
                  }`}>
                  {label}
                </button>
              ))}
            </div>
            <div className="flex-1" />
            {loading && <Loader2 className="w-4 h-4 animate-spin text-c-brand" />}
          </div>

          {/* 2 tableaux cote a cote */}
          <div className="flex-1 grid grid-cols-2 gap-3 overflow-hidden">
            <OffreTable label={pro ? 'Offres SFR Fibre Pro' : 'Offres SFR Fibre'}
              rows={fibres} produits={prodFib}
              onChange={(id, patch) => {
                updateOffre(fibres, setFibres, id, patch)
                const cur = fibres.find(o => o.id_offres_sfr === id)
                if (cur) void saveOffre({ ...cur, ...patch })
              }}
            />
            <OffreTable label={pro ? 'Offres SFR Mobile Pro' : 'Offres SFR Mobile'}
              rows={mobile} produits={prodMob}
              onChange={(id, patch) => {
                updateOffre(mobile, setMobile, id, patch)
                const cur = mobile.find(o => o.id_offres_sfr === id)
                if (cur) void saveOffre({ ...cur, ...patch })
              }}
            />
          </div>
        </>
      )}
    </div>
  )
}

function OffreTable({
  label, rows, produits, onChange,
}: {
  label: string
  rows: Offre[]; produits: Produit[]
  onChange: (id: string, patch: Partial<Offre>) => void
}) {
  return (
    <div className="bg-white rounded-xl border border-c-line overflow-hidden flex flex-col">
      <div className="px-3 py-1.5 border-b border-c-line-soft text-xs font-medium text-c-ink-faint flex justify-between">
        <span>{label}</span>
        <span>{rows.length} offre(s)</span>
      </div>
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs">
          <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0">
            <tr>
              <th className="px-2 py-2 text-left">Produit associé</th>
              <th className="px-2 py-2 text-center w-14">Online</th>
              <th className="px-2 py-2 text-left">Lib offre</th>
              <th className="px-2 py-2 text-left">Débit ↓/↑</th>
              <th className="px-2 py-2 text-right">Prix</th>
              <th className="px-2 py-2 text-left">Récurr.</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-c-line-soft">
            {rows.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-12 text-c-ink-faint-2 italic">
                Aucune offre.
              </td></tr>
            ) : rows.map(o => (
              <tr key={o.id_offres_sfr}
                className={o.en_promo ? 'bg-yellow-50 hover:bg-yellow-100'
                                       : 'hover:bg-c-surface-soft'}>
                <td className="px-2 py-1">
                  <select value={o.id_produit || 0}
                    onChange={(e) => onChange(o.id_offres_sfr,
                      { id_produit: parseInt(e.target.value, 10) || 0 })}
                    className="w-full px-1 py-0.5 bg-transparent border border-transparent hover:border-c-line focus:border-c-brand rounded text-xs">
                    <option value={0}>—</option>
                    {produits.map(p => (
                      <option key={p.id_produit} value={p.id_produit}>{p.lib_produit}</option>
                    ))}
                  </select>
                </td>
                <td className="px-2 py-1 text-center">
                  <input type="checkbox" checked={o.online}
                    onChange={(e) => onChange(o.id_offres_sfr, { online: e.target.checked })} />
                </td>
                <td className="px-2 py-1">
                  {o.lib_offre}
                  {o.en_promo && (
                    <span className="ml-1 px-1 py-0.5 rounded bg-orange-100 text-orange-700 text-[9px] uppercase">
                      Promo
                    </span>
                  )}
                </td>
                <td className="px-2 py-1 tabular-nums text-[10px] text-c-ink-soft">
                  {o.debit_down || '—'} / {o.debit_up || '—'}
                </td>
                <td className="px-2 py-1 text-right tabular-nums">
                  {o.prix_offre ? `${o.prix_offre.toFixed(2)} €` : ''}
                </td>
                <td className="px-2 py-1 text-[10px] text-c-ink-soft">{o.recurrence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
