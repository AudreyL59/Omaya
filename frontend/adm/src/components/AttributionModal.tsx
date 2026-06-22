import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, Save, Search, UserPlus, X } from 'lucide-react'
import { showToast } from '@shared/ui/dialog'
import { getToken } from '@/api'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

type Mode = 'create' | 'edit'

interface Societe { id_ste: string; lib: string }

interface SalarieMatch {
  id_salarie: string
  nom_complet: string
  prenom: string
  lib: string
}

interface AttribForm {
  id_vehicule_pc: string
  id_vehicule: string
  id_conducteur: string
  id_ste: string
  perception_date: string
  perception_heure: string
  restitution_date: string
  restitution_heure: string
  k_mdepart: number
  k_mdepart_max: number
  temporaire: boolean
  conv_dispo: boolean
  cg_originale_dossier: boolean
  cg_conducteur: boolean
  fiche_rest: boolean
  c_vet_vignette: boolean
  permis_cnd: boolean
}

const emptyForm = (idVehicule: string): AttribForm => ({
  id_vehicule_pc: '0',
  id_vehicule: idVehicule,
  id_conducteur: '',
  id_ste: '',
  perception_date: '',
  perception_heure: '',
  restitution_date: '',
  restitution_heure: '',
  k_mdepart: 0,
  k_mdepart_max: 100,
  temporaire: false,
  conv_dispo: false,
  cg_originale_dossier: false,
  cg_conducteur: false,
  fiche_rest: false,
  c_vet_vignette: false,
  permis_cnd: false,
})

interface Props {
  open: boolean
  mode: Mode
  idVehicule: string
  idVehiculePc?: string
  societes: Societe[]
  onClose: () => void
  onSaved: () => void
}

export default function AttributionModal({
  open,
  mode,
  idVehicule,
  idVehiculePc,
  societes,
  onClose,
  onSaved,
}: Props) {
  const [form, setForm] = useState<AttribForm>(() => emptyForm(idVehicule))
  const [conducteurLib, setConducteurLib] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [pickerOpen, setPickerOpen] = useState(false)

  // Charge l'attribution en mode edit
  useEffect(() => {
    if (!open) return
    if (mode === 'create' || !idVehiculePc) {
      setForm(emptyForm(idVehicule))
      setConducteurLib('')
      return
    }
    setLoading(true)
    fetch(`/api/adm/parc-auto/conducteurs/${idVehiculePc}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return
        setForm({
          id_vehicule_pc: d.id_vehicule_pc,
          id_vehicule: d.id_vehicule,
          id_conducteur: d.id_conducteur,
          id_ste: d.id_ste,
          perception_date: d.perception_date || '',
          perception_heure: (d.perception_heure || '').slice(0, 5),
          restitution_date: d.restitution_date || '',
          restitution_heure: (d.restitution_heure || '').slice(0, 5),
          k_mdepart: d.k_mdepart || 0,
          k_mdepart_max: 100,
          temporaire: !!d.temporaire,
          conv_dispo: !!d.conv_dispo,
          cg_originale_dossier: !!d.cg_originale_dossier,
          cg_conducteur: !!d.cg_conducteur,
          fiche_rest: !!d.fiche_rest,
          c_vet_vignette: !!d.c_vet_vignette,
          permis_cnd: !!d.permis_cnd,
        })
        // Charge le lib du conducteur
        if (d.id_conducteur && d.id_conducteur !== '0') {
          fetch(`/api/adm/parc-auto/conducteurs/${idVehiculePc}`, {
            headers: { Authorization: `Bearer ${getToken()}` },
          })
            .then((r) => r.ok ? r.json() : null)
            .then(() => {
              // Le lib est servi par list_conducteurs, on n'a pas
              // d'endpoint dédié. On le récupère via le nom déjà connu.
            })
        }
      })
      .finally(() => setLoading(false))
  }, [open, mode, idVehiculePc, idVehicule])

  // En mode edit, on récupère le lib via /vehicules/{id}/conducteurs
  useEffect(() => {
    if (!open || mode !== 'edit' || !idVehiculePc) return
    fetch(`/api/adm/parc-auto/vehicules/${idVehicule}/conducteurs`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.ok ? r.json() : [])
      .then((list: Array<{ id_vehicule_pc: string; lib_conducteur: string }>) => {
        const row = list.find((x) => x.id_vehicule_pc === idVehiculePc)
        if (row) setConducteurLib(row.lib_conducteur)
      })
  }, [open, mode, idVehiculePc, idVehicule])

  const upd = <K extends keyof AttribForm>(k: K, v: AttribForm[K]) =>
    setForm((f) => ({ ...f, [k]: v }))

  const handleSave = async () => {
    if (!form.id_conducteur) {
      showToast('Choisissez un conducteur.', 'error')
      return
    }
    if (!form.id_ste) {
      showToast('Choisissez un réseau (société).', 'error')
      return
    }
    setSaving(true)
    try {
      const r = await fetch('/api/adm/parc-auto/conducteurs/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_vehicule_pc: form.id_vehicule_pc,
          id_vehicule: form.id_vehicule,
          id_conducteur: form.id_conducteur,
          id_ste: Number(form.id_ste) || 0,
          perception_date: form.perception_date,
          perception_heure: form.perception_heure,
          restitution_date: form.restitution_date,
          restitution_heure: form.restitution_heure,
          k_mdepart: form.k_mdepart,
          temporaire: form.temporaire,
          conv_dispo: form.conv_dispo,
          cg_originale_dossier: form.cg_originale_dossier,
          cg_conducteur: form.cg_conducteur,
          fiche_rest: form.fiche_rest,
          c_vet_vignette: form.c_vet_vignette,
          permis_cnd: form.permis_cnd,
        }),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast(
        mode === 'create' ? 'Attribution créée.' : 'Attribution modifiée.',
        'success',
      )
      onSaved()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const onConducteurPicked = async (s: SalarieMatch) => {
    setPickerOpen(false)
    try {
      const r = await fetch(
        `/api/adm/parc-auto/conducteurs/from-salarie/${s.id_salarie}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const d = await r.json()
      upd('id_conducteur', String(d.id_conducteur))
      setConducteurLib(String(d.lib))
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    }
  }

  const inputCls =
    'w-full px-2.5 py-1.5 rounded border bg-white text-sm focus:outline-none focus:ring-1'

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between px-5 py-3 border-b"
              style={{ borderColor: COL_BORDER, color: 'white', backgroundColor: COL_PRIMARY }}
            >
              <h2 className="text-base font-semibold flex items-center gap-2">
                <UserPlus className="w-5 h-5" />
                {mode === 'create' ? 'Nouvelle attribution' : 'Modifier l\'attribution'}
              </h2>
              <button onClick={onClose} className="text-white/80 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {loading ? (
              <div className="flex-1 flex items-center justify-center p-10">
                <Loader2 className="w-6 h-6 animate-spin" style={{ color: COL_PRIMARY }} />
              </div>
            ) : (
              <div className="flex-1 overflow-auto p-5 space-y-4">
                {/* Bloc haut : conducteur + réseau / dates */}
                <div className="grid grid-cols-[260px_1fr] gap-4">
                  <div className="space-y-3">
                    <button
                      type="button"
                      onClick={() => setPickerOpen(true)}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded border text-sm"
                      style={{ borderColor: COL_BORDER, color: COL_BRUN, backgroundColor: COL_BG_SOFT }}
                    >
                      <Search className="w-4 h-4" />
                      {conducteurLib || 'Choisir le conducteur'}
                    </button>

                    <select
                      value={form.id_ste}
                      onChange={(e) => upd('id_ste', e.target.value)}
                      className={inputCls}
                      style={{ borderColor: COL_BORDER }}
                    >
                      <option value="">Réseau</option>
                      {societes.map((s) => (
                        <option key={s.id_ste} value={s.id_ste}>
                          {s.lib}
                        </option>
                      ))}
                    </select>

                    <label className="flex items-center gap-2 text-sm" style={{ color: COL_BRUN }}>
                      <input
                        type="checkbox"
                        checked={form.temporaire}
                        onChange={(e) => upd('temporaire', e.target.checked)}
                      />
                      Perception Temporaire
                    </label>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <label className="text-sm w-28 whitespace-nowrap" style={{ color: COL_BRUN }}>
                        Perception le :
                      </label>
                      <input
                        type="date"
                        value={form.perception_date}
                        onChange={(e) => upd('perception_date', e.target.value)}
                        className={`${inputCls} flex-1`}
                        style={{ borderColor: COL_BORDER }}
                      />
                      <span className="text-sm" style={{ color: COL_BRUN }}>à :</span>
                      <input
                        type="time"
                        value={form.perception_heure}
                        onChange={(e) => upd('perception_heure', e.target.value)}
                        className={`${inputCls} w-24`}
                        style={{ borderColor: COL_BORDER }}
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="text-sm w-28 whitespace-nowrap" style={{ color: COL_BRUN }}>
                        Restitution le :
                      </label>
                      <input
                        type="date"
                        value={form.restitution_date}
                        onChange={(e) => upd('restitution_date', e.target.value)}
                        className={`${inputCls} flex-1`}
                        style={{ borderColor: COL_BORDER }}
                      />
                      <span className="text-sm" style={{ color: COL_BRUN }}>à :</span>
                      <input
                        type="time"
                        value={form.restitution_heure}
                        onChange={(e) => upd('restitution_heure', e.target.value)}
                        className={`${inputCls} w-24`}
                        style={{ borderColor: COL_BORDER }}
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="text-sm whitespace-nowrap" style={{ color: COL_BRUN }}>
                        Kilométrage à la perception :
                      </label>
                      <input
                        type="number"
                        value={form.k_mdepart || ''}
                        onChange={(e) => upd('k_mdepart', Number(e.target.value) || 0)}
                        placeholder="De 0 à 100"
                        className={`${inputCls} flex-1`}
                        style={{ borderColor: COL_BORDER }}
                      />
                    </div>
                  </div>
                </div>

                {/* Bloc pointage docs */}
                <div className="border rounded p-4" style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
                  <h3 className="text-sm font-bold uppercase mb-3" style={{ color: COL_BRUN }}>
                    Pointage des documents à remettre et à récupérer
                  </h3>
                  <div className="grid grid-cols-2 gap-y-2 gap-x-6 text-sm" style={{ color: COL_BRUN }}>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.conv_dispo}
                        onChange={(e) => upd('conv_dispo', e.target.checked)}
                      />
                      Convention de mise à dispo signée
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.cg_originale_dossier}
                        onChange={(e) => upd('cg_originale_dossier', e.target.checked)}
                      />
                      Carte Grise originale dossier
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.cg_conducteur}
                        onChange={(e) => upd('cg_conducteur', e.target.checked)}
                      />
                      Carte Grise photocopie Conducteur
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.fiche_rest}
                        onChange={(e) => upd('fiche_rest', e.target.checked)}
                      />
                      Fiche de Restitution
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.c_vet_vignette}
                        onChange={(e) => upd('c_vet_vignette', e.target.checked)}
                      />
                      Carte verte + vignette
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.permis_cnd}
                        onChange={(e) => upd('permis_cnd', e.target.checked)}
                      />
                      Permis du Conducteur
                    </label>
                  </div>
                </div>
              </div>
            )}

            {/* Footer */}
            <div
              className="flex justify-end gap-2 px-5 py-3 border-t"
              style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}
            >
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 rounded text-sm border"
                style={{ borderColor: COL_BORDER, color: COL_BRUN }}
              >
                Annuler
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm font-medium disabled:opacity-50"
                style={{ backgroundColor: COL_PRIMARY }}
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Valider
              </button>
            </div>
          </motion.div>

          {pickerOpen && (
            <SalariePicker
              onClose={() => setPickerOpen(false)}
              onPicked={onConducteurPicked}
            />
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}

// ============================================================================
// SalariePicker (Fen_RechercheNomSalarie)
// ============================================================================

function SalariePicker({
  onClose,
  onPicked,
}: {
  onClose: () => void
  onPicked: (s: SalarieMatch) => void
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
        .then((r) => (r.ok ? r.json() : []))
        .then((d) => setList(Array.isArray(d) ? d : []))
        .finally(() => setLoading(false))
    }, 200)
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current)
    }
  }, [q])

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[80vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="flex items-center justify-between px-4 py-2 border-b"
          style={{ borderColor: COL_BORDER, color: 'white', backgroundColor: COL_PRIMARY }}
        >
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Search className="w-4 h-4" />
            Rechercher un salarié
          </h3>
          <button onClick={onClose} className="text-white/80 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-3">
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Nom ou prénom..."
            autoFocus
            className="w-full px-3 py-2 rounded border text-sm"
            style={{ borderColor: COL_BORDER }}
          />
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
              <button
                key={s.id_salarie}
                type="button"
                onClick={() => onPicked(s)}
                className="w-full text-left px-3 py-2 hover:bg-gray-50 text-sm border-b"
                style={{ borderColor: COL_BORDER, color: COL_BRUN }}
              >
                {s.lib}
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
