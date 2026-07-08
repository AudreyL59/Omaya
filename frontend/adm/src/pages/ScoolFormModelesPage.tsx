/**
 * Fen_ScoolFormModele - Modeles de plan de formation.
 *
 * 2 tables :
 *   - Haut : liste des modeles (pgt_form_modele)
 *     Actions : Nouveau / Dupliquer / Supprimer / Utiliser (si idFormation)
 *   - Bas : programme du modele selectionne (pgt_form_modele_programme)
 *     Actions : Ajouter un jour / Dupliquer / Supprimer
 *
 * Chaque ligne programme est editable inline (auto-save au blur).
 */
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Plus, Copy, Trash2, GraduationCap, X, Save, ArrowLeft,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'

const API_BASE = '/api/adm'

interface ModeleRow {
  id_modele: string
  intitule: string
  categorie: string
  nb_heure_salle: number
  nb_heure_terrain: number
  heure_jour_salle: number
  heure_jour_terrain: number
}
interface ProgRow {
  id_modele_programme: string
  id_modele_form: string
  num_jour: number
  salle: number
  terrain: number
  duree: number
  horaires: string
}

interface ModelePayload {
  intitule: string; categorie: string
  nb_heure_salle: number; nb_heure_terrain: number
  heure_jour_salle: number; heure_jour_terrain: number
}

const CATEGORIES = ['N1', 'N2', 'N3']

export default function ScoolFormModelesPage() {
  useDocumentTitle('Modèles de formation')
  const nav = useNavigate()
  const [sp] = useSearchParams()
  const idFormation = sp.get('id_formation') || ''

  const [modeles, setModeles] = useState<ModeleRow[]>([])
  const [selIdx, setSelIdx] = useState<number>(-1)
  const [progs, setProgs] = useState<ProgRow[]>([])
  const [selProgIdx, setSelProgIdx] = useState<number>(-1)
  const [modal, setModal] = useState<{
    mode: 'new' | 'edit'
    data: ModelePayload & { id_modele: string }
  } | null>(null)

  const loadModeles = useCallback(async () => {
    const r = await fetch(`${API_BASE}/scool/modeles`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    setModeles(await r.json())
  }, [])

  const loadProgs = useCallback(async (idModele: string) => {
    if (!idModele) { setProgs([]); return }
    const r = await fetch(
      `${API_BASE}/scool/modeles/${idModele}/programme`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
    setProgs(await r.json())
  }, [])

  useEffect(() => { void loadModeles() }, [loadModeles])
  useEffect(() => {
    if (selIdx >= 0 && modeles[selIdx]) {
      void loadProgs(modeles[selIdx].id_modele)
    } else setProgs([])
  }, [selIdx, modeles, loadProgs])

  // ---- Actions modele ----

  const nouveau = () => setModal({
    mode: 'new',
    data: {
      id_modele: '', intitule: '', categorie: '',
      nb_heure_salle: 0, nb_heure_terrain: 0,
      heure_jour_salle: 8, heure_jour_terrain: 8,
    },
  })

  const editer = () => {
    if (selIdx < 0) return
    const m = modeles[selIdx]
    setModal({
      mode: 'edit',
      data: {
        id_modele: m.id_modele,
        intitule: m.intitule, categorie: m.categorie,
        nb_heure_salle: m.nb_heure_salle,
        nb_heure_terrain: m.nb_heure_terrain,
        heure_jour_salle: m.heure_jour_salle,
        heure_jour_terrain: m.heure_jour_terrain,
      },
    })
  }

  const saveModal = async () => {
    if (!modal) return
    if (!modal.data.intitule.trim()) {
      showToast('Intitulé requis', 'info'); return
    }
    const url = modal.mode === 'new'
      ? `${API_BASE}/scool/modeles`
      : `${API_BASE}/scool/modeles/${modal.data.id_modele}`
    const method = modal.mode === 'new' ? 'POST' : 'PUT'
    const { id_modele: _, ...payload } = modal.data
    const r = await fetch(url, {
      method,
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    const d = await r.json()
    if (d.ok) {
      showToast('Enregistré', 'success')
      setModal(null)
      await loadModeles()
    } else showToast('Erreur', 'error')
  }

  const dupliquer = async () => {
    if (selIdx < 0) return
    const r = await fetch(
      `${API_BASE}/scool/modeles/${modeles[selIdx].id_modele}/dupliquer`,
      { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    const d = await r.json()
    if (d.ok) { showToast('Modèle dupliqué', 'success'); await loadModeles() }
  }

  const supprimer = async () => {
    if (selIdx < 0) return
    if (!await showConfirm({
      title: 'Supprimer',
      message: `Supprimer le modèle "${modeles[selIdx].intitule}" ?`,
    })) return
    await fetch(
      `${API_BASE}/scool/modeles/${modeles[selIdx].id_modele}`,
      { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    await loadModeles()
    setSelIdx(-1)
  }

  const utiliserCeModele = () => {
    if (selIdx < 0 || !idFormation) return
    // Retourne a la page fiche formation avec l'id modele
    nav(`/scool/formations/${idFormation}?id_modele=${modeles[selIdx].id_modele}`)
  }

  // ---- Actions programme du modele ----

  const idModeleSel = selIdx >= 0 ? modeles[selIdx].id_modele : ''

  const ajouterJour = async () => {
    if (!idModeleSel) { showToast('Sélectionne un modèle', 'info'); return }
    const r = await fetch(
      `${API_BASE}/scool/modeles/${idModeleSel}/programme`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          num_jour: 0, salle: 0, terrain: 0, duree: 0, horaires: '',
        }),
      },
    )
    const d = await r.json()
    if (d.ok) { await loadProgs(idModeleSel) }
  }

  const dupliquerJour = async () => {
    if (selProgIdx < 0 || !idModeleSel) return
    const p = progs[selProgIdx]
    await fetch(
      `${API_BASE}/scool/modeles/${idModeleSel}/programme/${p.id_modele_programme}/dupliquer`,
      { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    await loadProgs(idModeleSel)
  }

  const supprimerJour = async () => {
    if (selProgIdx < 0 || !idModeleSel) return
    const p = progs[selProgIdx]
    if (!await showConfirm({
      title: 'Supprimer', message: `Supprimer le jour ${p.num_jour} ?`,
    })) return
    await fetch(
      `${API_BASE}/scool/modeles/${idModeleSel}/programme/${p.id_modele_programme}`,
      { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    await loadProgs(idModeleSel)
    setSelProgIdx(-1)
  }

  const updateProg = async (idx: number, patch: Partial<ProgRow>) => {
    const p = { ...progs[idx], ...patch }
    setProgs((cur) => {
      const c = [...cur]; c[idx] = p; return c
    })
    await fetch(
      `${API_BASE}/scool/modeles/${idModeleSel}/programme/${p.id_modele_programme}`,
      {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          num_jour: p.num_jour, salle: p.salle,
          terrain: p.terrain, duree: p.duree, horaires: p.horaires,
        }),
      },
    )
  }

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-full mx-auto">
        <PageHeader
          icon={GraduationCap}
          backTo="/scool/formations"
          title="Modèles de plan de formation"
          right={idFormation && (
            <button onClick={() => nav('/scool/formations')}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] text-sm">
              <ArrowLeft className="w-4 h-4" /> Retour
            </button>
          )}
        />

        {/* Table modeles */}
        <div className="bg-white rounded-lg shadow p-4 mb-4">
          <div className="flex items-center gap-2 mb-3">
            <button onClick={nouveau}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm">
              <Plus className="w-4 h-4" /> Nouveau Modèle
            </button>
            <button onClick={editer}
                    disabled={selIdx < 0}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] text-sm disabled:opacity-40">
              Éditer
            </button>
            <button onClick={dupliquer}
                    disabled={selIdx < 0}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] text-sm disabled:opacity-40">
              <Copy className="w-4 h-4" /> Dupliquer
            </button>
            <button onClick={supprimer}
                    disabled={selIdx < 0}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#B91C1C] text-[#B91C1C] hover:bg-red-50 text-sm disabled:opacity-40">
              <Trash2 className="w-4 h-4" /> Supprimer
            </button>
            {idFormation && (
              <button onClick={utiliserCeModele}
                      disabled={selIdx < 0}
                      className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm disabled:opacity-40">
                <GraduationCap className="w-4 h-4" /> Utiliser ce modèle
              </button>
            )}
          </div>

          <div className="overflow-x-auto max-h-[35vh] overflow-y-auto">
            <table className="text-xs w-full">
              <thead className="sticky top-0 bg-[#F5F5F0]">
                <tr>
                  <th className="py-1.5 px-2 text-left">Intitulé</th>
                  <th className="py-1.5 px-2 text-left">Catégorie</th>
                  <th className="py-1.5 px-2 text-right">Heure Salle</th>
                  <th className="py-1.5 px-2 text-right">Heure Terrain</th>
                  <th className="py-1.5 px-2 text-right">H/Jour Salle</th>
                  <th className="py-1.5 px-2 text-right">H/Jour Terrain</th>
                </tr>
              </thead>
              <tbody>
                {modeles.map((m, i) => (
                  <tr key={i} onClick={() => { setSelIdx(i); setSelProgIdx(-1) }}
                      onDoubleClick={idFormation ? utiliserCeModele : undefined}
                      className={`cursor-pointer border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${
                        selIdx === i ? 'bg-[#FFF5E0] ring-1 ring-[#8B7355]' : ''
                      }`}>
                    <td className="py-1.5 px-2 font-medium">{m.intitule}</td>
                    <td className="py-1.5 px-2">{m.categorie}</td>
                    <td className="py-1.5 px-2 text-right tabular-nums">{m.nb_heure_salle}h</td>
                    <td className="py-1.5 px-2 text-right tabular-nums">{m.nb_heure_terrain}h</td>
                    <td className="py-1.5 px-2 text-right tabular-nums">{m.heure_jour_salle}h</td>
                    <td className="py-1.5 px-2 text-right tabular-nums">{m.heure_jour_terrain}h</td>
                  </tr>
                ))}
                {modeles.length === 0 && (
                  <tr><td colSpan={6} className="py-6 text-center text-gray-400">
                    Aucun modèle - Ajoute avec + Nouveau Modèle
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Programme du modele */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-2 mb-3">
            <h3 className="text-sm font-semibold text-[#17494E]">
              Programme du modèle
              {selIdx >= 0 && (
                <span className="ml-2 text-[#8B7355] font-normal">
                  · {modeles[selIdx].intitule}
                </span>
              )}
            </h3>
            <div className="ml-auto flex items-center gap-2">
              <button onClick={ajouterJour}
                      disabled={selIdx < 0}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm disabled:opacity-40">
                <Plus className="w-4 h-4" /> Ajouter un jour
              </button>
              <button onClick={dupliquerJour}
                      disabled={selProgIdx < 0}
                      className="p-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] disabled:opacity-40">
                <Copy className="w-4 h-4" />
              </button>
              <button onClick={supprimerJour}
                      disabled={selProgIdx < 0}
                      className="p-1.5 rounded border border-[#B91C1C] text-[#B91C1C] hover:bg-red-50 disabled:opacity-40">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto max-h-[45vh] overflow-y-auto">
            <table className="text-xs w-full">
              <thead className="sticky top-0 bg-[#F5F5F0]">
                <tr>
                  <th className="py-1.5 px-2 text-left w-20">Num Jour</th>
                  <th className="py-1.5 px-2 text-right w-16">Salle</th>
                  <th className="py-1.5 px-2 text-right w-16">Terrain</th>
                  <th className="py-1.5 px-2 text-right w-16">Durée</th>
                  <th className="py-1.5 px-2 text-left">Horaires</th>
                </tr>
              </thead>
              <tbody>
                {progs.map((p, i) => (
                  <tr key={i} onClick={() => setSelProgIdx(i)}
                      className={`cursor-pointer border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${
                        selProgIdx === i ? 'bg-[#FFF5E0] ring-1 ring-[#8B7355]' : ''
                      }`}>
                    <td className="py-1 px-2">
                      <input type="number" value={p.num_jour}
                             onChange={(e) => updateProg(i, { num_jour: Number(e.target.value) })}
                             onClick={(e) => e.stopPropagation()}
                             className="w-16 px-1 py-0.5 border border-transparent hover:border-[#E5E0D5] rounded text-right" />
                    </td>
                    <td className="py-1 px-2">
                      <input type="number" value={p.salle}
                             onChange={(e) => updateProg(i, { salle: Number(e.target.value) })}
                             onClick={(e) => e.stopPropagation()}
                             className="w-14 px-1 py-0.5 border border-transparent hover:border-[#E5E0D5] rounded text-right" />
                    </td>
                    <td className="py-1 px-2">
                      <input type="number" value={p.terrain}
                             onChange={(e) => updateProg(i, { terrain: Number(e.target.value) })}
                             onClick={(e) => e.stopPropagation()}
                             className="w-14 px-1 py-0.5 border border-transparent hover:border-[#E5E0D5] rounded text-right" />
                    </td>
                    <td className="py-1 px-2">
                      <input type="number" value={p.duree}
                             onChange={(e) => updateProg(i, { duree: Number(e.target.value) })}
                             onClick={(e) => e.stopPropagation()}
                             className="w-14 px-1 py-0.5 border border-transparent hover:border-[#E5E0D5] rounded text-right" />
                    </td>
                    <td className="py-1 px-2">
                      <input type="text" value={p.horaires}
                             onChange={(e) => updateProg(i, { horaires: e.target.value })}
                             onClick={(e) => e.stopPropagation()}
                             className="w-full px-1 py-0.5 border border-transparent hover:border-[#E5E0D5] rounded" />
                    </td>
                  </tr>
                ))}
                {progs.length === 0 && (
                  <tr><td colSpan={5} className="py-6 text-center text-gray-400">
                    {selIdx < 0
                      ? 'Sélectionne un modèle dans le tableau du haut'
                      : 'Aucun jour - Ajoute avec + Ajouter un jour'}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Modale Ajout/Edit modele */}
      {modal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-[#17494E]">
                {modal.mode === 'new' ? 'Nouveau modèle' : 'Éditer le modèle'}
              </h3>
              <button onClick={() => setModal(null)}
                      className="p-1 rounded hover:bg-gray-100">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-3">
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Intitulé *</span>
                <input type="text" value={modal.data.intitule}
                       onChange={(e) => setModal({ ...modal, data: { ...modal.data, intitule: e.target.value } })}
                       className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
              </label>
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Catégorie</span>
                <select value={modal.data.categorie}
                        onChange={(e) => setModal({ ...modal, data: { ...modal.data, categorie: e.target.value } })}
                        className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded">
                  <option value="">—</option>
                  {CATEGORIES.map((c) => (<option key={c} value={c}>{c}</option>))}
                </select>
              </label>
              <div className="grid grid-cols-2 gap-2">
                <label className="block text-xs">
                  <span className="text-[#8B7355] font-medium">Nb h Salle</span>
                  <input type="number" min={0} value={modal.data.nb_heure_salle}
                         onChange={(e) => setModal({ ...modal, data: { ...modal.data, nb_heure_salle: Number(e.target.value) } })}
                         className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
                </label>
                <label className="block text-xs">
                  <span className="text-[#8B7355] font-medium">Nb h Terrain</span>
                  <input type="number" min={0} value={modal.data.nb_heure_terrain}
                         onChange={(e) => setModal({ ...modal, data: { ...modal.data, nb_heure_terrain: Number(e.target.value) } })}
                         className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
                </label>
                <label className="block text-xs">
                  <span className="text-[#8B7355] font-medium">H/jour Salle</span>
                  <input type="number" min={0} value={modal.data.heure_jour_salle}
                         onChange={(e) => setModal({ ...modal, data: { ...modal.data, heure_jour_salle: Number(e.target.value) } })}
                         className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
                </label>
                <label className="block text-xs">
                  <span className="text-[#8B7355] font-medium">H/jour Terrain</span>
                  <input type="number" min={0} value={modal.data.heure_jour_terrain}
                         onChange={(e) => setModal({ ...modal, data: { ...modal.data, heure_jour_terrain: Number(e.target.value) } })}
                         className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
                </label>
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <button onClick={saveModal}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white hover:bg-[#0F3438]">
                <Save className="w-4 h-4" /> Enregistrer
              </button>
              <button onClick={() => setModal(null)}
                      className="flex-1 px-3 py-2 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]">
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
