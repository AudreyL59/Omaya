/**
 * Fen_EntretienAjout (WinDev) - Planifier un RDV pour un candidat.
 *
 * Ouvre depuis Fen_CVFiche via le bouton 'Planifier un RDV'.
 * Au valid : INSERT cvsuivi statut=6 + INSERT agenda_evenement.
 * Si tout OK : ferme la fiche CV (parent fait onClose(true)).
 *
 * V_later : envoi SMS de confirmation + animation cooptation +
 * vue agenda du recruteur (commit ulterieur).
 */

import { useEffect, useMemo, useState } from 'react'
import {
  ArrowLeft, Check, Loader2, MapPin, Plus,
  Save, Video, X,
} from 'lucide-react'
import { getToken } from '@/api'
import { showConfirm, showToast } from '../ui/dialog'
import RecruteurAgenda from './RecruteurAgenda'
import SalonsSalarieModal from './SalonsSalarieModal'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface ComboItem { id: string; label: string }

interface SessionItem {
  id_prevision_recrut: string
  date_session: string
  nom_ville: string
  label: string
  id_recruteur: string
  id_cv_lieu_rdv: string
}

interface LieuRdvItem {
  id_cv_lieu_rdv: string
  lib_lieu: string
  adresse1: string
  adresse2: string
  code_postal: string
  nom_ville: string
  latitude_deg?: number | null
  longitude_deg?: number | null
}

interface SalonVisioItem {
  id_salon_visio: string
  lib_salon: string
  lien_salon: string
  id_salon: string
  mpd_salon: string
}

interface CandidatBasic {
  nom: string
  prenom: string
  gsm: string
  mail: string
}

interface EntretienAjoutModalProps {
  apiBase: string
  idCv: string
  candidat: CandidatBasic
  onClose: (rdvCreated: boolean) => void
}

export default function EntretienAjoutModal({
  apiBase, idCv, candidat, onClose,
}: EntretienAjoutModalProps) {
  const today = new Date()
  const [recruteurs, setRecruteurs] = useState<ComboItem[]>([])
  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [lieux, setLieux] = useState<LieuRdvItem[]>([])
  const [salonsVisio, setSalonsVisio] = useState<SalonVisioItem[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [idSession, setIdSession] = useState('')
  const [idRecruteur, setIdRecruteur] = useState('')
  const [date, setDate] = useState(today.toISOString().slice(0, 10))
  const [heure, setHeure] = useState(
    `${String(today.getHours()).padStart(2, '0')}:${String(today.getMinutes()).padStart(2, '0')}`,
  )
  const [typeEntretien, setTypeEntretien] = useState<'Physique' | 'Visio'>('Physique')
  const [idLieu, setIdLieu] = useState('')
  const [idSalon, setIdSalon] = useState('')
  const [sendSms, setSendSms] = useState(true)
  const [choixServeur, setChoixServeur] = useState<1 | 2>(1)
  const [gsm, setGsm] = useState(candidat.gsm)
  const [showSalons, setShowSalons] = useState(false)
  const [mail, setMail] = useState(candidat.mail)

  // Charge combos
  useEffect(() => {
    const h = { Authorization: `Bearer ${getToken()}` }
    Promise.all([
      fetch(`${apiBase}/recrutement/cv/entretien/recruteurs`, { headers: h }).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/entretien/sessions`, { headers: h }).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/entretien/lieux`, { headers: h }).then(r => r.json()),
    ])
      .then(([rec, sess, li]) => {
        setRecruteurs(rec); setSessions(sess); setLieux(li)
      })
      .finally(() => setLoading(false))
  }, [apiBase])

  // Recharge salons visio quand recruteur change
  useEffect(() => {
    if (!idRecruteur) { setSalonsVisio([]); return }
    fetch(`${apiBase}/recrutement/cv/entretien/salons-visio/${idRecruteur}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(setSalonsVisio)
  }, [apiBase, idRecruteur])

  // Quand session change : pre-remplir recruteur + lieu
  const handleSelectSession = (id: string) => {
    setIdSession(id)
    const s = sessions.find(x => x.id_prevision_recrut === id)
    if (s) {
      if (s.id_recruteur) setIdRecruteur(s.id_recruteur)
      if (s.date_session) setDate(s.date_session)
      if (s.id_cv_lieu_rdv === '1') {
        setTypeEntretien('Visio')
      } else if (s.id_cv_lieu_rdv) {
        setTypeEntretien('Physique')
        setIdLieu(s.id_cv_lieu_rdv)
      }
    }
  }

  const lieuSelectionne = useMemo(
    () => lieux.find(l => l.id_cv_lieu_rdv === idLieu),
    [lieux, idLieu],
  )
  const salonSelectionne = useMemo(
    () => salonsVisio.find(s => s.id_salon_visio === idSalon),
    [salonsVisio, idSalon],
  )

  const canValider = useMemo(() => {
    if (!idRecruteur || !date || !heure) return false
    if (typeEntretien === 'Physique' && !idLieu) return false
    if (typeEntretien === 'Visio' && !idSalon) return false
    return true
  }, [idRecruteur, date, heure, typeEntretien, idLieu, idSalon])

  const ouvrirMaps = () => {
    if (!lieuSelectionne?.latitude_deg || !lieuSelectionne?.longitude_deg) return
    const url = `https://www.google.com/maps/?q=${lieuSelectionne.latitude_deg},${lieuSelectionne.longitude_deg}`
    window.open(url, '_blank', 'noopener')
  }

  const updateCoords = async () => {
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/${idCv}/coordonnees`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ gsm, mail }),
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Coordonnées mises à jour.', 'success')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const valider = async () => {
    if (!canValider) return
    const recNom = recruteurs.find(r => r.id === idRecruteur)?.label || ''
    const ok = await showConfirm({
      title: 'Planifier ce RDV ?',
      message: `Le ${new Date(`${date}T${heure}`).toLocaleString('fr-FR')}\nAvec : ${recNom}`,
      confirmLabel: 'Planifier',
    })
    if (!ok) return
    setSaving(true)
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/${idCv}/rdv`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_recruteur: Number(idRecruteur),
          date_debut: `${date}T${heure}:00`,
          type_entretien: typeEntretien,
          id_cv_lieu_rdv: Number(idLieu) || 0,
          id_salon_visio: Number(idSalon) || 0,
          id_prevision_recrut: Number(idSession) || 0,
          send_sms: sendSms,
          choix_serveur: choixServeur,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json().catch(() => ({}))
      const smsRes = d?.sms?.statut
      const anim = d?.animation
      const messages: string[] = ['RDV planifié']
      if (sendSms && smsRes) messages.push(`SMS : ${smsRes}`)
      if (anim?.ok) {
        messages.push(
          `Animation coopt : +${anim.credit_livret} EC, ${anim.nb_sms_envoyes} SMS staff`,
        )
      }
      showToast(messages.join(' — '), 'success')
      onClose(true)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4"
         onClick={() => onClose(false)}>
      <div className="bg-white rounded-xl shadow-2xl max-w-5xl w-full max-h-[95vh] flex flex-col"
           onClick={e => e.stopPropagation()}
           style={{ border: `1px solid ${COL_BORDER}` }}>
        {/* HEADER */}
        <div className="px-4 py-3 border-b flex items-center gap-2"
             style={{ borderColor: COL_BORDER }}>
          <Plus className="w-5 h-5" style={{ color: COL_PRIMARY }} />
          <h2 className="text-lg font-bold flex-1" style={{ color: COL_BRUN }}>
            Nouveau RDV — {candidat.nom} {candidat.prenom}
          </h2>
          <button type="button" onClick={() => onClose(false)}
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
          <div className="w-[380px] shrink-0 overflow-y-auto p-4 space-y-3 border-r"
               style={{ borderColor: COL_BORDER }}>
            {/* Session */}
            <Row label="Session">
              <select value={idSession} onChange={e => handleSelectSession(e.target.value)}
                      className="w-full px-2 py-1.5 rounded border text-sm"
                      style={{ borderColor: COL_BORDER }}>
                <option value="">— Choisir une session (optionnel) —</option>
                {sessions.map(s => (
                  <option key={s.id_prevision_recrut} value={s.id_prevision_recrut}>
                    {s.label}
                  </option>
                ))}
              </select>
            </Row>

            {/* Recruteur */}
            <Row label="Recruteur">
              <select value={idRecruteur} onChange={e => setIdRecruteur(e.target.value)}
                      className="w-full px-2 py-1.5 rounded border text-sm"
                      style={{ borderColor: COL_BORDER }}>
                <option value="">— Choisir un recruteur —</option>
                {recruteurs.map(r => (
                  <option key={r.id} value={r.id}>{r.label}</option>
                ))}
              </select>
            </Row>

            {/* Date + Heure */}
            <Row label="Date / Heure">
              <div className="flex gap-2">
                <input type="date" value={date} onChange={e => setDate(e.target.value)}
                       className="flex-1 px-2 py-1.5 rounded border text-sm"
                       style={{ borderColor: COL_BORDER }} />
                <input type="time" value={heure} onChange={e => setHeure(e.target.value)}
                       className="w-32 px-2 py-1.5 rounded border text-sm"
                       style={{ borderColor: COL_BORDER }} />
              </div>
            </Row>

            {/* Type : Physique / Visio */}
            <Row label="Type">
              <div className="flex gap-2">
                <ToggleBtn active={typeEntretien === 'Physique'}
                           onClick={() => setTypeEntretien('Physique')}
                           icon={MapPin}>
                  RDV physique
                </ToggleBtn>
                <ToggleBtn active={typeEntretien === 'Visio'}
                           onClick={() => setTypeEntretien('Visio')}
                           icon={Video}>
                  Visio
                </ToggleBtn>
              </div>
            </Row>

            {/* Si Visio : salon + lien/ID/MDP */}
            {typeEntretien === 'Visio' && (
              <>
                <Row label="Visio">
                  <div className="flex gap-1">
                    <select value={idSalon} onChange={e => setIdSalon(e.target.value)}
                            className="flex-1 px-2 py-1.5 rounded border text-sm"
                            style={{ borderColor: COL_BORDER }}
                            disabled={!idRecruteur}>
                      <option value="">— Choisir un salon visio —</option>
                      {salonsVisio.map(s => (
                        <option key={s.id_salon_visio} value={s.id_salon_visio}>
                          {s.lib_salon}
                        </option>
                      ))}
                    </select>
                    <button type="button" onClick={() => setShowSalons(true)}
                            disabled={!idRecruteur}
                            title="Gérer les salons visio du recruteur"
                            className="px-2 rounded border disabled:opacity-40"
                            style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </Row>
                {salonSelectionne && (
                  <>
                    <Row label="Lien">
                      <input value={salonSelectionne.lien_salon} readOnly
                             className="w-full px-2 py-1.5 rounded border text-sm bg-gray-50"
                             style={{ borderColor: COL_BORDER }} />
                    </Row>
                    {salonSelectionne.id_salon && (
                      <Row label="ID">
                        <input value={salonSelectionne.id_salon} readOnly
                               className="w-full px-2 py-1.5 rounded border text-sm bg-gray-50"
                               style={{ borderColor: COL_BORDER }} />
                      </Row>
                    )}
                    {salonSelectionne.mpd_salon && (
                      <Row label="MDP">
                        <input value={salonSelectionne.mpd_salon} readOnly
                               className="w-full px-2 py-1.5 rounded border text-sm bg-gray-50"
                               style={{ borderColor: COL_BORDER }} />
                      </Row>
                    )}
                  </>
                )}
              </>
            )}

            {/* Si Physique : lieu + adresse + bouton Maps */}
            {typeEntretien === 'Physique' && (
              <>
                <Row label="Lieu">
                  <select value={idLieu} onChange={e => setIdLieu(e.target.value)}
                          className="w-full px-2 py-1.5 rounded border text-sm"
                          style={{ borderColor: COL_BORDER }}>
                    <option value="">— Choisir un lieu —</option>
                    {lieux.map(l => (
                      <option key={l.id_cv_lieu_rdv} value={l.id_cv_lieu_rdv}>
                        {l.lib_lieu} ({l.code_postal} {l.nom_ville})
                      </option>
                    ))}
                  </select>
                </Row>
                {lieuSelectionne && (
                  <Row label="Adresse">
                    <div className="space-y-1">
                      <div className="text-xs whitespace-pre-line px-2 py-1.5 rounded border bg-gray-50"
                           style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
                        {lieuSelectionne.adresse1}
                        {lieuSelectionne.adresse2 && '\n' + lieuSelectionne.adresse2}
                        {'\n'}{lieuSelectionne.code_postal} {lieuSelectionne.nom_ville}
                      </div>
                      {lieuSelectionne.latitude_deg && lieuSelectionne.longitude_deg && (
                        <button type="button" onClick={ouvrirMaps}
                                className="flex items-center gap-1 px-2 py-1 text-xs rounded border"
                                style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
                          <MapPin className="w-3 h-3" /> Afficher sur Maps
                        </button>
                      )}
                    </div>
                  </Row>
                )}
              </>
            )}

            {/* SMS de confirmation */}
            <div className="pt-2 mt-2 border-t" style={{ borderColor: COL_BORDER }}>
              <label className="flex items-center gap-2 text-sm" style={{ color: COL_BRUN }}>
                <input type="checkbox" checked={sendSms}
                       onChange={e => setSendSms(e.target.checked)} />
                Envoyer un SMS de confirmation
              </label>
            </div>

            {/* Coordonnees candidat */}
            {sendSms && (
              <>
                <Row label="Mobile">
                  <div className="flex gap-2">
                    <input type="tel" value={gsm} onChange={e => setGsm(e.target.value)}
                           className="flex-1 px-2 py-1.5 rounded border text-sm"
                           style={{ borderColor: COL_BORDER }} />
                    <button type="button" onClick={updateCoords}
                            title="Mettre à jour les coordonnées du candidat"
                            className="px-2 rounded border"
                            style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
                      <Check className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </Row>
                <Row label="Mail">
                  <input type="email" value={mail} onChange={e => setMail(e.target.value)}
                         className="w-full px-2 py-1.5 rounded border text-sm"
                         style={{ borderColor: COL_BORDER }} />
                </Row>

                {/* Choix serveur */}
                <Row label="Lien confirm.">
                  <div className="flex gap-3">
                    <label className="flex items-center gap-1 text-xs" style={{ color: COL_BRUN }}>
                      <input type="radio" checked={choixServeur === 1}
                             onChange={() => setChoixServeur(1)} />
                      Serveur classique
                    </label>
                    <label className="flex items-center gap-1 text-xs" style={{ color: COL_BRUN }}>
                      <input type="radio" checked={choixServeur === 2}
                             onChange={() => setChoixServeur(2)} />
                      Serveur de secours
                    </label>
                  </div>
                </Row>
                <p className="text-xs italic pl-32" style={{ color: '#A68D8A' }}>
                  Le SMS est envoyé via smsmode.com après validation du RDV.
                </p>
              </>
            )}
          </div>

          {/* PANNEAU AGENDA (a droite) */}
          <div className="flex-1 min-w-0 flex flex-col">
            {idRecruteur ? (
              <RecruteurAgenda apiBase={apiBase} idRecruteur={idRecruteur}
                               jour={date}
                               highlightHeure={heure}
                               onSelectSlot={(d, h) => { setDate(d); setHeure(h) }}
                               onChangeJour={(d) => setDate(d)} />
            ) : (
              <div className="flex-1 flex items-center justify-center text-sm italic"
                   style={{ color: '#A68D8A' }}>
                Sélectionne un recruteur pour voir son agenda
              </div>
            )}
          </div>
          </div>
        )}

        {/* FOOTER */}
        {!loading && (
          <div className="px-4 py-3 border-t flex items-center gap-2"
               style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
            <button type="button" onClick={() => onClose(false)}
                    className="flex items-center gap-1 px-3 py-1.5 rounded border text-sm"
                    style={{ borderColor: COL_BORDER, color: COL_BRUN, backgroundColor: 'white' }}>
              <ArrowLeft className="w-3.5 h-3.5" />
              Retour sur la fiche CV
            </button>
            <div className="flex-1" />
            <button type="button" onClick={valider} disabled={!canValider || saving}
                    className="flex items-center gap-2 px-4 py-2 rounded text-white text-sm disabled:opacity-50"
                    style={{ backgroundColor: COL_PRIMARY }}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin" />
                      : <Save className="w-4 h-4" />}
              Valider le RDV
            </button>
          </div>
        )}
      </div>

      {/* Sous-modal Fen_SalonSalarie (gestion salons visio du recruteur) */}
      {showSalons && (
        <SalonsSalarieModal apiBase={apiBase} idRecruteur={idRecruteur}
                            onClose={(selId) => {
                              setShowSalons(false)
                              // Refresh la liste des salons puis pre-selectionne
                              fetch(`${apiBase}/recrutement/cv/salons-visio?id_salarie=${idRecruteur}`, {
                                headers: { Authorization: `Bearer ${getToken()}` },
                              })
                                .then(r => r.ok ? r.json() : [])
                                .then(setSalonsVisio)
                                .then(() => { if (selId) setIdSalon(selId) })
                            }} />
      )}
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[120px_1fr] items-center gap-3 min-h-9">
      <label className="text-xs text-right" style={{ color: COL_BRUN }}>{label}</label>
      <div className="min-w-0">{children}</div>
    </div>
  )
}

function ToggleBtn({ active, onClick, icon: Icon, children }: {
  active: boolean
  onClick: () => void
  icon: React.ComponentType<{ className?: string }>
  children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick}
            className="flex items-center gap-1 px-3 py-1.5 rounded border text-xs"
            style={{
              backgroundColor: active ? COL_PRIMARY : 'white',
              color: active ? 'white' : COL_BRUN,
              borderColor: COL_BORDER,
            }}>
      <Icon className="w-3.5 h-3.5" />
      {children}
    </button>
  )
}
