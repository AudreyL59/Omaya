/**
 * Fen_ScoolFormation - Liste des formations S'Cool.
 *
 * Filtres : date debut affichage + uniquement actives
 * Actions : Nouvelle / Dupliquer / Editer (crayon) / Modele / Supprimer
 * Tableau : Prod / Ville / Intitule / Du / Au / Cloturee / H Salle / H Terrain
 */
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Plus, Copy, Trash2, BookOpen, Save, X, Search, Check, FileText,
  Loader2,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'

const API_BASE = '/api/adm'

interface FormationRow {
  id_formation: string
  intitule: string
  date_debut: string
  date_fin: string
  ville_formation: string
  type_produit: string
  categorie: string
  formateur1_nom: string
  formateur2_nom: string
  nb_heure_salle: number
  nb_heure_terrain: number
  heure_jour_salle: number
  heure_jour_terrain: number
  duree: number
  formation_active: boolean
  formation_cloturee: boolean
}

interface EffectifRow {
  periode: string
  date: string
  nb_vend: number
  nb_vend_prod: number
  nb_ctt_brut: number
  nb_ctt_hr: number
  nb_cqt: number
  nb_cqt_hr: number
  nb_mig: number
  nb_mig_hr: number
  nb_mob_brut: number
  nb_mob_hr: number
}

interface StagiaireRow {
  id_stagiaire: string
  nom: string
  prenom: string
  du: string
  au: string
  en_activite: boolean
  type_sortie: string
  livrable: boolean
  nb_fibre_brut: number
  nb_fibre_hr: number
  nb_cqt_brut: number
  nb_cqt_hr: number
  nb_mig_brut: number
  nb_mig_hr: number
  nb_mob_brut: number
  nb_mob_hr: number
}

interface AnalyseFormation {
  id_formation: string
  intitule: string
  ville_formation: string
  du: string
  au: string
  formation_cloturee: boolean
  presents: number
  retenus: number
  jo: number
  intermediaires: number
  finaux: number
  nb_jours_terrain: number
  total_prod: number
  total_livrable: number
  total_cqt: number
  obj_cqt: number
  effectif: EffectifRow[]
  stagiaires: StagiaireRow[]
}

interface FormationDetail extends FormationRow {
  dest_promo: string
  formateur3_nom: string
  formateur4_nom: string
  formateur5_nom: string
  formateur1_id: string
  formateur2_id: string
  formateur3_id: string
  formateur4_id: string
  formateur5_id: string
  id_modele_form?: string
}

interface FormateurCombo {
  id_formateur: string
  lib: string
  niveau: string
  is_actif: boolean
}

interface ModeleCombo {
  id_modele: string
  nom_formation: string
}

const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? ''
    : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

const currentDate = () => new Date().toISOString().slice(0, 10)

const TYPES_PROD = ['SFR', 'ENI', 'IAG', 'STR', 'VAL', 'PRO', 'OEN', 'TLC', 'ADV', 'RH']
const CATEGORIES = ['Formation initiale', 'Perfectionnement', 'Reprise', 'Autre']

export default function ScoolFormationsPage() {
  useDocumentTitle('Formations S\'Cool')
  const nav = useNavigate()

  const [formations, setFormations] = useState<FormationRow[]>([])
  const [afficherDepuis, setAfficherDepuis] = useState(currentDate())
  const [uniquActives, setUniquActives] = useState(true)
  const [loading, setLoading] = useState(false)

  const [selIdx, setSelIdx] = useState(-1)
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const [formateurs, setFormateurs] = useState<FormateurCombo[]>([])
  const [modeles, setModeles] = useState<ModeleCombo[]>([])
  const [analyses, setAnalyses] = useState<AnalyseFormation[]>([])
  const [analyseLoading, setAnalyseLoading] = useState(false)

  const [ficheModal, setFicheModal] = useState<{
    mode: 'new' | 'edit'
    data: FormationDetail
  } | null>(null)

  const loadFormations = useCallback(async () => {
    setLoading(true)
    try {
      const url = `${API_BASE}/scool/formations?` +
        `afficher_depuis_le=${encodeURIComponent(afficherDepuis)}` +
        `&uniquement_actives=${uniquActives}`
      const r = await fetch(url, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      const d: FormationRow[] = await r.json()
      setFormations(d || [])
    } finally { setLoading(false) }
  }, [afficherDepuis, uniquActives])

  useEffect(() => { void loadFormations() }, [loadFormations])

  // Chargements one-shot des combos
  useEffect(() => {
    void fetch(`${API_BASE}/scool/formateurs`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    }).then((r) => r.json()).then(setFormateurs).catch(() => {})
    void fetch(`${API_BASE}/scool/modeles-combo`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    }).then((r) => r.json()).then(setModeles).catch(() => {})
  }, [])

  const emptyDetail = (): FormationDetail => ({
    id_formation: '', intitule: '',
    date_debut: '', date_fin: '',
    ville_formation: '', type_produit: '', categorie: '',
    dest_promo: '',
    formateur1_nom: '', formateur2_nom: '',
    formateur3_nom: '', formateur4_nom: '', formateur5_nom: '',
    formateur1_id: '', formateur2_id: '',
    formateur3_id: '', formateur4_id: '', formateur5_id: '',
    nb_heure_salle: 0, nb_heure_terrain: 0,
    heure_jour_salle: 8, heure_jour_terrain: 8,
    duree: 0, formation_active: true, formation_cloturee: false,
  })

  const nouvelle = () => setFicheModal({
    mode: 'new', data: emptyDetail(),
  })

  const editer = (idx: number) => {
    nav(`/scool/formations/${formations[idx].id_formation}`)
  }

  const dupliquer = async (idx: number) => {
    const dup_prog = await showConfirm({
      title: 'Dupliquer',
      message: 'Dupliquer aussi le programme de formation ?',
    })
    const r = await fetch(
      `${API_BASE}/scool/formations/${formations[idx].id_formation}/dupliquer?dupliquer_programme=${dup_prog}`,
      { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    const d = await r.json()
    if (d.ok) {
      showToast('Formation dupliquée', 'success')
      await loadFormations()
    }
  }

  const supprimer = async (idx: number) => {
    if (!await showConfirm({
      title: 'Supprimer',
      message: `Supprimer la formation "${formations[idx].intitule}" ?`,
    })) return
    await fetch(
      `${API_BASE}/scool/formations/${formations[idx].id_formation}`,
      { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    await loadFormations()
    setSelIdx(-1)
  }

  const saveFiche = async () => {
    if (!ficheModal) return
    if (!ficheModal.data.intitule.trim()) {
      showToast('Intitulé requis', 'info')
      return
    }
    const url = ficheModal.mode === 'new'
      ? `${API_BASE}/scool/formations`
      : `${API_BASE}/scool/formations/${ficheModal.data.id_formation}`
    const method = ficheModal.mode === 'new' ? 'POST' : 'PUT'
    const {
      id_formation: _, formateur1_nom: __, formateur2_nom: ___,
      formateur3_nom: ____, formateur4_nom: _____, formateur5_nom: ______,
      ...payload
    } = ficheModal.data
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
      setFicheModal(null)
      await loadFormations()
    } else showToast('Erreur', 'error')
  }

  const toggleSel = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelAll = () => {
    if (selected.size === formations.length) setSelected(new Set())
    else setSelected(new Set(formations.map((f) => f.id_formation)))
  }

  const doAnalyse = async () => {
    if (selected.size === 0) {
      showToast('Coche au moins une formation', 'info')
      return
    }
    setAnalyseLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/scool/formations/analyse-promo`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ id_formations: Array.from(selected) }),
        },
      )
      if (!r.ok) { showToast('Erreur analyse', 'error'); return }
      const d: AnalyseFormation[] = await r.json()
      setAnalyses(d)
      showToast(`${d.length} formation(s) analysée(s)`, 'success')
      // Scroll vers le bas
      setTimeout(() => {
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
      }, 100)
    } finally { setAnalyseLoading(false) }
  }

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-full mx-auto">
        <PageHeader icon={BookOpen} title="Formations S'Cool" />

        {/* Barre actions + filtres */}
        <div className="bg-white rounded-lg shadow p-3 mb-4">
          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={nouvelle}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#17494E] text-white hover:bg-[#0F3438] text-sm">
              <Plus className="w-4 h-4" /> Nouvelle Formation
            </button>
            <button
              onClick={() => selIdx >= 0 && dupliquer(selIdx)}
              disabled={selIdx < 0}
              title="Dupliquer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] text-sm disabled:opacity-40">
              <Copy className="w-4 h-4" /> Dupliquer
            </button>
            <button
              onClick={() => selIdx >= 0 && editer(selIdx)}
              disabled={selIdx < 0}
              title="Éditer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] text-sm disabled:opacity-40">
              Éditer
            </button>
            <button
              onClick={() => showToast('Modèles de formation - à venir', 'info')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] text-sm">
              Modèle Formation
            </button>
            <button
              onClick={() => selIdx >= 0 && supprimer(selIdx)}
              disabled={selIdx < 0}
              title="Supprimer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#B91C1C] text-[#B91C1C] hover:bg-red-50 text-sm disabled:opacity-40">
              <Trash2 className="w-4 h-4" /> Supprimer
            </button>

            <div className="ml-auto flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs text-[#8B7355]">
                Afficher depuis le
                <input type="date" value={afficherDepuis}
                       onChange={(e) => setAfficherDepuis(e.target.value)}
                       className="px-2 py-1 border border-[#E5E0D5] rounded" />
              </label>
              <label className="flex items-center gap-2 text-xs">
                <input type="checkbox" checked={uniquActives}
                       onChange={(e) => setUniquActives(e.target.checked)}
                       className="accent-[#17494E]" />
                <span className="text-[#8B7355]">Uniquement Formations actives</span>
              </label>
            </div>
          </div>
        </div>

        {/* Tableau */}
        <div className="bg-white rounded-lg shadow p-3 mb-4">
          <div className="overflow-x-auto max-h-[55vh] overflow-y-auto">
            <table className="text-xs w-full">
              <thead className="sticky top-0 bg-[#17494E] text-white z-10">
                <tr>
                  <th className="py-2 px-2 w-8">
                    <input type="checkbox"
                           checked={selected.size > 0 && selected.size === formations.length}
                           onChange={toggleSelAll}
                           className="accent-white" />
                  </th>
                  <th className="py-2 px-2 text-left">Prod</th>
                  <th className="py-2 px-2 text-left">Ville Formation</th>
                  <th className="py-2 px-2 text-left">Intitulé</th>
                  <th className="py-2 px-2 text-left">Du</th>
                  <th className="py-2 px-2 text-left">Au</th>
                  <th className="py-2 px-2 text-center">Clôturée</th>
                  <th className="py-2 px-2 text-right">H Salle</th>
                  <th className="py-2 px-2 text-right">H Terrain</th>
                  <th className="py-2 px-2 text-left">Formateurs</th>
                </tr>
              </thead>
              <tbody>
                {formations.map((f, i) => (
                  <tr key={i}
                      onClick={() => setSelIdx(i)}
                      onDoubleClick={() => editer(i)}
                      className={`border-b border-[#F0EDE5] hover:bg-[#ECF1F2] cursor-pointer ${
                        selIdx === i ? 'bg-[#FFF5E0] ring-1 ring-[#8B7355]' : ''
                      }`}>
                    <td className="py-1.5 px-2" onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox"
                             checked={selected.has(f.id_formation)}
                             onChange={() => toggleSel(f.id_formation)}
                             className="accent-[#17494E]" />
                    </td>
                    <td className="py-1.5 px-2">{f.type_produit}</td>
                    <td className="py-1.5 px-2">{f.ville_formation}</td>
                    <td className="py-1.5 px-2 font-medium">{f.intitule}</td>
                    <td className="py-1.5 px-2 tabular-nums">{shortDate(f.date_debut)}</td>
                    <td className="py-1.5 px-2 tabular-nums">{shortDate(f.date_fin)}</td>
                    <td className="py-1.5 px-2 text-center">
                      {f.formation_cloturee ? <Check className="w-3 h-3 inline text-green-700" /> : ''}
                    </td>
                    <td className="py-1.5 px-2 text-right tabular-nums">{f.nb_heure_salle}h</td>
                    <td className="py-1.5 px-2 text-right tabular-nums">{f.nb_heure_terrain}h</td>
                    <td className="py-1.5 px-2 text-[11px]">
                      {[f.formateur1_nom, f.formateur2_nom].filter(Boolean).join(' / ')}
                    </td>
                  </tr>
                ))}
                {formations.length === 0 && !loading && (
                  <tr><td colSpan={10} className="py-8 text-center text-gray-400">
                    Aucune formation
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Btn Analyse (bas) */}
        <div className="flex items-center gap-3 mb-4">
          <button onClick={doAnalyse}
                  disabled={selected.size === 0 || analyseLoading}
                  className="flex items-center gap-2 px-4 py-2 rounded bg-[#17494E] text-white hover:bg-[#0F3438] disabled:opacity-40">
            <Search className="w-4 h-4" />
            Faire l'analyse des sessions sélectionnées ({selected.size})
          </button>
        </div>

        {/* Résultats analyse promo */}
        {analyses.length > 0 && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-[#17494E] flex items-center gap-2">
              <Search className="w-4 h-4" /> Analyse des promotions
            </h2>
            {analyses.map((a) => (
              <AnalysePromoCard key={a.id_formation} data={a} />
            ))}
          </div>
        )}
      </div>

      {/* Fiche formation modale */}
      {ficheModal && (
        <FicheFormationModal
          data={ficheModal.data}
          mode={ficheModal.mode}
          formateurs={formateurs}
          modeles={modeles}
          onChange={(d) => setFicheModal({ ...ficheModal, data: d })}
          onSave={saveFiche}
          onClose={() => setFicheModal(null)}
        />
      )}
    </div>
  )
}

// =====================================================================
// Modale Fiche Formation
// =====================================================================

function FicheFormationModal({
  data, mode, formateurs, modeles, onChange, onSave, onClose,
}: {
  data: FormationDetail
  mode: 'new' | 'edit'
  formateurs: FormateurCombo[]
  modeles: ModeleCombo[]
  onChange: (d: FormationDetail) => void
  onSave: () => void
  onClose: () => void
}) {
  const setFormateur = (idx: number, id: string) => {
    const f = formateurs.find((x) => x.id_formateur === id)
    const key = `formateur${idx}_id` as keyof FormationDetail
    const keyNom = `formateur${idx}_nom` as keyof FormationDetail
    onChange({
      ...data,
      [key]: id,
      [keyNom]: f ? f.lib : '',
    })
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl p-4 my-8">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-[#17494E]">
            {mode === 'new' ? 'Nouvelle Formation' : 'Éditer Formation'}
          </h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3">
          {mode === 'new' && (
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Utiliser ce modèle</span>
              <select value={data.id_modele_form || '0'}
                      onChange={(e) => onChange({ ...data, id_modele_form: e.target.value })}
                      className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded">
                {modeles.map((m) => (
                  <option key={m.id_modele} value={m.id_modele}>
                    {m.nom_formation}
                  </option>
                ))}
              </select>
            </label>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label className="block text-xs md:col-span-2">
              <span className="text-[#8B7355] font-medium">Intitulé *</span>
              <input type="text" value={data.intitule}
                     onChange={(e) => onChange({ ...data, intitule: e.target.value })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Ville Formation</span>
              <input type="text" value={data.ville_formation}
                     onChange={(e) => onChange({ ...data, ville_formation: e.target.value })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Type Produit</span>
              <select value={data.type_produit}
                      onChange={(e) => onChange({ ...data, type_produit: e.target.value })}
                      className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded">
                <option value="">—</option>
                {TYPES_PROD.map((t) => (<option key={t} value={t}>{t}</option>))}
              </select>
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Catégorie</span>
              <select value={data.categorie}
                      onChange={(e) => onChange({ ...data, categorie: e.target.value })}
                      className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded">
                <option value="">—</option>
                {CATEGORIES.map((t) => (<option key={t} value={t}>{t}</option>))}
              </select>
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Destinataires Promo</span>
              <input type="text" value={data.dest_promo}
                     onChange={(e) => onChange({ ...data, dest_promo: e.target.value })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Date début</span>
              <input type="date" value={data.date_debut}
                     onChange={(e) => onChange({ ...data, date_debut: e.target.value })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Date fin</span>
              <input type="date" value={data.date_fin}
                     onChange={(e) => onChange({ ...data, date_fin: e.target.value })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
          </div>

          <div className="grid grid-cols-4 gap-3">
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Nb h Salle</span>
              <input type="number" min={0} value={data.nb_heure_salle}
                     onChange={(e) => onChange({ ...data, nb_heure_salle: Number(e.target.value) })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">Nb h Terrain</span>
              <input type="number" min={0} value={data.nb_heure_terrain}
                     onChange={(e) => onChange({ ...data, nb_heure_terrain: Number(e.target.value) })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">H/j Salle</span>
              <input type="number" min={0} value={data.heure_jour_salle}
                     onChange={(e) => onChange({ ...data, heure_jour_salle: Number(e.target.value) })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
            <label className="block text-xs">
              <span className="text-[#8B7355] font-medium">H/j Terrain</span>
              <input type="number" min={0} value={data.heure_jour_terrain}
                     onChange={(e) => onChange({ ...data, heure_jour_terrain: Number(e.target.value) })}
                     className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded" />
            </label>
          </div>

          {/* Formateurs */}
          <div>
            <div className="text-xs text-[#8B7355] font-medium mb-1">Formateurs</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {[1, 2, 3, 4, 5].map((idx) => {
                const idKey = `formateur${idx}_id` as keyof FormationDetail
                const id = (data[idKey] as string) || ''
                const label = idx === 1 ? 'Formateur principal'
                  : idx === 2 ? 'Formateur adjoint'
                  : `Formateur ${idx}`
                return (
                  <label key={idx} className="block text-xs">
                    <span className="text-[#8B7355] font-medium">{label}</span>
                    <select value={id}
                            onChange={(e) => setFormateur(idx, e.target.value)}
                            className="w-full mt-1 px-2 py-1.5 border border-[#E5E0D5] rounded">
                      <option value="">Non renseigné</option>
                      {formateurs.map((f) => (
                        <option key={f.id_formateur} value={f.id_formateur}
                                disabled={!f.is_actif}>
                          {f.lib}{!f.is_actif ? ' (inactif)' : ''}
                        </option>
                      ))}
                    </select>
                  </label>
                )
              })}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={data.formation_active}
                     onChange={(e) => onChange({ ...data, formation_active: e.target.checked })}
                     className="accent-[#17494E]" />
              <span className="text-[#8B7355]">Formation active</span>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={data.formation_cloturee}
                     onChange={(e) => onChange({ ...data, formation_cloturee: e.target.checked })}
                     className="accent-[#17494E]" />
              <span className="text-[#8B7355]">Formation clôturée</span>
            </label>
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <button onClick={onSave}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded bg-[#17494E] text-white hover:bg-[#0F3438]">
            <Save className="w-4 h-4" /> Enregistrer
          </button>
          <button onClick={onClose}
                  className="flex-1 px-3 py-2 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2]">
            Annuler
          </button>
        </div>

      </div>
    </div>
  )
}

// =====================================================================
// AnalysePromoCard - une fiche d'analyse par formation
// =====================================================================

function AnalysePromoCard({ data: a }: { data: AnalyseFormation }) {
  const txLiv = a.jo > 0 ? Math.round((a.total_livrable / a.jo) * 1000) / 10 : 0
  const txCqt = a.obj_cqt > 0 ? Math.round((a.total_cqt / a.obj_cqt) * 1000) / 10 : 0
  const [pdfLoading, setPdfLoading] = useState(false)

  const downloadPdf = async () => {
    if (pdfLoading) return
    setPdfLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/scool/formations/${a.id_formation}/analyse-promo-pdf`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        showToast('Erreur génération PDF', 'error')
        return
      }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const disp = r.headers.get('Content-Disposition') || ''
      const m = disp.match(/filename="?([^";]+)"?/)
      const fic = m ? m[1] : 'analyse.pdf'
      const link = document.createElement('a')
      link.href = url; link.download = fic; link.click()
      setTimeout(() => URL.revokeObjectURL(url), 30_000)
    } finally { setPdfLoading(false) }
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="mb-4 pb-3 border-b border-[#F0EDE5] flex items-start gap-2">
        <div className="flex-1">
          <h3 className="text-base font-semibold text-[#17494E]">
            {a.intitule}
            {a.ville_formation && (
              <span className="ml-2 text-[#8B7355] font-normal">// {a.ville_formation}</span>
            )}
          </h3>
          <div className="flex gap-4 mt-1 text-xs text-[#8B7355]">
            <span>Promo du {shortDate(a.du)} au {shortDate(a.au)}</span>
            <span>nb Jours Terrain : <b className="text-[#17494E]">{a.nb_jours_terrain}</b></span>
            {a.formation_cloturee && (
              <span className="px-2 py-0.5 rounded bg-green-100 text-green-800 text-[10px]">
                Formation Clôturée
              </span>
            )}
          </div>
        </div>
        <button onClick={downloadPdf}
                disabled={pdfLoading}
                title="Télécharger la version PDF"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] hover:bg-[#ECF1F2] text-sm disabled:opacity-60 disabled:cursor-wait">
          {pdfLoading
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Génération...</>
            : <><FileText className="w-4 h-4" /> PDF</>}
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4 text-xs">
        <div className="p-3 rounded bg-[#F5F5F0]">
          <div className="text-[#8B7355] mb-1">Recrutement</div>
          <div className="text-[#17494E] text-sm">
            <b>{a.presents}</b> présents · <b>{a.retenus}</b> retenus · <b>{a.jo}</b> JO
          </div>
        </div>
        <div className="p-3 rounded bg-[#F5F5F0]">
          <div className="text-[#8B7355] mb-1">Bulletins édités</div>
          <div className="text-[#17494E] text-sm">
            <b>{a.intermediaires}</b> intermédiaires · <b>{a.finaux}</b> finaux
          </div>
        </div>
        <div className="p-3 rounded bg-[#F5F5F0]">
          <div className="text-[#8B7355] mb-1">Résultats Promo</div>
          <div className="text-[#17494E] text-sm">
            <b>{a.total_prod}</b> nb Prod · <b>{a.total_livrable}</b> livrable ·{' '}
            <b className={txLiv >= 100 ? 'text-green-700' : 'text-orange-700'}>
              {txLiv.toFixed(1)}%
            </b>
          </div>
        </div>
        <div className="p-3 rounded bg-[#F5F5F0]">
          <div className="text-[#8B7355] mb-1">Résultats CQT Premium</div>
          <div className="text-[#17494E] text-sm">
            <b>{a.total_cqt}</b> / <b>{a.obj_cqt}</b> ·{' '}
            <b className={txCqt >= 100 ? 'text-green-700' : 'text-orange-700'}>
              {txCqt.toFixed(1)}%
            </b>
          </div>
        </div>
      </div>

      <div className="mb-4">
        <h4 className="text-sm font-semibold text-[#17494E] mb-2">Effectifs et prod Promo</h4>
        <div className="overflow-x-auto">
          <table className="text-xs w-full">
            <thead className="bg-[#17494E] text-white">
              <tr>
                <th className="py-1.5 px-2 text-left">Période</th>
                <th className="py-1.5 px-2 text-left">Date</th>
                <th className="py-1.5 px-2 text-right">NB Vend</th>
                <th className="py-1.5 px-2 text-right">nb Vend Prod</th>
                <th className="py-1.5 px-2 text-right">Fibre brut</th>
                <th className="py-1.5 px-2 text-right">Fibre HR*</th>
                <th className="py-1.5 px-2 text-right">CQT Brut</th>
                <th className="py-1.5 px-2 text-right">CQT HR*</th>
                <th className="py-1.5 px-2 text-right">Mig Brut</th>
                <th className="py-1.5 px-2 text-right">Mig HR*</th>
                <th className="py-1.5 px-2 text-right">Mob Brut</th>
                <th className="py-1.5 px-2 text-right">Mob HR*</th>
              </tr>
            </thead>
            <tbody>
              {a.effectif.map((e, i) => (
                <tr key={i} className="border-b border-[#F0EDE5]">
                  <td className="py-1 px-2 font-medium">{e.periode}</td>
                  <td className="py-1 px-2 tabular-nums">{shortDate(e.date)}</td>
                  <td className="py-1 px-2 text-right tabular-nums">{e.nb_vend}</td>
                  <td className="py-1 px-2 text-right tabular-nums">{e.nb_vend_prod}</td>
                  <td className="py-1 px-2 text-right tabular-nums">{e.nb_ctt_brut}</td>
                  <td className="py-1 px-2 text-right tabular-nums">{e.nb_ctt_hr}</td>
                  <td className="py-1 px-2 text-right tabular-nums">{e.nb_cqt}</td>
                  <td className="py-1 px-2 text-right tabular-nums">{e.nb_cqt_hr}</td>
                  <td className="py-1 px-2 text-right tabular-nums">{e.nb_mig}</td>
                  <td className="py-1 px-2 text-right tabular-nums">{e.nb_mig_hr}</td>
                  <td className="py-1 px-2 text-right tabular-nums">{e.nb_mob_brut}</td>
                  <td className="py-1 px-2 text-right tabular-nums">{e.nb_mob_hr}</td>
                </tr>
              ))}
              {a.effectif.length === 0 && (
                <tr><td colSpan={12} className="py-4 text-center text-gray-400">Aucune étape</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h4 className="text-sm font-semibold text-[#17494E] mb-2">
          Stagiaires ({a.stagiaires.length})
        </h4>
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
              </tr>
            </thead>
            <tbody>
              {a.stagiaires.map((s, i) => (
                <tr key={i} className="border-b border-[#F0EDE5] hover:bg-[#ECF1F2]">
                  <td className="py-1 px-2 font-medium">{s.nom}</td>
                  <td className="py-1 px-2">{s.prenom}</td>
                  <td className="py-1 px-2 tabular-nums">{shortDate(s.du)}</td>
                  <td className="py-1 px-2 tabular-nums">{shortDate(s.au)}</td>
                  <td className="py-1 px-2 text-center">
                    {s.en_activite
                      ? <Check className="w-3 h-3 inline text-green-700" />
                      : ''}
                  </td>
                  <td className="py-1 px-2">{s.type_sortie}</td>
                  <td className="py-1 px-2 text-center">
                    {s.livrable ? <Check className="w-3 h-3 inline text-green-700" /> : ''}
                  </td>
                  <td className="py-1 px-2 text-right tabular-nums">{s.nb_fibre_brut || ''}</td>
                  <td className="py-1 px-2 text-right tabular-nums">{s.nb_fibre_hr || ''}</td>
                  <td className="py-1 px-2 text-right tabular-nums">{s.nb_cqt_brut || ''}</td>
                  <td className="py-1 px-2 text-right tabular-nums">{s.nb_cqt_hr || ''}</td>
                </tr>
              ))}
              {a.stagiaires.length === 0 && (
                <tr><td colSpan={11} className="py-4 text-center text-gray-400">Aucun stagiaire</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="text-[10px] text-red-700 italic mt-2">* HR : Hors Rejet</p>
      </div>
    </div>
  )
}
