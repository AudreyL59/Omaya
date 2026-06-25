/**
 * Fen_PrevRec_Ajout — modal de creation d'une nouvelle session de
 * prevision de recrutement.
 *
 * Charge au mount : orga info (lib + capacite + ville + nb_productifs).
 * Form complet avec sections : Info session / Lieu PC / Stats S-1 J-2 /
 * Commentaire. Boutons "Rech pour S-1" / "Rech pour J-2" calculent les
 * cooptations + sourcing dans la zone geographique + periode.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Calendar, Loader2, Plus, Save, Search, Users, X,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '../ui/dialog'
import VilleAutocomplete from './VilleAutocomplete'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'
const COL_RED = '#fee2e2'
const COL_GREEN = '#dcfce7'

interface ComboItem { id: string; label: string }

interface OrgaInfo {
  idorganigramme: string
  lib_orga: string
  capacite: number
  ville: string
  cp: string
  nb_productifs: number
}

interface PrevRecAjoutModalProps {
  apiBase: string
  idOrga: string
  onClose: (createdId?: string) => void
}

export default function PrevRecAjoutModal({
  apiBase, idOrga, onClose,
}: PrevRecAjoutModalProps) {
  // ---- Combos ----
  const [etats, setEtats] = useState<ComboItem[]>([])
  const [lieux, setLieux] = useState<ComboItem[]>([])
  const [recruteurs, setRecruteurs] = useState<ComboItem[]>([])

  // ---- Form fields ----
  const [orgaInfo, setOrgaInfo] = useState<OrgaInfo | null>(null)
  const [loadingOrga, setLoadingOrga] = useState(true)
  const [dateCrea] = useState(new Date().toISOString())

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

  const [busy, setBusy] = useState(false)
  const [searching, setSearching] = useState<null | 'S1' | 'J2'>(null)

  // ---- Initial load : orga info + combos ----
  const loadOrga = useCallback(() => {
    setLoadingOrga(true)
    fetch(`${apiBase}/recrutement/cv/prev-rec/orga-info/${idOrga}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then((info: OrgaInfo | null) => {
        if (info) {
          setOrgaInfo(info)
          setPotentielAccueil(info.capacite)
          setNbProd(info.nb_productifs)
        }
      })
      .finally(() => setLoadingOrga(false))
  }, [apiBase, idOrga])

  useEffect(() => { loadOrga() }, [loadOrga])

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
      setRecruteurs((recR || []).map((r: { id_salarie: string; nom: string; prenom: string }) =>
        ({ id: r.id_salarie, label: `${r.nom?.toUpperCase()} ${r.prenom}` })))
    })
  }, [apiBase])

  // ---- Auto-fill date butoire = date_session - 2j ----
  useEffect(() => {
    if (dateSession && !dateButoire) {
      const d = new Date(dateSession)
      d.setDate(d.getDate() - 2)
      setDateButoire(d.toISOString().slice(0, 10))
    }
  }, [dateSession, dateButoire])

  // ---- Recompute objectifs ----
  useEffect(() => {
    setObjCoopt(Math.max(0, miniCoopt - coopt_S1))
    setObjSourcing(Math.max(0, miniSourcing - src_S1))
  }, [miniCoopt, miniSourcing, coopt_S1, src_S1])

  // ---- Recherche coopt + sourcing ----
  const rech = async (type: 'S1' | 'J2') => {
    if (!idCommune) {
      showToast('Choisis une ville pour le Lieu de PC.', 'info')
      return
    }
    setSearching(type)
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/prev-rec/cherche-coopt-sourcing`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_communes_france: idCommune,
          rayon_km: rayon,
          type_recherche: type === 'S1' ? 1 : 2,
          date_crea_iso: dateCrea,
        }),
      })
      const d = await r.json()
      if (type === 'S1') { setCooptS1(d.coopt || 0); setSrcS1(d.sourcing || 0) }
      else               { setCooptJ2(d.coopt || 0); setSrcJ2(d.sourcing || 0) }
      showToast(
        `Recherche ${type} : ${d.nb_communes} communes / ${d.nb_cv_analyses} CV analysés`,
        'success',
      )
    } catch {
      showToast('Erreur recherche.', 'error')
    } finally { setSearching(null) }
  }

  // ---- Save ----
  const save = async () => {
    if (!dateSession) { showToast('Date de session requise.', 'info'); return }
    setBusy(true)
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/prev-rec`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          idorganigramme: idOrga,
          id_recruteur: idRecruteur,
          id_prev_recrut_etat: idEtat,
          id_cv_lieu_rdv: idLieuRdv,
          id_communes_france: idCommune,
          date_session: dateSession, date_butoire: dateButoire,
          date_debut: dateDebut, date_fin: dateFin,
          taille_session: tailleSession,
          potentiel_accueil: potentielAccueil,
          nb_prod: nbProd,
          nb_coopt_mini: miniCoopt, nb_sourcing_mini: miniSourcing,
          obj_coopt: objCoopt, obj_sourcing: objSourcing,
          coopt_smoins1: coopt_S1, coopt_jmoins2: coopt_J2,
          sourcing_smoins1: src_S1, sourcing_jmoins2: src_J2,
          commentaire,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      showToast('Session enregistrée.', 'success')
      onClose(d.id_prevision_recrut)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setBusy(false) }
  }

  // Couleur cadre (rouge si en dessous mini, vert sinon)
  const cellBg = (val: number, mini: number) =>
    val < mini ? COL_RED : COL_GREEN

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[95vh] flex flex-col"
           style={{ border: `1px solid ${COL_BORDER}` }}>
        <div className="px-4 py-3 border-b flex items-center gap-2"
             style={{ borderColor: COL_BORDER }}>
          <Plus className="w-5 h-5" style={{ color: COL_PRIMARY }} />
          <h2 className="text-lg font-bold flex-1" style={{ color: COL_BRUN }}>
            Nouvelle Prévision de recrutement
          </h2>
          <button type="button" onClick={() => onClose()}
                  className="p-1.5 rounded hover:bg-gray-100">
            <X className="w-5 h-5" style={{ color: COL_BRUN }} />
          </button>
        </div>

        {loadingOrga ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin"
                     style={{ color: COL_PRIMARY }} />
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            <h3 className="text-base font-bold" style={{ color: COL_BRUN }}>
              {orgaInfo?.lib_orga || '—'}
            </h3>

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
                  <Select value={idLieuRdv} onChange={setIdLieuRdv}
                          options={lieux} />
                  <button type="button"
                          onClick={() => showToast('Nouveau lieu RDV : utilise le menu Lieux RDV', 'info')}
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
              <div className="grid grid-cols-[1fr_120px] gap-2 items-start">
                <Row label="Ville">
                  <VilleAutocomplete apiBase={apiBase}
                                     value={idCommune} label={villeLabel}
                                     onChange={(id, cp, ville) => {
                                       setIdCommune(id)
                                       setVilleLabel(id ? `${cp} ${ville}` : '')
                                     }} />
                </Row>
                <Row label="Rayon (km)">
                  <input type="number" value={rayon}
                         onChange={e => setRayon(Number(e.target.value) || 0)}
                         className="w-full px-2 py-1.5 rounded border text-sm"
                         style={{ borderColor: COL_BORDER }} />
                </Row>
              </div>
            </Section>

            <Section title="Stats Coopt et Sourcing">
              <p className="text-xs italic" style={{ color: '#A68D8A' }}>
                Date de réf : {new Date(dateCrea).toLocaleDateString('fr-FR')}
              </p>
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
        )}

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
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helpers UI
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
