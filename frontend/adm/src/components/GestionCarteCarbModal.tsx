/**
 * Fen_GestionCarteCarb : 2 onglets.
 *
 * Onglet "Cartes carburant" :
 *   - Liste des cartes (Code, Num, Fournisseur, Actif)
 *   - Form edition (Code Carte, Num Carte, Fournisseur, Actif)
 *   - Sous-section : Attributions de la carte selectionnee (conducteur + DU/AU)
 *
 * Onglet "Fournisseurs" :
 *   - Liste fournisseurs (Logo + Nom) + form (Nom + click image -> upload logo)
 *   - Liste types releve (Categorie, Lib_Type) + form (Lib + Categorie)
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CreditCard, Edit3, Image as ImageIcon, Loader2, Plus,
  Save, Search, Trash2, X,
} from 'lucide-react'
import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface Carte {
  id_carte_carburant: string
  code_carte: string
  num_carte: string
  id_carte_fournisseur: string
  nom_fournisseur: string
  is_actif: boolean
}
interface CarteForm {
  id_carte_carburant: string
  code_carte: string
  num_carte: string
  id_carte_fournisseur: string
  is_actif: boolean
}
interface Fournisseur {
  id_carte_fournisseur: string
  nom_fournisseur: string
  logo: string
}
interface TypeReleve {
  id_type_releve_fournisseur: string
  lib_type: string
  categorie: string
}
interface Attribution {
  id_carte_attribution: string
  id_conducteur: string
  conducteur: string
  du: string
  au: string
}
interface SalarieMatch {
  id_salarie: string
  lib: string
}

const inputCls =
  'w-full px-2.5 py-1.5 rounded border bg-white text-sm focus:outline-none focus:ring-1'

interface Props {
  open: boolean
  onClose: () => void
}

export default function GestionCarteCarbModal({ open, onClose }: Props) {
  const [tab, setTab] = useState<'cartes' | 'fournisseurs'>('cartes')

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-white rounded-2xl shadow-xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div
              className="flex items-center justify-between px-5 py-3 border-b"
              style={{ borderColor: COL_BORDER, backgroundColor: COL_PRIMARY, color: 'white' }}
            >
              <h2 className="text-base font-semibold flex items-center gap-2">
                <CreditCard className="w-5 h-5" />
                Gestion des cartes carburant
              </h2>
              <button onClick={onClose} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Onglets */}
            <div className="flex border-b" style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
              {([
                { key: 'cartes', label: 'Cartes carburant' },
                { key: 'fournisseurs', label: 'Fournisseurs' },
              ] as const).map((t) => {
                const active = tab === t.key
                return (
                  <button
                    key={t.key}
                    type="button"
                    onClick={() => setTab(t.key)}
                    className="px-4 py-2 text-sm font-medium transition-colors"
                    style={{
                      color: active ? 'white' : COL_BRUN,
                      backgroundColor: active ? COL_PRIMARY : 'transparent',
                    }}
                  >
                    {t.label}
                  </button>
                )
              })}
            </div>

            <div className="flex-1 overflow-auto p-4" style={{ backgroundColor: COL_BG_SOFT }}>
              {tab === 'cartes' ? <CartesTab /> : <FournisseursTab />}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

// ============================================================================
// Onglet 1 - Cartes carburant + sous-section attributions
// ============================================================================

const emptyCarte: CarteForm = {
  id_carte_carburant: '0',
  code_carte: '',
  num_carte: '',
  id_carte_fournisseur: '',
  is_actif: true,
}

function CartesTab() {
  const [list, setList] = useState<Carte[]>([])
  const [fournisseurs, setFournisseurs] = useState<Fournisseur[]>([])
  const [form, setForm] = useState<CarteForm>(emptyCarte)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [selected, setSelected] = useState<string>('')

  const reload = useCallback(() => {
    setLoading(true)
    Promise.all([
      fetch('/api/adm/carte-carb/cartes', {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) => (r.ok ? r.json() : [])),
      fetch('/api/adm/carte-carb/fournisseurs', {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) => (r.ok ? r.json() : [])),
    ])
      .then(([cs, fs]) => {
        setList(Array.isArray(cs) ? cs : [])
        setFournisseurs(Array.isArray(fs) ? fs : [])
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { reload() }, [reload])

  const upd = <K extends keyof CarteForm>(k: K, v: CarteForm[K]) =>
    setForm((f) => ({ ...f, [k]: v }))

  const onAdd = () => {
    setForm(emptyCarte)
    setSelected('')
  }

  const onEdit = (c: Carte) => {
    setSelected(c.id_carte_carburant)
    setForm({
      id_carte_carburant: c.id_carte_carburant,
      code_carte: c.code_carte,
      num_carte: c.num_carte,
      id_carte_fournisseur: c.id_carte_fournisseur,
      is_actif: c.is_actif,
    })
  }

  const onDelete = async () => {
    if (!selected) return
    const ok = await showConfirm({
      title: 'Supprimer cette carte carburant ?',
      message: 'Vous êtes sur le point de supprimer cette carte carburant.',
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    setSaving(true)
    try {
      const r = await fetch(`/api/adm/carte-carb/cartes/${selected}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Carte supprimée.', 'success')
      onAdd()
      reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleSave = async () => {
    if (!form.num_carte) {
      showToast('Le numéro de carte est obligatoire.', 'error')
      return
    }
    setSaving(true)
    try {
      const r = await fetch('/api/adm/carte-carb/cartes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_carte_carburant: form.id_carte_carburant,
          code_carte: form.code_carte,
          num_carte: form.num_carte,
          id_carte_fournisseur: Number(form.id_carte_fournisseur) || 0,
          is_actif: form.is_actif,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      showToast('Information enregistrée.', 'success')
      setSelected(d.id_carte_carburant)
      upd('id_carte_carburant', d.id_carte_carburant)
      reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Liste cartes */}
      <div>
        <Toolbar
          onAdd={onAdd}
          onEdit={() => {
            const c = list.find((x) => x.id_carte_carburant === selected)
            if (c) onEdit(c)
          }}
          onDelete={onDelete}
          editDisabled={!selected}
          deleteDisabled={!selected || saving}
        />
        <div className="border rounded-lg overflow-auto bg-white"
             style={{ borderColor: COL_BORDER, maxHeight: 460 }}>
          <table className="w-full text-xs">
            <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
              <tr>
                <th className="px-2 py-2 text-left">Code</th>
                <th className="px-2 py-2 text-left">NumCarte</th>
                <th className="px-2 py-2 text-left">Fournisseur</th>
                <th className="px-2 py-2 text-center w-14">Actif</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={4} className="p-4 text-center">
                  <Loader2 className="w-4 h-4 animate-spin inline" /></td></tr>
              ) : list.length === 0 ? (
                <tr><td colSpan={4} className="p-4 text-center italic" style={{ color: '#A68D8A' }}>
                  Aucune carte.</td></tr>
              ) : (
                list.map((c) => {
                  const isSel = selected === c.id_carte_carburant
                  return (
                    <tr key={c.id_carte_carburant}
                        onClick={() => onEdit(c)}
                        className="cursor-pointer border-b"
                        style={{
                          backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                          color: isSel ? 'white' : COL_BRUN,
                          borderColor: COL_BORDER,
                        }}>
                      <td className="px-2 py-1">{c.code_carte}</td>
                      <td className="px-2 py-1">{c.num_carte}</td>
                      <td className="px-2 py-1">{c.nom_fournisseur}</td>
                      <td className="px-2 py-1 text-center">{c.is_actif ? '✓' : ''}</td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Form + attributions */}
      <div className="space-y-3">
        <div className="bg-white border rounded-lg p-3 space-y-2"
             style={{ borderColor: COL_BORDER }}>
          <div className="flex items-center gap-2">
            <label className="text-xs w-16" style={{ color: COL_BRUN }}>ID</label>
            <input value={form.id_carte_carburant} disabled
                   className={`${inputCls} flex-1 bg-gray-50`}
                   style={{ borderColor: COL_BORDER }} />
          </div>
          <input type="text" value={form.code_carte}
                 onChange={(e) => upd('code_carte', e.target.value)}
                 placeholder="Code Carte"
                 className={inputCls} style={{ borderColor: COL_BORDER }} />
          <input type="text" value={form.num_carte}
                 onChange={(e) => upd('num_carte', e.target.value)}
                 placeholder="Num Carte"
                 className={inputCls} style={{ borderColor: COL_BORDER }} />
          <div className="flex items-center gap-3">
            <select value={form.id_carte_fournisseur}
                    onChange={(e) => upd('id_carte_fournisseur', e.target.value)}
                    className={`${inputCls} flex-1`}
                    style={{ borderColor: COL_BORDER }}>
              <option value="">Fournisseur</option>
              {fournisseurs.map((f) => (
                <option key={f.id_carte_fournisseur} value={f.id_carte_fournisseur}>
                  {f.nom_fournisseur}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-1.5 text-sm" style={{ color: COL_BRUN }}>
              <input type="checkbox" checked={form.is_actif}
                     onChange={(e) => upd('is_actif', e.target.checked)} />
              Actif
            </label>
          </div>
          <div className="pt-1">
            <button type="button" onClick={handleSave} disabled={saving}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-white text-sm font-medium disabled:opacity-50"
                    style={{ backgroundColor: COL_PRIMARY }}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Enregistrer
            </button>
          </div>
        </div>

        {/* Sous-section : attributions */}
        <AttributionsSection idCarte={selected} />
      </div>
    </div>
  )
}

// ============================================================================
// Sous-section : Attributions de la carte
// ============================================================================

function AttributionsSection({ idCarte }: { idCarte: string }) {
  const [list, setList] = useState<Attribution[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<string>('')
  const [editing, setEditing] = useState<Partial<Attribution> | null>(null)

  const reload = useCallback(() => {
    if (!idCarte) { setList([]); return }
    setLoading(true)
    fetch(`/api/adm/carte-carb/cartes/${idCarte}/attributions`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.ok ? r.json() : [])
      .then((d) => setList(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }, [idCarte])

  useEffect(() => { reload() }, [reload])

  const onAdd = () => setEditing({
    id_carte_attribution: '0',
    id_conducteur: '',
    conducteur: '',
    du: '',
    au: '',
  })

  const onEdit = () => {
    const a = list.find((x) => x.id_carte_attribution === selected)
    if (a) setEditing(a)
  }

  const onDelete = async () => {
    if (!selected) return
    const ok = await showConfirm({
      title: 'Supprimer cette attribution ?',
      message: 'Vous êtes sur le point de supprimer cette attribution de carte carburant.',
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    try {
      const r = await fetch(`/api/adm/carte-carb/attributions/${selected}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      setSelected('')
      reload()
      showToast('Attribution supprimée.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    }
  }

  return (
    <div className="bg-white border rounded-lg p-3 space-y-2"
         style={{ borderColor: COL_BORDER }}>
      <h3 className="text-xs font-bold uppercase" style={{ color: COL_BRUN }}>
        Attributions de la carte
      </h3>
      <Toolbar
        onAdd={onAdd}
        onEdit={onEdit}
        onDelete={onDelete}
        addDisabled={!idCarte}
        editDisabled={!selected}
        deleteDisabled={!selected}
      />
      <div className="border rounded overflow-auto"
           style={{ borderColor: COL_BORDER, maxHeight: 200 }}>
        <table className="w-full text-xs">
          <thead className="sticky top-0"
                 style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
            <tr>
              <th className="px-2 py-2 text-left">Conducteur</th>
              <th className="px-2 py-2 text-left w-28">DU</th>
              <th className="px-2 py-2 text-left w-28">AU</th>
            </tr>
          </thead>
          <tbody>
            {!idCarte ? (
              <tr><td colSpan={3} className="p-3 text-center italic" style={{ color: '#A68D8A' }}>
                Sélectionne une carte.</td></tr>
            ) : loading ? (
              <tr><td colSpan={3} className="p-3 text-center">
                <Loader2 className="w-4 h-4 animate-spin inline" /></td></tr>
            ) : list.length === 0 ? (
              <tr><td colSpan={3} className="p-3 text-center italic" style={{ color: '#A68D8A' }}>
                Aucune attribution.</td></tr>
            ) : (
              list.map((a) => {
                const isSel = selected === a.id_carte_attribution
                return (
                  <tr key={a.id_carte_attribution}
                      onClick={() => setSelected(a.id_carte_attribution)}
                      onDoubleClick={() => setEditing(a)}
                      className="cursor-pointer border-b"
                      style={{
                        backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                        color: isSel ? 'white' : COL_BRUN,
                        borderColor: COL_BORDER,
                      }}>
                    <td className="px-2 py-1">{a.conducteur}</td>
                    <td className="px-2 py-1">{fmtDate(a.du)}</td>
                    <td className="px-2 py-1">{fmtDate(a.au)}</td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {editing && (
        <AttCarteCarbForm
          idCarte={idCarte}
          editing={editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); reload() }}
        />
      )}
    </div>
  )
}

// ============================================================================
// Fen_AttCarteCarb (form overlay)
// ============================================================================

function AttCarteCarbForm({
  idCarte, editing, onClose, onSaved,
}: {
  idCarte: string
  editing: Partial<Attribution>
  onClose: () => void
  onSaved: () => void
}) {
  const [conducteurLib, setConducteurLib] = useState(editing.conducteur || '')
  const [idConducteur, setIdConducteur] = useState(editing.id_conducteur || '')
  const [du, setDu] = useState(editing.du || '')
  const [au, setAu] = useState(editing.au || '')
  const [pickerOpen, setPickerOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!idConducteur) {
      showToast('Choisissez un conducteur.', 'error')
      return
    }
    setSaving(true)
    try {
      const r = await fetch('/api/adm/carte-carb/attributions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_carte_attribution: editing.id_carte_attribution || '0',
          id_carte_carburant: idCarte,
          id_conducteur: idConducteur,
          du, au,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Information enregistrée.', 'success')
      onSaved()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const onPicked = async (s: SalarieMatch) => {
    setPickerOpen(false)
    try {
      const r = await fetch(
        `/api/adm/parc-auto/conducteurs/from-salarie/${s.id_salarie}`,
        { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setIdConducteur(String(d.id_conducteur))
      setConducteurLib(String(d.lib))
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4"
         onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-2 border-b"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_PRIMARY, color: 'white' }}>
          <h3 className="text-sm font-semibold">
            {editing.id_carte_attribution && editing.id_carte_attribution !== '0'
              ? 'Modifier l\'attribution' : 'Nouvelle attribution'}
          </h3>
          <button onClick={onClose}><X className="w-4 h-4" /></button>
        </div>
        <div className="p-4 space-y-3">
          <button type="button" onClick={() => setPickerOpen(true)}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded border text-sm"
                  style={{ borderColor: COL_BORDER, color: COL_BRUN, backgroundColor: COL_BG_SOFT }}>
            <Search className="w-4 h-4" />
            {conducteurLib || 'Choisir le conducteur'}
          </button>
          <div className="flex items-center gap-2">
            <label className="text-sm w-12" style={{ color: COL_BRUN }}>DU :</label>
            <input type="date" value={du} onChange={(e) => setDu(e.target.value)}
                   className={`${inputCls} flex-1`} style={{ borderColor: COL_BORDER }} />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm w-12" style={{ color: COL_BRUN }}>AU :</label>
            <input type="date" value={au} onChange={(e) => setAu(e.target.value)}
                   className={`${inputCls} flex-1`} style={{ borderColor: COL_BORDER }} />
          </div>
        </div>
        <div className="flex justify-end gap-2 px-4 py-2 border-t"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <button type="button" onClick={onClose}
                  className="px-3 py-1.5 rounded text-sm border"
                  style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
            Annuler
          </button>
          <button type="button" onClick={handleSave} disabled={saving}
                  className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm font-medium disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Valider
          </button>
        </div>
      </div>

      {pickerOpen && <SalariePicker onClose={() => setPickerOpen(false)} onPicked={onPicked} />}
    </div>
  )
}

// ============================================================================
// Onglet 2 - Fournisseurs + Types relevé
// ============================================================================

function FournisseursTab() {
  return (
    <div className="grid grid-cols-2 gap-4">
      <FournisseursSection />
      <TypesReleveSection />
    </div>
  )
}

function FournisseursSection() {
  const [list, setList] = useState<Fournisseur[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string>('')
  const [form, setForm] = useState({ id_carte_fournisseur: '0', nom_fournisseur: '' })
  const [saving, setSaving] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const reload = useCallback(() => {
    setLoading(true)
    fetch('/api/adm/carte-carb/fournisseurs', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.ok ? r.json() : [])
      .then((d) => setList(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { reload() }, [reload])

  const current = list.find((f) => f.id_carte_fournisseur === selected)

  const onAdd = () => {
    setSelected('')
    setForm({ id_carte_fournisseur: '0', nom_fournisseur: '' })
  }

  const onEdit = () => {
    const f = list.find((x) => x.id_carte_fournisseur === selected)
    if (f) setForm({
      id_carte_fournisseur: f.id_carte_fournisseur,
      nom_fournisseur: f.nom_fournisseur,
    })
  }

  const onDelete = async () => {
    if (!selected) return
    const ok = await showConfirm({
      title: 'Supprimer ce fournisseur ?',
      message: 'Vous êtes sur le point de supprimer ce fournisseur.',
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    try {
      const r = await fetch(`/api/adm/carte-carb/fournisseurs/${selected}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      onAdd()
      reload()
      showToast('Fournisseur supprimé.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    }
  }

  const handleSave = async () => {
    if (!form.nom_fournisseur) {
      showToast('Nom obligatoire.', 'error')
      return
    }
    setSaving(true)
    try {
      const r = await fetch('/api/adm/carte-carb/fournisseurs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(form),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setForm({ ...form, id_carte_fournisseur: d.id_carte_fournisseur })
      setSelected(d.id_carte_fournisseur)
      reload()
      showToast('Information enregistrée.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const onLogoClick = () => {
    if (!form.id_carte_fournisseur || form.id_carte_fournisseur === '0') {
      showToast('Enregistre d\'abord le fournisseur.', 'info')
      return
    }
    fileInputRef.current?.click()
  }

  const onLogoChange = async (ev: React.ChangeEvent<HTMLInputElement>) => {
    const f = ev.target.files?.[0]
    if (!f) return
    const fd = new FormData()
    fd.append('file', f)
    try {
      const r = await fetch(
        `/api/adm/carte-carb/fournisseurs/${form.id_carte_fournisseur}/logo`,
        { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` }, body: fd },
      )
      if (!r.ok) throw new Error(String(r.status))
      reload()
      showToast('Logo mis à jour.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    }
    ev.target.value = ''
  }

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-bold uppercase" style={{ color: COL_BRUN }}>
        Fournisseurs
      </h3>
      <Toolbar onAdd={onAdd} onEdit={onEdit} onDelete={onDelete}
               editDisabled={!selected} deleteDisabled={!selected} />
      <div className="border rounded-lg overflow-auto bg-white"
           style={{ borderColor: COL_BORDER, maxHeight: 180 }}>
        <table className="w-full text-xs">
          <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
            <tr>
              <th className="px-2 py-2 w-16">Logo</th>
              <th className="px-2 py-2 text-left">Fournisseur</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={2} className="p-3 text-center">
                <Loader2 className="w-4 h-4 animate-spin inline" /></td></tr>
            ) : list.length === 0 ? (
              <tr><td colSpan={2} className="p-3 text-center italic" style={{ color: '#A68D8A' }}>
                Aucun fournisseur.</td></tr>
            ) : (
              list.map((f) => {
                const isSel = selected === f.id_carte_fournisseur
                return (
                  <tr key={f.id_carte_fournisseur}
                      onClick={() => { setSelected(f.id_carte_fournisseur); setForm({
                        id_carte_fournisseur: f.id_carte_fournisseur,
                        nom_fournisseur: f.nom_fournisseur,
                      }) }}
                      className="cursor-pointer border-b"
                      style={{
                        backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                        color: isSel ? 'white' : COL_BRUN,
                        borderColor: COL_BORDER,
                      }}>
                    <td className="px-2 py-1 text-center">
                      {f.logo ? <img src={f.logo} alt="" className="w-8 h-8 object-contain inline" />
                              : <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-2 py-1">{f.nom_fournisseur}</td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="bg-white border rounded-lg p-3 space-y-2"
           style={{ borderColor: COL_BORDER }}>
        <div className="flex items-center gap-2">
          <label className="text-xs w-12" style={{ color: COL_BRUN }}>ID</label>
          <input value={form.id_carte_fournisseur} disabled
                 className={`${inputCls} flex-1 bg-gray-50`}
                 style={{ borderColor: COL_BORDER }} />
        </div>
        <div className="flex items-center gap-3">
          <input type="text" value={form.nom_fournisseur}
                 onChange={(e) => setForm({ ...form, nom_fournisseur: e.target.value })}
                 placeholder="Nom Fournisseur"
                 className={`${inputCls} flex-1`} style={{ borderColor: COL_BORDER }} />
          <button type="button" onClick={onLogoClick}
                  className="w-16 h-16 border rounded flex items-center justify-center bg-gray-50 hover:bg-gray-100 cursor-pointer"
                  style={{ borderColor: COL_BORDER }}
                  title={form.id_carte_fournisseur === '0' ? 'Enregistre d\'abord' : 'Cliquer pour uploader'}>
            {current?.logo ? (
              <img src={current.logo} alt="" className="w-full h-full object-contain p-1" />
            ) : (
              <ImageIcon className="w-6 h-6 text-gray-300" />
            )}
          </button>
          <input ref={fileInputRef} type="file" accept="image/*"
                 onChange={onLogoChange} className="hidden" />
        </div>
        <button type="button" onClick={handleSave} disabled={saving}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-white text-sm font-medium disabled:opacity-50"
                style={{ backgroundColor: COL_PRIMARY }}>
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Enregistrer
        </button>
      </div>
    </div>
  )
}

function TypesReleveSection() {
  const [list, setList] = useState<TypeReleve[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string>('')
  const [form, setForm] = useState({
    id_type_releve_fournisseur: '0', lib_type: '', categorie: '',
  })
  const [saving, setSaving] = useState(false)

  const reload = useCallback(() => {
    setLoading(true)
    fetch('/api/adm/carte-carb/types-releve', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.ok ? r.json() : [])
      .then((d) => setList(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { reload() }, [reload])

  const onAdd = () => {
    setSelected('')
    setForm({ id_type_releve_fournisseur: '0', lib_type: '', categorie: '' })
  }

  const onEdit = () => {
    const t = list.find((x) => x.id_type_releve_fournisseur === selected)
    if (t) setForm(t)
  }

  const onDelete = async () => {
    if (!selected) return
    const ok = await showConfirm({
      title: 'Supprimer ce type ?',
      message: 'Vous êtes sur le point de supprimer ce type de relevé.',
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    try {
      const r = await fetch(`/api/adm/carte-carb/types-releve/${selected}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      onAdd()
      reload()
      showToast('Type supprimé.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    }
  }

  const handleSave = async () => {
    if (!form.lib_type || !form.categorie) {
      showToast('Lib et Catégorie obligatoires.', 'error')
      return
    }
    setSaving(true)
    try {
      const r = await fetch('/api/adm/carte-carb/types-releve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(form),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setForm({ ...form, id_type_releve_fournisseur: d.id_type_releve_fournisseur })
      setSelected(d.id_type_releve_fournisseur)
      reload()
      showToast('Information enregistrée.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-bold uppercase" style={{ color: COL_BRUN }}>
        Types de relevé fournisseur
      </h3>
      <Toolbar onAdd={onAdd} onEdit={onEdit} onDelete={onDelete}
               editDisabled={!selected} deleteDisabled={!selected} />
      <div className="border rounded-lg overflow-auto bg-white"
           style={{ borderColor: COL_BORDER, maxHeight: 180 }}>
        <table className="w-full text-xs">
          <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
            <tr>
              <th className="px-2 py-2 text-left">Catégorie</th>
              <th className="px-2 py-2 text-left">Lib_Type</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={2} className="p-3 text-center">
                <Loader2 className="w-4 h-4 animate-spin inline" /></td></tr>
            ) : list.length === 0 ? (
              <tr><td colSpan={2} className="p-3 text-center italic" style={{ color: '#A68D8A' }}>
                Aucun type.</td></tr>
            ) : (
              list.map((t) => {
                const isSel = selected === t.id_type_releve_fournisseur
                return (
                  <tr key={t.id_type_releve_fournisseur}
                      onClick={() => { setSelected(t.id_type_releve_fournisseur); setForm(t) }}
                      className="cursor-pointer border-b"
                      style={{
                        backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                        color: isSel ? 'white' : COL_BRUN,
                        borderColor: COL_BORDER,
                      }}>
                    <td className="px-2 py-1">{t.categorie}</td>
                    <td className="px-2 py-1">{t.lib_type}</td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="bg-white border rounded-lg p-3 space-y-2"
           style={{ borderColor: COL_BORDER }}>
        <div className="flex items-center gap-2">
          <label className="text-xs w-12" style={{ color: COL_BRUN }}>ID</label>
          <input value={form.id_type_releve_fournisseur} disabled
                 className={`${inputCls} flex-1 bg-gray-50`}
                 style={{ borderColor: COL_BORDER }} />
        </div>
        <input type="text" value={form.lib_type}
               onChange={(e) => setForm({ ...form, lib_type: e.target.value })}
               placeholder="Lib"
               className={inputCls} style={{ borderColor: COL_BORDER }} />
        <input type="text" value={form.categorie}
               onChange={(e) => setForm({ ...form, categorie: e.target.value })}
               placeholder="Catégorie"
               className={inputCls} style={{ borderColor: COL_BORDER }} />
        <button type="button" onClick={handleSave} disabled={saving}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-white text-sm font-medium disabled:opacity-50"
                style={{ backgroundColor: COL_PRIMARY }}>
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Enregistrer
        </button>
      </div>
    </div>
  )
}

// ============================================================================
// Helpers
// ============================================================================

function Toolbar({
  onAdd, onEdit, onDelete,
  addDisabled = false, editDisabled = false, deleteDisabled = false,
}: {
  onAdd: () => void; onEdit: () => void; onDelete: () => void
  addDisabled?: boolean; editDisabled?: boolean; deleteDisabled?: boolean
}) {
  return (
    <div className="flex items-center gap-1 mb-1">
      <IconBtn onClick={onAdd} title="Ajouter" disabled={addDisabled}>
        <Plus className="w-4 h-4" />
      </IconBtn>
      <IconBtn onClick={onEdit} title="Modifier" disabled={editDisabled}>
        <Edit3 className="w-4 h-4" />
      </IconBtn>
      <IconBtn onClick={onDelete} title="Supprimer" disabled={deleteDisabled} danger>
        <Trash2 className="w-4 h-4" />
      </IconBtn>
    </div>
  )
}

function IconBtn({
  onClick, title, disabled, danger, children,
}: {
  onClick: () => void; title: string; disabled?: boolean; danger?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      type="button" onClick={onClick} title={title} disabled={disabled}
      className="w-8 h-8 flex items-center justify-center rounded border disabled:opacity-40"
      style={{
        borderColor: danger ? '#B91C1C' : COL_BORDER,
        color: danger ? '#B91C1C' : COL_BRUN,
        backgroundColor: 'white',
      }}
    >
      {children}
    </button>
  )
}

function fmtDate(s: string): string {
  if (!s || s.length < 10) return ''
  return `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}`
}

// ============================================================================
// SalariePicker (re-utilise du AttributionModal)
// ============================================================================

function SalariePicker({
  onClose, onPicked,
}: {
  onClose: () => void; onPicked: (s: SalarieMatch) => void
}) {
  const [q, setQ] = useState('')
  const [list, setList] = useState<SalarieMatch[]>([])
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<number | null>(null)

  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current)
    debounceRef.current = window.setTimeout(() => {
      setLoading(true)
      fetch(`/api/adm/parc-auto/salaries/search?q=${encodeURIComponent(q)}&limit=100`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
        .then((r) => r.ok ? r.json() : [])
        .then((d) => setList(Array.isArray(d) ? d : []))
        .finally(() => setLoading(false))
    }, 200)
    return () => { if (debounceRef.current) window.clearTimeout(debounceRef.current) }
  }, [q])

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[80vh] flex flex-col overflow-hidden"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-2 border-b"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_PRIMARY, color: 'white' }}>
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Search className="w-4 h-4" /> Rechercher un salarié
          </h3>
          <button onClick={onClose}><X className="w-4 h-4" /></button>
        </div>
        <div className="p-3">
          <input type="text" value={q} onChange={(e) => setQ(e.target.value)}
                 placeholder="Nom ou prénom..." autoFocus
                 className="w-full px-3 py-2 rounded border text-sm"
                 style={{ borderColor: COL_BORDER }} />
        </div>
        <div className="flex-1 overflow-auto border-t" style={{ borderColor: COL_BORDER }}>
          {loading ? (
            <div className="p-4 text-center">
              <Loader2 className="w-5 h-5 animate-spin inline" style={{ color: COL_PRIMARY }} />
            </div>
          ) : list.length === 0 ? (
            <div className="p-4 text-center text-sm italic" style={{ color: '#A68D8A' }}>
              Aucun résultat
            </div>
          ) : (
            list.map((s) => (
              <button key={s.id_salarie} type="button" onClick={() => onPicked(s)}
                      className="w-full text-left px-3 py-2 hover:bg-gray-50 text-sm border-b"
                      style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
                {s.lib}
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
