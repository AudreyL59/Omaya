/**
 * Fen_FicheVehicule (transposition WinDev) - Ulease.
 *
 * Modal fullscreen avec menu sidebar gauche (5 plans) + contenu droite.
 * V1 : Plan 1 (Info Vehicule) fonctionnel + boutons header + delete.
 * Plans 2-5 placeholders en attente du code WinDev.
 */

import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Car as CarIcon,
  Download,
  ExternalLink,
  FileText,
  Gauge,
  Loader2,
  Plus,
  Printer,
  Save,
  Trash2,
  X,
} from 'lucide-react'

import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

type TabKey =
  | 'info'
  | 'conducteurs'
  | 'carnet'
  | 'pv'
  | 'accidents'

const MENU: { key: TabKey; label: string; coded: boolean }[] = [
  { key: 'info',        label: 'Info Véhicule',     coded: true },
  { key: 'conducteurs', label: 'Conducteurs',       coded: false },
  { key: 'carnet',      label: "Carnet d'entretien",coded: false },
  { key: 'pv',          label: 'PV / Amendes',      coded: false },
  { key: 'accidents',   label: 'Accidents',         coded: false },
]

interface VehiculeMeta {
  id_vehicule: string
  immat: string
  modele: string
  id_vehicule_marque: string
  marque_nom: string
  marque_logo: string
  id_vehicule_etat: number
  lib_etat: string
  etat_logo: string
  id_vehicule_type_capacite: string
  lib_type: string
  nb_place: number
  chevaux_fiscaux: number
  date_mise_circulation: string
  date_deb: string
  date_fin: string
  k_mdepart: number
  km_actuel: number
  km_mensuel: number
  forfait_km: number
  date_releve: string
  id_ste_proprio: string
  ste_proprio_lib: string
  id_ste_reseau: string
  ste_reseau_lib: string
  carte_grise: boolean
  lien_carte_grise: string
  achat_loc: string
  info_vehicule: string
}

interface Lookups {
  marques: { id_vehicule_marque: string; nom: string }[]
  etats: { id_vehicule_etat: number; lib_etat: string }[]
  types_capacite: {
    id_vehicule_type_capacite: string
    lib_type: string
    nb_place: number
  }[]
  societes: { id_ste: string; lib: string }[]
  types_possession: { value: string; label: string }[]
}

interface Props {
  idVehicule: string
  onClose: () => void
  onChanged?: () => void  // appele apres save/delete pour reloader TDB
}

export default function FicheVehiculeModal({
  idVehicule,
  onClose,
  onChanged,
}: Props) {
  const [meta, setMeta] = useState<VehiculeMeta | null>(null)
  const [lookups, setLookups] = useState<Lookups | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [tab, setTab] = useState<TabKey>('info')

  const update = (patch: Partial<VehiculeMeta>) =>
    setMeta((m) => (m ? { ...m, ...patch } : m))

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const [vR, lkR] = await Promise.all([
          fetch(`/api/adm/parc-auto/vehicules/${idVehicule}`, {
            headers: { Authorization: `Bearer ${getToken()}` },
          }),
          fetch(`/api/adm/parc-auto/lookups`, {
            headers: { Authorization: `Bearer ${getToken()}` },
          }),
        ])
        if (cancelled) return
        if (!vR.ok) throw new Error(`Véhicule ${vR.status}`)
        setMeta((await vR.json()) as VehiculeMeta)
        setLookups((await lkR.json()) as Lookups)
      } catch (e) {
        showToast(`Échec chargement : ${(e as Error).message}`, 'error')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [idVehicule])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const handleSave = async () => {
    if (!meta) return
    setSaving(true)
    try {
      const r = await fetch(
        `/api/adm/parc-auto/vehicules/${idVehicule}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({
            id_vehicule_marque: Number(meta.id_vehicule_marque) || 0,
            modele: meta.modele,
            immat: meta.immat,
            chevaux_fiscaux: meta.chevaux_fiscaux,
            date_mise_circulation: meta.date_mise_circulation,
            id_vehicule_type_capacite: Number(meta.id_vehicule_type_capacite) || 0,
            date_deb: meta.date_deb,
            date_fin: meta.date_fin,
            id_ste_proprio: Number(meta.id_ste_proprio) || 0,
            id_ste_reseau: Number(meta.id_ste_reseau) || 0,
            achat_loc: meta.achat_loc,
            id_vehicule_etat: meta.id_vehicule_etat,
            forfait_km: meta.forfait_km,
            k_mdepart: meta.k_mdepart,
            km_actuel: meta.km_actuel,
            km_mensuel: meta.km_mensuel,
            date_releve: meta.date_releve,
            info_vehicule: meta.info_vehicule,
          }),
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast('Fiche véhicule enregistrée.', 'success')
      onChanged?.()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    const ok = await showConfirm({
      title: 'Supprimer la fiche véhicule ?',
      message: `« ${meta?.immat || idVehicule} » sera supprimé.`,
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    setSaving(true)
    try {
      const r = await fetch(
        `/api/adm/parc-auto/vehicules/${idVehicule}`,
        {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast('Fiche véhicule supprimée.', 'success')
      onChanged?.()
      onClose()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const titleLabel = meta
    ? `${meta.marque_nom} ${meta.modele} — ${meta.immat}`.trim()
    : 'Fiche véhicule'

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.96, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.96, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-lg shadow-2xl w-full max-w-7xl h-[92vh] overflow-hidden flex flex-col font-normal"
      >
        {/* Titre */}
        <div
          className="flex items-center gap-2 px-4 py-2 border-b"
          style={{ borderColor: COL_BORDER }}
        >
          <CarIcon className="w-4 h-4" style={{ color: COL_PRIMARY }} />
          <span
            className="text-sm font-semibold"
            style={{ color: COL_BRUN }}
          >
            {titleLabel}
          </span>
          <div className="flex-1" />
          <button
            onClick={onClose}
            className="ml-3 p-1 text-gray-500 hover:text-gray-800 hover:bg-[#ECF1F2] rounded"
            title="Fermer (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Barre d'actions */}
        <ActionBar
          meta={meta}
          onDelete={handleDelete}
          saving={saving}
        />

        {loading || !meta || !lookups ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-5 h-5 animate-spin text-[#A68D8A]" />
          </div>
        ) : (
          <div className="flex-1 flex overflow-hidden">
            {/* Sidebar menu */}
            <aside
              className="w-56 shrink-0 overflow-y-auto py-2"
              style={{ backgroundColor: COL_BG_SOFT, borderRight: `1px solid ${COL_BORDER}` }}
            >
              {MENU.map((m) => {
                const active = tab === m.key
                return (
                  <button
                    key={m.key}
                    type="button"
                    onClick={() => setTab(m.key)}
                    title={m.coded ? '' : 'À venir'}
                    className="w-full flex items-center justify-between gap-2 px-4 py-2 text-sm text-left transition-colors"
                    style={{
                      backgroundColor: active ? 'white' : 'transparent',
                      color: m.coded ? COL_BRUN : '#A68D8A',
                      fontWeight: active ? 600 : 400,
                      borderLeft: active
                        ? `3px solid ${COL_PRIMARY}`
                        : '3px solid transparent',
                      fontStyle: m.coded ? 'normal' : 'italic',
                    }}
                  >
                    <span>{m.label}</span>
                    {active && <span style={{ color: COL_PRIMARY }}>▸</span>}
                  </button>
                )
              })}
            </aside>

            {/* Contenu */}
            <div className="flex-1 overflow-y-auto p-6">
              {tab === 'info' && (
                <>
                  <InfoVehiculeTab
                    meta={meta}
                    update={update}
                    lookups={lookups}
                    onSave={handleSave}
                    saving={saving}
                  />
                  <div className="mt-6">
                    <DocumentsSection
                      idVehicule={idVehicule}
                      meta={meta}
                      onCarteGriseChange={(name) =>
                        update({ carte_grise: true, lien_carte_grise: name })
                      }
                    />
                  </div>
                </>
              )}
              {tab !== 'info' && (
                <div
                  className="text-sm italic p-10 text-center"
                  style={{ color: COL_BRUN }}
                >
                  Plan « {MENU.find((m) => m.key === tab)?.label} » :
                  module à venir.
                </div>
              )}
            </div>
          </div>
        )}
      </motion.div>
    </motion.div>
  )
}

// ============================================================================
// Barre d'actions (header)
// ============================================================================

function ActionBar({
  meta,
  onDelete,
  saving,
}: {
  meta: VehiculeMeta | null
  onDelete: () => void
  saving: boolean
}) {
  const lienCG = meta?.carte_grise && meta?.lien_carte_grise
  return (
    <div
      className="flex items-center gap-2 px-4 py-2 border-b"
      style={{ borderColor: COL_BORDER, backgroundColor: 'white' }}
    >
      <button
        type="button"
        onClick={onDelete}
        disabled={saving}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm border disabled:opacity-50"
        style={{ borderColor: '#B91C1C', color: '#B91C1C' }}
      >
        <Trash2 className="w-4 h-4" />
        Supprimer la fiche
      </button>
      <button
        type="button"
        onClick={() =>
          showToast('Impression fiche véhicule : à venir.', 'info')
        }
        className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm border"
        style={{ borderColor: COL_BORDER, color: COL_BRUN }}
      >
        <Printer className="w-4 h-4" />
        Imprimer fiche
      </button>
      {lienCG && (
        <button
          type="button"
          onClick={() =>
            showToast('Voir la carte grise : à venir.', 'info')
          }
          className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm border"
          style={{ borderColor: COL_BORDER, color: COL_BRUN }}
        >
          <ExternalLink className="w-4 h-4" />
          Voir la Carte grise
        </button>
      )}
      <button
        type="button"
        onClick={() =>
          showToast('Ajouter relevé kilométrique : à venir.', 'info')
        }
        className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm border"
        style={{ borderColor: COL_BORDER, color: COL_BRUN }}
      >
        <Gauge className="w-4 h-4" />
        KM
      </button>
    </div>
  )
}

// ============================================================================
// Plan 1 - Info Véhicule
// ============================================================================

function InfoVehiculeTab({
  meta,
  update,
  lookups,
  onSave,
  saving,
}: {
  meta: VehiculeMeta
  update: (patch: Partial<VehiculeMeta>) => void
  lookups: Lookups
  onSave: () => void
  saving: boolean
}) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-6">
        {/* Infos générales */}
        <Section title="Infos Générales">
          <Field label="Marque">
            <select
              value={meta.id_vehicule_marque}
              onChange={(e) => update({ id_vehicule_marque: e.target.value })}
              className={inputCls}
            >
              <option value="0">—</option>
              {lookups.marques.map((m) => (
                <option key={m.id_vehicule_marque} value={m.id_vehicule_marque}>
                  {m.nom}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Modèle">
            <input
              type="text"
              value={meta.modele}
              onChange={(e) => update({ modele: e.target.value })}
              className={inputCls}
            />
          </Field>
          <Field label="Immatriculation">
            <input
              type="text"
              value={meta.immat}
              onChange={(e) =>
                update({ immat: e.target.value.toUpperCase() })
              }
              className={inputCls}
            />
          </Field>
          <Field label="Nb de chevaux fiscaux">
            <input
              type="number"
              value={meta.chevaux_fiscaux || ''}
              onChange={(e) =>
                update({ chevaux_fiscaux: Number(e.target.value) || 0 })
              }
              className={inputCls}
            />
          </Field>
          <Field label="Mise en circulation le">
            <input
              type="date"
              value={meta.date_mise_circulation}
              onChange={(e) =>
                update({ date_mise_circulation: e.target.value })
              }
              className={inputCls}
            />
            <p className="text-xs italic mt-0.5" style={{ color: '#A68D8A' }}>
              * pour vérifier le CT
            </p>
          </Field>
          <Field label="Capacité">
            <select
              value={meta.id_vehicule_type_capacite}
              onChange={(e) =>
                update({ id_vehicule_type_capacite: e.target.value })
              }
              className={inputCls}
            >
              <option value="0">—</option>
              {lookups.types_capacite.map((t) => (
                <option
                  key={t.id_vehicule_type_capacite}
                  value={t.id_vehicule_type_capacite}
                >
                  {t.lib_type} — {t.nb_place} pl
                </option>
              ))}
            </select>
          </Field>
        </Section>

        {/* Données commerciales */}
        <Section title="Données Commerciales">
          <Field label="Type">
            <select
              value={meta.achat_loc}
              onChange={(e) => update({ achat_loc: e.target.value })}
              className={inputCls}
            >
              <option value="">—</option>
              {lookups.types_possession.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Date d'achat / Location">
            <input
              type="date"
              value={meta.date_deb}
              onChange={(e) => update({ date_deb: e.target.value })}
              className={inputCls}
            />
          </Field>
          <Field label="Jusqu'au">
            <input
              type="date"
              value={meta.date_fin}
              onChange={(e) => update({ date_fin: e.target.value })}
              className={inputCls}
            />
          </Field>
          <Field label="Propriétaire">
            <select
              value={meta.id_ste_proprio}
              onChange={(e) => update({ id_ste_proprio: e.target.value })}
              className={inputCls}
            >
              <option value="0">—</option>
              {lookups.societes.map((s) => (
                <option key={s.id_ste} value={s.id_ste}>
                  {s.lib}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Réseau">
            <select
              value={meta.id_ste_reseau}
              onChange={(e) => update({ id_ste_reseau: e.target.value })}
              className={inputCls}
            >
              <option value="0">—</option>
              {lookups.societes.map((s) => (
                <option key={s.id_ste} value={s.id_ste}>
                  {s.lib}
                </option>
              ))}
            </select>
          </Field>
          <Field label="État">
            <select
              value={meta.id_vehicule_etat || ''}
              onChange={(e) =>
                update({ id_vehicule_etat: Number(e.target.value) || 0 })
              }
              className={inputCls}
            >
              <option value="">—</option>
              {lookups.etats.map((s) => (
                <option key={s.id_vehicule_etat} value={s.id_vehicule_etat}>
                  {s.lib_etat}
                </option>
              ))}
            </select>
          </Field>
        </Section>

        {/* Infos kilométrages */}
        <Section title="Infos Kilométrages">
          <Field label="Kilométrage à l'achat">
            <input
              type="number"
              value={meta.k_mdepart || ''}
              onChange={(e) =>
                update({ k_mdepart: Number(e.target.value) || 0 })
              }
              className={inputCls}
            />
          </Field>
          <Field label="Forfait KM">
            <input
              type="number"
              value={meta.forfait_km || ''}
              onChange={(e) =>
                update({ forfait_km: Number(e.target.value) || 0 })
              }
              className={inputCls}
            />
          </Field>
          <Field label="Kilométrage actuel">
            <input
              type="number"
              value={meta.km_actuel || ''}
              onChange={(e) =>
                update({ km_actuel: Number(e.target.value) || 0 })
              }
              className={inputCls}
            />
          </Field>
          <Field label="Kilométrage par mois">
            <input
              type="number"
              value={meta.km_mensuel || ''}
              onChange={(e) =>
                update({ km_mensuel: Number(e.target.value) || 0 })
              }
              className={inputCls}
            />
          </Field>
          <Field label="Date de dernière Relève">
            <input
              type="date"
              value={meta.date_releve}
              onChange={(e) => update({ date_releve: e.target.value })}
              className={inputCls}
            />
          </Field>
          <div className="pt-2">
            <button
              type="button"
              onClick={onSave}
              disabled={saving}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-white text-sm font-medium disabled:opacity-50"
              style={{ backgroundColor: COL_PRIMARY }}
            >
              {saving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              Enregistrer
            </button>
          </div>
        </Section>
      </div>

      {/* Informations diverses */}
      <Section title="Informations Diverses">
        <textarea
          value={meta.info_vehicule}
          onChange={(e) => update({ info_vehicule: e.target.value })}
          rows={5}
          className="w-full p-2 border rounded text-sm resize-none"
          style={{ borderColor: COL_BORDER, color: COL_BRUN }}
          placeholder="Notes et informations diverses sur le véhicule..."
        />
      </Section>
    </div>
  )
}

// ============================================================================
// Documents du véhicule (FTP /OMAYA/Vehicules/{id}/)
// ============================================================================

interface VDoc {
  nom: string
  taille_mo: number
  date_iso: string
}

function DocumentsSection({
  idVehicule,
  meta,
  onCarteGriseChange,
}: {
  idVehicule: string
  meta: VehiculeMeta
  onCarteGriseChange: (name: string) => void
}) {
  const [files, setFiles] = useState<VDoc[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string>('')
  const [busy, setBusy] = useState(false)

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`/api/adm/parc-auto/vehicules/${idVehicule}/documents`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: { files?: VDoc[] }) => setFiles(d?.files || []))
      .catch(() => setFiles([]))
      .finally(() => setLoading(false))
  }, [idVehicule])

  useEffect(() => {
    reload()
  }, [reload])

  const handleUpload = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.onchange = async () => {
      const f = input.files?.[0]
      if (!f) return
      setBusy(true)
      try {
        const fd = new FormData()
        fd.append('file', f)
        const r = await fetch(
          `/api/adm/parc-auto/vehicules/${idVehicule}/documents`,
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
        showToast(`Fichier chargé : ${f.name}`, 'success')
        reload()
      } catch (e) {
        showToast(`Échec upload : ${(e as Error).message}`, 'error')
      } finally {
        setBusy(false)
      }
    }
    input.click()
  }

  const handleDownload = async () => {
    if (!selected) return
    const url = `/api/adm/parc-auto/vehicules/${idVehicule}/documents/download?name=${encodeURIComponent(selected)}`
    try {
      const r = await fetch(url, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const blob = await r.blob()
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = selected
      link.click()
      URL.revokeObjectURL(objectUrl)
    } catch (e) {
      showToast(`Échec téléchargement : ${(e as Error).message}`, 'error')
    }
  }

  const handleDelete = async () => {
    if (!selected) return
    const ok = await showConfirm({
      title: 'Supprimer ce document ?',
      message: `« ${selected} » sera supprimé.`,
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/parc-auto/vehicules/${idVehicule}/documents?name=${encodeURIComponent(selected)}`,
        {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast('Document supprimé.', 'success')
      setSelected('')
      reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleSetCarteGrise = async () => {
    if (!selected) return
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/parc-auto/vehicules/${idVehicule}/documents/carte-grise?name=${encodeURIComponent(selected)}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      onCarteGriseChange(selected)
      showToast('Défini comme Carte grise.', 'success')
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3 pb-1 border-b" style={{ borderColor: COL_BORDER }}>
        <h2
          className="text-xs font-bold uppercase tracking-wide"
          style={{ color: COL_BRUN }}
        >
          Documents du véhicule
        </h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSetCarteGrise}
            disabled={!selected || busy}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs border disabled:opacity-50"
            style={{ borderColor: COL_BORDER, color: COL_BRUN }}
          >
            <FileText className="w-3.5 h-3.5" />
            Définir comme Carte grise
          </button>
          <span className="flex-1" />
          <IconBtn onClick={handleUpload} title="Ajouter un document" disabled={busy}>
            <Plus className="w-4 h-4" />
          </IconBtn>
          <IconBtn onClick={handleDownload} title="Télécharger" disabled={!selected}>
            <Download className="w-4 h-4" />
          </IconBtn>
          <IconBtn onClick={handleDelete} title="Supprimer" disabled={!selected || busy} danger>
            <Trash2 className="w-4 h-4" />
          </IconBtn>
        </div>
      </div>

      <div
        className="border rounded overflow-hidden"
        style={{ borderColor: COL_BORDER }}
      >
        <table className="w-full text-sm">
          <thead style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
            <tr>
              <th className="px-3 py-2 text-left text-xs font-semibold uppercase">
                Nom Fichier
              </th>
              <th className="px-3 py-2 text-right text-xs font-semibold uppercase w-24">
                Taille (Mo)
              </th>
              <th className="px-3 py-2 text-left text-xs font-semibold uppercase w-28">
                Date
              </th>
              <th className="px-3 py-2 text-left text-xs font-semibold uppercase w-20">
                Heure
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={4} className="p-6 text-center">
                  <Loader2 className="w-4 h-4 animate-spin inline" />
                </td>
              </tr>
            ) : files.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="p-6 text-center italic"
                  style={{ color: '#A68D8A' }}
                >
                  Aucun document.
                </td>
              </tr>
            ) : (
              files.map((f) => {
                const isSel = selected === f.nom
                const isCG = meta.carte_grise && meta.lien_carte_grise === f.nom
                return (
                  <tr
                    key={f.nom}
                    onClick={() => setSelected(f.nom)}
                    onDoubleClick={handleDownload}
                    className="cursor-pointer border-b"
                    style={{
                      backgroundColor: isSel ? COL_PRIMARY : 'white',
                      color: isSel ? 'white' : COL_BRUN,
                      borderColor: COL_BORDER,
                    }}
                  >
                    <td className="px-3 py-1.5">
                      {isCG && '★ '}
                      {f.nom}
                    </td>
                    <td className="px-3 py-1.5 text-right">
                      {f.taille_mo.toFixed(2)}
                    </td>
                    <td className="px-3 py-1.5">
                      {f.date_iso.length >= 10
                        ? `${f.date_iso.slice(8, 10)}/${f.date_iso.slice(5, 7)}/${f.date_iso.slice(0, 4)}`
                        : ''}
                    </td>
                    <td className="px-3 py-1.5">
                      {f.date_iso.length >= 16 ? f.date_iso.slice(11, 16) : ''}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function IconBtn({
  onClick,
  title,
  disabled,
  danger,
  children,
}: {
  onClick: () => void
  title: string
  disabled?: boolean
  danger?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className="p-1.5 rounded border disabled:opacity-50"
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

// ============================================================================
// UI helpers
// ============================================================================

const inputCls =
  'w-full px-2 py-1.5 border rounded text-sm focus:outline-none focus:ring-1 focus:ring-[#17494E]'

function Section({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div>
      <h2
        className="text-xs font-bold uppercase tracking-wide mb-3 pb-1 border-b"
        style={{ color: COL_BRUN, borderColor: COL_BORDER }}
      >
        {title}
      </h2>
      <div className="space-y-2.5">{children}</div>
    </div>
  )
}

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div>
      <label className="block text-xs mb-0.5" style={{ color: COL_BRUN }}>
        {label}
      </label>
      {children}
    </div>
  )
}
