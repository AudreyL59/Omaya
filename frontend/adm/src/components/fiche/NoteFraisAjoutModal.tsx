/**
 * Popup 'Ajouter une note de frais' (transposition Fen_NoteFraisAjout).
 *
 * Champs : Type (combo) + Date + Description + HT + TVA + TTC +
 * Vérifiée + Photo (optionnelle). POST en multipart.
 */

import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Image as ImageIcon, Loader2, Save, Upload, X } from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import {
  AdmCheckbox,
  COLOR_BG_SOFT,
  COLOR_BRUN,
  COLOR_PRIMARY,
} from '@shared/fiche/EmbaucheTab'

interface TypeRef {
  id_note_frais_type: number
  lib_type_note_frais: string
}

interface Props {
  idSalarie: string
  onClose: () => void
  onSaved: () => void
}

export default function NoteFraisAjoutModal({ idSalarie, onClose, onSaved }: Props) {
  const today = new Date().toISOString().slice(0, 10)
  const [types, setTypes] = useState<TypeRef[]>([])
  const [idType, setIdType] = useState(0)
  const [date, setDate] = useState(today)
  const [description, setDescription] = useState('')
  const [ht, setHt] = useState(0)
  const [tva, setTva] = useState(0)
  const [ttc, setTtc] = useState(0)
  const [verifiee, setVerifiee] = useState(false)
  const [photoFile, setPhotoFile] = useState<File | null>(null)
  const [photoPreview, setPhotoPreview] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const fileRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    fetch('/api/adm/fiche-salarie/note-frais/types', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((j) => setTypes((j as { items: TypeRef[] }).items || []))
      .catch(() => {})
  }, [])

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null
    setPhotoFile(f)
    if (photoPreview) URL.revokeObjectURL(photoPreview)
    setPhotoPreview(f ? URL.createObjectURL(f) : '')
  }

  const handleSave = async () => {
    if (!idType) {
      showToast('Sélectionner un type.', 'error')
      return
    }
    if (!date) {
      showToast('Saisir une date.', 'error')
      return
    }
    setSaving(true)
    try {
      const params = new URLSearchParams({
        id_note_frais_type: String(idType),
        date,
        description,
        montant_ht: String(ht),
        montant_tva: String(tva),
        montant_ttc: String(ttc),
        verifiee: String(verifiee),
      })
      const fd = new FormData()
      if (photoFile) fd.append('photo', photoFile)
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/note-frais?${params.toString()}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
          body: photoFile ? fd : undefined,
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast('Note ajoutée.', 'success')
      onSaved()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white rounded-2xl shadow-2xl w-[820px] max-w-[95vw] max-h-[85vh] flex flex-col overflow-hidden"
        >
          <div
            className="flex items-center justify-between px-5 py-3 border-b"
            style={{ borderColor: COLOR_BG_SOFT }}
          >
            <h2 className="text-base font-semibold" style={{ color: COLOR_BRUN }}>
              Nouvelle note de frais
            </h2>
            <button
              onClick={onClose}
              className="p-1 rounded hover:bg-[#EFE9E7]"
              style={{ color: COLOR_BRUN }}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-5 flex gap-5">
            <div className="flex-1 grid grid-cols-2 gap-x-6 gap-y-2 min-w-0">
              <Field label="Type">
                <select
                  value={idType}
                  onChange={(e) => setIdType(Number(e.target.value) || 0)}
                  className="w-full px-2 py-1 border rounded text-sm"
                  style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
                >
                  <option value={0}>—</option>
                  {types.map((t) => (
                    <option key={t.id_note_frais_type} value={t.id_note_frais_type}>
                      {t.lib_type_note_frais}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Vérifiée">
                <div className="flex items-center h-7">
                  <AdmCheckbox checked={verifiee} onChange={setVerifiee} />
                </div>
              </Field>
              <Field label="Dépense du">
                <input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="w-full px-2 py-1 border rounded text-sm"
                  style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
                />
              </Field>
              <Field label="HT (€)">
                <input
                  type="number"
                  step="0.01"
                  value={ht}
                  onChange={(e) => {
                    const v = Number(e.target.value) || 0
                    setHt(v)
                    setTtc(v + tva)
                  }}
                  className="w-full px-2 py-1 border rounded text-sm text-right"
                  style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
                />
              </Field>
              <Field label="Description" full>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  className="w-full px-2 py-1 border rounded text-sm"
                  style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN, resize: 'vertical' }}
                />
              </Field>
              <Field label="TVA (€)">
                <input
                  type="number"
                  step="0.01"
                  value={tva}
                  onChange={(e) => {
                    const v = Number(e.target.value) || 0
                    setTva(v)
                    setTtc(ht + v)
                  }}
                  className="w-full px-2 py-1 border rounded text-sm text-right"
                  style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
                />
              </Field>
              <div />
              <Field label="TTC (€)">
                <input
                  type="number"
                  step="0.01"
                  value={ttc}
                  onChange={(e) => setTtc(Number(e.target.value) || 0)}
                  className="w-full px-2 py-1 border rounded text-sm text-right"
                  style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
                />
              </Field>
            </div>

            <div className="w-48 flex flex-col items-center justify-center gap-2">
              {photoPreview ? (
                <img
                  src={photoPreview}
                  alt="Aperçu"
                  className="w-40 h-40 object-cover border rounded"
                  style={{ borderColor: COLOR_BG_SOFT }}
                />
              ) : (
                <div
                  className="w-40 h-40 border rounded flex items-center justify-center"
                  style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN, opacity: 0.4 }}
                >
                  <ImageIcon className="w-12 h-12" />
                </div>
              )}
              <input
                ref={fileRef}
                type="file"
                accept="image/*,application/pdf"
                className="hidden"
                onChange={handleFile}
              />
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded border"
                style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
              >
                <Upload className="w-3.5 h-3.5" />
                Charger une photo
              </button>
            </div>
          </div>

          <div
            className="px-5 py-3 border-t flex justify-end gap-2"
            style={{ borderColor: COLOR_BG_SOFT }}
          >
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-sm rounded border"
              style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
            >
              Annuler
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !idType || !date}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded text-white disabled:opacity-40"
              style={{ backgroundColor: COLOR_PRIMARY }}
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Enregistrer
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

function Field({
  label,
  children,
  full,
}: {
  label: string
  children: React.ReactNode
  full?: boolean
}) {
  return (
    <div className={`flex flex-col gap-1 min-w-0 ${full ? 'col-span-2' : ''}`}>
      <label className="text-[10px] font-medium uppercase tracking-wider" style={{ color: COLOR_BRUN }}>
        {label}
      </label>
      {children}
    </div>
  )
}
