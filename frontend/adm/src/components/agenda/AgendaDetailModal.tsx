/**
 * Modal Fen_AgendaDetail (transposition WinDev).
 *
 * Champs :
 *  - Titre, Recruteur, Statut, 4 checkboxes Pb (visibles si categorie 4 ou 7)
 *  - Motif
 *  - Session (combo : prevRecrut)
 *  - Date debut / Date fin
 *  - Type entretien (radio Physique / Visio) - toggle dynamique
 *    - Si Physique : combo Lieu + adresse affichee
 *    - Si Visio : combo Salon + Lien + ID + MDP
 *
 * Boutons : Choisir l'Operateur, Voir Fiche CV, Renvoyer SMS, Supprimer,
 * Enregistrer.
 */

import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ExternalLink,
  Loader2,
  Save,
  Send,
  Trash2,
  UserCog,
  X,
} from 'lucide-react'

import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'
import RecruteurPicker from '@/components/agenda/RecruteurPicker'

interface RdvDetail {
  id_agenda_evenement: string
  titre: string
  contenu: string
  date_debut: string
  date_fin: string
  id_categorie: number
  id_recruteur: string
  id_cv_suivi: string
  id_cvtheque: string
  id_cv_lieux: string
  id_salon_visio: string
  id_prevision_recrut: string
  type_entretien: 'Physique' | 'Visio'
  op_crea: string
  op_crea_lib: string
  motif_statut: string
  pb_presentation: boolean
  pb_elocution: boolean
  pb_motivation: boolean
  pb_horaires: boolean
}

interface StatutItem {
  id_categorie: number
  lib_categorie: string
}

interface RecruteurItem {
  id_salarie: string
  nom: string
  prenom: string
  nom_prenom?: string
}

interface Session {
  id_prevision_recrut: string
  date_session: string
  lib_lieu: string
}

interface Lieu {
  id_cv_lieu_rdv: string
  lib_lieu: string
  adresse1: string
  adresse2: string
}

interface Salon {
  id_salon_visio: string
  lib_salon: string
}

interface SalonDetail {
  id_salon_visio: string
  lien: string
  id_salon: string
  mdp: string
}

const COLOR_PRIMARY = '#17494E'
const COLOR_BRUN = '#4E1D17'
const COLOR_BG_SOFT = '#EFE9E7'
const COLOR_DANGER = '#993636'

// Categories qui affichent les 4 checkboxes Pb (cf. WinDev : 4 ou 7)
const PB_CATEGORIES = new Set([4, 7])

interface Props {
  idRdv: string
  onClose: () => void
  onSaved?: () => void
}

export default function AgendaDetailModal({ idRdv, onClose, onSaved }: Props) {
  const [detail, setDetail] = useState<RdvDetail | null>(null)
  const [statuts, setStatuts] = useState<StatutItem[]>([])
  const [recruteurs, setRecruteurs] = useState<RecruteurItem[]>([])
  const [sessions, setSessions] = useState<Session[]>([])
  const [lieux, setLieux] = useState<Lieu[]>([])
  const [salons, setSalons] = useState<Salon[]>([])
  const [salonDetail, setSalonDetail] = useState<SalonDetail | null>(null)
  const [lieuDetail, setLieuDetail] = useState<Lieu | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [opPickerOpen, setOpPickerOpen] = useState(false)

  // Charge le RDV + referentiels au montage
  useEffect(() => {
    if (!idRdv) return
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        // Cf. WinDev : combo Statut = TOUTE la table AgendaCategorie
        // (endpoint /categories), pas /statuts qui filtre id_cv_statut>6.
        const [rdvR, statutsR, sessionsR, lieuxR] = await Promise.all([
          fetch(`/api/adm/agenda-recrutement/rdv/${idRdv}/detail`, {
            headers: { Authorization: `Bearer ${getToken()}` },
          }),
          fetch('/api/adm/agenda-recrutement/categories', {
            headers: { Authorization: `Bearer ${getToken()}` },
          }),
          fetch('/api/adm/agenda-recrutement/sessions-en-cours', {
            headers: { Authorization: `Bearer ${getToken()}` },
          }),
          fetch('/api/adm/agenda-recrutement/lieux', {
            headers: { Authorization: `Bearer ${getToken()}` },
          }),
        ])
        if (cancelled) return
        if (!rdvR.ok) throw new Error(`RDV ${rdvR.status}`)
        const rdv = (await rdvR.json()) as RdvDetail
        setDetail(rdv)
        setStatuts(await statutsR.json())
        setSessions(await sessionsR.json())
        setLieux(await lieuxR.json())
      } catch (e) {
        showToast(`Échec chargement : ${(e as Error).message}`, 'error')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [idRdv])

  // Charge la combo Recruteur (cf. WinDev : salaries avec agenda_actif=TRUE)
  useEffect(() => {
    fetch('/api/adm/agenda-recrutement/recruteurs-agenda-actif', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => setRecruteurs(Array.isArray(d) ? d : []))
      .catch(() => {})
  }, [])

  // Charge les salons visio quand le recruteur change OU on bascule en Visio
  useEffect(() => {
    if (!detail) return
    if (detail.type_entretien !== 'Visio') return
    if (!detail.id_recruteur) {
      setSalons([])
      return
    }
    fetch(
      `/api/adm/agenda-recrutement/salons-visio?id_recruteur=${detail.id_recruteur}`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
      .then((r) => r.json())
      .then((d) => setSalons(Array.isArray(d) ? d : []))
      .catch(() => setSalons([]))
  }, [detail?.id_recruteur, detail?.type_entretien])

  // Charge le detail du salon (lien/id/mdp) quand id_salon_visio change
  useEffect(() => {
    if (!detail?.id_salon_visio) {
      setSalonDetail(null)
      return
    }
    fetch(
      `/api/adm/agenda-recrutement/salons-visio/${detail.id_salon_visio}`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
      .then((r) => (r.ok ? r.json() : null))
      .then(setSalonDetail)
      .catch(() => setSalonDetail(null))
  }, [detail?.id_salon_visio])

  // Charge le detail du lieu (adresse + CP/ville) quand id_cv_lieux change
  useEffect(() => {
    if (!detail?.id_cv_lieux || detail.id_cv_lieux === '1') {
      setLieuDetail(null)
      return
    }
    fetch(`/api/adm/agenda-recrutement/lieux/${detail.id_cv_lieux}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then(setLieuDetail)
      .catch(() => setLieuDetail(null))
  }, [detail?.id_cv_lieux])

  const update = useCallback((patch: Partial<RdvDetail>) => {
    setDetail((d) => (d ? { ...d, ...patch } : d))
  }, [])

  const handleSave = async () => {
    if (!detail) return
    setSaving(true)
    try {
      const r = await fetch(
        `/api/adm/agenda-recrutement/rdv/${idRdv}/detail`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({
            titre: detail.titre,
            contenu: detail.contenu,
            id_recruteur: parseInt(detail.id_recruteur, 10) || 0,
            id_categorie: detail.id_categorie,
            date_debut: detail.date_debut,
            date_fin: detail.date_fin,
            id_prevision_recrut: parseInt(detail.id_prevision_recrut, 10) || 0,
            type_entretien: detail.type_entretien,
            id_cv_lieux: parseInt(detail.id_cv_lieux, 10) || 0,
            id_salon_visio: parseInt(detail.id_salon_visio, 10) || 0,
            motif_statut: detail.motif_statut,
            pb_presentation: detail.pb_presentation,
            pb_elocution: detail.pb_elocution,
            pb_motivation: detail.pb_motivation,
            pb_horaires: detail.pb_horaires,
          }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast('RDV enregistré.', 'success')
      onSaved?.()
      onClose()
    } catch (e) {
      showToast(`Échec enregistrement : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    const ok = await showConfirm({
      title: 'Supprimer ce RDV ?',
      message: 'Cette action est irréversible. Voulez-vous continuer ?',
      confirmLabel: 'Supprimer',
      variant: 'danger',
    })
    if (!ok) return
    try {
      const r = await fetch(`/api/adm/agenda-recrutement/rdv/${idRdv}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      showToast('RDV supprimé.', 'success')
      onSaved?.()
      onClose()
    } catch (e) {
      showToast(`Échec suppression : ${(e as Error).message}`, 'error')
    }
  }

  const showPb = detail && PB_CATEGORIES.has(detail.id_categorie)

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white rounded-lg shadow-xl w-full max-w-4xl flex flex-col max-h-[90vh]"
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-4 py-3 border-b"
            style={{ borderColor: COLOR_BG_SOFT, backgroundColor: COLOR_BG_SOFT }}
          >
            <h3 className="text-base font-bold" style={{ color: COLOR_BRUN }}>
              Détail RDV
            </h3>
            <button
              type="button"
              onClick={onClose}
              className="p-1 hover:bg-white/40 rounded"
            >
              <X className="w-4 h-4" style={{ color: COLOR_BRUN }} />
            </button>
          </div>

          {loading || !detail ? (
            <div className="p-10 flex items-center justify-center">
              <Loader2 className="w-6 h-6 animate-spin" style={{ color: COLOR_PRIMARY }} />
            </div>
          ) : (
            <>
              {/* Toolbar : 5 boutons */}
              <div
                className="grid grid-cols-5 gap-2 px-4 py-2 border-b"
                style={{ borderColor: COLOR_BG_SOFT }}
              >
                <ToolbarBtn
                  icon={<UserCog className="w-4 h-4" />}
                  label={detail.op_crea_lib || "Choisir l'Opérateur"}
                  onClick={() => setOpPickerOpen(true)}
                />
                <ToolbarBtn
                  icon={<Trash2 className="w-4 h-4" />}
                  label="Supprimer le RDV"
                  onClick={() => void handleDelete()}
                  danger
                />
                <ToolbarBtn
                  icon={<ExternalLink className="w-4 h-4" />}
                  label="Voir Fiche CV"
                  onClick={() =>
                    showToast('Fiche CV : à venir.', 'info')
                  }
                  disabled={!detail.id_cv_suivi}
                />
                <ToolbarBtn
                  icon={<Send className="w-4 h-4" />}
                  label="Renvoyer le SMS"
                  onClick={() =>
                    showToast('Renvoi SMS : à implémenter.', 'info')
                  }
                  disabled={!detail.id_cv_suivi}
                />
                <ToolbarBtn
                  icon={saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  label="Enregistrer"
                  onClick={() => void handleSave()}
                  primary
                  disabled={saving}
                />
              </div>

              {/* Body : 2 colonnes (form gauche + contenu droite) */}
              <div className="flex-1 overflow-y-auto grid grid-cols-2 gap-4 p-4">
                {/* Colonne gauche : champs */}
                <div className="flex flex-col gap-3">
                  <Field label="Titre">
                    <input
                      type="text"
                      value={detail.titre}
                      onChange={(e) => update({ titre: e.target.value })}
                      className="px-2 py-1 border rounded text-sm"
                      style={{ borderColor: COLOR_BG_SOFT }}
                    />
                  </Field>

                  <Field label="Recruteur">
                    <select
                      value={detail.id_recruteur}
                      onChange={(e) => update({ id_recruteur: e.target.value })}
                      className="px-2 py-1 border rounded text-sm bg-white"
                      style={{ borderColor: COLOR_BG_SOFT }}
                    >
                      <option value="">—</option>
                      {recruteurs.map((r) => (
                        <option key={r.id_salarie} value={r.id_salarie}>
                          {r.nom_prenom || `${r.nom} ${r.prenom}`}
                        </option>
                      ))}
                    </select>
                  </Field>

                  <Field label="Statut">
                    <select
                      value={detail.id_categorie}
                      onChange={(e) =>
                        update({ id_categorie: parseInt(e.target.value, 10) || 0 })
                      }
                      className="px-2 py-1 border rounded text-sm bg-white"
                      style={{ borderColor: COLOR_BG_SOFT }}
                    >
                      <option value={0}>—</option>
                      {statuts.map((s) => (
                        <option key={s.id_categorie} value={s.id_categorie}>
                          {s.lib_categorie}
                        </option>
                      ))}
                    </select>
                  </Field>

                  {/* 4 checkboxes Pb : visibles uniquement si categorie 4 ou 7 */}
                  {showPb && (
                    <div
                      className="grid grid-cols-2 gap-2 p-2 border rounded"
                      style={{ borderColor: COLOR_BG_SOFT, backgroundColor: '#FBF6F4' }}
                    >
                      <PbCheckbox
                        label="Pb Présentation"
                        checked={detail.pb_presentation}
                        onChange={(v) => update({ pb_presentation: v })}
                      />
                      <PbCheckbox
                        label="Pb Motivation"
                        checked={detail.pb_motivation}
                        onChange={(v) => update({ pb_motivation: v })}
                      />
                      <PbCheckbox
                        label="Pb Elocution"
                        checked={detail.pb_elocution}
                        onChange={(v) => update({ pb_elocution: v })}
                      />
                      <PbCheckbox
                        label="Pb Horaires"
                        checked={detail.pb_horaires}
                        onChange={(v) => update({ pb_horaires: v })}
                      />
                    </div>
                  )}

                  <Field label="Motif">
                    <input
                      type="text"
                      value={detail.motif_statut}
                      onChange={(e) => update({ motif_statut: e.target.value })}
                      className="px-2 py-1 border rounded text-sm"
                      style={{ borderColor: COLOR_BG_SOFT }}
                    />
                  </Field>

                  <Field label="Session">
                    <select
                      value={detail.id_prevision_recrut}
                      onChange={(e) => update({ id_prevision_recrut: e.target.value })}
                      className="px-2 py-1 border rounded text-sm bg-white"
                      style={{ borderColor: COLOR_BG_SOFT }}
                    >
                      <option value="">—</option>
                      {sessions.map((s) => (
                        <option key={s.id_prevision_recrut} value={s.id_prevision_recrut}>
                          {s.date_session} - {s.lib_lieu}
                        </option>
                      ))}
                    </select>
                  </Field>

                  <div className="grid grid-cols-2 gap-2">
                    <Field label="Date début">
                      <input
                        type="datetime-local"
                        value={detail.date_debut.slice(0, 16)}
                        onChange={(e) => update({ date_debut: e.target.value })}
                        className="px-2 py-1 border rounded text-sm"
                        style={{ borderColor: COLOR_BG_SOFT }}
                      />
                    </Field>
                    <Field label="Date fin">
                      <input
                        type="datetime-local"
                        value={detail.date_fin.slice(0, 16)}
                        onChange={(e) => update({ date_fin: e.target.value })}
                        className="px-2 py-1 border rounded text-sm"
                        style={{ borderColor: COLOR_BG_SOFT }}
                      />
                    </Field>
                  </div>

                  {/* Toggle Physique / Visio */}
                  <div
                    className="flex items-center gap-4 p-2 border rounded"
                    style={{ borderColor: COLOR_BG_SOFT }}
                  >
                    <label className="flex items-center gap-1.5 cursor-pointer text-sm" style={{ color: COLOR_BRUN }}>
                      <input
                        type="radio"
                        checked={detail.type_entretien === 'Physique'}
                        onChange={() => update({ type_entretien: 'Physique', id_salon_visio: '' })}
                      />
                      RDV physique
                    </label>
                    <label className="flex items-center gap-1.5 cursor-pointer text-sm" style={{ color: COLOR_BRUN }}>
                      <input
                        type="radio"
                        checked={detail.type_entretien === 'Visio'}
                        onChange={() => update({ type_entretien: 'Visio', id_cv_lieux: '1' })}
                      />
                      Visio
                    </label>
                  </div>

                  {/* Gr_Visio : visible si Visio */}
                  {detail.type_entretien === 'Visio' && (
                    <div
                      className="flex flex-col gap-2 p-3 border rounded"
                      style={{ borderColor: COLOR_BG_SOFT, backgroundColor: '#FBF6F4' }}
                    >
                      <Field label="Visio">
                        <select
                          value={detail.id_salon_visio}
                          onChange={(e) => update({ id_salon_visio: e.target.value })}
                          className="px-2 py-1 border rounded text-sm bg-white"
                          style={{ borderColor: COLOR_BG_SOFT }}
                        >
                          <option value="">—</option>
                          {salons.map((s) => (
                            <option key={s.id_salon_visio} value={s.id_salon_visio}>
                              {s.lib_salon}
                            </option>
                          ))}
                        </select>
                      </Field>
                      {salonDetail && (
                        <>
                          <Field label="Lien">
                            <div className="px-2 py-1 text-sm truncate" style={{ color: COLOR_BRUN }}>
                              {salonDetail.lien || '—'}
                            </div>
                          </Field>
                          <Field label="ID">
                            <div className="px-2 py-1 text-sm truncate" style={{ color: COLOR_BRUN }}>
                              {salonDetail.id_salon || '—'}
                            </div>
                          </Field>
                          <Field label="MDP">
                            <div className="px-2 py-1 text-sm truncate" style={{ color: COLOR_BRUN }}>
                              {salonDetail.mdp || '—'}
                            </div>
                          </Field>
                        </>
                      )}
                    </div>
                  )}

                  {/* Gr_LieuRDV : visible si Physique */}
                  {detail.type_entretien === 'Physique' && (
                    <div
                      className="flex flex-col gap-2 p-3 border rounded"
                      style={{ borderColor: COLOR_BG_SOFT, backgroundColor: '#FBF6F4' }}
                    >
                      <Field label="Lieu">
                        <select
                          value={detail.id_cv_lieux}
                          onChange={(e) => update({ id_cv_lieux: e.target.value })}
                          className="px-2 py-1 border rounded text-sm bg-white"
                          style={{ borderColor: COLOR_BG_SOFT }}
                        >
                          <option value="">—</option>
                          {lieux
                            .filter((l) => l.id_cv_lieu_rdv !== '1')
                            .map((l) => (
                              <option key={l.id_cv_lieu_rdv} value={l.id_cv_lieu_rdv}>
                                {l.lib_lieu}
                              </option>
                            ))}
                        </select>
                      </Field>
                      {lieuDetail && (
                        <div className="text-xs space-y-0.5" style={{ color: COLOR_BRUN }}>
                          <div>{lieuDetail.adresse1}</div>
                          {lieuDetail.adresse2 && <div>{lieuDetail.adresse2}</div>}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Colonne droite : Contenu (gros textarea) */}
                <div className="flex flex-col">
                  <label className="text-xs mb-1" style={{ color: COLOR_BRUN }}>
                    Contenu
                  </label>
                  <textarea
                    value={detail.contenu}
                    onChange={(e) => update({ contenu: e.target.value })}
                    className="flex-1 p-2 border rounded text-sm resize-none"
                    style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN, minHeight: '400px' }}
                  />
                </div>
              </div>
            </>
          )}
        </motion.div>

        {/* Picker pour le bouton 'Choisir l'Operateur' */}
        {opPickerOpen && (
          <RecruteurPicker
            title="Choisir l'opérateur"
            onClose={() => setOpPickerOpen(false)}
            onSelect={async (r) => {
              setOpPickerOpen(false)
              try {
                const resp = await fetch(
                  `/api/adm/agenda-recrutement/rdv/${idRdv}/op-crea`,
                  {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      Authorization: `Bearer ${getToken()}`,
                    },
                    body: JSON.stringify({ new_op: parseInt(r.id_salarie, 10) }),
                  },
                )
                if (!resp.ok) {
                  const j = await resp.json().catch(() => ({}))
                  throw new Error(
                    (j as { detail?: string })?.detail || String(resp.status),
                  )
                }
                const j = (await resp.json()) as { op_crea_lib: string }
                update({
                  op_crea: r.id_salarie,
                  op_crea_lib: j.op_crea_lib,
                })
                showToast('Opérateur modifié.', 'success')
              } catch (e) {
                showToast(`Échec : ${(e as Error).message}`, 'error')
              }
            }}
          />
        )}
      </motion.div>
    </AnimatePresence>
  )
}

function ToolbarBtn({
  icon,
  label,
  onClick,
  disabled,
  primary,
  danger,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
  disabled?: boolean
  primary?: boolean
  danger?: boolean
}) {
  const color = primary || danger ? 'white' : COLOR_PRIMARY
  const bg = primary ? COLOR_PRIMARY : danger ? COLOR_DANGER : 'white'
  const border = primary ? COLOR_PRIMARY : danger ? COLOR_DANGER : COLOR_PRIMARY
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center justify-center gap-1.5 px-2 py-1.5 text-xs rounded border disabled:opacity-40 truncate"
      style={{ backgroundColor: bg, color, borderColor: border }}
      title={label}
    >
      {icon}
      <span className="truncate">{label}</span>
    </button>
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
    <div className="flex flex-col gap-0.5">
      <label className="text-xs" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
        {label}
      </label>
      {children}
    </div>
  )
}

function PbCheckbox({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex items-center gap-1.5 cursor-pointer text-xs" style={{ color: COLOR_BRUN }}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="w-3.5 h-3.5"
      />
      {label}
    </label>
  )
}
