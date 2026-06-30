/**
 * Fen_RemInterneSFR - Suivi SFR > Rémunérations.
 *
 * 2 onglets Fibre / Mobile. Chaque onglet :
 *   - Tableau des rémunérations (avec lib produit, dates, montants)
 *   - 4 boutons d'action en haut : Ajouter / Éditer / Dupliquer / Supprimer
 *   - Formulaire à droite pour saisir/éditer (Produit, Type Vente, Dates,
 *     Montants Va/Va Remise/Ra/Ra Remise + Prime Volumique/Abonnement TV
 *     uniquement pour Fibre + Répartition Rem)
 *   - Bouton Enregistrer en bas du formulaire
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Plus, Pencil, Copy, Trash2, Save, Loader2, ArrowLeft, Euro,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const API_BASE = '/api/adm'

type Categorie = 'FIBRE' | 'MOBILE'

interface RemunItem {
  id_sfr_remun: string; categorie: string
  id_produit: number; lib_produit: string
  type_vente: number
  date_debut: string; date_fin: string
  montant_va: number; montant_va_remise: number
  montant_ra: number; montant_ra_remise: number
  prime_volumique: number; abonnement_tv: number
  type_repart_rem: number
}
interface ProduitSfr { id_produit: number; lib_produit: string }

const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? '' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

const formatEur = (n: number): string =>
  n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })

const EMPTY_FORM = {
  id_produit: 0, type_vente: 0,
  date_debut: '', date_fin: '',
  montant_va: 0, montant_va_remise: 0,
  montant_ra: 0, montant_ra_remise: 0,
  prime_volumique: 0, abonnement_tv: 0,
  type_repart_rem: 0,
}

export default function SfrRemunerationsPage() {
  useDocumentTitle('Rémunérations SFR')
  const [categorie, setCategorie] = useState<Categorie>('FIBRE')
  const [lignes, setLignes] = useState<RemunItem[]>([])
  const [produits, setProduits] = useState<ProduitSfr[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [editMode, setEditMode] = useState<'none' | 'create' | 'edit'>('none')
  const [form, setForm] = useState<typeof EMPTY_FORM>(EMPTY_FORM)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const h = { Authorization: `Bearer ${getToken()}` }
      const [rem, prods] = await Promise.all([
        fetch(`${API_BASE}/suivi-sfr/remunerations?categorie=${categorie}`, { headers: h })
          .then(r => r.json() as Promise<RemunItem[]>),
        fetch(`${API_BASE}/suivi-sfr/remunerations/produits?categorie=${categorie}`, { headers: h })
          .then(r => r.json() as Promise<ProduitSfr[]>),
      ])
      setLignes(Array.isArray(rem) ? rem : [])
      setProduits(Array.isArray(prods) ? prods : [])
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [categorie])

  useEffect(() => {
    void reload()
    setSelectedId('')
    setEditMode('none')
  }, [reload])

  const handleAjouter = () => {
    setSelectedId('')
    setForm(EMPTY_FORM)
    setEditMode('create')
  }

  const handleEditer = () => {
    if (!selectedId) {
      showToast('Sélectionne une ligne dans le tableau.', 'info'); return
    }
    const l = lignes.find(x => x.id_sfr_remun === selectedId)
    if (!l) return
    setForm({
      id_produit: l.id_produit, type_vente: l.type_vente,
      date_debut: l.date_debut?.slice(0, 10) || '',
      date_fin: l.date_fin?.slice(0, 10) || '',
      montant_va: l.montant_va, montant_va_remise: l.montant_va_remise,
      montant_ra: l.montant_ra, montant_ra_remise: l.montant_ra_remise,
      prime_volumique: l.prime_volumique, abonnement_tv: l.abonnement_tv,
      type_repart_rem: l.type_repart_rem,
    })
    setEditMode('edit')
  }

  const handleDupliquer = async () => {
    if (!selectedId) {
      showToast('Sélectionne une ligne dans le tableau.', 'info'); return
    }
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/remunerations/${selectedId}/duplicate`,
        { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast('Dupliqué.', 'success')
      await reload()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const handleSupprimer = async () => {
    if (!selectedId) {
      showToast('Sélectionne une ligne dans le tableau.', 'info'); return
    }
    const ok = await showConfirm({
      title: 'Vous êtes sur le point de supprimer cette REM',
      message: 'Souhaitez-vous continuer ?',
    })
    if (!ok) return
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/remunerations/${selectedId}`,
        { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast('Supprimé.', 'success')
      setSelectedId(''); setEditMode('none')
      await reload()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const handleEnregistrer = async () => {
    if (!form.id_produit) {
      showToast('Choisis un produit.', 'info'); return
    }
    setSaving(true)
    try {
      const payload = {
        categorie,
        id_produit: form.id_produit,
        type_vente: form.type_vente,
        date_debut: form.date_debut || null,
        date_fin: form.date_fin || null,
        montant_va: form.montant_va,
        montant_va_remise: form.montant_va_remise,
        montant_ra: form.montant_ra,
        montant_ra_remise: form.montant_ra_remise,
        prime_volumique: categorie === 'FIBRE' ? form.prime_volumique : 0,
        abonnement_tv: categorie === 'FIBRE' ? form.abonnement_tv : 0,
        type_repart_rem: form.type_repart_rem,
      }
      const isEdit = editMode === 'edit' && selectedId
      const url = isEdit
        ? `${API_BASE}/suivi-sfr/remunerations/${selectedId}`
        : `${API_BASE}/suivi-sfr/remunerations`
      const r = await fetch(url, {
        method: isEdit ? 'PUT' : 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast(isEdit ? 'Modifications enregistrées' : 'Rémunération créée', 'success')
      setEditMode('none')
      setSelectedId('')
      await reload()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setSaving(false) }
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-110px)] text-c-ink">
      <div className="flex items-center gap-2 mb-3">
        <Link to=".." relative="path"
          className="p-1.5 hover:bg-c-surface-soft rounded text-c-ink-faint-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-lg font-bold flex items-center gap-2">
          <Euro className="w-4 h-4 text-c-brand" /> Rémunérations SFR
        </h1>
      </div>

      {/* Onglets Fibre/Mobile */}
      <div className="flex gap-1 border-b border-c-line mb-3">
        {(['FIBRE', 'MOBILE'] as const).map(c => (
          <button key={c} type="button"
            onClick={() => setCategorie(c)}
            className={`px-4 py-1.5 text-sm font-medium rounded-t ${
              categorie === c
                ? 'bg-white border border-c-line border-b-white text-c-brand'
                : 'text-c-ink-faint hover:bg-c-surface-soft'
            }`}>
            {c === 'FIBRE' ? 'Fibre' : 'Mobile'}
          </button>
        ))}
      </div>

      <div className="flex-1 grid grid-cols-3 gap-4 overflow-hidden">
        {/* Colonne gauche : tableau (2/3) */}
        <div className="col-span-2 bg-white rounded-xl border border-c-line overflow-hidden flex flex-col">
          {/* 4 boutons d'action */}
          <div className="px-3 py-2 border-b border-c-line-soft flex items-center gap-2 text-xs">
            <button type="button" onClick={handleAjouter}
              title="Ajouter"
              className="p-1.5 rounded text-c-brand hover:bg-c-brand/10">
              <Plus className="w-4 h-4" />
            </button>
            <button type="button" onClick={handleEditer} disabled={!selectedId}
              title="Éditer"
              className="p-1.5 rounded text-c-brand hover:bg-c-brand/10 disabled:opacity-30 disabled:cursor-not-allowed">
              <Pencil className="w-4 h-4" />
            </button>
            <button type="button" onClick={handleDupliquer} disabled={!selectedId}
              title="Dupliquer"
              className="p-1.5 rounded text-c-brand hover:bg-c-brand/10 disabled:opacity-30 disabled:cursor-not-allowed">
              <Copy className="w-4 h-4" />
            </button>
            <button type="button" onClick={handleSupprimer} disabled={!selectedId}
              title="Supprimer"
              className="p-1.5 rounded text-red-600 hover:bg-red-50 disabled:opacity-30 disabled:cursor-not-allowed">
              <Trash2 className="w-4 h-4" />
            </button>
            <span className="w-px h-5 bg-c-line mx-1" />
            <span className="text-c-ink-faint">
              {loading ? 'Chargement…' : `${lignes.length} rémunération(s)`}
            </span>
          </div>

          <div className="flex-1 overflow-auto">
            <table className="w-full text-xs">
              <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0">
                <tr>
                  <th className="px-2 py-2 text-left">Produit</th>
                  <th className="px-2 py-2 text-center">Type Vente</th>
                  <th className="px-2 py-2 text-left">Du</th>
                  <th className="px-2 py-2 text-left">Au</th>
                  <th className="px-2 py-2 text-right">Va</th>
                  <th className="px-2 py-2 text-right">Va Rem</th>
                  <th className="px-2 py-2 text-right">Ra</th>
                  <th className="px-2 py-2 text-right">Ra Rem</th>
                  {categorie === 'FIBRE' && (
                    <>
                      <th className="px-2 py-2 text-right">Prime Vol</th>
                      <th className="px-2 py-2 text-right">Abo TV</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-c-line-soft">
                {lignes.length === 0 ? (
                  <tr>
                    <td colSpan={categorie === 'FIBRE' ? 10 : 8}
                      className="text-center py-12 text-c-ink-faint-2 italic">
                      Aucune rémunération.
                    </td>
                  </tr>
                ) : lignes.map(l => (
                  <tr key={l.id_sfr_remun}
                    onClick={() => setSelectedId(l.id_sfr_remun)}
                    onDoubleClick={() => { setSelectedId(l.id_sfr_remun); handleEditer() }}
                    className={`cursor-pointer hover:bg-c-surface-soft ${
                      selectedId === l.id_sfr_remun ? 'bg-c-brand/10' : ''
                    }`}>
                    <td className="px-2 py-1.5">{l.lib_produit}</td>
                    <td className="px-2 py-1.5 text-center">{l.type_vente || '—'}</td>
                    <td className="px-2 py-1.5 tabular-nums">{shortDate(l.date_debut)}</td>
                    <td className="px-2 py-1.5 tabular-nums">{shortDate(l.date_fin)}</td>
                    <td className="px-2 py-1.5 text-right tabular-nums">{formatEur(l.montant_va)}</td>
                    <td className="px-2 py-1.5 text-right tabular-nums">{formatEur(l.montant_va_remise)}</td>
                    <td className="px-2 py-1.5 text-right tabular-nums">{formatEur(l.montant_ra)}</td>
                    <td className="px-2 py-1.5 text-right tabular-nums">{formatEur(l.montant_ra_remise)}</td>
                    {categorie === 'FIBRE' && (
                      <>
                        <td className="px-2 py-1.5 text-right tabular-nums">{formatEur(l.prime_volumique)}</td>
                        <td className="px-2 py-1.5 text-right tabular-nums">{formatEur(l.abonnement_tv)}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Colonne droite : formulaire */}
        <div className="bg-white rounded-xl border border-c-line overflow-hidden flex flex-col">
          <div className="px-3 py-2 border-b border-c-line-soft text-xs font-medium">
            {editMode === 'create' ? 'Nouvelle rémunération'
              : editMode === 'edit' ? 'Édition rémunération'
              : 'Détails'}
          </div>
          {editMode === 'none' ? (
            <div className="p-6 text-xs text-c-ink-faint italic text-center">
              Clique sur + pour ajouter ou sélectionne une ligne puis ✏️.
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-3 space-y-2.5 text-sm">
              <div>
                <label className="text-[10px] text-c-ink-faint">Produit</label>
                <select value={form.id_produit}
                  onChange={e => setForm({ ...form, id_produit: parseInt(e.target.value, 10) || 0 })}
                  className="w-full px-2 py-1.5 border border-c-line rounded text-sm">
                  <option value={0}>—</option>
                  {produits.map(p => (
                    <option key={p.id_produit} value={p.id_produit}>{p.lib_produit}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[10px] text-c-ink-faint">Type Vente</label>
                <input type="number" value={form.type_vente || ''}
                  onChange={e => setForm({ ...form, type_vente: parseInt(e.target.value, 10) || 0 })}
                  className="w-full px-2 py-1.5 border border-c-line rounded text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-c-ink-faint">Du</label>
                  <input type="date" value={form.date_debut}
                    onChange={e => setForm({ ...form, date_debut: e.target.value })}
                    className="w-full px-2 py-1.5 border border-c-line rounded text-xs" />
                </div>
                <div>
                  <label className="text-[10px] text-c-ink-faint">Au</label>
                  <input type="date" value={form.date_fin}
                    onChange={e => setForm({ ...form, date_fin: e.target.value })}
                    className="w-full px-2 py-1.5 border border-c-line rounded text-xs" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-c-ink-faint">Montant Va (€)</label>
                  <input type="number" step="0.01" value={form.montant_va || ''}
                    onChange={e => setForm({ ...form, montant_va: parseFloat(e.target.value) || 0 })}
                    className="w-full px-2 py-1.5 border border-c-line rounded text-sm text-right" />
                </div>
                <div>
                  <label className="text-[10px] text-c-ink-faint">Va Remise (€)</label>
                  <input type="number" step="0.01" value={form.montant_va_remise || ''}
                    onChange={e => setForm({ ...form, montant_va_remise: parseFloat(e.target.value) || 0 })}
                    className="w-full px-2 py-1.5 border border-c-line rounded text-sm text-right" />
                </div>
                <div>
                  <label className="text-[10px] text-c-ink-faint">Montant Ra (€)</label>
                  <input type="number" step="0.01" value={form.montant_ra || ''}
                    onChange={e => setForm({ ...form, montant_ra: parseFloat(e.target.value) || 0 })}
                    className="w-full px-2 py-1.5 border border-c-line rounded text-sm text-right" />
                </div>
                <div>
                  <label className="text-[10px] text-c-ink-faint">Ra Remise (€)</label>
                  <input type="number" step="0.01" value={form.montant_ra_remise || ''}
                    onChange={e => setForm({ ...form, montant_ra_remise: parseFloat(e.target.value) || 0 })}
                    className="w-full px-2 py-1.5 border border-c-line rounded text-sm text-right" />
                </div>
              </div>

              {/* Specifique Fibre (GrFibre WinDev) */}
              {categorie === 'FIBRE' && (
                <div className="grid grid-cols-2 gap-2 border-t border-c-line-soft pt-2">
                  <div>
                    <label className="text-[10px] text-c-ink-faint">Prime Volumique (€)</label>
                    <input type="number" step="0.01" value={form.prime_volumique || ''}
                      onChange={e => setForm({ ...form, prime_volumique: parseFloat(e.target.value) || 0 })}
                      className="w-full px-2 py-1.5 border border-c-line rounded text-sm text-right" />
                  </div>
                  <div>
                    <label className="text-[10px] text-c-ink-faint">Abonnement TV (€)</label>
                    <input type="number" step="0.01" value={form.abonnement_tv || ''}
                      onChange={e => setForm({ ...form, abonnement_tv: parseFloat(e.target.value) || 0 })}
                      className="w-full px-2 py-1.5 border border-c-line rounded text-sm text-right" />
                  </div>
                </div>
              )}

              <div>
                <label className="text-[10px] text-c-ink-faint">Type Répart Rem</label>
                <input type="number" value={form.type_repart_rem || ''}
                  onChange={e => setForm({ ...form, type_repart_rem: parseInt(e.target.value, 10) || 0 })}
                  className="w-full px-2 py-1.5 border border-c-line rounded text-sm" />
              </div>

              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setEditMode('none')}
                  className="px-3 py-1.5 border border-c-line rounded text-sm text-c-ink-soft hover:bg-c-surface-soft">
                  Annuler
                </button>
                <button type="button" onClick={handleEnregistrer} disabled={saving}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 bg-c-brand text-white rounded text-sm font-medium hover:opacity-90 disabled:opacity-50">
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" />
                          : <Save className="w-4 h-4" />}
                  Enregistrer
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
