/**
 * Fen_ScoolFormation_Fiche - Fiche detail d'une formation S'Cool.
 *
 * 2 colonnes :
 * - Gauche : Formulaire principal (intitule, ville, dates, formateurs,
 *   DA/DR, formation active, formation cloturee, btn Enregistrer)
 * - Droite : 6 onglets (Programme, Evenement, Eleves, Session, Bulletins,
 *   Bareme Notes)
 *
 * Onglet Programme fonctionnel : liste + Ajouter date + Dupliquer +
 * Supprimer + Convertir en modele + Version PDF.
 * Onglets 2-6 : placeholders 'a venir'.
 */
import { useCallback, useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Save, Plus, Copy, Trash2, X, ArrowLeft, BookOpen, FileText,
  Loader2, Check, UserPlus,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'
import PersonnePicker, { type SalarieItem } from '@/components/PersonnePicker'

const API_BASE = '/api/adm'

// ---------- Types ----------

interface FormationDetail {
  id_formation: string
  intitule: string
  date_debut: string
  date_fin: string
  ville_formation: string
  type_produit: string
  categorie: string
  formateur1_nom: string
  formateur2_nom: string
  formateur3_nom: string
  formateur4_nom: string
  formateur5_nom: string
  formateur1_id: string
  formateur2_id: string
  formateur3_id: string
  formateur4_id: string
  formateur5_id: string
  dest_promo: string
  nb_heure_salle: number
  nb_heure_terrain: number
  heure_jour_salle: number
  heure_jour_terrain: number
  duree: number
  formation_active: boolean
  formation_cloturee: boolean
}

interface FormateurCombo {
  id_formateur: string
  lib: string
  niveau: string
  is_actif: boolean
}

interface ProgrammeRow {
  id_programme: string
  id_formation: string
  num_semaine: number
  date: string
  salle: number
  terrain: number
  duree: number
  horaires: string
  objectif: number
}

type Tab = 'programme' | 'evenement' | 'eleves' | 'session' | 'bulletins' | 'bareme'

const TYPES_PROD = ['SFR', 'ENI', 'IAG', 'STR', 'VAL', 'PRO', 'OEN', 'TLC']
const CATEGORIES = ['N1', 'N2', 'N3']

const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? ''
    : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

// ---------- Page ----------

export default function ScoolFormationFichePage() {
  const { id } = useParams()
  const nav = useNavigate()
  useDocumentTitle('Fiche Formation')

  const [data, setData] = useState<FormationDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [formateurs, setFormateurs] = useState<FormateurCombo[]>([])

  const [tab, setTab] = useState<Tab>('programme')
  const [programme, setProgramme] = useState<ProgrammeRow[]>([])
  const [selProgIdx, setSelProgIdx] = useState<number>(-1)

  const loadFormation = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/scool/formations/${id}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) { showToast('Formation introuvable', 'error'); return }
      setData(await r.json())
    } finally { setLoading(false) }
  }, [id])

  const loadProgramme = useCallback(async () => {
    if (!id) return
    const r = await fetch(
      `${API_BASE}/scool/formations/${id}/programme`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
    setProgramme(await r.json())
  }, [id])

  useEffect(() => {
    void loadFormation()
    void loadProgramme()
    void fetch(`${API_BASE}/scool/formateurs`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    }).then((r) => r.json()).then(setFormateurs).catch(() => {})
  }, [loadFormation, loadProgramme])

  const setFormateur = (idx: number, sid: string) => {
    if (!data) return
    const f = formateurs.find((x) => x.id_formateur === sid)
    const key = `formateur${idx}_id` as keyof FormationDetail
    const keyNom = `formateur${idx}_nom` as keyof FormationDetail
    setData({
      ...data,
      [key]: sid,
      [keyNom]: f ? f.lib : '',
    })
  }

  const doSave = async () => {
    if (!data || !id) return
    if (!data.intitule.trim()) { showToast('Intitulé requis', 'info'); return }
    setSaving(true)
    try {
      const {
        id_formation: _, formateur1_nom: __, formateur2_nom: ___,
        formateur3_nom: ____, formateur4_nom: _____, formateur5_nom: ______,
        ...payload
      } = data
      const r = await fetch(`${API_BASE}/scool/formations/${id}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })
      const d = await r.json()
      if (d.ok) { showToast('Enregistré', 'success'); await loadFormation() }
      else showToast('Erreur', 'error')
    } finally { setSaving(false) }
  }

  // ----- Programme actions -----

  const ajouterDate = async () => {
    const dateStr = window.prompt(
      'Date à ajouter (YYYY-MM-DD) :',
      data?.date_debut || new Date().toISOString().slice(0, 10),
    )
    if (!dateStr || dateStr.length < 10) return
    const r = await fetch(
      `${API_BASE}/scool/formations/${id}/programme`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ date: dateStr }),
      },
    )
    const d = await r.json()
    if (d.ok) { showToast('Date ajoutée', 'success'); await loadProgramme() }
  }

  const dupliquerDate = async (idx: number) => {
    const p = programme[idx]
    const r = await fetch(
      `${API_BASE}/scool/formations/${id}/programme/${p.id_programme}/dupliquer`,
      { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    const d = await r.json()
    if (d.ok) { showToast('Ligne dupliquée', 'success'); await loadProgramme() }
  }

  const supprimerDate = async (idx: number) => {
    const p = programme[idx]
    if (!await showConfirm({
      title: 'Supprimer', message: `Supprimer la date du ${shortDate(p.date)} ?`,
    })) return
    await fetch(
      `${API_BASE}/scool/formations/${id}/programme/${p.id_programme}`,
      { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    await loadProgramme()
    setSelProgIdx(-1)
  }

  const supprimerTout = async () => {
    if (!await showConfirm({
      title: 'ATTENTION',
      message: 'Souhaitez-vous supprimer la totalité du programme ?',
    })) return
    if (!await showConfirm({
      title: 'Confirmation',
      message: '⚠️ La totalité du programme va être supprimée. Continuer ?',
    })) return
    await fetch(
      `${API_BASE}/scool/formations/${id}/programme`,
      { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    await loadProgramme()
    showToast('Programme supprimé', 'success')
  }

  const convertirModele = async () => {
    if (!data) return
    if (!await showConfirm({
      title: 'Convertir en modèle',
      message: 'Créer un nouveau modèle depuis ce plan de formation ?',
    })) return
    const r = await fetch(
      `${API_BASE}/scool/formations/${id}/convertir-modele`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          intitule: data.intitule,
          categorie: data.categorie,
          nb_heure_salle: data.nb_heure_salle,
          nb_heure_terrain: data.nb_heure_terrain,
          heure_jour_salle: data.heure_jour_salle,
          heure_jour_terrain: data.heure_jour_terrain,
        }),
      },
    )
    const d = await r.json()
    if (d.ok) showToast('Modèle créé', 'success')
    else showToast('Erreur', 'error')
  }

  const updateProg = async (idx: number, patch: Partial<ProgrammeRow>) => {
    const p = { ...programme[idx], ...patch }
    await fetch(
      `${API_BASE}/scool/formations/${id}/programme/${p.id_programme}`,
      {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          date: p.date, num_semaine: p.num_semaine,
          salle: p.salle, terrain: p.terrain,
          duree: p.duree, horaires: p.horaires, objectif: p.objectif,
        }),
      },
    )
    await loadProgramme()
  }

  if (loading || !data) {
    return (
      <div className="min-h-screen bg-[#F5F5F0] p-6">
        <div className="max-w-full mx-auto flex items-center gap-2 text-[#8B7355]">
          <Loader2 className="w-4 h-4 animate-spin" /> Chargement...
        </div>
      </div>
    )
  }

  const totalSalle = programme.reduce((s, p) => s + p.salle, 0)
  const totalTerrain = programme.reduce((s, p) => s + p.terrain, 0)
  const nbJours = programme.length

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-full mx-auto">
        <PageHeader
          icon={BookOpen}
          backTo="/scool/formations"
          title={`Fiche Formation : ${data.intitule}`}
          subtitle={`${shortDate(data.date_debut)} - ${shortDate(data.date_fin)}`}
          right={
            <button onClick={() => nav('/scool/formations')}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] text-sm">
              <ArrowLeft className="w-4 h-4" /> Retour
            </button>
          }
        />

        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)] gap-4">
          {/* --- Colonne gauche : formulaire principal --- */}
          <div className="bg-white rounded-lg shadow p-4 space-y-3">
            <h3 className="text-sm font-semibold text-[#17494E] border-b border-[#F0EDE5] pb-2">
              Fiche Formation
            </h3>

            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Intitulé *</span>
              <input type="text" value={data.intitule}
                     onChange={(e) => setData({ ...data, intitule: e.target.value })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>

            <div className="grid grid-cols-2 gap-2">
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Catégorie</span>
                <select value={data.categorie}
                        onChange={(e) => setData({ ...data, categorie: e.target.value })}
                        className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded">
                  <option value="">—</option>
                  {CATEGORIES.map((c) => (<option key={c} value={c}>{c}</option>))}
                </select>
              </label>
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Type Produit</span>
                <select value={data.type_produit}
                        onChange={(e) => setData({ ...data, type_produit: e.target.value })}
                        className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded">
                  <option value="">—</option>
                  {TYPES_PROD.map((t) => (<option key={t} value={t}>{t}</option>))}
                </select>
              </label>
            </div>

            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Ville Formation</span>
              <input type="text" value={data.ville_formation}
                     onChange={(e) => setData({ ...data, ville_formation: e.target.value })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>

            <div className="grid grid-cols-2 gap-2">
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Du</span>
                <input type="date" value={data.date_debut}
                       onChange={(e) => setData({ ...data, date_debut: e.target.value })}
                       className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
              </label>
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Au</span>
                <input type="date" value={data.date_fin}
                       onChange={(e) => setData({ ...data, date_fin: e.target.value })}
                       className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
              </label>
            </div>

            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={data.formation_active}
                     onChange={(e) => setData({ ...data, formation_active: e.target.checked })}
                     className="accent-[#17494E]" />
              <span className="text-[#8B7355]">Formation Active</span>
            </label>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#F0EDE5]">
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Total Salle</span>
                <input type="number" value={data.nb_heure_salle}
                       onChange={(e) => setData({ ...data, nb_heure_salle: Number(e.target.value) })}
                       className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
              </label>
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Heure/Jour Salle</span>
                <input type="number" value={data.heure_jour_salle}
                       onChange={(e) => setData({ ...data, heure_jour_salle: Number(e.target.value) })}
                       className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
              </label>
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Total Terrain</span>
                <input type="number" value={data.nb_heure_terrain}
                       onChange={(e) => setData({ ...data, nb_heure_terrain: Number(e.target.value) })}
                       className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
              </label>
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Heure/Jour Terrain</span>
                <input type="number" value={data.heure_jour_terrain}
                       onChange={(e) => setData({ ...data, heure_jour_terrain: Number(e.target.value) })}
                       className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
              </label>
              <label className="block text-xs col-span-2">
                <span className="text-[#8B7355] font-medium">Durée totale</span>
                <input type="number" value={data.duree}
                       onChange={(e) => setData({ ...data, duree: Number(e.target.value) })}
                       className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
              </label>
            </div>

            <div className="pt-2 border-t border-[#F0EDE5] space-y-2">
              {[
                { i: 1, l: 'Formateur principal' },
                { i: 2, l: 'Formateur adjoint' },
                { i: 3, l: 'Formateur 3' },
                { i: 4, l: 'Formateur 4' },
                { i: 5, l: 'Formateur 5' },
              ].map((f) => (
                <label key={f.i} className="block text-xs">
                  <span className="text-[#8B7355] font-medium">{f.l}</span>
                  <select
                    value={(data[`formateur${f.i}_id` as keyof FormationDetail] as string) || ''}
                    onChange={(e) => setFormateur(f.i, e.target.value)}
                    className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded">
                    <option value="">Non renseigné</option>
                    {formateurs.map((fo) => (
                      <option key={fo.id_formateur} value={fo.id_formateur}
                              disabled={!fo.is_actif}>
                        {fo.lib}{!fo.is_actif ? ' (inactif)' : ''}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>

            <label className="flex items-center gap-2 text-sm pt-2 border-t border-[#F0EDE5]">
              <input type="checkbox" checked={data.formation_cloturee}
                     onChange={(e) => setData({ ...data, formation_cloturee: e.target.checked })}
                     className="accent-[#17494E]" />
              <span className="text-[#8B7355]">Formation Clôturée</span>
            </label>

            <button onClick={doSave} disabled={saving}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white hover:bg-[#0F3438] disabled:opacity-40">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Enregistrer
            </button>
          </div>

          {/* --- Colonne droite : onglets --- */}
          <div className="flex flex-col gap-4">
            <div className="flex border-b border-[#E5E0D5] flex-wrap">
              {[
                { key: 'programme' as Tab, label: 'Prog. de formation' },
                { key: 'evenement' as Tab, label: 'Évènement' },
                { key: 'eleves' as Tab, label: 'Élèves' },
                { key: 'session' as Tab, label: 'Session de recrut.' },
                { key: 'bulletins' as Tab, label: 'Bulletins' },
                { key: 'bareme' as Tab, label: 'Barème Notes' },
              ].map((t) => (
                <button
                  key={t.key}
                  onClick={() => setTab(t.key)}
                  className={`px-3 py-2 text-sm font-medium border-b-2 ${
                    tab === t.key
                      ? 'border-[#17494E] text-[#17494E]'
                      : 'border-transparent text-gray-500 hover:text-[#17494E]'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {tab === 'programme' && (
              <div className="bg-white rounded-lg shadow p-4">
                <div className="flex items-center gap-2 mb-3 flex-wrap">
                  <button onClick={ajouterDate}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm">
                    <Plus className="w-4 h-4" /> Ajouter une date
                  </button>
                  <button
                    onClick={() => selProgIdx >= 0 && dupliquerDate(selProgIdx)}
                    disabled={selProgIdx < 0}
                    title="Dupliquer"
                    className="p-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] disabled:opacity-40">
                    <Copy className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => selProgIdx >= 0 && supprimerDate(selProgIdx)}
                    disabled={selProgIdx < 0}
                    title="Supprimer"
                    className="p-1.5 rounded border border-[#B91C1C] text-[#B91C1C] hover:bg-red-50 disabled:opacity-40">
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <button onClick={supprimerTout}
                          title="Supprimer tout le programme"
                          className="p-1.5 rounded border border-[#B91C1C] text-[#B91C1C] hover:bg-red-50 text-xs">
                    Tout
                  </button>
                  <div className="ml-auto flex items-center gap-2">
                    <button onClick={convertirModele}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] text-sm">
                      <FileText className="w-4 h-4" /> Convertir en modèle
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto max-h-[60vh] overflow-y-auto">
                  <table className="text-xs w-full">
                    <thead className="sticky top-0 bg-[#F5F5F0]">
                      <tr>
                        <th className="py-1.5 px-2 text-left w-14">Sem</th>
                        <th className="py-1.5 px-2 text-left w-28">Date</th>
                        <th className="py-1.5 px-2 text-right w-16">Salle</th>
                        <th className="py-1.5 px-2 text-right w-16">Terrain</th>
                        <th className="py-1.5 px-2 text-right w-16">Durée</th>
                        <th className="py-1.5 px-2 text-right w-16">Obj</th>
                        <th className="py-1.5 px-2 text-left">Horaires</th>
                      </tr>
                    </thead>
                    <tbody>
                      {programme.map((p, i) => (
                        <tr key={i} onClick={() => setSelProgIdx(i)}
                            className={`border-b border-[#F0EDE5] hover:bg-[#ECF1F2] cursor-pointer ${
                              selProgIdx === i ? 'bg-[#FFF5E0] ring-1 ring-[#8B7355]' : ''
                            }`}>
                          <td className="py-1 px-2">
                            <input type="number" value={p.num_semaine}
                                   onChange={(e) => updateProg(i, { num_semaine: Number(e.target.value) })}
                                   onClick={(e) => e.stopPropagation()}
                                   className="w-12 px-1 py-0.5 border border-transparent hover:border-[#E5E0D5] rounded text-right" />
                          </td>
                          <td className="py-1 px-2">
                            <input type="date" value={p.date}
                                   onChange={(e) => updateProg(i, { date: e.target.value })}
                                   onClick={(e) => e.stopPropagation()}
                                   className="w-full px-1 py-0.5 border border-transparent hover:border-[#E5E0D5] rounded" />
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
                            <input type="number" value={p.objectif}
                                   onChange={(e) => updateProg(i, { objectif: Number(e.target.value) })}
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
                      {programme.length === 0 && (
                        <tr><td colSpan={7} className="py-8 text-center text-gray-400">
                          Aucune date - Ajoute avec le bouton +
                        </td></tr>
                      )}
                    </tbody>
                    {programme.length > 0 && (
                      <tfoot className="font-semibold text-[#17494E] border-t-2 border-[#8B7355]">
                        <tr>
                          <td className="py-1.5 px-2" colSpan={2}>NB Jours : {nbJours}</td>
                          <td className="py-1.5 px-2 text-right">{totalSalle}h</td>
                          <td className="py-1.5 px-2 text-right">{totalTerrain}h</td>
                          <td className="py-1.5 px-2 text-right">{totalSalle + totalTerrain}h</td>
                          <td className="py-1.5 px-2" colSpan={2}></td>
                        </tr>
                      </tfoot>
                    )}
                  </table>
                </div>

                <p className="mt-3 text-xs text-red-700 italic">
                  Attention aux mots clés pour l'analyse : <b>BILAN</b> et <b>REMISE DIPLOME</b>
                </p>
              </div>
            )}

            {tab === 'evenement' && id && (
              <EvenementTab idFormation={id} />
            )}
            {tab === 'eleves' && id && data && (
              <ElevesTab idFormation={id} />
            )}
            {tab === 'session' && id && (
              <SessionRecrutTab idFormation={id} />
            )}
            {tab === 'bulletins' && id && (
              <BulletinsTab idFormation={id} />
            )}
            {tab === 'bareme' && id && (
              <BaremeTab idFormation={id} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// =====================================================================
// Onglet Evenement
// =====================================================================

interface EvenementRow {
  id_evenement: string
  date: string
  id_salarie: string
  nom_prenom: string
  intitule: string
}

function EvenementTab({ idFormation }: { idFormation: string }) {
  const [rows, setRows] = useState<EvenementRow[]>([])
  const [pickerOpen, setPickerOpen] = useState(false)
  const [pendingRow, setPendingRow] = useState<{
    id_salarie: string; nom_prenom: string
    date: string; intitule: string
    id_evenement?: string
  } | null>(null)

  const load = useCallback(async () => {
    const r = await fetch(
      `${API_BASE}/scool/formations/${idFormation}/evenements`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
    setRows(await r.json())
  }, [idFormation])
  useEffect(() => { void load() }, [load])

  const nouveau = () => {
    setPendingRow({
      id_salarie: '', nom_prenom: '',
      date: new Date().toISOString().slice(0, 10),
      intitule: '',
    })
  }

  const editer = (r: EvenementRow) => {
    setPendingRow({
      id_salarie: r.id_salarie, nom_prenom: r.nom_prenom,
      date: r.date, intitule: r.intitule, id_evenement: r.id_evenement,
    })
  }

  const save = async () => {
    if (!pendingRow) return
    if (!pendingRow.id_salarie) {
      showToast('Choisis un salarié', 'info'); return
    }
    if (!pendingRow.date) { showToast('Date requise', 'info'); return }
    const url = pendingRow.id_evenement
      ? `${API_BASE}/scool/formations/${idFormation}/evenements/${pendingRow.id_evenement}`
      : `${API_BASE}/scool/formations/${idFormation}/evenements`
    const method = pendingRow.id_evenement ? 'PUT' : 'POST'
    const res = await fetch(url, {
      method,
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        date: pendingRow.date,
        id_salarie: pendingRow.id_salarie,
        intitule: pendingRow.intitule,
      }),
    })
    const d = await res.json()
    if (d.ok) { showToast('Enregistré', 'success'); setPendingRow(null); await load() }
    else showToast('Erreur', 'error')
  }

  const supprimer = async (r: EvenementRow) => {
    if (!await showConfirm({
      title: 'Supprimer',
      message: `Supprimer l'évènement du ${shortDate(r.date)} ?`,
    })) return
    await fetch(
      `${API_BASE}/scool/formations/${idFormation}/evenements/${r.id_evenement}`,
      { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    await load()
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center gap-2 mb-3">
        <button onClick={nouveau}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm">
          <Plus className="w-4 h-4" /> Ajouter un évènement
        </button>
      </div>

      <table className="text-xs w-full">
        <thead className="bg-[#F5F5F0]">
          <tr>
            <th className="py-1.5 px-2 text-left">Date</th>
            <th className="py-1.5 px-2 text-left">Responsable</th>
            <th className="py-1.5 px-2 text-left">Intitulé</th>
            <th className="py-1.5 px-2 text-right w-20"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id_evenement} className="border-b border-[#F0EDE5] hover:bg-[#ECF1F2]">
              <td className="py-1.5 px-2 tabular-nums">{shortDate(r.date)}</td>
              <td className="py-1.5 px-2">{r.nom_prenom}</td>
              <td className="py-1.5 px-2">{r.intitule}</td>
              <td className="py-1.5 px-2 text-right space-x-1">
                <button onClick={() => editer(r)}
                        className="p-1 rounded hover:bg-[#ECF1F2] text-[#8B7355]">
                  Modifier
                </button>
                <button onClick={() => supprimer(r)}
                        className="p-1 rounded hover:bg-red-50 text-[#B91C1C]">
                  <Trash2 className="w-3 h-3 inline" />
                </button>
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={4} className="py-6 text-center text-gray-400">Aucun évènement</td></tr>
          )}
        </tbody>
      </table>

      {pendingRow && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-[#17494E]">
                {pendingRow.id_evenement ? 'Modifier' : 'Ajouter'} un évènement
              </h3>
              <button onClick={() => setPendingRow(null)}
                      className="p-1 rounded hover:bg-gray-100"><X className="w-4 h-4" /></button>
            </div>
            <div className="space-y-3">
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Date</span>
                <input type="date" value={pendingRow.date}
                       onChange={(e) => setPendingRow({ ...pendingRow, date: e.target.value })}
                       className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
              </label>
              <div>
                <div className="text-xs text-[#8B7355] font-medium mb-1">Responsable</div>
                <button onClick={() => setPickerOpen(true)}
                        className="w-full flex items-center gap-2 px-3 py-1.5 border border-[#E5E0D5] rounded text-left hover:bg-[#ECF1F2]">
                  <UserPlus className="w-4 h-4 text-[#17494E]" />
                  <span className={`flex-1 ${pendingRow.nom_prenom ? 'text-[#17494E]' : 'text-gray-400'}`}>
                    {pendingRow.nom_prenom || 'Choisir...'}
                  </span>
                </button>
              </div>
              <label className="block text-xs">
                <span className="text-[#8B7355] font-medium">Intitulé</span>
                <input type="text" value={pendingRow.intitule}
                       onChange={(e) => setPendingRow({ ...pendingRow, intitule: e.target.value })}
                       className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
              </label>
            </div>
            <div className="flex gap-2 mt-4">
              <button onClick={save}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white hover:bg-[#0F3438]">
                <Save className="w-4 h-4" /> Enregistrer
              </button>
              <button onClick={() => setPendingRow(null)}
                      className="flex-1 px-3 py-2 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]">
                Annuler
              </button>
            </div>

            {pickerOpen && (
              <PersonnePicker
                title="Choisir un responsable"
                onClose={() => setPickerOpen(false)}
                onSelect={(s: SalarieItem) => {
                  setPickerOpen(false)
                  setPendingRow({
                    ...pendingRow,
                    id_salarie: s.id_salarie,
                    nom_prenom: `${s.nom} ${s.prenom[0]?.toUpperCase() || ''}${(s.prenom.slice(1) || '').toLowerCase()}`,
                  })
                }}
              />
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// =====================================================================
// Onglet Eleves
// =====================================================================

interface EleveRow {
  id_salarie: string
  nom: string; prenom: string
  du: string; au: string
  en_activite: boolean
  type_sortie: string
  livrable: boolean
  nb_fibre_brut: number
  nb_fibre_hr: number
  nb_cqt_brut: number
  nb_cqt_hr: number
}

function ElevesTab({ idFormation }: { idFormation: string }) {
  const [rows, setRows] = useState<EleveRow[]>([])
  const [uniquActifs, setUniquActifs] = useState(true)
  const [pickerOpen, setPickerOpen] = useState(false)

  const load = useCallback(async () => {
    const r = await fetch(
      `${API_BASE}/scool/formations/${idFormation}/eleves?uniquement_actifs=${uniquActifs}`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
    setRows(await r.json())
  }, [idFormation, uniquActifs])
  useEffect(() => { void load() }, [load])

  const onPick = async (s: SalarieItem) => {
    setPickerOpen(false)
    const r = await fetch(
      `${API_BASE}/scool/formations/${idFormation}/eleves`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id_salarie: s.id_salarie }),
      },
    )
    const d = await r.json()
    if (d.ok) { showToast('Élève ajouté', 'success'); await load() }
  }

  const toggleLivrable = async (r: EleveRow) => {
    await fetch(
      `${API_BASE}/scool/formations/${idFormation}/eleves/${r.id_salarie}/toggle-livrable`,
      { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    await load()
  }

  const supprimer = async (r: EleveRow) => {
    if (!await showConfirm({
      title: 'Retirer',
      message: `Retirer ${r.prenom} ${r.nom} de la formation ?`,
    })) return
    await fetch(
      `${API_BASE}/scool/formations/${idFormation}/eleves/${r.id_salarie}`,
      { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    await load()
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <button onClick={() => setPickerOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm">
          <UserPlus className="w-4 h-4" /> Ajouter un élève
        </button>
        <label className="flex items-center gap-2 text-xs">
          <input type="checkbox" checked={uniquActifs}
                 onChange={(e) => setUniquActifs(e.target.checked)}
                 className="accent-[#17494E]" />
          <span className="text-[#8B7355]">Uniquement les stagiaires actifs</span>
        </label>
        <span className="ml-auto text-[10px] text-red-700 italic">* HR : Hors Rejet</span>
      </div>

      <div className="overflow-x-auto">
        <table className="text-xs w-full">
          <thead className="bg-[#17494E] text-white">
            <tr>
              <th className="py-1.5 px-2 text-left">Nom</th>
              <th className="py-1.5 px-2 text-left">Prénom</th>
              <th className="py-1.5 px-2 text-left">Du</th>
              <th className="py-1.5 px-2 text-left">Au</th>
              <th className="py-1.5 px-2 text-center">Actif</th>
              <th className="py-1.5 px-2 text-left">Type sortie</th>
              <th className="py-1.5 px-2 text-center">Livrable</th>
              <th className="py-1.5 px-2 text-right">Fibre brut</th>
              <th className="py-1.5 px-2 text-right">Fibre HR*</th>
              <th className="py-1.5 px-2 text-right">CQT brut</th>
              <th className="py-1.5 px-2 text-right">CQT HR*</th>
              <th className="py-1.5 px-2 w-8"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id_salarie} className="border-b border-[#F0EDE5] hover:bg-[#ECF1F2]">
                <td className="py-1 px-2 font-medium">{r.nom}</td>
                <td className="py-1 px-2">{r.prenom}</td>
                <td className="py-1 px-2 tabular-nums">{shortDate(r.du)}</td>
                <td className="py-1 px-2 tabular-nums">{shortDate(r.au)}</td>
                <td className="py-1 px-2 text-center">
                  {r.en_activite ? <Check className="w-3 h-3 inline text-green-700" /> : ''}
                </td>
                <td className="py-1 px-2">{r.type_sortie}</td>
                <td className="py-1 px-2 text-center">
                  <button onClick={() => toggleLivrable(r)}
                          className="p-0.5 rounded hover:bg-[#ECF1F2]"
                          title="Basculer livrable">
                    {r.livrable
                      ? <Check className="w-3 h-3 text-green-700" />
                      : <X className="w-3 h-3 text-gray-400" />}
                  </button>
                </td>
                <td className="py-1 px-2 text-right tabular-nums">{r.nb_fibre_brut || ''}</td>
                <td className="py-1 px-2 text-right tabular-nums">{r.nb_fibre_hr || ''}</td>
                <td className="py-1 px-2 text-right tabular-nums">{r.nb_cqt_brut || ''}</td>
                <td className="py-1 px-2 text-right tabular-nums">{r.nb_cqt_hr || ''}</td>
                <td className="py-1 px-2 text-right">
                  <button onClick={() => supprimer(r)}
                          className="p-0.5 rounded hover:bg-red-50 text-[#B91C1C]"
                          title="Retirer">
                    <Trash2 className="w-3 h-3" />
                  </button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={12} className="py-6 text-center text-gray-400">Aucun élève</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {pickerOpen && (
        <PersonnePicker
          title="Ajouter un élève"
          onClose={() => setPickerOpen(false)}
          onSelect={onPick}
        />
      )}
    </div>
  )
}

// =====================================================================
// Onglet Session de recrut
// =====================================================================

interface SessionRecrutRow {
  id_formation_prev_recrut: string
  id_prevision_recrut: string
  idorganigramme: string
  lib_orga: string
  date_debut: string
  date_fin: string
  date_session: string
  lib_lieu: string
}

function SessionRecrutTab({ idFormation }: { idFormation: string }) {
  const [rows, setRows] = useState<SessionRecrutRow[]>([])

  const load = useCallback(async () => {
    const r = await fetch(
      `${API_BASE}/scool/formations/${idFormation}/sessions-recrut`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
    setRows(await r.json())
  }, [idFormation])
  useEffect(() => { void load() }, [load])

  const ajouter = async () => {
    const id = window.prompt(
      'ID de la prévision de recrutement à associer :', '',
    )
    if (!id || !id.trim() || !/^\d+$/.test(id.trim())) return
    const r = await fetch(
      `${API_BASE}/scool/formations/${idFormation}/sessions-recrut`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id_prevision_recrut: id.trim() }),
      },
    )
    const d = await r.json()
    if (d.ok) { showToast('Session associée', 'success'); await load() }
    else showToast('Erreur', 'error')
  }

  const supprimer = async (r: SessionRecrutRow) => {
    if (!await showConfirm({
      title: 'Retirer',
      message: 'Retirer l\'association avec cette session ?',
    })) return
    await fetch(
      `${API_BASE}/scool/formations/${idFormation}/sessions-recrut/${r.id_formation_prev_recrut}`,
      { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    await load()
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center gap-2 mb-3">
        <button onClick={ajouter}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm">
          <Plus className="w-4 h-4" /> Associer une session
        </button>
      </div>

      <table className="text-xs w-full">
        <thead className="bg-[#F5F5F0]">
          <tr>
            <th className="py-1.5 px-2 text-left">Organigramme</th>
            <th className="py-1.5 px-2 text-left">Date Début</th>
            <th className="py-1.5 px-2 text-left">Date Fin</th>
            <th className="py-1.5 px-2 text-left">Date Session</th>
            <th className="py-1.5 px-2 text-left">Lieu</th>
            <th className="py-1.5 px-2 w-8"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id_formation_prev_recrut} className="border-b border-[#F0EDE5]">
              <td className="py-1.5 px-2 font-medium">{r.lib_orga}</td>
              <td className="py-1.5 px-2 tabular-nums">{shortDate(r.date_debut)}</td>
              <td className="py-1.5 px-2 tabular-nums">{shortDate(r.date_fin)}</td>
              <td className="py-1.5 px-2 tabular-nums">{shortDate(r.date_session)}</td>
              <td className="py-1.5 px-2">{r.lib_lieu}</td>
              <td className="py-1.5 px-2 text-right">
                <button onClick={() => supprimer(r)}
                        className="p-0.5 rounded hover:bg-red-50 text-[#B91C1C]">
                  <Trash2 className="w-3 h-3" />
                </button>
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={6} className="py-6 text-center text-gray-400">
              Aucune session associée
            </td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

// =====================================================================
// Onglet Bulletins (lecture + delete)
// =====================================================================

interface BulletinRow {
  id_bulletin: string
  id_salarie: string
  stagiaire: string
  du: string; au: string
  type_bulletin: number
}

function BulletinsTab({ idFormation }: { idFormation: string }) {
  const [rows, setRows] = useState<BulletinRow[]>([])

  const load = useCallback(async () => {
    const r = await fetch(
      `${API_BASE}/scool/formations/${idFormation}/bulletins`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
    setRows(await r.json())
  }, [idFormation])
  useEffect(() => { void load() }, [load])

  const supprimer = async (r: BulletinRow) => {
    if (!await showConfirm({
      title: 'Supprimer', message: `Supprimer le bulletin de ${r.stagiaire} ?`,
    })) return
    await fetch(
      `${API_BASE}/scool/formations/${idFormation}/bulletins/${r.id_bulletin}`,
      { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    await load()
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <p className="text-xs text-gray-500 mb-2 italic">
        La saisie complète du bulletin (notes, mentions...) sera dispo dans une prochaine session.
      </p>

      <table className="text-xs w-full">
        <thead className="bg-[#17494E] text-white">
          <tr>
            <th className="py-1.5 px-2 text-left">Stagiaire</th>
            <th className="py-1.5 px-2 text-left">Du</th>
            <th className="py-1.5 px-2 text-left">Au</th>
            <th className="py-1.5 px-2 text-center">Bulletin final</th>
            <th className="py-1.5 px-2 w-8"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id_bulletin} className="border-b border-[#F0EDE5]">
              <td className="py-1.5 px-2 font-medium">{r.stagiaire}</td>
              <td className="py-1.5 px-2 tabular-nums">{shortDate(r.du)}</td>
              <td className="py-1.5 px-2 tabular-nums">{shortDate(r.au)}</td>
              <td className="py-1.5 px-2 text-center">
                {r.type_bulletin === 1
                  ? <Check className="w-3 h-3 inline text-green-700" />
                  : ''}
              </td>
              <td className="py-1.5 px-2 text-right">
                <button onClick={() => supprimer(r)}
                        className="p-0.5 rounded hover:bg-red-50 text-[#B91C1C]">
                  <Trash2 className="w-3 h-3" />
                </button>
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={5} className="py-6 text-center text-gray-400">Aucun bulletin</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

// =====================================================================
// Onglet Bareme Notes
// =====================================================================

interface BaremeNoteRow {
  id_bareme: string
  type_note: string
  palier: number
  note: number
  sens_recherche: string
}

const TYPES_NOTE = [
  'Assiduite', 'CttHR', 'CQT', 'Premium', 'Mob', 'ObjDecale', 'Coopt',
  'AppTheo', 'AppPratique',
]

function BaremeTab({ idFormation }: { idFormation: string }) {
  const [rows, setRows] = useState<BaremeNoteRow[]>([])
  const [sel, setSel] = useState<BaremeNoteRow | null>(null)
  const [form, setForm] = useState<BaremeNoteRow>({
    id_bareme: '', type_note: '', palier: 0, note: 0, sens_recherche: 'ASC',
  })

  const load = useCallback(async () => {
    const r = await fetch(
      `${API_BASE}/scool/formations/${idFormation}/baremes`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
    setRows(await r.json())
  }, [idFormation])
  useEffect(() => { void load() }, [load])

  const nouveau = () => {
    setSel(null)
    setForm({
      id_bareme: '', type_note: '', palier: 0, note: 0, sens_recherche: 'ASC',
    })
  }

  const selectRow = (r: BaremeNoteRow) => {
    setSel(r)
    setForm({ ...r })
  }

  const save = async () => {
    if (!form.type_note) { showToast('Type de note requis', 'info'); return }
    const url = form.id_bareme
      ? `${API_BASE}/scool/formations/${idFormation}/baremes/${form.id_bareme}`
      : `${API_BASE}/scool/formations/${idFormation}/baremes`
    const method = form.id_bareme ? 'PUT' : 'POST'
    const r = await fetch(url, {
      method,
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        type_note: form.type_note,
        palier: form.palier,
        note: form.note,
        sens_recherche: form.sens_recherche,
      }),
    })
    const d = await r.json()
    if (d.ok) { showToast('Enregistré', 'success'); await load(); nouveau() }
  }

  const supprimer = async (r: BaremeNoteRow) => {
    if (!await showConfirm({
      title: 'Supprimer', message: `Supprimer ce barème ${r.type_note} ?`,
    })) return
    await fetch(
      `${API_BASE}/scool/formations/${idFormation}/baremes/${r.id_bareme}`,
      { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    await load()
  }

  // Groupement par type_note
  const groupes = (() => {
    const map = new Map<string, BaremeNoteRow[]>()
    rows.forEach((r) => {
      const arr = map.get(r.type_note) || []
      arr.push(r); map.set(r.type_note, arr)
    })
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b))
  })()

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)] gap-4">
        {/* Gauche : liste groupée par type */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <button onClick={nouveau}
                    className="p-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438]">
              <Plus className="w-4 h-4" />
            </button>
            <span className="text-xs text-[#8B7355]">
              {rows.length} barème(s)
            </span>
          </div>
          <div className="max-h-[50vh] overflow-y-auto">
            {groupes.map(([type, list]) => (
              <div key={type} className="mb-3">
                <div className="text-xs font-semibold text-[#17494E] bg-[#F5F5F0] px-2 py-1">
                  {type} <span className="text-[#8B7355] font-normal">({list.length})</span>
                </div>
                <table className="text-xs w-full">
                  <thead>
                    <tr className="text-[#8B7355] border-b border-[#F0EDE5]">
                      <th className="py-1 px-2 text-right">Palier</th>
                      <th className="py-1 px-2 text-right">Note</th>
                      <th className="py-1 px-2 text-center">Sens</th>
                      <th className="py-1 px-2 w-8"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {list.map((r) => (
                      <tr key={r.id_bareme}
                          onClick={() => selectRow(r)}
                          className={`cursor-pointer border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${
                            sel?.id_bareme === r.id_bareme ? 'bg-[#FFF5E0]' : ''
                          }`}>
                        <td className="py-1 px-2 text-right tabular-nums">{r.palier}</td>
                        <td className="py-1 px-2 text-right tabular-nums">{r.note}</td>
                        <td className="py-1 px-2 text-center">
                          {r.sens_recherche === 'DESC' ? '≤' : '≥'}
                        </td>
                        <td className="py-1 px-2 text-right">
                          <button onClick={(e) => { e.stopPropagation(); void supprimer(r) }}
                                  className="p-0.5 rounded hover:bg-red-50 text-[#B91C1C]">
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
            {groupes.length === 0 && (
              <div className="py-8 text-center text-gray-400 text-xs">Aucun barème</div>
            )}
          </div>
        </div>

        {/* Droite : formulaire édition */}
        <div className="border border-[#F0EDE5] rounded p-3 h-fit sticky top-4">
          <h4 className="text-sm font-semibold text-[#17494E] mb-3">
            {form.id_bareme ? 'Modifier' : 'Nouveau'} barème
          </h4>
          <div className="space-y-2">
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Type notation</span>
              <select value={form.type_note}
                      onChange={(e) => setForm({ ...form, type_note: e.target.value })}
                      className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded">
                <option value="">—</option>
                {TYPES_NOTE.map((t) => (<option key={t} value={t}>{t}</option>))}
              </select>
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Palier</span>
              <input type="number" step="0.01" value={form.palier}
                     onChange={(e) => setForm({ ...form, palier: Number(e.target.value) })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Note</span>
              <input type="number" step="0.01" value={form.note}
                     onChange={(e) => setForm({ ...form, note: Number(e.target.value) })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <div>
              <div className="text-xs text-[#8B7355] font-medium mb-1">
                Pour obtenir la note, le score réalisé doit être :
              </div>
              <div className="flex rounded border border-[#E5E0D5]">
                <button onClick={() => setForm({ ...form, sens_recherche: 'ASC' })}
                        className={`flex-1 px-3 py-1.5 text-xs ${
                          form.sens_recherche === 'ASC' ? 'bg-[#17494E] text-white' : 'text-[#17494E]'
                        }`}>
                  ≥ Supérieur ou égal
                </button>
                <button onClick={() => setForm({ ...form, sens_recherche: 'DESC' })}
                        className={`flex-1 px-3 py-1.5 text-xs ${
                          form.sens_recherche === 'DESC' ? 'bg-[#17494E] text-white' : 'text-[#17494E]'
                        }`}>
                  ≤ Inférieur ou égal
                </button>
              </div>
            </div>
            <button onClick={save}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm mt-2">
              <Save className="w-4 h-4" /> Enregistrer
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
