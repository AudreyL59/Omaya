/**
 * Fen_LotFiche - Fiche d'un lot Exo Cash.
 *
 * Formulaire :
 *   - Famille (combo) + Categorie (combo)
 *   - Marque + LibLot
 *   - Montant + Stock + Sur Commande + Actif
 *   - Bloc En Solde : MontantSolde + SoldeDeb + SoldeFin
 *   - Description (textarea) avec picker emoji (bouton Smiley)
 *   - 3 blocs Photo (Charger / Supprimer)
 *
 * Cf. WinDev Fen_LotFiche.
 */
import { useEffect, useRef, useState } from 'react'
import {
  X, Loader2, ImageIcon, Upload, Trash2, Save, Smile,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'

const API_BASE = '/api/adm'

interface Famille {
  id_exo_cash_famille_lot: string
  lib_famille_lot: string
}

interface LotDetail {
  id_exo_cash_lot: string
  id_exo_cash_famille_lot: string
  marque: string
  lib_lot: string
  categorie: number
  montant: number
  stock: number
  sur_commande: boolean
  en_solde: boolean
  montant_solde: number
  solde_deb: string
  solde_fin: string
  is_actif: boolean
  description: string
  has_photo1: boolean
  has_photo2: boolean
  has_photo3: boolean
}

const _EMPTY_LOT: LotDetail = {
  id_exo_cash_lot: '',
  id_exo_cash_famille_lot: '',
  marque: '',
  lib_lot: '',
  categorie: 0,
  montant: 0,
  stock: 0,
  sur_commande: false,
  en_solde: false,
  montant_solde: 0,
  solde_deb: '',
  solde_fin: '',
  is_actif: true,
  description: '',
  has_photo1: false,
  has_photo2: false,
  has_photo3: false,
}

// Petite palette d'emojis pour la description (cf. WinDev Smiley).
const _EMOJIS = [
  '😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '😉',
  '😍', '🥰', '😘', '😎', '🤩', '🥳', '🤔', '🙄', '😅', '😢',
  '😭', '😡', '👍', '👎', '👏', '🙏', '💪', '👌', '✌️', '🤝',
  '❤️', '💔', '💯', '🔥', '⭐', '🎉', '🎁', '🎊', '💎', '💰',
  '📱', '💻', '🖥️', '⌚', '🎮', '🎧', '📷', '📺', '🚗', '✈️',
]

const _CATEGORIES = [
  { v: 0, label: 'Non spécifiée' },
  { v: 1, label: 'Homme' },
  { v: 2, label: 'Femme' },
  { v: 3, label: 'Mixte' },
  { v: 4, label: 'Enfant' },
]

const toDateInput = (iso: string): string =>
  iso && iso.length >= 10 ? iso.slice(0, 10) : ''

export default function FI_LotFicheModal({
  idLot,
  onClose,
}: {
  idLot: string | null // null = nouveau
  onClose: (reload?: boolean) => void
}) {
  const isNew = !idLot
  const [familles, setFamilles] = useState<Famille[]>([])
  const [form, setForm] = useState<LotDetail>(_EMPTY_LOT)
  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving] = useState(false)
  const [emojiOpen, setEmojiOpen] = useState(false)
  const [savedId, setSavedId] = useState<string>('') // id apres save
  const descRef = useRef<HTMLTextAreaElement>(null)

  // Refs pour les inputs photos
  const photoRefs: Array<React.RefObject<HTMLInputElement | null>> = [
    useRef<HTMLInputElement | null>(null),
    useRef<HTMLInputElement | null>(null),
    useRef<HTMLInputElement | null>(null),
  ]

  const _fetch = (u: string, opts: RequestInit = {}) =>
    fetch(u, {
      ...opts,
      headers: {
        Authorization: `Bearer ${getToken()}`,
        ...(opts.headers || {}),
      },
    })

  // Charge familles + detail (si edition)
  useEffect(() => {
    let cancelled = false
    void (async () => {
      const [fr, dr] = await Promise.all([
        _fetch(`${API_BASE}/gestion-exo-cash/familles`).then((r) => r.json()),
        idLot
          ? _fetch(`${API_BASE}/gestion-exo-cash/lots/${idLot}`).then((r) =>
              r.json(),
            )
          : Promise.resolve(null),
      ])
      if (cancelled) return
      setFamilles(fr.items || [])
      if (dr && !dr.detail) {
        setForm({ ..._EMPTY_LOT, ...dr })
        setSavedId(dr.id_exo_cash_lot)
      }
      setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [idLot])

  const set = <K extends keyof LotDetail>(k: K, v: LotDetail[K]) =>
    setForm((f) => ({ ...f, [k]: v }))

  const handleSave = async () => {
    if (!form.id_exo_cash_famille_lot) {
      showToast('Sélectionne une famille', 'info')
      return
    }
    if (!form.lib_lot.trim()) {
      showToast('Saisi le nom du lot (LibLot)', 'info')
      return
    }
    setSaving(true)
    try {
      const r = await _fetch(`${API_BASE}/gestion-exo-cash/lots`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          id_exo_cash_lot: Number(form.id_exo_cash_lot || 0),
          id_exo_cash_famille_lot: Number(form.id_exo_cash_famille_lot),
        }),
      })
      const d = await r.json()
      if (d.ok) {
        showToast('Fiche enregistrée', 'success')
        setSavedId(d.id_exo_cash_lot)
        // Reste ouvert pour permettre l'upload des photos apres save
        setForm((f) => ({ ...f, id_exo_cash_lot: d.id_exo_cash_lot }))
      } else {
        showToast(d.error || 'Erreur', 'error')
      }
    } finally {
      setSaving(false)
    }
  }

  const insertEmoji = (e: string) => {
    const ta = descRef.current
    if (!ta) {
      set('description', form.description + e)
      return
    }
    const start = ta.selectionStart
    const end = ta.selectionEnd
    const next =
      form.description.slice(0, start) + e + form.description.slice(end)
    set('description', next)
    // Repositionne le curseur apres l'emoji
    requestAnimationFrame(() => {
      ta.focus()
      ta.setSelectionRange(start + e.length, start + e.length)
    })
    setEmojiOpen(false)
  }

  const onPhotoSelected = (num: 1 | 2 | 3) =>
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      e.target.value = ''
      if (!file || !savedId) {
        showToast('Enregistre d\'abord la fiche avant d\'ajouter des photos.', 'info')
        return
      }
      const fd = new FormData()
      fd.append('fichier', file)
      const r = await _fetch(
        `${API_BASE}/gestion-exo-cash/lots/${savedId}/photo/${num}`,
        { method: 'POST', body: fd },
      )
      const d = await r.json()
      if (d.ok) {
        showToast(`Photo ${num} chargée`, 'success')
        // Force reload de l'image (cache-bust)
        set(`has_photo${num}` as keyof LotDetail, true as never)
      } else {
        showToast(d.error || 'Erreur', 'error')
      }
    }

  const deletePhoto = async (num: 1 | 2 | 3) => {
    if (!savedId) return
    const ok = await showConfirm({
      title: 'Supprimer la photo',
      message: 'Vous êtes sur le point de supprimer cette photo. Voulez-vous continuer ?',
      variant: 'danger',
    })
    if (!ok) return
    const r = await _fetch(
      `${API_BASE}/gestion-exo-cash/lots/${savedId}/photo/${num}`,
      { method: 'DELETE' },
    )
    const d = await r.json()
    if (d.ok) {
      showToast(`Photo ${num} supprimée`, 'success')
      set(`has_photo${num}` as keyof LotDetail, false as never)
    } else {
      showToast(d.error || 'Erreur', 'error')
    }
  }

  const photoSrc = (num: 1 | 2 | 3): string | null => {
    if (!savedId) return null
    const has = form[`has_photo${num}` as keyof LotDetail]
    if (!has) return null
    // Cache-bust : reload apres upload/delete
    return `${API_BASE}/gestion-exo-cash/lots/${savedId}/photo/${num}?_=${Date.now()}`
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-[#F5F5F0] rounded-lg shadow-xl w-[95vw] max-w-[1000px] max-h-[95vh] overflow-y-auto">
        <div className="sticky top-0 bg-[#F5F5F0] border-b border-[#E5E0D5] px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[#8B7355]">
            Fiche Lot
          </h2>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500">
              IDExoCashLot :{' '}
              <span className="font-mono">
                {form.id_exo_cash_lot || '0'}
              </span>
            </span>
            <button
              onClick={() => onClose(true)}
              className="p-2 rounded hover:bg-white/50"
              title="Fermer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center p-16">
            <Loader2 className="w-8 h-8 animate-spin text-[#8B7355]" />
          </div>
        ) : (
          <div className="p-6 grid grid-cols-1 lg:grid-cols-[1fr_240px] gap-6">
            {/* Colonne principale */}
            <div className="space-y-4">
              {/* Famille + Categorie */}
              <div className="grid grid-cols-2 gap-3">
                <label className="flex flex-col text-sm gap-1">
                  <span className="text-[#8B7355] font-medium">Famille</span>
                  <select
                    value={form.id_exo_cash_famille_lot}
                    onChange={(e) => set('id_exo_cash_famille_lot', e.target.value)}
                    className="px-2 py-1.5 border border-[#E5E0D5] rounded bg-white"
                  >
                    <option value="">— Choisir —</option>
                    {familles.map((f) => (
                      <option
                        key={f.id_exo_cash_famille_lot}
                        value={f.id_exo_cash_famille_lot}
                      >
                        {f.lib_famille_lot}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col text-sm gap-1">
                  <span className="text-[#8B7355] font-medium">Catégorie</span>
                  <select
                    value={form.categorie}
                    onChange={(e) => set('categorie', Number(e.target.value))}
                    className="px-2 py-1.5 border border-[#E5E0D5] rounded bg-white"
                  >
                    {_CATEGORIES.map((c) => (
                      <option key={c.v} value={c.v}>{c.label}</option>
                    ))}
                  </select>
                </label>
              </div>

              {/* Marque + LibLot */}
              <label className="flex flex-col text-sm gap-1">
                <span className="text-[#8B7355] font-medium">Marque</span>
                <input
                  value={form.marque}
                  onChange={(e) => set('marque', e.target.value)}
                  maxLength={25}
                  className="px-2 py-1.5 border border-[#E5E0D5] rounded bg-white"
                />
              </label>
              <label className="flex flex-col text-sm gap-1">
                <span className="text-[#8B7355] font-medium">LibLot</span>
                <input
                  value={form.lib_lot}
                  onChange={(e) => set('lib_lot', e.target.value)}
                  maxLength={50}
                  className="px-2 py-1.5 border border-[#E5E0D5] rounded bg-white"
                />
              </label>

              {/* Montant + Stock + Sur Commande + Actif */}
              <div className="grid grid-cols-4 gap-3 items-end">
                <label className="flex flex-col text-sm gap-1">
                  <span className="text-[#8B7355] font-medium">Montant</span>
                  <input
                    type="number"
                    step="0.01"
                    value={form.montant}
                    onChange={(e) => set('montant', Number(e.target.value))}
                    className="px-2 py-1.5 border border-[#E5E0D5] rounded bg-white text-right tabular-nums"
                  />
                </label>
                <label className="flex flex-col text-sm gap-1">
                  <span className="text-[#8B7355] font-medium">Stock</span>
                  <input
                    type="number"
                    value={form.stock}
                    onChange={(e) => set('stock', Number(e.target.value))}
                    className="px-2 py-1.5 border border-[#E5E0D5] rounded bg-white text-right tabular-nums"
                  />
                </label>
                <label className="flex items-center gap-2 text-sm pt-6">
                  <input
                    type="checkbox"
                    checked={form.sur_commande}
                    onChange={(e) => set('sur_commande', e.target.checked)}
                    className="accent-[#8B7355]"
                  />
                  <span className="text-[#8B7355] font-medium">Sur Commande</span>
                </label>
                <label className="flex items-center gap-2 text-sm pt-6">
                  <input
                    type="checkbox"
                    checked={form.is_actif}
                    onChange={(e) => set('is_actif', e.target.checked)}
                    className="accent-[#8B7355]"
                  />
                  <span className="text-[#8B7355] font-medium">Actif</span>
                </label>
              </div>

              {/* Bloc En Solde */}
              <div className="border border-[#E5E0D5] rounded p-3 bg-white">
                <label className="flex items-center gap-2 text-sm mb-3">
                  <input
                    type="checkbox"
                    checked={form.en_solde}
                    onChange={(e) => set('en_solde', e.target.checked)}
                    className="accent-[#8B7355]"
                  />
                  <span className="text-[#8B7355] font-semibold">En Solde</span>
                </label>
                <div className="grid grid-cols-3 gap-3 items-end">
                  <label className="flex flex-col text-sm gap-1">
                    <span className="text-[#8B7355] font-medium">Montant Soldé</span>
                    <input
                      type="number"
                      step="0.01"
                      value={form.montant_solde}
                      onChange={(e) => set('montant_solde', Number(e.target.value))}
                      disabled={!form.en_solde}
                      className="px-2 py-1.5 border border-[#E5E0D5] rounded bg-white text-right tabular-nums disabled:opacity-40"
                    />
                  </label>
                  <label className="flex flex-col text-sm gap-1">
                    <span className="text-[#8B7355] font-medium">Solde du</span>
                    <input
                      type="date"
                      value={toDateInput(form.solde_deb)}
                      onChange={(e) => set('solde_deb', e.target.value)}
                      disabled={!form.en_solde}
                      className="px-2 py-1.5 border border-[#E5E0D5] rounded bg-white disabled:opacity-40"
                    />
                  </label>
                  <label className="flex flex-col text-sm gap-1">
                    <span className="text-[#8B7355] font-medium">au</span>
                    <input
                      type="date"
                      value={toDateInput(form.solde_fin)}
                      onChange={(e) => set('solde_fin', e.target.value)}
                      disabled={!form.en_solde}
                      className="px-2 py-1.5 border border-[#E5E0D5] rounded bg-white disabled:opacity-40"
                    />
                  </label>
                </div>
              </div>

              {/* Description + emoji picker */}
              <div className="relative">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-[#8B7355] font-medium">
                    Description
                  </span>
                  <button
                    type="button"
                    onClick={() => setEmojiOpen((o) => !o)}
                    className="p-1 rounded hover:bg-[#DEF7EC]"
                    title="Insérer un emoji"
                  >
                    <Smile className="w-5 h-5 text-[#059669]" />
                  </button>
                </div>
                <textarea
                  ref={descRef}
                  value={form.description}
                  onChange={(e) => set('description', e.target.value)}
                  rows={5}
                  className="w-full px-2 py-1.5 border border-[#E5E0D5] rounded bg-white text-sm resize-vertical"
                />
                {emojiOpen && (
                  <div className="absolute right-0 mt-1 bg-white border border-[#E5E0D5] rounded-lg shadow-lg p-2 z-10 w-64 grid grid-cols-10 gap-1">
                    {_EMOJIS.map((e) => (
                      <button
                        key={e}
                        type="button"
                        onClick={() => insertEmoji(e)}
                        className="text-lg hover:bg-[#ECF1F2] rounded p-0.5"
                      >
                        {e}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Btn Enregistrer */}
              <div className="flex justify-end">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 rounded bg-[#059669] text-white disabled:opacity-40 hover:bg-[#047857]"
                >
                  {saving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  Enregistrer la fiche lot
                </button>
              </div>
            </div>

            {/* Colonne photos */}
            <div className="space-y-4">
              {[1, 2, 3].map((num) => {
                const src = photoSrc(num as 1 | 2 | 3)
                const idx = num - 1
                return (
                  <div
                    key={num}
                    className="bg-white border border-[#E5E0D5] rounded p-2"
                  >
                    <div className="aspect-square bg-[#F5F5F0] rounded flex items-center justify-center overflow-hidden mb-2">
                      {src ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={src}
                          alt={`Photo ${num}`}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <ImageIcon className="w-10 h-10 text-gray-300" />
                      )}
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={() => photoRefs[idx].current?.click()}
                        disabled={!savedId}
                        className="flex-1 flex items-center justify-center gap-1 text-xs px-2 py-1 rounded bg-[#8B7355] text-white disabled:opacity-40 hover:bg-[#725e46]"
                      >
                        <Upload className="w-3 h-3" />
                        Photo {num}
                      </button>
                      <button
                        onClick={() => deletePhoto(num as 1 | 2 | 3)}
                        disabled={!savedId || !form[`has_photo${num}` as keyof LotDetail]}
                        className="p-1 rounded border border-red-300 text-red-500 disabled:opacity-40 hover:bg-red-50"
                        title="Supprimer la photo"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                    <input
                      ref={photoRefs[idx]}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={onPhotoSelected(num as 1 | 2 | 3)}
                    />
                  </div>
                )
              })}
              {!savedId && (
                <p className="text-xs text-gray-500 italic">
                  Enregistre d'abord la fiche pour ajouter des photos.
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
