/**
 * Fen_SalonSalarie (WinDev) - CRUD des salons visio d'un recruteur.
 *
 * Ouvert depuis Fen_EntretienAjout via le bouton '+' a cote du combo Visio.
 * Layout split : tableau gauche (liste) + form droite (edition).
 * Au close : appelle onClose(idSalonVisio) pour pre-selectionner dans le parent.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Edit, Loader2, Plus, Save, Trash2, Video, X,
} from 'lucide-react'
import { getToken } from '@/api'
import { showConfirm, showToast } from '../ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface SalonRow {
  id_salon_visio: string
  id_type_salon_visio: string
  lib_salon: string
  lien_salon: string
  id_salon: string
  mpd_salon: string
}

interface TypeSalon {
  id_type_salon_visio: string
  lib_salon: string
}

interface SalonsSalarieModalProps {
  apiBase: string
  idRecruteur: string
  onClose: (selectedId?: string) => void
}

export default function SalonsSalarieModal({
  apiBase, idRecruteur, onClose,
}: SalonsSalarieModalProps) {
  const [salons, setSalons] = useState<SalonRow[]>([])
  const [types, setTypes] = useState<TypeSalon[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [selectedId, setSelectedId] = useState('')

  // Form
  const [formId, setFormId] = useState('0')
  const [formType, setFormType] = useState('')
  const [formLien, setFormLien] = useState('')
  const [formIdSalon, setFormIdSalon] = useState('')
  const [formMdp, setFormMdp] = useState('')

  const reload = useCallback(() => {
    setLoading(true)
    Promise.all([
      fetch(`${apiBase}/recrutement/cv/salons-visio?id_salarie=${idRecruteur}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then(r => r.ok ? r.json() : []),
      fetch(`${apiBase}/recrutement/cv/salons-visio/types`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then(r => r.ok ? r.json() : []),
    ])
      .then(([s, t]) => { setSalons(s); setTypes(t) })
      .finally(() => setLoading(false))
  }, [apiBase, idRecruteur])

  useEffect(() => { reload() }, [reload])

  const resetForm = () => {
    setFormId('0'); setFormType(''); setFormLien('')
    setFormIdSalon(''); setFormMdp('')
    setSelectedId('')
  }

  const editSalon = (s: SalonRow) => {
    setSelectedId(s.id_salon_visio)
    setFormId(s.id_salon_visio)
    setFormType(s.id_type_salon_visio)
    setFormLien(s.lien_salon)
    setFormIdSalon(s.id_salon)
    setFormMdp(s.mpd_salon)
  }

  const enregistrer = async () => {
    if (!formType) { showToast('Choisis un type de salon.', 'info'); return }
    setSaving(true)
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/salons-visio`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_salon_visio: formId,
          id_salarie: idRecruteur,
          id_type_salon_visio: formType,
          lien_salon: formLien,
          id_salon: formIdSalon,
          mpd_salon: formMdp,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      showToast(formId === '0' ? 'Salon ajouté.' : 'Salon modifié.', 'success')
      setSelectedId(d.id_salon_visio)
      setFormId(d.id_salon_visio)
      reload()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setSaving(false) }
  }

  const supprimer = async () => {
    if (!selectedId) return
    const ok = await showConfirm({
      title: 'Supprimer ce salon ?',
      message: 'Confirmer la suppression de ce salon visio ?',
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/salons-visio/${selectedId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Salon supprimé.', 'success')
      resetForm()
      reload()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-[70] flex items-center justify-center p-4"
         onClick={() => onClose(selectedId || undefined)}>
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col"
           onClick={e => e.stopPropagation()}
           style={{ border: `1px solid ${COL_BORDER}` }}>
        <div className="px-4 py-3 border-b flex items-center gap-2"
             style={{ borderColor: COL_BORDER }}>
          <Video className="w-5 h-5" style={{ color: COL_PRIMARY }} />
          <h2 className="text-lg font-bold flex-1" style={{ color: COL_BRUN }}>
            Salons Visio du recruteur
          </h2>
          <button type="button" onClick={() => onClose(selectedId || undefined)}
                  className="p-1.5 rounded hover:bg-gray-100">
            <X className="w-5 h-5" style={{ color: COL_BRUN }} />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin" style={{ color: COL_PRIMARY }} />
          </div>
        ) : (
          <div className="flex-1 flex min-h-0">
            {/* GAUCHE : liste + toolbar */}
            <div className="flex-1 flex flex-col min-w-0 border-r"
                 style={{ borderColor: COL_BORDER }}>
              <div className="px-3 py-2 flex items-center gap-2 border-b"
                   style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
                <Btn onClick={resetForm} icon={Plus} primary>Nouveau</Btn>
                <Btn onClick={supprimer} icon={Trash2} variant="danger"
                     disabled={!selectedId}>Supprimer</Btn>
                <Btn onClick={() => {
                  const s = salons.find(x => x.id_salon_visio === selectedId)
                  if (s) editSalon(s)
                }} icon={Edit} disabled={!selectedId}>Éditer</Btn>
              </div>
              <div className="flex-1 overflow-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0"
                         style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                    <tr>
                      <th className="px-2 py-2 text-left">Type</th>
                      <th className="px-2 py-2 text-left">Lien Salon</th>
                      <th className="px-2 py-2 text-left">ID Salon</th>
                    </tr>
                  </thead>
                  <tbody>
                    {salons.length === 0 ? (
                      <tr><td colSpan={3} className="p-6 text-center italic"
                              style={{ color: '#A68D8A' }}>
                        Aucun salon pour ce recruteur.
                      </td></tr>
                    ) : (
                      salons.map(s => {
                        const isSel = selectedId === s.id_salon_visio
                        return (
                          <tr key={s.id_salon_visio}
                              onClick={() => editSalon(s)}
                              className="cursor-pointer border-b"
                              style={{
                                backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                                color: isSel ? 'white' : COL_BRUN,
                                borderColor: COL_BORDER,
                              }}>
                            <td className="px-2 py-1.5 font-semibold">{s.lib_salon}</td>
                            <td className="px-2 py-1.5 truncate max-w-xs">{s.lien_salon}</td>
                            <td className="px-2 py-1.5">{s.id_salon}</td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* DROITE : form edit/create */}
            <div className="w-80 shrink-0 p-4 space-y-2">
              <Row label="ID">
                <input value={formId} disabled
                       className="w-full px-2 py-1.5 rounded border bg-gray-50 text-sm"
                       style={{ borderColor: COL_BORDER }} />
              </Row>
              <Row label="Visio">
                <select value={formType} onChange={e => setFormType(e.target.value)}
                        className="w-full px-2 py-1.5 rounded border text-sm"
                        style={{ borderColor: COL_BORDER }}>
                  <option value="">—</option>
                  {types.map(t => (
                    <option key={t.id_type_salon_visio} value={t.id_type_salon_visio}>
                      {t.lib_salon}
                    </option>
                  ))}
                </select>
              </Row>
              <Row label="Lien">
                <input type="url" value={formLien}
                       onChange={e => setFormLien(e.target.value)}
                       placeholder="https://..."
                       className="w-full px-2 py-1.5 rounded border text-sm"
                       style={{ borderColor: COL_BORDER }} />
              </Row>
              <Row label="Id Salon">
                <input type="text" value={formIdSalon}
                       onChange={e => setFormIdSalon(e.target.value)}
                       className="w-full px-2 py-1.5 rounded border text-sm"
                       style={{ borderColor: COL_BORDER }} />
              </Row>
              <Row label="MDP">
                <input type="text" value={formMdp}
                       onChange={e => setFormMdp(e.target.value)}
                       className="w-full px-2 py-1.5 rounded border text-sm"
                       style={{ borderColor: COL_BORDER }} />
              </Row>
              <button type="button" onClick={enregistrer} disabled={saving}
                      className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-white text-sm mt-3 disabled:opacity-50"
                      style={{ backgroundColor: COL_PRIMARY }}>
                {saving ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Save className="w-4 h-4" />}
                Enregistrer
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
    <div className="grid grid-cols-[80px_1fr] items-center gap-2 min-h-9">
      <label className="text-xs text-right" style={{ color: COL_BRUN }}>{label}</label>
      <div className="min-w-0">{children}</div>
    </div>
  )
}

function Btn({ onClick, icon: Icon, children, primary, disabled, variant }: {
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
