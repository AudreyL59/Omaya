/**
 * Fen_PrevRec_Fiche — Fiche d'edition d'une session de prevision existante.
 *
 * Difference avec PrevRecAjoutModal :
 *  - Charge la session existante au mount (au lieu de la creer)
 *  - Panneau droit : liste des vendeurs actifs de l'orga avec leur
 *    dernier contrat (rouge si pas de contrat)
 *  - Boutons header : Lister vendeurs / Recalculer Productifs / Imprimer
 *  - Save = UPDATE au lieu d'INSERT
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Calendar, Loader2, Plus, Printer, RefreshCw, Save, Search, Users, X,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '../ui/dialog'
import VilleAutocomplete from './VilleAutocomplete'
import SendEmailModal from '../email/SendEmailModal'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'
const COL_RED = '#fee2e2'
const COL_GREEN = '#dcfce7'
const COL_RED_BG = '#fef2f2'

interface ComboItem { id: string; label: string }

interface VendeurRow {
  id_vendeur: string
  nom_prenom: string
  date_embauche: string
  dernier_ctt: string
  lib_equipe: string
  id_equipe: string
  has_ctt: boolean
}

interface SessionData {
  id_prevision_recrut: string
  id_prev_recrut_etat: string
  idorganigramme: string
  lib_orga: string
  id_cv_lieu_rdv: string
  id_communes_france: string
  localisation: string
  date_session: string
  date_butoire: string
  date_debut: string
  date_fin: string
  commentaire: string
  taille_session: number
  potentiel_accueil: number
  nb_prod: number
  nb_coopt_mini: number
  nb_sourcing_mini: number
  obj_coopt: number
  obj_sourcing: number
  coopt_smoins1: number
  coopt_jmoins2: number
  sourcing_smoins1: number
  sourcing_jmoins2: number
}

interface PrevRecFicheModalProps {
  apiBase: string
  idPrev: string
  onClose: (modified?: boolean) => void
}

const fmtFR = (iso: string): string => {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

export default function PrevRecFicheModal({
  apiBase, idPrev, onClose,
}: PrevRecFicheModalProps) {
  const [etats, setEtats] = useState<ComboItem[]>([])
  const [lieux, setLieux] = useState<ComboItem[]>([])
  const [recruteurs, setRecruteurs] = useState<ComboItem[]>([])

  const [loadingSess, setLoadingSess] = useState(true)
  const [sess, setSess] = useState<SessionData | null>(null)
  // Pour log changements
  const [dateSessionOld, setDateSessionOld] = useState('')
  const [dateButoireOld, setDateButoireOld] = useState('')

  // Form
  const [dateDebut, setDateDebut] = useState('')
  const [dateFin, setDateFin] = useState('')
  const [idEtat, setIdEtat] = useState('1')
  const [idLieuRdv, setIdLieuRdv] = useState('')
  const [idRecruteur, setIdRecruteur] = useState('')
  const [dateSession, setDateSession] = useState('')
  const [dateButoire, setDateButoire] = useState('')
  const [potentielAccueil, setPotentielAccueil] = useState(0)
  const [nbProd, setNbProd] = useState(0)
  const [tailleSession, setTailleSession] = useState(0)
  const [idCommune, setIdCommune] = useState('')
  const [villeLabel, setVilleLabel] = useState('')
  const [rayon, setRayon] = useState(30)
  const [miniCoopt, setMiniCoopt] = useState(30)
  const [miniSourcing, setMiniSourcing] = useState(50)
  const [coopt_S1, setCooptS1] = useState(0)
  const [src_S1, setSrcS1] = useState(0)
  const [coopt_J2, setCooptJ2] = useState(0)
  const [src_J2, setSrcJ2] = useState(0)
  const [objCoopt, setObjCoopt] = useState(0)
  const [objSourcing, setObjSourcing] = useState(0)
  const [commentaire, setCommentaire] = useState('')

  // Vendeurs orga
  const [vendeurs, setVendeurs] = useState<VendeurRow[]>([])
  const [loadingVend, setLoadingVend] = useState(false)

  const [busy, setBusy] = useState(false)
  const [searching, setSearching] = useState<null | 'S1' | 'J2'>(null)
  const [printing, setPrinting] = useState(false)
  const [emailOpen, setEmailOpen] = useState(false)
  const [emailInit, setEmailInit] = useState<{
    to: string[]; cc: string[]; subject: string; html: string
    pj: { name: string; size: number; contentB64: string }[]
  } | null>(null)

  // ---- Initial load : combos ----
  useEffect(() => {
    const h = { headers: { Authorization: `Bearer ${getToken()}` } }
    Promise.all([
      fetch(`${apiBase}/recrutement/cv/prev-rec/etats`, h).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/lieux-rdv?is_actif=true`, h).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/entretien/recruteurs`, h).then(r => r.json()),
    ]).then(([etatsR, lieuxR, recR]) => {
      setEtats((etatsR || []).map((e: { id_prev_recrut_etat: string; lib_etat: string }) =>
        ({ id: e.id_prev_recrut_etat, label: e.lib_etat })))
      setLieux((lieuxR || []).map((l: { id_cv_lieu_rdv: string; lib_lieu: string }) =>
        ({ id: l.id_cv_lieu_rdv, label: l.lib_lieu })))
      setRecruteurs(recR || [])
    })
  }, [apiBase])

  // ---- Initial load : session ----
  const loadSession = useCallback(() => {
    setLoadingSess(true)
    fetch(`${apiBase}/recrutement/cv/prev-rec/session/${idPrev}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then((s: SessionData | null) => {
        if (!s) { onClose(); return }
        setSess(s)
        setDateDebut(s.date_debut); setDateFin(s.date_fin)
        setIdEtat(s.id_prev_recrut_etat || '1')
        setIdLieuRdv(s.id_cv_lieu_rdv)
        setDateSession(s.date_session); setDateSessionOld(s.date_session)
        setDateButoire(s.date_butoire); setDateButoireOld(s.date_butoire)
        setPotentielAccueil(s.potentiel_accueil)
        setNbProd(s.nb_prod)
        setTailleSession(s.taille_session)
        setIdCommune(s.id_communes_france)
        setVilleLabel(s.localisation)
        setMiniCoopt(s.nb_coopt_mini || 30)
        setMiniSourcing(s.nb_sourcing_mini || 50)
        setCooptS1(s.coopt_smoins1); setCooptJ2(s.coopt_jmoins2)
        setSrcS1(s.sourcing_smoins1); setSrcJ2(s.sourcing_jmoins2)
        setObjCoopt(s.obj_coopt); setObjSourcing(s.obj_sourcing)
        setCommentaire(s.commentaire)
      })
      .finally(() => setLoadingSess(false))
  }, [apiBase, idPrev, onClose])

  useEffect(() => { loadSession() }, [loadSession])

  // ---- Charger les vendeurs orga quand session connue ----
  const loadVendeurs = useCallback(() => {
    if (!sess?.idorganigramme || sess.idorganigramme === '0') return
    setLoadingVend(true)
    fetch(`${apiBase}/recrutement/cv/prev-rec/vendeurs-orga/${sess.idorganigramme}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(setVendeurs)
      .finally(() => setLoadingVend(false))
  }, [apiBase, sess?.idorganigramme])

  useEffect(() => { loadVendeurs() }, [loadVendeurs])

  // Recalculer productifs : compte les vendeurs avec contrat
  const recalculerProductifs = () => {
    const n = vendeurs.filter(v => v.has_ctt).length
    setNbProd(n)
    showToast(`${n} vendeurs productifs sur ${vendeurs.length}.`, 'success')
  }

  // Objectifs auto
  useEffect(() => {
    setObjCoopt(Math.max(0, miniCoopt - coopt_S1))
    setObjSourcing(Math.max(0, miniSourcing - src_S1))
  }, [miniCoopt, miniSourcing, coopt_S1, src_S1])

  // Recherche coopt/sourcing
  const rech = async (type: 'S1' | 'J2') => {
    if (!idCommune) { showToast('Lieu de PC requis.', 'info'); return }
    setSearching(type)
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/prev-rec/cherche-coopt-sourcing`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_communes_france: idCommune, rayon_km: rayon,
          type_recherche: type === 'S1' ? 1 : 2,
          date_crea_iso: new Date().toISOString(),
        }),
      })
      const d = await r.json()
      if (type === 'S1') { setCooptS1(d.coopt || 0); setSrcS1(d.sourcing || 0) }
      else               { setCooptJ2(d.coopt || 0); setSrcJ2(d.sourcing || 0) }
      showToast(`Recherche ${type} : ${d.nb_cv_analyses} CV analysés`, 'success')
    } catch {
      showToast('Erreur recherche.', 'error')
    } finally { setSearching(null) }
  }

  // ---- Imprimer : telecharge PDF + ouvre SendEmailModal pre-rempli ----
  const imprimer = async () => {
    if (!sess) return
    setPrinting(true)
    try {
      // 1) Fetch PDF
      const pdfR = await fetch(`${apiBase}/recrutement/cv/prev-rec/session/${idPrev}/pdf`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!pdfR.ok) throw new Error('PDF KO')
      const blob = await pdfR.blob()
      const ts = new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 14)
      const safeOrga = (sess.lib_orga || 'orga').replace(/[\s\/\\]/g, '_')
      const fname = `${ts}_prevRecrutement_${safeOrga}.pdf`

      // Ouvre dans nouvel onglet pour apercu
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')

      // 2) Prepare le mail
      const arr = await blob.arrayBuffer()
      const b64 = btoa(String.fromCharCode(...new Uint8Array(arr)))

      // Mail recruteur
      let recMail = ''
      if (idRecruteur) {
        try {
          const mR = await fetch(`${apiBase}/recrutement/cv/salaries/${idRecruteur}/mail`, {
            headers: { Authorization: `Bearer ${getToken()}` },
          })
          if (mR.ok) recMail = (await mR.json()).mail || ''
        } catch { /* ignore */ }
      }

      // Contenu mail template etat + remplacements
      let html = ''
      if (idEtat) {
        try {
          const cR = await fetch(`${apiBase}/recrutement/cv/prev-rec/etats/${idEtat}/contenu-mail`, {
            headers: { Authorization: `Bearer ${getToken()}` },
          })
          if (cR.ok) html = (await cR.json()).contenu_mail || ''
        } catch { /* ignore */ }
      }
      const lieuLabel = lieux.find(l => l.id === idLieuRdv)?.label || ''
      const dateSessFR = fmtFR(dateSession)
      const dateSessLong = dateSession
        ? new Date(dateSession).toLocaleDateString('fr-FR', {
            weekday: 'long', day: '2-digit', month: 'long', year: 'numeric',
          })
        : ''
      html = html.replace(/NOMSESSION/g, lieuLabel).replace(/DATESESSION/g, dateSessLong)
      const etatLabel = etats.find(e => e.id === idEtat)?.label || ''
      const subject = `Session ${lieuLabel}-${dateSessFR}//${etatLabel}`

      setEmailInit({
        to: recMail ? [recMail] : [],
        cc: ['marie@exosphere.fr', 'm.doineau@exosphere.fr', 'g.aubry@exosphere.fr'],
        subject, html,
        pj: [{ name: fname, size: blob.size, contentB64: b64 }],
      })
      setEmailOpen(true)
    } catch (e) {
      showToast(`Impression KO : ${(e as Error).message}`, 'error')
    } finally { setPrinting(false) }
  }

  const save = async () => {
    if (!idCommune) {
      showToast('Merci de choisir un lieu de PC valide.', 'info')
      return
    }
    setBusy(true)
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/prev-rec/session/${idPrev}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          idorganigramme: sess?.idorganigramme || '0',
          id_recruteur: idRecruteur,
          id_prev_recrut_etat: idEtat,
          id_cv_lieu_rdv: idLieuRdv,
          id_communes_france: idCommune,
          date_session: dateSession, date_butoire: dateButoire,
          date_debut: dateDebut, date_fin: dateFin,
          taille_session: tailleSession,
          potentiel_accueil: potentielAccueil, nb_prod: nbProd,
          nb_coopt_mini: miniCoopt, nb_sourcing_mini: miniSourcing,
          obj_coopt: objCoopt, obj_sourcing: objSourcing,
          coopt_smoins1: coopt_S1, coopt_jmoins2: coopt_J2,
          sourcing_smoins1: src_S1, sourcing_jmoins2: src_J2,
          commentaire,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const msg = []
      if (dateSession !== dateSessionOld) {
        msg.push(`session ${fmtFR(dateSessionOld)} -> ${fmtFR(dateSession)}`)
      }
      if (dateButoire !== dateButoireOld) {
        msg.push(`butoire ${fmtFR(dateButoireOld)} -> ${fmtFR(dateButoire)}`)
      }
      showToast(`Prévision modifiée${msg.length ? ' (' + msg.join(', ') + ')' : ''}.`, 'success')
      onClose(true)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setBusy(false) }
  }

  const cellBg = (val: number, mini: number) =>
    val < mini ? COL_RED : COL_GREEN

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-6xl w-full max-h-[95vh] flex flex-col"
           style={{ border: `1px solid ${COL_BORDER}` }}>
        {/* Header */}
        <div className="px-4 py-3 border-b flex items-center gap-2"
             style={{ borderColor: COL_BORDER }}>
          <h2 className="text-lg font-bold flex-1" style={{ color: COL_BRUN }}>
            Fiche Prévision de recrutement
            {sess && <span className="text-sm font-normal ml-2"
                           style={{ color: COL_PRIMARY }}>
              — {sess.lib_orga}
            </span>}
          </h2>
          <button type="button" onClick={loadVendeurs}
                  className="flex items-center gap-1 px-2 py-1 rounded border text-xs"
                  style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
            <Users className="w-3.5 h-3.5" />Lister vendeurs
          </button>
          <button type="button" onClick={recalculerProductifs}
                  className="flex items-center gap-1 px-2 py-1 rounded border text-xs"
                  style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
            <RefreshCw className="w-3.5 h-3.5" />Recalculer Productifs
          </button>
          <button type="button" onClick={imprimer} disabled={printing}
                  className="flex items-center gap-1 px-2 py-1 rounded border text-xs disabled:opacity-50"
                  style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
            {printing ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      : <Printer className="w-3.5 h-3.5" />}
            Imprimer
          </button>
          <button type="button" onClick={() => onClose()}
                  className="p-1.5 rounded hover:bg-gray-100">
            <X className="w-5 h-5" style={{ color: COL_BRUN }} />
          </button>
        </div>

        {loadingSess ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin"
                     style={{ color: COL_PRIMARY }} />
          </div>
        ) : (
          <div className="flex-1 flex min-h-0">
            {/* Form gauche */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 border-r"
                 style={{ borderColor: COL_BORDER }}>
              <Section title="Information de session">
                <Row2>
                  <Row label="Du">
                    <DateInput value={dateDebut} onChange={setDateDebut} />
                  </Row>
                  <Row label="Au">
                    <DateInput value={dateFin} onChange={setDateFin} />
                  </Row>
                </Row2>
                <Row label="Etat session">
                  <Select value={idEtat} onChange={setIdEtat} options={etats} />
                </Row>
                <Row label="Lieu RDV">
                  <div className="flex gap-1">
                    <Select value={idLieuRdv} onChange={setIdLieuRdv} options={lieux} />
                    <button type="button"
                            onClick={() => showToast('Nouveau lieu : menu Lieux RDV', 'info')}
                            className="px-2 rounded border"
                            style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </Row>
                <Row label="Recruteur">
                  <Select value={idRecruteur} onChange={setIdRecruteur}
                          options={recruteurs} />
                </Row>
                <Row2>
                  <Row label="Session du">
                    <DateInput value={dateSession} onChange={setDateSession} />
                  </Row>
                  <Row label="Date Butoire">
                    <DateInput value={dateButoire} onChange={setDateButoire} />
                  </Row>
                </Row2>
                <div className="grid grid-cols-3 gap-2">
                  <Field label="Potentiel d'Accueil" value={potentielAccueil}
                         onChange={setPotentielAccueil} />
                  <Field label="NB éléments Productifs" value={nbProd}
                         onChange={setNbProd} />
                  <Field label="Taille Session" value={tailleSession}
                         onChange={setTailleSession} />
                </div>
              </Section>

              <Section title="Lieu de PC">
                <Row label="Ville">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 min-w-0">
                      <VilleAutocomplete apiBase={apiBase}
                                         value={idCommune} label={villeLabel}
                                         onChange={(id, cp, ville) => {
                                           setIdCommune(id)
                                           setVilleLabel(id ? `${cp} ${ville}` : '')
                                         }} />
                    </div>
                    <label className="text-xs whitespace-nowrap"
                           style={{ color: COL_BRUN }}>Rayon</label>
                    <input type="number" value={rayon}
                           onChange={e => setRayon(Number(e.target.value) || 0)}
                           className="w-16 px-2 py-1.5 rounded border text-sm text-center"
                           style={{ borderColor: COL_BORDER }} />
                    <span className="text-xs" style={{ color: COL_BRUN }}>km</span>
                  </div>
                </Row>
              </Section>

              <Section title="Stats Coopt et Sourcing">
                <div className="grid grid-cols-[60px_1fr_1fr_auto] items-center gap-2">
                  <div className="text-xs text-center" style={{ color: COL_BRUN }}>S-1</div>
                  <CellCount label="Cooptations" value={coopt_S1}
                             bg={cellBg(coopt_S1, miniCoopt)} />
                  <CellCount label="Sourcing" value={src_S1}
                             bg={cellBg(src_S1, miniSourcing)} />
                  <BtnRech onClick={() => rech('S1')}
                           loading={searching === 'S1'}>S-1</BtnRech>
                </div>
                <div className="grid grid-cols-[60px_1fr_1fr_auto] items-center gap-2">
                  <div className="text-xs text-center" style={{ color: COL_BRUN }}>J-2</div>
                  <CellCount label="Cooptations" value={coopt_J2}
                             bg={cellBg(coopt_J2, miniCoopt)} />
                  <CellCount label="Sourcing" value={src_J2}
                             bg={cellBg(src_J2, miniSourcing)} />
                  <BtnRech onClick={() => rech('J2')}
                           loading={searching === 'J2'}>J-2</BtnRech>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Nb Coopt Minimum" value={miniCoopt}
                         onChange={setMiniCoopt} />
                  <Field label="Nb Sourcing Minimum" value={miniSourcing}
                         onChange={setMiniSourcing} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Objectif Cooptation" value={objCoopt} readOnly />
                  <Field label="Objectif Sourcing" value={objSourcing} readOnly />
                </div>
              </Section>

              <Section title="Commentaire">
                <textarea value={commentaire}
                          onChange={e => setCommentaire(e.target.value)}
                          rows={3}
                          className="w-full px-2 py-1.5 rounded border text-sm"
                          style={{ borderColor: COL_BORDER }} />
              </Section>
            </div>

            {/* Panneau droit : vendeurs */}
            <div className="w-96 shrink-0 flex flex-col min-h-0">
              <div className="px-3 py-2 border-b"
                   style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
                <h3 className="text-sm font-bold" style={{ color: COL_BRUN }}>
                  Vendeurs actifs ({vendeurs.length})
                </h3>
              </div>
              <div className="flex-1 overflow-auto">
                {loadingVend ? (
                  <div className="p-4 flex justify-center">
                    <Loader2 className="w-5 h-5 animate-spin"
                             style={{ color: COL_PRIMARY }} />
                  </div>
                ) : vendeurs.length === 0 ? (
                  <p className="p-4 italic text-xs text-center"
                     style={{ color: '#A68D8A' }}>
                    Aucun vendeur actif.
                  </p>
                ) : (
                  <table className="w-full text-[11px]">
                    <thead className="sticky top-0"
                           style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                      <tr>
                        <th className="px-2 py-1.5 text-left">Vendeur</th>
                        <th className="px-2 py-1.5 text-left">Embauche</th>
                        <th className="px-2 py-1.5 text-left">Dernier Ctt</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vendeurs.map(v => (
                        <tr key={v.id_vendeur} className="border-b"
                            style={{
                              borderColor: COL_BORDER,
                              backgroundColor: v.has_ctt ? 'white' : COL_RED_BG,
                              color: v.has_ctt ? COL_BRUN : '#991B1B',
                            }}
                            title={v.lib_equipe}>
                          <td className="px-2 py-1">
                            <div className="font-semibold">{v.nom_prenom}</div>
                            <div className="text-[9px] italic"
                                 style={{ color: '#A68D8A' }}>{v.lib_equipe}</div>
                          </td>
                          <td className="px-2 py-1">{fmtFR(v.date_embauche)}</td>
                          <td className="px-2 py-1">{fmtFR(v.dernier_ctt) || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="px-4 py-3 border-t flex items-center justify-end gap-2"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <button type="button" onClick={() => onClose()}
                  className="px-3 py-1.5 rounded border text-sm"
                  style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
            Annuler
          </button>
          <button type="button" onClick={save} disabled={busy}
                  className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
        </div>
      </div>

      {emailInit && (
        <SendEmailModal open={emailOpen}
                        onClose={() => setEmailOpen(false)}
                        getToken={getToken}
                        to={emailInit.to} cc={emailInit.cc}
                        subject={emailInit.subject} html={emailInit.html}
                        initialAttachments={emailInit.pj} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helpers UI (dupliques de PrevRecAjoutModal pour autonomie)
// ---------------------------------------------------------------------------

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="border rounded p-3 space-y-2"
              style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
      <legend className="text-xs font-bold px-1"
              style={{ color: COL_PRIMARY }}>{title.toUpperCase()}</legend>
      {children}
    </fieldset>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[110px_1fr] items-center gap-2 min-h-8">
      <label className="text-xs text-right" style={{ color: COL_BRUN }}>{label}</label>
      <div className="min-w-0">{children}</div>
    </div>
  )
}

function Row2({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-2">{children}</div>
}

function DateInput({ value, onChange }: {
  value: string; onChange: (v: string) => void
}) {
  return (
    <div className="relative">
      <input type="date" value={value} onChange={e => onChange(e.target.value)}
             className="w-full px-2 py-1.5 rounded border text-sm pr-7"
             style={{ borderColor: COL_BORDER }} />
      <Calendar className="w-3.5 h-3.5 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none"
                style={{ color: COL_PRIMARY }} />
    </div>
  )
}

function Select({ value, onChange, options }: {
  value: string; onChange: (v: string) => void; options: ComboItem[]
}) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
            className="w-full px-2 py-1.5 rounded border text-sm"
            style={{ borderColor: COL_BORDER }}>
      <option value="">—</option>
      {options.map(o => <option key={o.id} value={o.id}>{o.label}</option>)}
    </select>
  )
}

function Field({ label, value, onChange, readOnly }: {
  label: string; value: number
  onChange?: (v: number) => void; readOnly?: boolean
}) {
  return (
    <div className="space-y-1">
      <label className="text-[10px]" style={{ color: COL_BRUN }}>{label}</label>
      <input type="number" value={value} readOnly={readOnly}
             onChange={e => onChange?.(Number(e.target.value) || 0)}
             className="w-full px-2 py-1.5 rounded border text-sm text-center"
             style={{
               borderColor: COL_BORDER,
               backgroundColor: readOnly ? '#f3f4f6' : 'white',
             }} />
    </div>
  )
}

function CellCount({ label, value, bg }: {
  label: string; value: number; bg: string
}) {
  return (
    <div className="space-y-1">
      <div className="text-[10px]" style={{ color: COL_BRUN }}>{label}</div>
      <div className="px-2 py-1.5 rounded border text-center text-sm font-bold"
           style={{ borderColor: COL_BORDER, backgroundColor: bg, color: COL_BRUN }}>
        {value}
      </div>
    </div>
  )
}

function BtnRech({ onClick, loading, children }: {
  onClick: () => void; loading?: boolean; children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick} disabled={loading}
            className="flex items-center gap-1 px-2 py-1.5 rounded border text-[10px]"
            style={{
              borderColor: COL_BORDER,
              backgroundColor: COL_PRIMARY_LIGHT, color: 'white',
            }}
            title="Recherche Coopt + Sourcing">
      {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
               : <Search className="w-3.5 h-3.5" />}
      <Users className="w-3 h-3" />
      {children}
    </button>
  )
}
