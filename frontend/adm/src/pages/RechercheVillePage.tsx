/**
 * Fen_RechercheVille - Recherche / Ajouter une ville.
 *
 * Page picker de communes (divers.pgt_communes_france) :
 *   - Recherche : CP + Ville (bouton loupe)
 *   - Tableau resultats : Code Postal, Nom Ville
 *   - Bouton 'Ajouter une ville' visible uniquement si droit
 *     AjoutCommune, ouvre un bloc formulaire :
 *     * CP, Nom (SANS ACCENT), Département, CodePays (défaut FR),
 *       Code Commune, Latitude, Longitude
 *     * Liens externes : Google (chercher code commune)
 *       + coordonneesgps.net
 *     * Bouton 'Ajouter la ville' -> POST /rech-ville
 *
 * En mode standalone (accès menu), le bouton 'Choisir cette ville'
 * n'affiche qu'un toast indicatif : le picker mode sera utilisé
 * depuis d'autres écrans via un composant modal dédié (à venir).
 */
import { useCallback, useState } from 'react'
import {
  Search, Loader2, ArrowLeft, MapPin, Plus, Save, ExternalLink,
  CheckCircle2,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { useAuth } from '@/hooks/useAuth'

const API_BASE = '/api/adm'

interface Commune {
  id_communes_france: string
  code_postal: string; nom_ville: string; departement: string
  code_commune: string; code_pays: string
  latitude_deg: number; longitude_deg: number
  favorite: boolean
}

interface FormNewCommune {
  code_postal: string; nom_ville: string; departement: string
  code_commune: string; code_pays: string
  latitude_deg: number; longitude_deg: number
}

const EMPTY_FORM: FormNewCommune = {
  code_postal: '', nom_ville: '', departement: '',
  code_commune: '', code_pays: 'FR',
  latitude_deg: 0, longitude_deg: 0,
}

export default function RechercheVillePage() {
  useDocumentTitle('Rechercher / Ajouter une ville')
  const { user } = useAuth()
  const canAdd = (user?.droits || []).includes('AjoutCommune')

  const [cp, setCp] = useState('')
  const [nom, setNom] = useState('')
  const [rows, setRows] = useState<Commune[]>([])
  const [selected, setSelected] = useState<string>('')
  const [loading, setLoading] = useState(false)

  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState<FormNewCommune>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const rechercher = useCallback(async () => {
    setLoading(true)
    try {
      const q = `cp=${encodeURIComponent(cp)}&nom=${encodeURIComponent(nom)}`
      const r = await fetch(
        `${API_BASE}/rech-ville/search?${q}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d: Commune[] = await r.json()
      setRows(d)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [cp, nom])

  const choisirCetteVille = () => {
    const sel = rows.find(r => r.id_communes_france === selected)
    if (!sel) { showToast('Sélectionne une ligne d\'abord.', 'info'); return }
    showToast(
      `Ville sélectionnée : ${sel.code_postal} ${sel.nom_ville}. `
      + '(Cette action sert lorsque la fenêtre est ouverte depuis un formulaire.)',
      'info',
    )
  }

  const ajouterLaVille = async () => {
    // Client-side check comme WinDev
    if (!form.code_postal || !form.nom_ville || !form.code_commune
        || !form.departement || form.latitude_deg === 0
        || form.longitude_deg === 0) {
      showToast(
        'Merci de remplir correctement tous les champs pour que la ville '
        + 'soit utilisable dans la CVTHEQUE',
        'error',
      )
      return
    }
    setSaving(true)
    try {
      const r = await fetch(`${API_BASE}/rech-ville`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(form),
      })
      if (!r.ok) {
        const t = await r.text()
        throw new Error(t || String(r.status))
      }
      showToast('Ville ajoutée', 'success')
      setForm(EMPTY_FORM)
      setShowAdd(false)
      // Refresh recherche
      await rechercher()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setSaving(false) }
  }

  const updateForm = (patch: Partial<FormNewCommune>) => {
    setForm(prev => ({ ...prev, ...patch }))
  }

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-110px)] text-c-ink">
      <div className="flex items-center gap-2 mb-3">
        <Link to=".." relative="path"
          className="p-1.5 hover:bg-c-surface-soft rounded text-c-ink-faint-2">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-lg font-bold flex items-center gap-2">
          <MapPin className="w-4 h-4 text-c-brand" />
          Recherche Ville
        </h1>
      </div>

      {/* Filtres recherche */}
      <div className="flex items-center gap-3 mb-3 bg-white p-3 rounded-xl border border-c-line text-sm flex-wrap">
        <label className="text-c-ink-faint text-xs">CP</label>
        <input type="text" value={cp} onChange={e => setCp(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && rechercher()}
          className="px-2 py-1 border border-c-line rounded text-xs h-7 w-24 tabular-nums"
          placeholder="Ex 75001" />
        <label className="text-c-ink-faint text-xs">Ville</label>
        <input type="text" value={nom} onChange={e => setNom(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === 'Enter' && rechercher()}
          className="px-2 py-1 border border-c-line rounded text-xs h-7 flex-1"
          placeholder="TOUT EN MAJUSCULE (SANS ACCENT)" />
        <button type="button" onClick={rechercher} disabled={loading}
          className="flex items-center gap-2 px-4 bg-c-brand text-white rounded text-sm font-medium hover:opacity-90 disabled:opacity-50 h-7">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" />
                   : <Search className="w-4 h-4" />}
          Rechercher
        </button>
      </div>

      {/* Tableau résultats */}
      <div className="bg-white rounded-xl border border-c-line overflow-hidden flex-1 flex flex-col">
        <div className="px-3 py-1.5 border-b border-c-line-soft text-xs text-c-ink-faint">
          {rows.length} commune(s)
        </div>
        <div className="flex-1 overflow-auto">
          <table className="w-full text-xs">
            <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0 z-10">
              <tr>
                <th className="px-2 py-2 text-left w-32">Code Postal</th>
                <th className="px-2 py-2 text-left">Nom Ville</th>
                <th className="px-2 py-2 text-left w-24">Dép.</th>
                <th className="px-2 py-2 text-left w-32">Code Commune</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-c-line-soft">
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={4} className="text-center py-12 text-c-ink-faint-2 italic">
                    Saisis un CP ou une ville puis Rechercher.
                  </td>
                </tr>
              ) : rows.map(r => (
                <tr key={r.id_communes_france}
                  onClick={() => setSelected(r.id_communes_france)}
                  className={`cursor-pointer ${
                    selected === r.id_communes_france
                      ? 'bg-c-brand/10' : 'hover:bg-c-surface-soft'
                  }`}>
                  <td className="px-2 py-1.5 tabular-nums">{r.code_postal}</td>
                  <td className="px-2 py-1.5">{r.nom_ville}
                    {r.favorite && (
                      <span className="ml-1 px-1 py-0.5 rounded bg-yellow-100 text-yellow-700 text-[9px] uppercase">
                        Favori
                      </span>
                    )}
                  </td>
                  <td className="px-2 py-1.5">{r.departement}</td>
                  <td className="px-2 py-1.5 tabular-nums">{r.code_commune}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Boutons d'action */}
      <div className="flex gap-3 mt-3">
        <button type="button" onClick={choisirCetteVille}
          disabled={!selected}
          className="flex items-center gap-2 px-4 py-2 bg-c-brand text-white rounded text-sm font-medium hover:opacity-90 disabled:opacity-50">
          <CheckCircle2 className="w-4 h-4" />
          Choisir cette ville
        </button>
        {canAdd && (
          <button type="button" onClick={() => setShowAdd(v => !v)}
            className="flex items-center gap-2 px-4 py-2 rounded border border-c-line text-sm text-c-brand hover:bg-c-brand/10">
            <Plus className="w-4 h-4" />
            Ajouter une ville
          </button>
        )}
      </div>

      {/* Formulaire d'ajout */}
      {canAdd && showAdd && (
        <div className="mt-3 bg-white rounded-xl border border-c-brand p-4">
          <h3 className="text-sm font-bold text-c-brand uppercase tracking-wide mb-3">
            Ajouter une ville
          </h3>
          <div className="grid grid-cols-3 gap-3 text-xs">
            <div>
              <label className="text-[10px] text-c-ink-faint">Code Postal *</label>
              <input type="text" value={form.code_postal}
                onChange={e => updateForm({ code_postal: e.target.value })}
                className="w-full px-2 py-1 border border-c-line rounded text-xs h-7 tabular-nums" />
            </div>
            <div className="col-span-2">
              <label className="text-[10px] text-c-ink-faint">
                Nom Ville * — pas d'accent, écrire SAINT/SAINTE et pas ST/STE
              </label>
              <input type="text" value={form.nom_ville}
                onChange={e => updateForm({ nom_ville: e.target.value.toUpperCase() })}
                className="w-full px-2 py-1 border border-c-line rounded text-xs h-7" />
            </div>
            <div>
              <label className="text-[10px] text-c-ink-faint">Département *</label>
              <input type="text" value={form.departement}
                onChange={e => updateForm({ departement: e.target.value })}
                className="w-full px-2 py-1 border border-c-line rounded text-xs h-7" />
            </div>
            <div>
              <label className="text-[10px] text-c-ink-faint">Code Pays</label>
              <input type="text" value={form.code_pays}
                onChange={e => updateForm({ code_pays: e.target.value.toUpperCase() })}
                className="w-full px-2 py-1 border border-c-line rounded text-xs h-7" />
            </div>
            <div className="flex items-end gap-1">
              <div className="flex-1">
                <label className="text-[10px] text-c-ink-faint">Code Commune *</label>
                <input type="text" value={form.code_commune}
                  onChange={e => updateForm({ code_commune: e.target.value })}
                  className="w-full px-2 py-1 border border-c-line rounded text-xs h-7 tabular-nums" />
              </div>
              <a href={`https://www.google.com/search?q=${encodeURIComponent(form.nom_ville + ' code commune')}`}
                target="_blank" rel="noreferrer"
                title="Chercher le code commune sur internet"
                className="p-1.5 rounded border border-c-line hover:bg-c-surface-soft h-7">
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
            <div>
              <label className="text-[10px] text-c-ink-faint">Latitude ° *</label>
              <input type="number" step="0.00000001" value={form.latitude_deg || ''}
                onChange={e => updateForm({ latitude_deg: parseFloat(e.target.value) || 0 })}
                className="w-full px-2 py-1 border border-c-line rounded text-xs h-7 tabular-nums" />
            </div>
            <div className="flex items-end gap-1">
              <div className="flex-1">
                <label className="text-[10px] text-c-ink-faint">Longitude ° *</label>
                <input type="number" step="0.00000001" value={form.longitude_deg || ''}
                  onChange={e => updateForm({ longitude_deg: parseFloat(e.target.value) || 0 })}
                  className="w-full px-2 py-1 border border-c-line rounded text-xs h-7 tabular-nums" />
              </div>
              <a href="https://www.coordonneesgps.net/coordonnees-gps/"
                target="_blank" rel="noreferrer"
                title="Chercher les coordonnées GPS"
                className="p-1.5 rounded border border-c-line hover:bg-c-surface-soft h-7">
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
            <div className="col-span-3 text-[10px] text-c-ink-faint italic">
              Ex Paris : Latitude = 48.8566140, Longitude = 2.3522219
              (bien prendre le signe - si besoin)
            </div>
            <div className="col-span-3 flex justify-end">
              <button type="button" onClick={ajouterLaVille} disabled={saving}
                className="flex items-center gap-2 px-4 py-1.5 rounded bg-c-brand text-white text-xs font-medium hover:opacity-90 disabled:opacity-50">
                {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                         : <Save className="w-3.5 h-3.5" />}
                Ajouter la ville
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
