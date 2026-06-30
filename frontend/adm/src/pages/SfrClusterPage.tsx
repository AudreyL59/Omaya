/**
 * Fen_SFRCluster - Suivi SFR > Cluster.
 *
 * 2 tableaux côte à côte :
 *   - Gauche : liste des clusters SFR (Région, Code VAD, Nom, Mail BO)
 *     éditable inline (au blur d'une cellule -> PUT).
 *   - Droite : périodes du cluster sélectionné (Du, Au, Objectif) éditable.
 *
 * Boutons :
 *   - Nouveau Cluster : crée une ligne vide à éditer
 *   - Supprimer le cluster : soft-delete + retrait de la liste
 *   - Ajouter la période : formulaire à droite (Du, Au, Objectif)
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Plus, Trash2, ArrowLeft, MapPin, Loader2, Save,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const API_BASE = '/api/adm'

interface Cluster {
  id_sfr_cluster: string; region: string
  code_vad: string; nom_cluster: string; mail_bo: string
}
interface Periode {
  id_sfr_cluster_periode: string; id_sfr_cluster: string
  du: string; au: string; objectif_vv: number
}

const todayIso = (): string => new Date().toISOString().slice(0, 10)

export default function SfrClusterPage() {
  useDocumentTitle('Cluster SFR')
  const [clusters, setClusters] = useState<Cluster[]>([])
  const [selected, setSelected] = useState<string>('')
  const [periodes, setPeriodes] = useState<Periode[]>([])
  const [loading, setLoading] = useState(false)
  const [savingId, setSavingId] = useState('')
  const [newDu, setNewDu] = useState(todayIso())
  const [newAu, setNewAu] = useState(todayIso())
  const [newObj, setNewObj] = useState(0)

  const loadClusters = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/suivi-sfr/clusters`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const d: Cluster[] = await r.json()
      setClusters(d)
      if (!selected && d.length > 0) setSelected(d[0].id_sfr_cluster)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [selected])

  const loadPeriodes = useCallback(async (id: string) => {
    setPeriodes([])   // reset avant tout fetch pour eviter le "fantome"
    if (!id) return
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/clusters/${id}/periodes`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      setPeriodes(await r.json())
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }, [])

  useEffect(() => { void loadClusters() }, [loadClusters])
  useEffect(() => { void loadPeriodes(selected) }, [selected, loadPeriodes])

  const saveCluster = async (c: Cluster) => {
    setSavingId(c.id_sfr_cluster)
    try {
      const r = await fetch(`${API_BASE}/suivi-sfr/clusters/${c.id_sfr_cluster}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          region: c.region, code_vad: c.code_vad,
          nom_cluster: c.nom_cluster, mail_bo: c.mail_bo,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setSavingId('') }
  }

  const savePeriode = async (p: Periode) => {
    setSavingId(p.id_sfr_cluster_periode)
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/cluster-periodes/${p.id_sfr_cluster_periode}`, {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id_sfr_cluster: parseInt(p.id_sfr_cluster, 10),
            du: p.du, au: p.au, objectif_vv: p.objectif_vv,
          }),
        })
      if (!r.ok) throw new Error(String(r.status))
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setSavingId('') }
  }

  const handleNouveauCluster = async () => {
    try {
      const r = await fetch(`${API_BASE}/suivi-sfr/clusters`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          region: '', code_vad: '', nom_cluster: 'Nouveau cluster', mail_bo: '',
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d: { id_sfr_cluster: string } = await r.json()
      await loadClusters()
      setSelected(d.id_sfr_cluster)
      showToast('Cluster créé', 'success')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const handleSupprimerCluster = async () => {
    if (!selected) return
    const ok = await showConfirm({
      title: 'Supprimer ce cluster',
      message: 'Êtes-vous sûr de vouloir supprimer ce cluster ?',
    })
    if (!ok) return
    try {
      const r = await fetch(`${API_BASE}/suivi-sfr/clusters/${selected}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      setSelected('')
      await loadClusters()
      showToast('Cluster supprimé', 'success')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const handleAjouterPeriode = async () => {
    if (!selected) {
      showToast('Sélectionne d\'abord un cluster.', 'info'); return
    }
    if (newDu > newAu) {
      showToast('Dates incohérentes.', 'error'); return
    }
    try {
      const r = await fetch(`${API_BASE}/suivi-sfr/cluster-periodes`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_sfr_cluster: parseInt(selected, 10),
          du: newDu, au: newAu, objectif_vv: newObj,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Période ajoutée', 'success')
      setNewObj(0)
      await loadPeriodes(selected)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const handleDeletePeriode = async (id: string) => {
    const ok = await showConfirm({
      title: 'Supprimer cette période',
      message: 'Confirmer ?',
    })
    if (!ok) return
    try {
      const r = await fetch(`${API_BASE}/suivi-sfr/cluster-periodes/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      await loadPeriodes(selected)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const updateClusterCell = (id: string, field: keyof Cluster, value: string) => {
    setClusters(prev => prev.map(c =>
      c.id_sfr_cluster === id ? { ...c, [field]: value } : c))
  }
  const updatePeriodeCell = (id: string, field: keyof Periode, value: string | number) => {
    setPeriodes(prev => prev.map(p =>
      p.id_sfr_cluster_periode === id ? { ...p, [field]: value } : p))
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-110px)] text-c-ink">
      <div className="flex items-center gap-2 mb-3">
        <Link to=".." relative="path"
          className="p-1.5 hover:bg-c-surface-soft rounded text-c-ink-faint-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-lg font-bold flex items-center gap-2">
          <MapPin className="w-4 h-4 text-c-brand" /> Cluster SFR
        </h1>
      </div>

      <div className="flex items-center gap-2 mb-3 bg-white p-3 rounded-xl border border-c-line text-sm flex-wrap">
        <button type="button" onClick={handleNouveauCluster}
          className="flex items-center gap-2 px-3 py-1.5 rounded text-c-brand hover:bg-c-brand/10 text-xs">
          <Plus className="w-4 h-4" /> Nouveau Cluster
        </button>
        <button type="button" onClick={handleSupprimerCluster}
          disabled={!selected}
          className="flex items-center gap-2 px-3 py-1.5 rounded text-red-600 hover:bg-red-50 disabled:opacity-30 text-xs">
          <Trash2 className="w-4 h-4" /> Supprimer le cluster
        </button>
        <div className="flex-1" />
        <span className="text-xs text-c-ink-faint">{clusters.length} cluster(s)</span>
      </div>

      <div className="flex-1 grid grid-cols-2 gap-3 overflow-hidden">
        {/* Tableau clusters */}
        <div className="bg-white rounded-xl border border-c-line overflow-hidden flex flex-col">
          <div className="px-3 py-1.5 border-b border-c-line-soft text-xs font-medium text-c-ink-faint">
            Clusters
          </div>
          <div className="flex-1 overflow-auto">
            {loading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-5 h-5 animate-spin text-c-brand" />
              </div>
            ) : (
              <table className="w-full text-xs">
                <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0">
                  <tr>
                    <th className="px-2 py-2 text-left">Région</th>
                    <th className="px-2 py-2 text-left">Code</th>
                    <th className="px-2 py-2 text-left">Cluster</th>
                    <th className="px-2 py-2 text-left">Mail BO</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-c-line-soft">
                  {clusters.map(c => {
                    const sel = c.id_sfr_cluster === selected
                    return (
                      <tr key={c.id_sfr_cluster}
                        onClick={() => setSelected(c.id_sfr_cluster)}
                        className={`cursor-pointer hover:bg-c-surface-soft ${sel ? 'bg-c-brand/10' : ''}`}>
                        {(['region', 'code_vad', 'nom_cluster', 'mail_bo'] as const).map(f => (
                          <td key={f} className="px-2 py-1">
                            <input type="text" value={c[f] ?? ''}
                              onChange={(e) => updateClusterCell(c.id_sfr_cluster, f, e.target.value)}
                              onBlur={() => saveCluster(c)}
                              onClick={(e) => e.stopPropagation()}
                              className="w-full px-1 py-0.5 bg-transparent border border-transparent hover:border-c-line focus:border-c-brand rounded text-xs" />
                          </td>
                        ))}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Tableau périodes + formulaire ajout */}
        <div className="bg-white rounded-xl border border-c-line overflow-hidden flex flex-col">
          {(() => {
            const c = clusters.find(x => x.id_sfr_cluster === selected)
            return (
              <div className="px-3 py-2 border-b border-c-line-soft bg-c-brand/5">
                <div className="text-[10px] uppercase tracking-wide text-c-ink-faint">
                  Périodes du cluster
                </div>
                {c ? (
                  <div className="flex items-center gap-3 mt-1 text-xs flex-wrap">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-c-brand" />
                      <span className="font-semibold text-c-ink">
                        {c.nom_cluster || '(sans nom)'}
                      </span>
                    </span>
                    {c.code_vad && (
                      <span className="px-1.5 py-0.5 rounded bg-white border border-c-line text-c-ink-soft tabular-nums">
                        {c.code_vad}
                      </span>
                    )}
                    {c.region && (
                      <span className="text-c-ink-soft">
                        Région : <span className="text-c-ink">{c.region}</span>
                      </span>
                    )}
                    {c.mail_bo && (
                      <span className="text-c-ink-soft truncate">
                        Mail BO : <span className="text-c-ink">{c.mail_bo}</span>
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="text-xs italic text-c-ink-faint mt-1">
                    Aucun cluster sélectionné
                  </div>
                )}
              </div>
            )
          })()}
          <div className="flex-1 overflow-auto">
            <table className="w-full text-xs">
              <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0">
                <tr>
                  <th className="px-2 py-2 text-left">Du</th>
                  <th className="px-2 py-2 text-left">Au</th>
                  <th className="px-2 py-2 text-right">Objectif</th>
                  <th className="px-2 py-2 w-8"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-c-line-soft">
                {!selected ? (
                  <tr>
                    <td colSpan={4} className="text-center py-12 text-c-ink-faint-2 italic">
                      Sélectionne un cluster.
                    </td>
                  </tr>
                ) : periodes.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center py-12 text-c-ink-faint-2 italic">
                      Aucune période.
                    </td>
                  </tr>
                ) : periodes.map(p => (
                  <tr key={p.id_sfr_cluster_periode}>
                    <td className="px-2 py-1">
                      <input type="date" value={p.du?.slice(0, 10) ?? ''}
                        onChange={(e) => updatePeriodeCell(p.id_sfr_cluster_periode, 'du', e.target.value)}
                        onBlur={() => savePeriode(p)}
                        className="w-full px-1 py-0.5 bg-transparent border border-transparent hover:border-c-line focus:border-c-brand rounded text-xs" />
                    </td>
                    <td className="px-2 py-1">
                      <input type="date" value={p.au?.slice(0, 10) ?? ''}
                        onChange={(e) => updatePeriodeCell(p.id_sfr_cluster_periode, 'au', e.target.value)}
                        onBlur={() => savePeriode(p)}
                        className="w-full px-1 py-0.5 bg-transparent border border-transparent hover:border-c-line focus:border-c-brand rounded text-xs" />
                    </td>
                    <td className="px-2 py-1">
                      <input type="number" value={p.objectif_vv || 0}
                        onChange={(e) => updatePeriodeCell(p.id_sfr_cluster_periode, 'objectif_vv', parseInt(e.target.value, 10) || 0)}
                        onBlur={() => savePeriode(p)}
                        className="w-full px-1 py-0.5 bg-transparent border border-transparent hover:border-c-line focus:border-c-brand rounded text-xs text-right" />
                    </td>
                    <td className="px-1 py-1 text-center">
                      <button onClick={() => handleDeletePeriode(p.id_sfr_cluster_periode)}
                        className="p-1 text-red-600 hover:bg-red-50 rounded">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Formulaire ajout periode */}
          {selected && (
            <div className="border-t border-c-line bg-c-surface-soft p-3 grid grid-cols-2 gap-2 text-xs">
              <div>
                <label className="text-[10px] text-c-ink-faint">Du</label>
                <input type="date" value={newDu} onChange={e => setNewDu(e.target.value)}
                  className="w-full px-2 py-1 border border-c-line rounded text-xs h-7" />
              </div>
              <div>
                <label className="text-[10px] text-c-ink-faint">Au</label>
                <input type="date" value={newAu} onChange={e => setNewAu(e.target.value)}
                  className="w-full px-2 py-1 border border-c-line rounded text-xs h-7" />
              </div>
              <div>
                <label className="text-[10px] text-c-ink-faint">Objectif</label>
                <input type="number" value={newObj || ''}
                  onChange={e => setNewObj(parseInt(e.target.value, 10) || 0)}
                  className="w-full px-2 py-1 border border-c-line rounded text-xs h-7 text-right" />
              </div>
              <button type="button" onClick={handleAjouterPeriode}
                className="self-end flex items-center justify-center gap-1.5 px-3 bg-c-brand text-white rounded text-xs h-7 font-medium hover:opacity-90">
                <Save className="w-3.5 h-3.5" /> Ajouter la période
              </button>
            </div>
          )}
        </div>
      </div>

      {savingId && (
        <div className="fixed bottom-4 right-4 bg-c-brand text-white px-3 py-1.5 rounded shadow text-xs flex items-center gap-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          Enregistrement…
        </div>
      )}
    </div>
  )
}
