/**
 * Fen_ParamRH (WinDev) - Salariés -> Paramètres RH.
 *
 * Page à onglets : éditeur CRUD sur 8 tables de référence + type_produit
 * (avec partenaires liés + logo).
 *
 * Onglets :
 *   - Type de Postes
 *   - Type de contrat
 *   - Type d'horaire
 *   - Type de Sortie RH
 *   - Organismes Mutuelles
 *   - Type Absences
 *   - Type Opé Livret EC
 *   - Orga - Groupe de Produits (avec partenaires + logo)
 *   - Portails Partenaires : V2 (table pas encore migrée en PG)
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Briefcase, Building2, Calendar, FileSignature, HeartPulse,
  Image as ImageIcon,
  LayoutDashboard, Loader2, LogOut, Plus, RotateCcw,
  Settings, Trash2, Wallet,
} from 'lucide-react'

import { getToken } from '@/api'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { showConfirm, showToast } from '@shared/ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface FieldConfig {
  key: string
  label: string
  type?: 'text' | 'bool'
}

interface TabConfig {
  key: string
  label: string
  icon: React.ReactNode
  entity: string  // endpoint /params-rh/{entity}
  fields: FieldConfig[]
}

const TABS: TabConfig[] = [
  { key: 'type_poste', label: 'Type de Postes', icon: <Briefcase className="w-4 h-4" />,
    entity: 'type_poste',
    fields: [
      { key: 'lib_poste', label: 'Lib Poste' },
      { key: 'categorie', label: 'Catégorie' },
    ] },
  { key: 'type_ctt', label: 'Type de contrat', icon: <FileSignature className="w-4 h-4" />,
    entity: 'type_ctt',
    fields: [{ key: 'intitule', label: 'Intitulé' }] },
  { key: 'type_horaire', label: "Type d'horaire", icon: <Calendar className="w-4 h-4" />,
    entity: 'type_horaire',
    fields: [{ key: 'lib_horaire', label: 'Lib Horaire' }] },
  { key: 'type_sortie', label: 'Type de Sortie RH', icon: <LogOut className="w-4 h-4" />,
    entity: 'type_sortie',
    fields: [{ key: 'lib_sortie', label: 'Lib Sortie' }] },
  { key: 'mutuelle', label: 'Organismes Mutuelles', icon: <HeartPulse className="w-4 h-4" />,
    entity: 'mutuelle',
    fields: [
      { key: 'lib_mutuelle', label: 'Lib Mutuelle' },
      { key: 'is_actif', label: 'Actif', type: 'bool' },
    ] },
  { key: 'type_absence', label: 'Type Absences', icon: <Calendar className="w-4 h-4" />,
    entity: 'type_absence',
    fields: [{ key: 'lib_absence', label: 'Lib Absence' }] },
  { key: 'type_ope_livret', label: 'Type Opé Livret EC', icon: <Wallet className="w-4 h-4" />,
    entity: 'type_ope_livret',
    fields: [{ key: 'lib_opeation', label: 'Lib Opération' }] },
  { key: 'type_produit', label: 'Orga - Groupe de Produits', icon: <LayoutDashboard className="w-4 h-4" />,
    entity: 'type_produit',
    fields: [
      { key: 'lib', label: 'Lib' },
      { key: 'type', label: 'Type' },
    ] },
  { key: 'portail', label: 'Portails Partenaires', icon: <Building2 className="w-4 h-4" />,
    entity: 'portail',
    fields: [] /* géré par PortailsEditor */ },
]

export default function ParametresRHPage() {
  useDocumentTitle('Paramètres RH')
  const [tabKey, setTabKey] = useState<string>(TABS[0].key)
  const tab = TABS.find((t) => t.key === tabKey) || TABS[0]

  return (
    <div className="p-6 max-w-7xl mx-auto font-normal space-y-4">
      <div className="flex items-center gap-3">
        <Settings className="w-6 h-6" style={{ color: COL_BRUN }} />
        <h1 className="text-xl font-bold" style={{ color: COL_BRUN }}>
          Paramétrage RH
        </h1>
      </div>

      {/* Onglets */}
      <div className="flex flex-wrap gap-1 border-b" style={{ borderColor: COL_BORDER }}>
        {TABS.map((t) => {
          const active = tabKey === t.key
          return (
            <button key={t.key} type="button" onClick={() => setTabKey(t.key)}
                    className="flex items-center gap-2 px-3 py-2 text-sm rounded-t transition-colors"
                    style={{
                      backgroundColor: active ? COL_PRIMARY : 'transparent',
                      color: active ? 'white' : COL_BRUN,
                      borderBottom: active ? `2px solid ${COL_PRIMARY}` : 'none',
                    }}>
              {t.icon}
              {t.label}
            </button>
          )
        })}
      </div>

      {tab.key === 'type_produit' ? (
        <TypeProduitEditor />
      ) : tab.key === 'portail' ? (
        <PortailsEditor />
      ) : (
        <RefTableEditor key={tab.key} tab={tab} />
      )}
    </div>
  )
}

// ============================================================================
// Editeur generique : tableau gauche + form droite
// ============================================================================

interface Row { id: string; [k: string]: string | boolean | number }

function RefTableEditor({ tab }: { tab: TabConfig }) {
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState('')
  const [form, setForm] = useState<Row>(emptyForm(tab))
  const [saving, setSaving] = useState(false)

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`/api/adm/params-rh/${tab.entity}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => setRows(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }, [tab.entity])

  useEffect(() => { reload() }, [reload])

  const handleSelect = (r: Row) => {
    setSelected(r.id)
    setForm({ ...r })
  }

  const handleNew = () => {
    setSelected('')
    setForm(emptyForm(tab))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const r = await fetch(`/api/adm/params-rh/${tab.entity}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(form),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setForm((f) => ({ ...f, id: d.id }))
      setSelected(d.id)
      showToast('Enregistré.', 'success')
      reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!selected) return
    const ok = await showConfirm({
      title: 'Supprimer ?',
      message: 'Confirmer la suppression de cet enregistrement ?',
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    setSaving(true)
    try {
      const r = await fetch(`/api/adm/params-rh/${tab.entity}/${selected}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      handleNew()
      reload()
      showToast('Supprimé.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <Toolbar onNew={handleNew} onDelete={handleDelete} onReload={reload}
                 deleteDisabled={!selected || saving} />
        <div className="border rounded-lg overflow-auto bg-white"
             style={{ borderColor: COL_BORDER, maxHeight: 500 }}>
          <table className="w-full text-sm">
            <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
              <tr>
                {tab.fields.map((f) => (
                  <th key={f.key} className="px-3 py-2 text-left">{f.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={tab.fields.length} className="p-4 text-center">
                  <Loader2 className="w-4 h-4 animate-spin inline" /></td></tr>
              ) : rows.length === 0 ? (
                <tr><td colSpan={tab.fields.length} className="p-4 text-center italic" style={{ color: '#A68D8A' }}>
                  Aucun enregistrement.</td></tr>
              ) : (
                rows.map((r) => {
                  const isSel = selected === r.id
                  return (
                    <tr key={r.id} onClick={() => handleSelect(r)}
                        className="cursor-pointer border-b"
                        style={{
                          backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                          color: isSel ? 'white' : COL_BRUN,
                          borderColor: COL_BORDER,
                        }}>
                      {tab.fields.map((f) => (
                        <td key={f.key} className="px-3 py-1.5">
                          {typeof r[f.key] === 'boolean'
                            ? (r[f.key] ? '✓' : '')
                            : String(r[f.key] ?? '')}
                        </td>
                      ))}
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-4 space-y-3 h-fit"
           style={{ borderColor: COL_BORDER }}>
        <div className="flex items-center gap-2">
          <label className="text-xs w-16" style={{ color: COL_BRUN }}>ID</label>
          <input value={form.id || '0'} disabled
                 className="flex-1 px-2 py-1.5 rounded border bg-gray-50 text-sm"
                 style={{ borderColor: COL_BORDER }} />
        </div>
        {tab.fields.map((f) => (
          <div key={f.key} className="flex items-center gap-2">
            <label className="text-xs w-32" style={{ color: COL_BRUN }}>{f.label}</label>
            {f.type === 'bool' ? (
              <input type="checkbox" checked={!!form[f.key]}
                     onChange={(e) => setForm({ ...form, [f.key]: e.target.checked })} />
            ) : (
              <input type="text" value={(form[f.key] as string) || ''}
                     onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                     className="flex-1 px-2 py-1.5 rounded border bg-white text-sm"
                     style={{ borderColor: COL_BORDER }} />
            )}
          </div>
        ))}
        <button type="button" onClick={handleSave} disabled={saving}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-white text-sm disabled:opacity-50"
                style={{ backgroundColor: COL_PRIMARY }}>
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          {form.id && form.id !== '0' ? 'Enregistrer' : 'Créer'}
        </button>
      </div>
    </div>
  )
}

function emptyForm(tab: TabConfig): Row {
  const f: Row = { id: '0' }
  tab.fields.forEach((field) => {
    f[field.key] = field.type === 'bool' ? true : ''
  })
  return f
}

function Toolbar({ onNew, onDelete, onReload, deleteDisabled }: {
  onNew: () => void; onDelete: () => void; onReload: () => void
  deleteDisabled?: boolean
}) {
  return (
    <div className="flex items-center gap-1 mb-2">
      <IconBtn onClick={onNew} title="Nouveau"><Plus className="w-4 h-4" /></IconBtn>
      <IconBtn onClick={onDelete} title="Supprimer" disabled={deleteDisabled} danger>
        <Trash2 className="w-4 h-4" />
      </IconBtn>
      <IconBtn onClick={onReload} title="Recharger"><RotateCcw className="w-4 h-4" /></IconBtn>
    </div>
  )
}

function IconBtn({ onClick, title, disabled, danger, children }: {
  onClick: () => void; title: string; disabled?: boolean; danger?: boolean
  children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick} title={title} disabled={disabled}
            className="w-8 h-8 flex items-center justify-center rounded border disabled:opacity-40"
            style={{
              borderColor: danger ? '#B91C1C' : COL_BORDER,
              color: danger ? '#B91C1C' : COL_BRUN,
              backgroundColor: 'white',
            }}>
      {children}
    </button>
  )
}

// ============================================================================
// TypeProduit : version etendue avec logo + partenaires lies
// ============================================================================

interface TypeProduitRow {
  id: string
  lib: string
  type: string
  logo: string
}

interface PartenaireCombo { id_partenaire: string; lib: string }

interface TypeProduitPartenaire {
  id_type_produit_partenaire: string
  id_partenaire: string
}

function TypeProduitEditor() {
  const [rows, setRows] = useState<TypeProduitRow[]>([])
  const [partenaires, setPartenaires] = useState<PartenaireCombo[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState('')
  const [form, setForm] = useState<TypeProduitRow>({ id: '0', lib: '', type: '', logo: '' })
  const [liens, setLiens] = useState<TypeProduitPartenaire[]>([])
  const [newPartId, setNewPartId] = useState('')
  const [saving, setSaving] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const reload = useCallback(() => {
    setLoading(true)
    Promise.all([
      fetch('/api/adm/params-rh/type_produit', {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) => r.ok ? r.json() : []),
      fetch('/api/adm/params-rh/partenaires', {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) => r.ok ? r.json() : []),
    ])
      .then(([tp, pa]) => {
        setRows(Array.isArray(tp) ? tp : [])
        setPartenaires(Array.isArray(pa) ? pa : [])
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { reload() }, [reload])

  const reloadLiens = useCallback(() => {
    if (!selected) { setLiens([]); return }
    fetch(`/api/adm/params-rh/type-produit/${selected}/partenaires`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.ok ? r.json() : [])
      .then((d) => setLiens(Array.isArray(d) ? d : []))
  }, [selected])

  useEffect(() => { reloadLiens() }, [reloadLiens])

  const handleSelect = (r: TypeProduitRow) => {
    setSelected(r.id)
    setForm(r)
  }

  const handleNew = () => {
    setSelected('')
    setForm({ id: '0', lib: '', type: '', logo: '' })
    setLiens([])
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const r = await fetch('/api/adm/params-rh/type_produit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(form),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setForm((f) => ({ ...f, id: d.id }))
      setSelected(d.id)
      showToast('Enregistré.', 'success')
      reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally { setSaving(false) }
  }

  const handleDelete = async () => {
    if (!selected) return
    const ok = await showConfirm({
      title: 'Supprimer ?',
      message: 'Confirmer la suppression de ce type de produit ?',
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    try {
      const r = await fetch(`/api/adm/params-rh/type_produit/${selected}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      handleNew()
      reload()
      showToast('Supprimé.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    }
  }

  const onLogoClick = () => {
    if (!selected) {
      showToast('Sélectionne d\'abord un type de produit.', 'info')
      return
    }
    fileInputRef.current?.click()
  }

  const onLogoChange = async (ev: React.ChangeEvent<HTMLInputElement>) => {
    const f = ev.target.files?.[0]
    if (!f || !selected) return
    const fd = new FormData()
    fd.append('file', f)
    try {
      const r = await fetch(`/api/adm/params-rh/type-produit/${selected}/logo`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      if (!r.ok) throw new Error(String(r.status))
      reload()
      showToast('Logo mis à jour.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    }
    ev.target.value = ''
  }

  const handleAddPart = async () => {
    if (!selected || !newPartId) return
    try {
      const r = await fetch(`/api/adm/params-rh/type-produit/${selected}/partenaires`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ id_partenaire: Number(newPartId) }),
      })
      if (!r.ok) throw new Error(String(r.status))
      setNewPartId('')
      reloadLiens()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    }
  }

  const handleDelPart = async (idLien: string) => {
    try {
      const r = await fetch(`/api/adm/params-rh/type_produit_partenaire/${idLien}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      reloadLiens()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    }
  }

  const partLibById = (id: string) =>
    partenaires.find((p) => p.id_partenaire === id)?.lib || `#${id}`

  const current = rows.find((x) => x.id === selected)

  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <Toolbar onNew={handleNew} onDelete={handleDelete} onReload={reload}
                 deleteDisabled={!selected || saving} />
        <div className="border rounded-lg overflow-auto bg-white"
             style={{ borderColor: COL_BORDER, maxHeight: 500 }}>
          <table className="w-full text-sm">
            <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
              <tr>
                <th className="px-3 py-2 text-left">Lib</th>
                <th className="px-3 py-2 text-left">Type</th>
                <th className="px-3 py-2 w-16">Logo</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={3} className="p-4 text-center">
                  <Loader2 className="w-4 h-4 animate-spin inline" /></td></tr>
              ) : rows.length === 0 ? (
                <tr><td colSpan={3} className="p-4 text-center italic" style={{ color: '#A68D8A' }}>
                  Aucun type.</td></tr>
              ) : (
                rows.map((r) => {
                  const isSel = selected === r.id
                  return (
                    <tr key={r.id} onClick={() => handleSelect(r)}
                        className="cursor-pointer border-b"
                        style={{
                          backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                          color: isSel ? 'white' : COL_BRUN,
                          borderColor: COL_BORDER,
                        }}>
                      <td className="px-3 py-1.5">{r.lib}</td>
                      <td className="px-3 py-1.5">{r.type}</td>
                      <td className="px-3 py-1.5 text-center">
                        {r.logo ? <img src={r.logo} alt="" className="w-6 h-6 object-contain inline" />
                                : <span className="text-gray-300">—</span>}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="space-y-3">
        <div className="bg-white border rounded-lg p-4 space-y-3"
             style={{ borderColor: COL_BORDER }}>
          <div className="flex items-center gap-3">
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2">
                <label className="text-xs w-16" style={{ color: COL_BRUN }}>ID</label>
                <input value={form.id} disabled
                       className="flex-1 px-2 py-1.5 rounded border bg-gray-50 text-sm"
                       style={{ borderColor: COL_BORDER }} />
              </div>
              <input type="text" value={form.lib}
                     onChange={(e) => setForm({ ...form, lib: e.target.value })}
                     placeholder="Lib"
                     className="w-full px-2 py-1.5 rounded border bg-white text-sm"
                     style={{ borderColor: COL_BORDER }} />
              <input type="text" value={form.type}
                     onChange={(e) => setForm({ ...form, type: e.target.value })}
                     placeholder="Type"
                     className="w-full px-2 py-1.5 rounded border bg-white text-sm"
                     style={{ borderColor: COL_BORDER }} />
            </div>
            <button type="button" onClick={onLogoClick}
                    className="w-20 h-20 border rounded flex items-center justify-center bg-gray-50 hover:bg-gray-100 cursor-pointer shrink-0"
                    style={{ borderColor: COL_BORDER }}>
              {current?.logo ? (
                <img src={current.logo} alt="" className="w-full h-full object-contain p-1" />
              ) : (
                <ImageIcon className="w-8 h-8 text-gray-300" />
              )}
            </button>
            <input ref={fileInputRef} type="file" accept="image/*"
                   onChange={onLogoChange} className="hidden" />
          </div>
          <button type="button" onClick={handleSave} disabled={saving}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-white text-sm disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            {form.id && form.id !== '0' ? 'Enregistrer' : 'Créer'}
          </button>
        </div>

        {/* Partenaires liés */}
        <div className="bg-white border rounded-lg p-3 space-y-2"
             style={{ borderColor: COL_BORDER }}>
          <h3 className="text-xs font-bold uppercase" style={{ color: COL_BRUN }}>
            Partenaires liés
          </h3>
          {!selected || selected === '0' ? (
            <p className="text-xs italic" style={{ color: '#A68D8A' }}>
              Sélectionne un type pour gérer les partenaires.
            </p>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <select value={newPartId}
                        onChange={(e) => setNewPartId(e.target.value)}
                        className="flex-1 px-2 py-1.5 rounded border bg-white text-sm"
                        style={{ borderColor: COL_BORDER }}>
                  <option value="">— Choisir un partenaire —</option>
                  {partenaires
                    .filter((p) => !liens.some((l) => l.id_partenaire === p.id_partenaire))
                    .map((p) => (
                      <option key={p.id_partenaire} value={p.id_partenaire}>
                        {p.lib}
                      </option>
                    ))}
                </select>
                <button type="button" onClick={handleAddPart}
                        disabled={!newPartId}
                        className="px-3 py-1.5 rounded text-white text-sm disabled:opacity-50"
                        style={{ backgroundColor: COL_PRIMARY }}>
                  Ajouter
                </button>
              </div>
              <div className="border rounded overflow-auto"
                   style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT, maxHeight: 200 }}>
                {liens.length === 0 ? (
                  <p className="text-xs italic p-3" style={{ color: '#A68D8A' }}>
                    Aucun partenaire lié.
                  </p>
                ) : (
                  liens.map((l) => (
                    <div key={l.id_type_produit_partenaire}
                         className="flex items-center justify-between px-2 py-1.5 border-b text-sm"
                         style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
                      <span>{partLibById(l.id_partenaire)}</span>
                      <button type="button" onClick={() => handleDelPart(l.id_type_produit_partenaire)}
                              className="text-red-600 hover:text-red-800">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Portails Partenaires (BDD recrutement.pgt_portail_partenaire)
// ============================================================================

interface PortailRow {
  id: string
  id_partenaire: string
  partenaire_lib: string
  lien_portail: string
  login: string
  mdp: string
  id_entite: string
  mail_contact: string
  is_actif: boolean
}

function emptyPortail(): PortailRow {
  return {
    id: '0', id_partenaire: '', partenaire_lib: '',
    lien_portail: '', login: '', mdp: '',
    id_entite: '', mail_contact: '', is_actif: true,
  }
}

function PortailField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-xs w-24" style={{ color: COL_BRUN }}>{label}</label>
      <div className="flex-1">{children}</div>
    </div>
  )
}

function PortailsEditor() {
  const [rows, setRows] = useState<PortailRow[]>([])
  const [partenaires, setPartenaires] = useState<PartenaireCombo[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState('')
  const [form, setForm] = useState<PortailRow>(emptyPortail())
  const [saving, setSaving] = useState(false)

  const reload = useCallback(() => {
    setLoading(true)
    Promise.all([
      fetch('/api/adm/params-rh/portail', {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) => r.ok ? r.json() : []),
      fetch('/api/adm/params-rh/partenaires', {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then((r) => r.ok ? r.json() : []),
    ])
      .then(([rs, pa]) => {
        setRows(Array.isArray(rs) ? rs : [])
        setPartenaires(Array.isArray(pa) ? pa : [])
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { reload() }, [reload])

  const handleSelect = (r: PortailRow) => {
    setSelected(r.id)
    setForm(r)
  }

  const handleNew = () => {
    setSelected('')
    setForm(emptyPortail())
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const r = await fetch('/api/adm/params-rh/portail', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id: form.id,
          id_partenaire: Number(form.id_partenaire) || 0,
          lien_portail: form.lien_portail,
          login: form.login,
          mdp: form.mdp,
          id_entite: form.id_entite,
          mail_contact: form.mail_contact,
          is_actif: form.is_actif,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setForm((f) => ({ ...f, id: d.id }))
      setSelected(d.id)
      showToast('Enregistré.', 'success')
      reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally { setSaving(false) }
  }

  const handleDelete = async () => {
    if (!selected) return
    const ok = await showConfirm({
      title: 'Supprimer ?',
      message: 'Confirmer la suppression de ce portail partenaire ?',
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    try {
      const r = await fetch(`/api/adm/params-rh/portail/${selected}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      handleNew()
      reload()
      showToast('Supprimé.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <Toolbar onNew={handleNew} onDelete={handleDelete} onReload={reload}
                 deleteDisabled={!selected || saving} />
        <div className="border rounded-lg overflow-auto bg-white"
             style={{ borderColor: COL_BORDER, maxHeight: 500 }}>
          <table className="w-full text-xs">
            <thead className="sticky top-0" style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
              <tr>
                <th className="px-2 py-2 text-left">Partenaire</th>
                <th className="px-2 py-2 text-left">Lien Portail</th>
                <th className="px-2 py-2 text-left">Login</th>
                <th className="px-2 py-2 text-left">Entité</th>
                <th className="px-2 py-2 text-center w-12">Actif</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} className="p-4 text-center">
                  <Loader2 className="w-4 h-4 animate-spin inline" /></td></tr>
              ) : rows.length === 0 ? (
                <tr><td colSpan={5} className="p-4 text-center italic" style={{ color: '#A68D8A' }}>
                  Aucun portail.</td></tr>
              ) : (
                rows.map((r) => {
                  const isSel = selected === r.id
                  return (
                    <tr key={r.id} onClick={() => handleSelect(r)}
                        className="cursor-pointer border-b"
                        style={{
                          backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                          color: isSel ? 'white' : COL_BRUN,
                          borderColor: COL_BORDER,
                        }}>
                      <td className="px-2 py-1 font-semibold">{r.partenaire_lib}</td>
                      <td className="px-2 py-1 truncate max-w-xs">{r.lien_portail}</td>
                      <td className="px-2 py-1">{r.login}</td>
                      <td className="px-2 py-1">{r.id_entite}</td>
                      <td className="px-2 py-1 text-center">{r.is_actif ? '✓' : ''}</td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-4 grid grid-cols-2 gap-x-6 gap-y-2 max-w-3xl"
           style={{ borderColor: COL_BORDER }}>
        <div className="flex items-center gap-2 col-span-2">
          <label className="text-xs w-24" style={{ color: COL_BRUN }}>ID</label>
          <input value={form.id} disabled
                 className="flex-1 px-2 py-1.5 rounded border bg-gray-50 text-sm"
                 style={{ borderColor: COL_BORDER }} />
        </div>
        <PortailField label="Partenaire">
          <select value={form.id_partenaire}
                  onChange={(e) => setForm({ ...form, id_partenaire: e.target.value })}
                  className="w-full px-2 py-1.5 rounded border bg-white text-sm"
                  style={{ borderColor: COL_BORDER }}>
            <option value="">—</option>
            {partenaires.map((p) => (
              <option key={p.id_partenaire} value={p.id_partenaire}>{p.lib}</option>
            ))}
          </select>
        </PortailField>
        <PortailField label="Url Portail">
          <input type="text" value={form.lien_portail}
                 onChange={(e) => setForm({ ...form, lien_portail: e.target.value })}
                 className="w-full px-2 py-1.5 rounded border bg-white text-sm"
                 style={{ borderColor: COL_BORDER }} />
        </PortailField>
        <PortailField label="Login">
          <input type="text" value={form.login}
                 onChange={(e) => setForm({ ...form, login: e.target.value })}
                 className="w-full px-2 py-1.5 rounded border bg-white text-sm"
                 style={{ borderColor: COL_BORDER }} />
        </PortailField>
        <PortailField label="MDP">
          <input type="text" value={form.mdp}
                 onChange={(e) => setForm({ ...form, mdp: e.target.value })}
                 className="w-full px-2 py-1.5 rounded border bg-white text-sm"
                 style={{ borderColor: COL_BORDER }} />
        </PortailField>
        <PortailField label="Id Entité">
          <input type="text" value={form.id_entite}
                 onChange={(e) => setForm({ ...form, id_entite: e.target.value })}
                 placeholder="Toutes"
                 className="w-full px-2 py-1.5 rounded border bg-white text-sm"
                 style={{ borderColor: COL_BORDER }} />
        </PortailField>
        <PortailField label="Mail contact">
          <input type="email" value={form.mail_contact}
                 onChange={(e) => setForm({ ...form, mail_contact: e.target.value })}
                 className="w-full px-2 py-1.5 rounded border bg-white text-sm"
                 style={{ borderColor: COL_BORDER }} />
        </PortailField>
        <label className="flex items-center gap-2 text-sm col-span-2" style={{ color: COL_BRUN }}>
          <input type="checkbox" checked={form.is_actif}
                 onChange={(e) => setForm({ ...form, is_actif: e.target.checked })} />
          Visible / Actif
        </label>
        <button type="button" onClick={handleSave} disabled={saving}
                className="col-span-2 flex items-center justify-center gap-2 px-3 py-2 rounded text-white text-sm disabled:opacity-50"
                style={{ backgroundColor: COL_PRIMARY }}>
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          {form.id && form.id !== '0' ? 'Enregistrer' : 'Créer'}
        </button>
      </div>
    </div>
  )
}
