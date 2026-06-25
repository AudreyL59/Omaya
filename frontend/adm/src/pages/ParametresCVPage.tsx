/**
 * Fen_ParamCV (ADM Recrutement -> Parametres CVtheque).
 *
 * 5 onglets : Source / Annonceurs / Salons Visio / Postes / Statuts.
 * Pattern identique a ParametresRH : layout split tableau gauche +
 * form droite, toolbar Nouveau / Editer / Supprimer.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Edit, Image as ImageIcon, Loader2, Plus, Save, Settings, Trash2, Upload,
} from 'lucide-react'
import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface EntityRow {
  id: string
  [k: string]: string | boolean
}

interface TabCfg {
  key: string
  label: string
  entity: string                 // backend entity name
  labelCol: string               // ex: lib_source
  labelHeader: string            // ex: 'Source'
  hasIsActif: boolean            // false pour cv_statut
  hasLogo?: boolean              // cv_annonceur
  extraField?: string            // cv_statut -> 'icone'
  extraFieldLabel?: string
}

const TABS: TabCfg[] = [
  { key: 'source', label: 'Source', entity: 'cv_source',
    labelCol: 'lib_source', labelHeader: 'Source', hasIsActif: true },
  { key: 'annonceurs', label: 'Annonceurs', entity: 'cv_annonceur',
    labelCol: 'lib_annonceur', labelHeader: 'Annonceur',
    hasIsActif: true, hasLogo: true },
  { key: 'salons', label: 'Salons Visio', entity: 'salon_visio',
    labelCol: 'lib_salon', labelHeader: 'Nom', hasIsActif: true },
  { key: 'postes', label: 'Postes', entity: 'cv_poste',
    labelCol: 'lib_poste', labelHeader: 'Poste', hasIsActif: true },
  { key: 'statuts', label: 'Statuts', entity: 'cv_statut',
    labelCol: 'lib_statut', labelHeader: 'Statut',
    hasIsActif: false, extraField: 'icone', extraFieldLabel: 'Icône' },
]

const API_BASE = '/api/adm'

export default function ParametresCVPage() {
  useDocumentTitle('Paramètres CVthèque')
  const [activeTab, setActiveTab] = useState(TABS[0].key)

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-120px)]"
         style={{ color: COL_BRUN }}>
      <h1 className="text-xl font-bold mb-3 flex items-center gap-2">
        <Settings className="w-5 h-5" style={{ color: COL_PRIMARY }} />
        Paramètres CVthèque
      </h1>

      <div className="flex border-b mb-3" style={{ borderColor: COL_BORDER }}>
        {TABS.map(t => (
          <button key={t.key} type="button" onClick={() => setActiveTab(t.key)}
                  className="px-4 py-2 text-sm border-b-2"
                  style={{
                    borderColor: activeTab === t.key ? COL_PRIMARY : 'transparent',
                    color: activeTab === t.key ? COL_PRIMARY : '#A68D8A',
                    fontWeight: activeTab === t.key ? 'bold' : 'normal',
                  }}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 min-h-0">
        {TABS.filter(t => t.key === activeTab).map(t => (
          <EntityTab key={t.key} cfg={t} />
        ))}
      </div>
    </div>
  )
}

function EntityTab({ cfg }: { cfg: TabCfg }) {
  const [rows, setRows] = useState<EntityRow[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState('')

  // Form
  const [formId, setFormId] = useState('0')
  const [formLabel, setFormLabel] = useState('')
  const [formActif, setFormActif] = useState(true)
  const [formExtra, setFormExtra] = useState('')
  const [busy, setBusy] = useState(false)
  const fileInputRef = useState<HTMLInputElement | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    fetch(`${API_BASE}/params-cv/${cfg.entity}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(d => setRows(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false))
  }, [cfg.entity])

  useEffect(() => {
    load()
    setSelectedId(''); setFormId('0'); setFormLabel('')
    setFormActif(true); setFormExtra('')
  }, [load])

  const resetForm = () => {
    setSelectedId(''); setFormId('0'); setFormLabel('')
    setFormActif(true); setFormExtra('')
  }

  const editRow = (r: EntityRow) => {
    setSelectedId(r.id); setFormId(r.id)
    setFormLabel(String(r[cfg.labelCol] || ''))
    if (cfg.hasIsActif) setFormActif(Boolean(r.is_actif))
    if (cfg.extraField) setFormExtra(String(r[cfg.extraField] || ''))
  }

  const save = async () => {
    if (!formLabel.trim()) {
      showToast(`${cfg.labelHeader} requis.`, 'info'); return
    }
    setBusy(true)
    try {
      const payload: Record<string, unknown> = {
        id: formId, [cfg.labelCol]: formLabel,
      }
      if (cfg.hasIsActif) payload.is_actif = formActif
      if (cfg.extraField) payload[cfg.extraField] = formExtra
      const r = await fetch(`${API_BASE}/params-cv/${cfg.entity}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(payload),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      showToast(formId === '0' ? 'Ajouté.' : 'Modifié.', 'success')
      setSelectedId(d.id); setFormId(d.id); load()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setBusy(false) }
  }

  const supprimer = async () => {
    if (!selectedId) return
    const ok = await showConfirm({
      title: 'Supprimer ?',
      message: `Confirmer la suppression de "${formLabel}" ?`,
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    try {
      const r = await fetch(`${API_BASE}/params-cv/${cfg.entity}/${selectedId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Supprimé.', 'success')
      resetForm(); load()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }

  const uploadLogo = async (f: File) => {
    if (!selectedId || !f) return
    const fd = new FormData()
    fd.append('file', f)
    try {
      const r = await fetch(`${API_BASE}/params-cv/cv-annonceur/${selectedId}/logo`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Logo mis à jour.', 'success'); load()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }

  return (
    <div className="flex gap-3 h-full">
      {/* Tableau gauche */}
      <div className="flex-1 flex flex-col min-w-0 border rounded"
           style={{ borderColor: COL_BORDER }}>
        <div className="px-3 py-2 flex items-center gap-2 border-b"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <BtnTb onClick={resetForm} icon={Plus} primary>Nouveau</BtnTb>
          <BtnTb onClick={() => {
                   const r = rows.find(x => x.id === selectedId)
                   if (r) editRow(r)
                 }} icon={Edit} disabled={!selectedId}>Éditer</BtnTb>
          <BtnTb onClick={supprimer} icon={Trash2} variant="danger"
                 disabled={!selectedId}>Supprimer</BtnTb>
          <div className="flex-1" />
          <span className="text-xs italic" style={{ color: '#A68D8A' }}>
            {rows.length} ligne(s)
          </span>
        </div>
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="p-8 flex justify-center">
              <Loader2 className="w-6 h-6 animate-spin"
                       style={{ color: COL_PRIMARY }} />
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0"
                     style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                <tr>
                  <th className="px-2 py-2 text-left w-20">ID</th>
                  <th className="px-2 py-2 text-left">{cfg.labelHeader}</th>
                  {cfg.hasIsActif && <th className="px-2 py-2 text-center w-16">Actif</th>}
                  {cfg.hasLogo && <th className="px-2 py-2 text-center w-20">Logo</th>}
                  {cfg.extraField && (
                    <th className="px-2 py-2 text-left w-24">{cfg.extraFieldLabel}</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {rows.map(r => {
                  const isSel = selectedId === r.id
                  return (
                    <tr key={r.id} onClick={() => editRow(r)}
                        className="border-b cursor-pointer"
                        style={{
                          borderColor: COL_BORDER,
                          backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                          color: isSel ? 'white' : COL_BRUN,
                        }}>
                      <td className="px-2 py-1.5 font-mono">{r.id}</td>
                      <td className="px-2 py-1.5 font-semibold">
                        {String(r[cfg.labelCol] || '')}
                      </td>
                      {cfg.hasIsActif && (
                        <td className="px-2 py-1.5 text-center">
                          {r.is_actif ? '✅' : '❌'}
                        </td>
                      )}
                      {cfg.hasLogo && (
                        <td className="px-2 py-1.5 text-center">
                          {r.logo_b64 ? (
                            <img src={String(r.logo_b64)} alt="logo"
                                 className="h-6 inline" />
                          ) : <ImageIcon className="w-3 h-3 inline opacity-30" />}
                        </td>
                      )}
                      {cfg.extraField && (
                        <td className="px-2 py-1.5">
                          {String(r[cfg.extraField] || '')}
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Form droite */}
      <div className="w-80 shrink-0 border rounded p-3 space-y-2"
           style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
        <Row label="ID">
          <input value={formId} disabled
                 className="w-full px-2 py-1.5 rounded border bg-gray-100 text-sm font-mono"
                 style={{ borderColor: COL_BORDER }} />
        </Row>
        <Row label={cfg.labelHeader}>
          <input value={formLabel} onChange={e => setFormLabel(e.target.value)}
                 className="w-full px-2 py-1.5 rounded border text-sm"
                 style={{ borderColor: COL_BORDER }} />
        </Row>
        {cfg.extraField && (
          <Row label={cfg.extraFieldLabel || ''}>
            <input value={formExtra} onChange={e => setFormExtra(e.target.value)}
                   className="w-full px-2 py-1.5 rounded border text-sm"
                   style={{ borderColor: COL_BORDER }} />
          </Row>
        )}
        {cfg.hasIsActif && (
          <label className="flex items-center gap-2 text-sm pl-24"
                 style={{ color: COL_BRUN }}>
            <input type="checkbox" checked={formActif}
                   onChange={e => setFormActif(e.target.checked)} />
            Visible
          </label>
        )}
        <button type="button" onClick={save} disabled={busy}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-white text-sm mt-3 disabled:opacity-50"
                style={{ backgroundColor: COL_PRIMARY }}>
          {busy ? <Loader2 className="w-4 h-4 animate-spin" />
                : <Save className="w-4 h-4" />}
          Enregistrer
        </button>
        {cfg.hasLogo && selectedId && (
          <div className="border-t pt-3 mt-3" style={{ borderColor: COL_BORDER }}>
            <label className="text-[10px] block mb-1" style={{ color: COL_BRUN }}>
              Logo de l'annonceur
            </label>
            <div className="flex items-center gap-2">
              {(() => {
                const sel = rows.find(x => x.id === selectedId)
                const src = sel?.logo_b64 ? String(sel.logo_b64) : ''
                return src ? (
                  <img src={src} alt="logo"
                       className="h-10 border rounded p-1"
                       style={{ borderColor: COL_BORDER }} />
                ) : (
                  <div className="h-10 px-2 flex items-center text-[10px] italic"
                       style={{ color: '#A68D8A' }}>(aucun)</div>
                )
              })()}
              <input ref={el => { fileInputRef[0] = el }}
                     type="file" accept="image/*" className="hidden"
                     onChange={e => {
                       const f = e.target.files?.[0]; if (f) uploadLogo(f)
                       e.target.value = ''
                     }} />
              <button type="button" onClick={() => fileInputRef[0]?.click()}
                      className="flex items-center gap-1 px-2 py-1.5 rounded border text-xs"
                      style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
                <Upload className="w-3.5 h-3.5" />
                Changer
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[100px_1fr] items-center gap-2 min-h-8">
      <label className="text-xs text-right" style={{ color: COL_BRUN }}>{label}</label>
      <div className="min-w-0">{children}</div>
    </div>
  )
}

function BtnTb({ onClick, icon: Icon, children, primary, disabled, variant }: {
  onClick: () => void
  icon: React.ComponentType<{ className?: string }>
  children: React.ReactNode
  primary?: boolean
  disabled?: boolean
  variant?: 'danger'
}) {
  const bg = variant === 'danger' ? '#B91C1C' : primary ? COL_PRIMARY : 'white'
  const fg = primary || variant === 'danger' ? 'white' : COL_BRUN
  return (
    <button type="button" onClick={onClick} disabled={disabled}
            className="flex items-center gap-1 px-3 py-1.5 rounded border text-xs disabled:opacity-40"
            style={{ borderColor: COL_BORDER, backgroundColor: bg, color: fg }}>
      <Icon className="w-3.5 h-3.5" />
      {children}
    </button>
  )
}
