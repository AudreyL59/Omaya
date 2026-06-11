/**
 * Popup 'Absence du salarié' (transposition Fen_SalarieAbsence WinDev).
 *
 * Champs : Type d'absence (combo) + Date début + Date fin.
 * Les metadonnees (Periode, NBJ, NBJ_OUVRES, nbSamedi) sont
 * recalculees cote backend a la sauvegarde et reaffichees en
 * lecture seule.
 */

import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { CalendarDays, Loader2, Save, X } from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'

interface TypeAbsence {
  id_type_absence: number
  lib_absence: string
}

interface AbsenceDetail {
  id_absence: string
  id_salarie: string
  id_type_absence: number
  date_debut: string
  date_fin: string
  nbj: number
  nbj_ouvres: number
  nb_samedi: number
  periode: string
}

interface Props {
  idSalarie: string
  idAbsence: string // '' = creation
  onClose: () => void
  onSaved: () => void
}

export default function SalarieAbsenceModal({
  idSalarie,
  idAbsence,
  onClose,
  onSaved,
}: Props) {
  const [types, setTypes] = useState<TypeAbsence[]>([])
  const [idType, setIdType] = useState<number>(0)
  const [dateDebut, setDateDebut] = useState('')
  const [dateFin, setDateFin] = useState('')
  const [meta, setMeta] = useState<{ periode: string; nbj: number; nbj_ouvres: number; nb_samedi: number } | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  // Charge la combo
  useEffect(() => {
    fetch('/api/adm/fiche-salarie/absences/types', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((j) => setTypes((j as { items: TypeAbsence[] }).items || []))
      .catch(() => {})
  }, [])

  // En modification : recupere l'absence
  useEffect(() => {
    if (!idAbsence) return
    setLoading(true)
    fetch(`/api/adm/fiche-salarie/absences/${idAbsence}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((j: AbsenceDetail) => {
        setIdType(j.id_type_absence)
        setDateDebut(j.date_debut || '')
        setDateFin(j.date_fin || '')
        setMeta({
          periode: j.periode,
          nbj: j.nbj,
          nbj_ouvres: j.nbj_ouvres,
          nb_samedi: j.nb_samedi,
        })
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [idAbsence])

  const handleSave = async () => {
    if (!idType) {
      showToast("Sélectionner un type d'absence.", 'error')
      return
    }
    if (!dateDebut) {
      showToast('Saisir une date de début.', 'error')
      return
    }
    setSaving(true)
    try {
      const url = idAbsence
        ? `/api/adm/fiche-salarie/absences/${idAbsence}`
        : `/api/adm/fiche-salarie/${idSalarie}/absences`
      const method = idAbsence ? 'PUT' : 'POST'
      const r = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_type_absence: idType,
          date_debut: dateDebut,
          date_fin: dateFin,
        }),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const j = (await r.json()) as { nbj: number; nbj_ouvres: number; nb_samedi: number; periode: string }
      setMeta({
        periode: j.periode,
        nbj: j.nbj,
        nbj_ouvres: j.nbj_ouvres,
        nb_samedi: j.nb_samedi,
      })
      showToast(
        `Enregistré (${j.nbj} jour(s), ${j.nbj_ouvres} ouvré(s), ${j.nb_samedi} samedi(s)).`,
        'success',
      )
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
          className="bg-white rounded-2xl shadow-2xl w-[680px] max-w-[95vw] max-h-[85vh] flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-5 py-3 border-b"
            style={{ borderColor: COLOR_BG_SOFT }}
          >
            <div className="flex items-center gap-2">
              <CalendarDays className="w-5 h-5" style={{ color: COLOR_PRIMARY }} />
              <h2 className="text-base font-semibold" style={{ color: COLOR_BRUN }}>
                {idAbsence ? 'Modifier une absence' : 'Nouvelle absence'}
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded hover:bg-[#EFE9E7]"
              style={{ color: COLOR_BRUN }}
              title="Fermer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4">
            {loading && (
              <div className="flex items-center gap-2 text-sm" style={{ color: COLOR_BRUN }}>
                <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
              </div>
            )}

            <Field label="Type d'absence">
              <select
                value={idType}
                onChange={(e) => setIdType(Number(e.target.value) || 0)}
                className="w-full px-2 py-1 border rounded text-sm"
                style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
              >
                <option value={0}>— (sélectionner) —</option>
                {types.map((t) => (
                  <option key={t.id_type_absence} value={t.id_type_absence}>
                    {t.lib_absence}
                  </option>
                ))}
              </select>
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Date de début">
                <input
                  type="date"
                  value={dateDebut}
                  onChange={(e) => setDateDebut(e.target.value)}
                  className="w-full px-2 py-1 border rounded text-sm"
                  style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
                />
              </Field>
              <Field label="Date de fin">
                <input
                  type="date"
                  value={dateFin}
                  onChange={(e) => setDateFin(e.target.value)}
                  className="w-full px-2 py-1 border rounded text-sm"
                  style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
                />
              </Field>
            </div>

            {/* Récap (lecture seule) */}
            {meta && (
              <div
                className="grid grid-cols-4 gap-3 p-3 rounded"
                style={{ backgroundColor: COLOR_BG_SOFT, color: COLOR_BRUN }}
              >
                <ReadOnly label="Période" value={meta.periode || '—'} />
                <ReadOnly label="Nb jours cal." value={String(meta.nbj)} />
                <ReadOnly label="Nb jours ouvrés (HS)" value={String(meta.nbj_ouvres)} />
                <ReadOnly label="Nb Samedi" value={String(meta.nb_samedi)} />
              </div>
            )}

            <p className="text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
              Convention Omaya : 30 jours de congés ; chaque vendredi posé
              décompte 1 samedi (max 5/an, à vérifier manuellement).
            </p>
          </div>

          {/* Footer */}
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
              disabled={saving || !idType || !dateDebut}
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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium" style={{ color: COLOR_BRUN }}>
        {label}
      </label>
      {children}
    </div>
  )
}

function ReadOnly({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider opacity-70">{label}</div>
      <div className="text-sm font-semibold">{value}</div>
    </div>
  )
}
