/**
 * Onglet 'Note de frais' de la fiche salarie ADM.
 *
 * Etape 1 : combos Mois + Annee + tableau (rupture par mois) + selection
 * + formulaire d'edition + Enregistrer + Supprimer.
 *
 * Etapes suivantes (commits dedies) :
 *   - Bouton '+' : popup Nouvelle ligne (Fen_NoteFraisAjout)
 *   - Charger une photo (upload bytea)
 *   - Bouton impression (PDF complet : EtatNoteFrais + EtatPhotoTicket)
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Image as ImageIcon, Loader2, Plus, Printer, Save, Trash2 } from 'lucide-react'

import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'
import {
  AdmCheckbox,
  COLOR_BG_SOFT,
  COLOR_BRUN,
  COLOR_PRIMARY,
} from '@shared/fiche/EmbaucheTab'
import NoteFraisAjoutModal from './NoteFraisAjoutModal'

interface TypeRef {
  id_note_frais_type: number
  lib_type_note_frais: string
}

interface NoteRow {
  id_note_frais: string
  id_note_frais_type: number
  lib_type_note_frais: string
  date: string
  description: string
  montant_ht: number
  montant_tva: number
  montant_ttc: number
  verifiee: boolean
  has_photo: boolean
}

interface Props {
  idSalarie: string
}

const MOIS_LIBELLES = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
]

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

function fmtEur(n: number): string {
  return `${n.toFixed(2).replace('.', ',')} €`
}

function moisAn(iso: string): string {
  if (!iso || iso.length < 7) return ''
  const m = Number(iso.slice(5, 7))
  return `${MOIS_LIBELLES[m - 1] || ''} ${iso.slice(0, 4)}`
}

export default function NoteFraisTab({ idSalarie }: Props) {
  const today = new Date()
  const [mois, setMois] = useState(today.getMonth() + 1)
  const [annee, setAnnee] = useState(today.getFullYear())
  const [types, setTypes] = useState<TypeRef[]>([])
  const [rows, setRows] = useState<NoteRow[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [edit, setEdit] = useState<NoteRow | null>(null)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [ajoutOpen, setAjoutOpen] = useState(false)
  const [uploadingPhoto, setUploadingPhoto] = useState(false)
  const [photoUrl, setPhotoUrl] = useState<string>('')
  const [photoVersion, setPhotoVersion] = useState(0)
  const photoInputRef = useRef<HTMLInputElement | null>(null)

  // Combo Types
  useEffect(() => {
    fetch('/api/adm/fiche-salarie/note-frais/types', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((j) => setTypes((j as { items: TypeRef[] }).items || []))
      .catch(() => {})
  }, [])

  const reload = useCallback(async () => {
    if (!idSalarie) return
    setLoading(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/note-frais?mois=${mois}&annee=${annee}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as { items: NoteRow[] }
      const items = j.items || []
      setRows(items)
      if (selected && !items.some((i) => i.id_note_frais === selected)) {
        setSelected(null)
        setEdit(null)
      }
    } catch (e) {
      showToast(`Échec chargement : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idSalarie, mois, annee, selected])

  useEffect(() => {
    void reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idSalarie, mois, annee])

  // Charge la photo en blob (impossible de mettre Authorization sur <img>).
  // photoVersion force le refetch apres un upload sur la meme note.
  useEffect(() => {
    if (!edit || !edit.has_photo) {
      setPhotoUrl('')
      return
    }
    let cancelled = false
    let objUrl = ''
    fetch(`/api/adm/fiche-salarie/note-frais/${edit.id_note_frais}/photo`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.blob() : Promise.reject(String(r.status))))
      .then((blob) => {
        if (cancelled) return
        objUrl = URL.createObjectURL(blob)
        setPhotoUrl(objUrl)
      })
      .catch(() => !cancelled && setPhotoUrl(''))
    return () => {
      cancelled = true
      if (objUrl) URL.revokeObjectURL(objUrl)
    }
  }, [edit?.id_note_frais, edit?.has_photo, photoVersion])

  // Selection -> charge le detail
  const handleSelect = async (id: string) => {
    setSelected(id)
    const row = rows.find((r) => r.id_note_frais === id)
    if (row) setEdit({ ...row })
  }

  const groups = useMemo(() => {
    const map = new Map<string, NoteRow[]>()
    for (const it of rows) {
      const k = it.date.slice(0, 7) || '?'
      const arr = map.get(k) || []
      arr.push(it)
      map.set(k, arr)
    }
    return Array.from(map.entries()).map(([key, items]) => ({
      key,
      label: moisAn(items[0]?.date || `${key}-01`),
      items,
    }))
  }, [rows])

  const totals = useMemo(() => {
    const ht = rows.reduce((a, r) => a + (r.montant_ht || 0), 0)
    const tva = rows.reduce((a, r) => a + (r.montant_tva || 0), 0)
    const ttc = rows.reduce((a, r) => a + (r.montant_ttc || 0), 0)
    return { ht, tva, ttc }
  }, [rows])

  const handleSave = async () => {
    if (!edit) return
    if (!edit.id_note_frais_type) {
      showToast('Sélectionner un type.', 'error')
      return
    }
    setSaving(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/note-frais/${edit.id_note_frais}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({
            id_note_frais_type: edit.id_note_frais_type,
            date: edit.date,
            description: edit.description,
            montant_ht: edit.montant_ht,
            montant_tva: edit.montant_tva,
            montant_ttc: edit.montant_ttc,
            verifiee: edit.verifiee,
          }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast('Note enregistrée.', 'success')
      await reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleSupprimer = async () => {
    if (!selected) {
      showToast('Sélectionner une ligne.', 'info')
      return
    }
    const ok = await showConfirm({
      title: 'Supprimer cette ligne ?',
      message: 'Vous êtes sur le point de supprimer cette ligne. Voulez-vous continuer ?',
      confirmLabel: 'Supprimer',
      variant: 'danger',
    })
    if (!ok) return
    setDeleting(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/note-frais/${selected}`,
        { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      setSelected(null)
      setEdit(null)
      await reload()
      showToast('Ligne supprimée.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setDeleting(false)
    }
  }

  const handleChargerPhoto = () => {
    if (!edit) return
    photoInputRef.current?.click()
  }

  const handlePhotoChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !edit) return
    setUploadingPhoto(true)
    try {
      const fd = new FormData()
      fd.append('photo', file)
      const r = await fetch(
        `/api/adm/fiche-salarie/note-frais/${edit.id_note_frais}/photo`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
          body: fd,
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast('Photo enregistrée.', 'success')
      setEdit((p) => (p ? { ...p, has_photo: true } : p))
      // Force le useEffect a refetch meme si has_photo etait deja true.
      setPhotoVersion((v) => v + 1)
      await reload()
    } catch (err) {
      showToast(`Échec upload : ${(err as Error).message}`, 'error')
    } finally {
      setUploadingPhoto(false)
      e.target.value = ''
    }
  }

  const placeholder = (label: string) => () =>
    showToast(`${label} : à brancher dans un prochain commit.`, 'info')

  const template = '110px 90px 130px 1fr 80px 80px 80px 70px 30px'

  // Liste années (current ± 5)
  const annees = useMemo(() => {
    const out: number[] = []
    for (let y = today.getFullYear() + 1; y >= today.getFullYear() - 10; y--) {
      out.push(y)
    }
    return out
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Combos + actions */}
      <div className="flex items-center gap-2 flex-wrap">
        <select
          value={mois}
          onChange={(e) => setMois(Number(e.target.value))}
          className="px-2 py-1 border rounded text-sm bg-white"
          style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
        >
          {MOIS_LIBELLES.map((m, i) => (
            <option key={m} value={i + 1}>
              {m}
            </option>
          ))}
        </select>
        <select
          value={annee}
          onChange={(e) => setAnnee(Number(e.target.value))}
          className="px-2 py-1 border rounded text-sm bg-white"
          style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
        >
          {annees.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
        <div className="flex-1" />
        <ToolBtn icon={Plus} label="Nouveau" onClick={() => setAjoutOpen(true)} primary />
        <ToolBtn icon={Printer} label="Imprimer" onClick={placeholder('Imprimer')} />
        <ToolBtn
          icon={Trash2}
          label="Supprimer"
          onClick={handleSupprimer}
          disabled={!selected || deleting}
          danger
        />
        {(loading || deleting) && (
          <Loader2 className="w-4 h-4 animate-spin ml-2" style={{ color: COLOR_PRIMARY }} />
        )}
      </div>

      {/* Tableau */}
      <div
        className="border rounded overflow-hidden flex flex-col flex-shrink-0"
        style={{ borderColor: COLOR_BG_SOFT, maxHeight: 320 }}
      >
        <div
          className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
          style={{
            gridTemplateColumns: template,
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div>Mois An</div>
          <div>Date</div>
          <div>Type</div>
          <div>Description</div>
          <div className="text-right">HT</div>
          <div className="text-right">TVA</div>
          <div className="text-right">TTC</div>
          <div className="text-center">Vérif.</div>
          <div className="text-center">📎</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {!loading && rows.length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucune note de frais sur cette période.
            </div>
          )}
          {groups.map((g) => (
            <div key={g.key}>
              <div
                className="px-3 py-1 text-xs font-bold"
                style={{ backgroundColor: '#F7EEEB', color: COLOR_BRUN }}
              >
                {g.label}
              </div>
              {g.items.map((it) => {
                const sel = selected === it.id_note_frais
                return (
                  <div
                    key={it.id_note_frais}
                    onClick={() => void handleSelect(it.id_note_frais)}
                    className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
                    style={{
                      gridTemplateColumns: template,
                      backgroundColor: sel ? COLOR_BG_SOFT : 'white',
                      borderColor: COLOR_BG_SOFT,
                      color: COLOR_BRUN,
                    }}
                  >
                    <div className="truncate">{moisAn(it.date)}</div>
                    <div>{fmtDate(it.date)}</div>
                    <div className="truncate" title={it.lib_type_note_frais}>
                      {it.lib_type_note_frais}
                    </div>
                    <div className="truncate" title={it.description}>
                      {it.description}
                    </div>
                    <div className="text-right">{fmtEur(it.montant_ht)}</div>
                    <div className="text-right">{fmtEur(it.montant_tva)}</div>
                    <div className="text-right">{fmtEur(it.montant_ttc)}</div>
                    <div className="text-center">{it.verifiee ? '✓' : ''}</div>
                    <div className="text-center">{it.has_photo ? '📷' : ''}</div>
                  </div>
                )
              })}
            </div>
          ))}
        </div>
        {/* Footer total */}
        <div
          className="grid items-center gap-2 px-3 py-1.5 text-xs font-semibold border-t"
          style={{
            gridTemplateColumns: template,
            color: COLOR_BRUN,
            backgroundColor: '#F0E6E2',
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div>Somme</div>
          <div />
          <div />
          <div />
          <div className="text-right">{fmtEur(totals.ht)}</div>
          <div className="text-right">{fmtEur(totals.tva)}</div>
          <div className="text-right">{fmtEur(totals.ttc)}</div>
          <div />
          <div />
        </div>
      </div>

      {/* Formulaire d'édition */}
      <div
        className="border rounded p-3 flex gap-4"
        style={{ borderColor: COLOR_BG_SOFT, backgroundColor: '#FBF9F8' }}
      >
        <div className="flex-1 grid grid-cols-2 gap-x-6 gap-y-2 min-w-0">
          <Field label="Type">
            <select
              value={edit?.id_note_frais_type || 0}
              onChange={(e) =>
                setEdit((p) => (p ? { ...p, id_note_frais_type: Number(e.target.value) || 0 } : p))
              }
              disabled={!edit}
              className="w-full px-2 py-1 border rounded text-sm bg-white disabled:opacity-50"
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
              <AdmCheckbox
                checked={edit?.verifiee || false}
                onChange={(v) => setEdit((p) => (p ? { ...p, verifiee: v } : p))}
              />
            </div>
          </Field>
          <Field label="Dépense du">
            <input
              type="date"
              value={edit?.date || ''}
              onChange={(e) => setEdit((p) => (p ? { ...p, date: e.target.value } : p))}
              disabled={!edit}
              className="w-full px-2 py-1 border rounded text-sm bg-white disabled:opacity-50"
              style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
            />
          </Field>
          <Field label="HT (€)">
            <input
              type="number"
              step="0.01"
              value={edit?.montant_ht ?? 0}
              onChange={(e) =>
                setEdit((p) => {
                  if (!p) return p
                  const ht = Number(e.target.value) || 0
                  return { ...p, montant_ht: ht, montant_ttc: ht + (p.montant_tva || 0) }
                })
              }
              disabled={!edit}
              className="w-full px-2 py-1 border rounded text-sm bg-white text-right disabled:opacity-50"
              style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
            />
          </Field>
          <Field label="Description" full>
            <textarea
              value={edit?.description || ''}
              onChange={(e) => setEdit((p) => (p ? { ...p, description: e.target.value } : p))}
              disabled={!edit}
              rows={2}
              className="w-full px-2 py-1 border rounded text-sm bg-white disabled:opacity-50"
              style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN, resize: 'vertical' }}
            />
          </Field>
          <Field label="TVA (€)">
            <input
              type="number"
              step="0.01"
              value={edit?.montant_tva ?? 0}
              onChange={(e) =>
                setEdit((p) => {
                  if (!p) return p
                  const tva = Number(e.target.value) || 0
                  return { ...p, montant_tva: tva, montant_ttc: (p.montant_ht || 0) + tva }
                })
              }
              disabled={!edit}
              className="w-full px-2 py-1 border rounded text-sm bg-white text-right disabled:opacity-50"
              style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
            />
          </Field>
          <div />
          <Field label="TTC (€)">
            <input
              type="number"
              step="0.01"
              value={edit?.montant_ttc ?? 0}
              onChange={(e) => setEdit((p) => (p ? { ...p, montant_ttc: Number(e.target.value) || 0 } : p))}
              disabled={!edit}
              className="w-full px-2 py-1 border rounded text-sm bg-white text-right disabled:opacity-50"
              style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
            />
          </Field>
          <div className="col-span-2 flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={!edit || saving}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded text-white disabled:opacity-40"
              style={{ backgroundColor: COLOR_PRIMARY }}
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Enregistrer
            </button>
          </div>
        </div>

        {/* Photo */}
        <div className="w-48 flex flex-col items-center justify-center gap-2">
          {edit?.has_photo && photoUrl ? (
            <a
              href={photoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="block"
            >
              <img
                src={photoUrl}
                alt="Ticket"
                className="w-40 h-40 object-cover border rounded cursor-zoom-in"
                style={{ borderColor: COLOR_BG_SOFT }}
              />
            </a>
          ) : (
            <div
              className="w-40 h-40 border rounded flex items-center justify-center"
              style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN, opacity: 0.4 }}
            >
              <ImageIcon className="w-12 h-12" />
            </div>
          )}
          <input
            ref={photoInputRef}
            type="file"
            accept="image/*,application/pdf"
            className="hidden"
            onChange={handlePhotoChange}
          />
          <button
            type="button"
            onClick={handleChargerPhoto}
            disabled={!edit || uploadingPhoto}
            className="inline-flex items-center gap-1 text-xs underline disabled:opacity-40"
            style={{ color: COLOR_PRIMARY }}
          >
            {uploadingPhoto && <Loader2 className="w-3 h-3 animate-spin" />}
            Charger une photo
          </button>
        </div>
      </div>

      {ajoutOpen && (
        <NoteFraisAjoutModal
          idSalarie={idSalarie}
          onClose={() => setAjoutOpen(false)}
          onSaved={() => {
            setAjoutOpen(false)
            void reload()
          }}
        />
      )}
    </div>
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

function ToolBtn({
  icon: Icon,
  label,
  onClick,
  disabled,
  primary,
  danger,
}: {
  icon: typeof Plus
  label: string
  onClick: () => void
  disabled?: boolean
  primary?: boolean
  danger?: boolean
}) {
  const color = primary ? 'white' : danger ? '#B91C1C' : COLOR_PRIMARY
  const bg = primary ? COLOR_PRIMARY : 'white'
  const border = primary ? COLOR_PRIMARY : danger ? '#B91C1C' : COLOR_PRIMARY
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border disabled:opacity-40"
      style={{ backgroundColor: bg, color, borderColor: border }}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  )
}
