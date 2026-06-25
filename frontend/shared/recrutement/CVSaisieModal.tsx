/**
 * Fen_CVSaisie (WinDev) - Creation d'un nouveau CV.
 *
 * Ouvert depuis le bouton 'Saisie de CV' en haut de la RechercheCVPage.
 * Workflow :
 *   1) Form -> bouton Enregistrer
 *   2) Check doublon -> si trouve, modal confirm (creer quand meme = statut=8)
 *   3) Create CV + cvsuivi
 *   4) Propose 'Joindre un CV ?' -> file picker + upload
 *   5) Propose 'Que faire ?' : Nouveau / Aller fiche / Fermer
 */

import { useEffect, useRef, useState } from 'react'
import {
  AlertCircle, ArrowRight, FileSearch, Loader2, Plus,
  Save, User, X,
} from 'lucide-react'
import { getToken } from '@/api'
import { showConfirm, showToast } from '../ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface ComboItem { id: string; label: string }
interface DoublonCandidat {
  id_cvtheque: string
  identite: string
  mail: string
  gsm: string
  date_saisie: string
}

interface CVSaisieModalProps {
  apiBase: string
  onClose: (createdId?: string, goToFiche?: boolean) => void
}

export default function CVSaisieModal({ apiBase, onClose }: CVSaisieModalProps) {
  // Form state
  const [nom, setNom] = useState('')
  const [prenom, setPrenom] = useState('')
  const [adresse, setAdresse] = useState('')
  const [idCommunesFrance, setIdCommunesFrance] = useState('')
  const [villeLabel, setVilleLabel] = useState('')
  const [pays, setPays] = useState('FRANCE')
  const [dateNaissance, setDateNaissance] = useState('')
  const [permisB, setPermisB] = useState(false)
  const [vehicule, setVehicule] = useState(false)
  const [mail, setMail] = useState('')
  const [gsm, setGsm] = useState('')
  const [idCvposte, setIdCvposte] = useState('')
  const [idCvsource, setIdCvsource] = useState('')
  const [idElemSource, setIdElemSource] = useState('')
  const [coopteurLabel, setCoopteurLabel] = useState('')
  const [showCoopteurPicker, setShowCoopteurPicker] = useState(false)
  const [pendingChoice, setPendingChoice] = useState<string>('')  // id_cv si dialog choix actif
  const [idSte, setIdSte] = useState('')
  const [idCvStatut, setIdCvStatut] = useState('1')

  // Combos
  const [postes, setPostes] = useState<ComboItem[]>([])
  const [sources, setSources] = useState<ComboItem[]>([])
  const [annonceurs, setAnnonceurs] = useState<ComboItem[]>([])
  const [societes, setSocietes] = useState<ComboItem[]>([])
  const [statuts, setStatuts] = useState<ComboItem[]>([])

  // Modal state
  const [saving, setSaving] = useState(false)
  const [doublons, setDoublons] = useState<DoublonCandidat[]>([])
  const [uploadingId, setUploadingId] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const h = { Authorization: `Bearer ${getToken()}` }
    fetch(`${apiBase}/recrutement/cv/postes`, { headers: h }).then(r => r.json()).then(setPostes)
    fetch(`${apiBase}/recrutement/cv/sources`, { headers: h }).then(r => r.json()).then(setSources)
    fetch(`${apiBase}/recrutement/cv/annonceurs`, { headers: h }).then(r => r.json()).then(setAnnonceurs)
    fetch(`${apiBase}/recrutement/cv/societes`, { headers: h }).then(r => r.json()).then(setSocietes)
    fetch(`${apiBase}/recrutement/cv/statuts`, { headers: h }).then(r => r.json()).then(setStatuts)
  }, [apiBase])

  const checkDoublonThenCreate = async () => {
    if (!nom.trim() || !prenom.trim()) {
      showToast('Nom et prénom obligatoires.', 'info')
      return
    }
    setSaving(true)
    try {
      const rD = await fetch(`${apiBase}/recrutement/cv/check-doublon`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ mail, gsm, nom, prenom }),
      })
      if (!rD.ok) throw new Error(String(rD.status))
      const data: { found: boolean; candidats: DoublonCandidat[] } = await rD.json()
      if (data.found && data.candidats.length > 0) {
        setDoublons(data.candidats)
        setSaving(false)
        return
      }
      await doCreate(false)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
      setSaving(false)
    }
  }

  const doCreate = async (forceDoublon: boolean) => {
    setSaving(true)
    setDoublons([])
    try {
      const r = await fetch(`${apiBase}/recrutement/cv`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          nom, prenom, adresse,
          id_communes_france: idCommunesFrance,
          pays, date_naissance: dateNaissance,
          permis_b: permisB, vehicule,
          mail, gsm,
          id_cvposte: idCvposte,
          id_cvsource: idCvsource,
          id_elem_source: idElemSource,
          id_ste: idSte,
          id_cv_statut: idCvStatut,
          force_doublon: forceDoublon,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d: { id_cvtheque: string; statut_applique: string } = await r.json()
      showToast('CV créé.', 'success')
      // Propose 'Joindre un CV ?'
      const wantUpload = await showConfirm({
        title: 'Joindre un CV',
        message: 'Voulez-vous joindre un CV à cette fiche ?',
        confirmLabel: 'Choisir un fichier',
      })
      if (wantUpload) {
        setUploadingId(d.id_cvtheque)
        fileInputRef.current?.click()
        // L'enchainement final (dialogue) sera fait dans onFileChosen
      } else {
        finChoisir(d.id_cvtheque)
      }
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
      setSaving(false)
    }
  }

  const onFileChosen = async (ev: React.ChangeEvent<HTMLInputElement>) => {
    const f = ev.target.files?.[0]
    if (!f || !uploadingId) {
      finChoisir(uploadingId || '')
      return
    }
    try {
      const fd = new FormData()
      fd.append('file', f)
      fd.append('nom', nom)
      const r = await fetch(`${apiBase}/recrutement/cv/${uploadingId}/upload-cv`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('CV joint.', 'success')
    } catch (e) {
      showToast(`Erreur upload : ${(e as Error).message}`, 'error')
    }
    ev.target.value = ''
    finChoisir(uploadingId)
  }

  const finChoisir = (idNew: string) => {
    // Affiche un overlay 2-choix dans le modal :
    //  - 'Saisir un nouveau CV' (reset form)
    //  - 'Ouvrir la fiche CV' (onClose avec goToFiche=true)
    setPendingChoice(idNew)
  }

  const choixNouveauCV = () => {
    setNom(''); setPrenom(''); setAdresse(''); setIdCommunesFrance('')
    setVilleLabel(''); setDateNaissance(''); setPermisB(false); setVehicule(false)
    setMail(''); setGsm(''); setIdCvposte(''); setIdCvsource('')
    setIdElemSource(''); setCoopteurLabel('')
    setIdSte(''); setIdCvStatut('1')
    setUploadingId(''); setSaving(false)
    setPendingChoice('')
  }

  const choixOuvrirFiche = () => {
    const id = pendingChoice
    setPendingChoice('')
    onClose(id, true)
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[95vh] flex flex-col"
           style={{ border: `1px solid ${COL_BORDER}` }}>
        {/* HEADER */}
        <div className="px-4 py-3 border-b flex items-center gap-2"
             style={{ borderColor: COL_BORDER }}>
          <Plus className="w-5 h-5" style={{ color: COL_PRIMARY }} />
          <h2 className="text-lg font-bold flex-1" style={{ color: COL_BRUN }}>
            Nouveau CV
          </h2>
          <button type="button" onClick={() => onClose()}
                  className="p-1.5 rounded hover:bg-gray-100">
            <X className="w-5 h-5" style={{ color: COL_BRUN }} />
          </button>
        </div>

        {/* BODY : form 2 colonnes */}
        <div className="flex-1 overflow-y-auto p-4 grid grid-cols-2 gap-x-6 gap-y-2">
          {/* Gauche : identite + coordonnees */}
          <div className="space-y-2">
            <Row label="Nom *">
              <input type="text" value={nom} onChange={e => setNom(e.target.value)}
                     className="w-full px-2 py-1.5 rounded border text-sm uppercase"
                     style={{ borderColor: COL_BORDER }} />
            </Row>
            <Row label="Prénom *">
              <input type="text" value={prenom} onChange={e => setPrenom(e.target.value)}
                     className="w-full px-2 py-1.5 rounded border text-sm"
                     style={{ borderColor: COL_BORDER }} />
            </Row>
            <Row label="Adresse">
              <input type="text" value={adresse} onChange={e => setAdresse(e.target.value)}
                     className="w-full px-2 py-1.5 rounded border text-sm"
                     style={{ borderColor: COL_BORDER }} />
            </Row>
            <Row label="Ville">
              <VillePicker apiBase={apiBase}
                           value={idCommunesFrance} label={villeLabel}
                           onChange={(id, cp, ville) => {
                             setIdCommunesFrance(id)
                             setVilleLabel(id ? `${cp} ${ville}` : '')
                           }} />
            </Row>
            <Row label="Pays">
              <input type="text" value={pays}
                     onChange={e => setPays(e.target.value.toUpperCase())}
                     className="w-full px-2 py-1.5 rounded border text-sm uppercase"
                     style={{ borderColor: COL_BORDER }} />
            </Row>
            <Row label="Date naissance">
              <input type="date" value={dateNaissance}
                     onChange={e => setDateNaissance(e.target.value)}
                     className="w-full px-2 py-1.5 rounded border text-sm"
                     style={{ borderColor: COL_BORDER }} />
            </Row>
            <div className="grid grid-cols-[120px_1fr] items-center gap-3 min-h-9">
              <div />
              <div className="flex items-center gap-4">
                <label className="text-xs flex items-center gap-1" style={{ color: COL_BRUN }}>
                  <input type="checkbox" checked={permisB} onChange={e => setPermisB(e.target.checked)} />
                  Permis B
                </label>
                <label className="text-xs flex items-center gap-1" style={{ color: COL_BRUN }}>
                  <input type="checkbox" checked={vehicule} onChange={e => setVehicule(e.target.checked)} />
                  Véhicule
                </label>
              </div>
            </div>
            <Row label="Mail">
              <input type="email" value={mail} onChange={e => setMail(e.target.value)}
                     className="w-full px-2 py-1.5 rounded border text-sm"
                     style={{ borderColor: COL_BORDER }} />
            </Row>
            <Row label="Mobile">
              <input type="tel" value={gsm} onChange={e => setGsm(e.target.value)}
                     className="w-full px-2 py-1.5 rounded border text-sm"
                     style={{ borderColor: COL_BORDER }} />
            </Row>
          </div>

          {/* Droite : poste / source / société / statut */}
          <div className="space-y-2">
            <Row label="Poste visé">
              <select value={idCvposte} onChange={e => setIdCvposte(e.target.value)}
                      className="w-full px-2 py-1.5 rounded border text-sm"
                      style={{ borderColor: COL_BORDER }}>
                <option value="">—</option>
                {postes.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
            </Row>
            <Row label="Source du CV">
              <select value={idCvsource}
                      onChange={e => { setIdCvsource(e.target.value); setIdElemSource('') }}
                      className="w-full px-2 py-1.5 rounded border text-sm"
                      style={{ borderColor: COL_BORDER }}>
                <option value="">—</option>
                {sources.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
              </select>
            </Row>
            {idCvsource === '2' && (
              <Row label="Annonceur">
                <select value={idElemSource} onChange={e => setIdElemSource(e.target.value)}
                        className="w-full px-2 py-1.5 rounded border text-sm"
                        style={{ borderColor: COL_BORDER }}>
                  <option value="">—</option>
                  {annonceurs.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}
                </select>
              </Row>
            )}
            {idCvsource === '1' && (
              <Row label="Coopteur">
                {idElemSource ? (
                  <div className="flex items-center gap-1">
                    <div className="flex-1 px-2 py-1.5 rounded border bg-gray-50 text-sm"
                         style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
                      {coopteurLabel || `#${idElemSource}`}
                    </div>
                    <button type="button"
                            onClick={() => { setIdElemSource(''); setCoopteurLabel('') }}
                            className="p-1 text-red-600 hover:text-red-800">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <button type="button" onClick={() => setShowCoopteurPicker(true)}
                          className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded border text-sm"
                          style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
                    <User className="w-4 h-4" />
                    Choisir le coopteur
                  </button>
                )}
              </Row>
            )}
            <Row label="Société">
              <select value={idSte} onChange={e => setIdSte(e.target.value)}
                      className="w-full px-2 py-1.5 rounded border text-sm"
                      style={{ borderColor: COL_BORDER }}>
                <option value="">—</option>
                {societes.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
              </select>
            </Row>
            <Row label="Statut du CV">
              <select value={idCvStatut} onChange={e => setIdCvStatut(e.target.value)}
                      className="w-full px-2 py-1.5 rounded border text-sm"
                      style={{ borderColor: COL_BORDER }}>
                {statuts.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
              </select>
            </Row>
          </div>

          {/* Bloc doublon (col-span-2) */}
          {doublons.length > 0 && (
            <div className="col-span-2 p-3 rounded border"
                 style={{ borderColor: '#F59E0B', backgroundColor: '#FFFBEB' }}>
              <div className="flex items-center gap-2 mb-2" style={{ color: '#92400E' }}>
                <AlertCircle className="w-5 h-5" />
                <strong>Doublon détecté : {doublons.length} CV similaire(s)</strong>
              </div>
              <ul className="text-xs space-y-1" style={{ color: COL_BRUN }}>
                {doublons.slice(0, 5).map(d => (
                  <li key={d.id_cvtheque}>
                    • <strong>{d.identite}</strong> — mail: {d.mail || '—'} — gsm: {d.gsm || '—'}
                    {d.date_saisie && ` — saisi ${d.date_saisie}`}
                  </li>
                ))}
                {doublons.length > 5 && (
                  <li>… et {doublons.length - 5} autre(s)</li>
                )}
              </ul>
              <div className="flex gap-2 mt-3">
                <button type="button" onClick={() => setDoublons([])}
                        className="flex-1 px-3 py-1.5 rounded border text-sm"
                        style={{ borderColor: COL_BORDER, color: COL_BRUN, backgroundColor: 'white' }}>
                  Annuler la saisie
                </button>
                <button type="button" onClick={() => doCreate(true)} disabled={saving}
                        className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 rounded text-white text-sm disabled:opacity-50"
                        style={{ backgroundColor: '#F59E0B' }}>
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" />
                          : <ArrowRight className="w-4 h-4" />}
                  Créer quand même (statut "CV Doublon")
                </button>
              </div>
            </div>
          )}
        </div>

        {/* FOOTER */}
        <div className="px-4 py-3 border-t flex items-center gap-2"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <button type="button" onClick={() => onClose()}
                  className="flex items-center gap-1 px-3 py-1.5 rounded border text-sm"
                  style={{ borderColor: COL_BORDER, color: COL_BRUN, backgroundColor: 'white' }}>
            Annuler
          </button>
          <div className="flex-1" />
          <button type="button" onClick={checkDoublonThenCreate}
                  disabled={saving || doublons.length > 0}
                  className="flex items-center gap-2 px-4 py-2 rounded text-white text-sm disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin" />
                    : <Save className="w-4 h-4" />}
            Enregistrer
          </button>
        </div>

        <input ref={fileInputRef} type="file" className="hidden" onChange={onFileChosen} />
      </div>

      {/* Overlay choix apres creation : Nouveau CV OU Ouvrir la fiche */}
      {pendingChoice && (
        <div className="fixed inset-0 bg-black/60 z-[55] flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6"
               style={{ border: `1px solid ${COL_BORDER}` }}>
            <h3 className="text-lg font-bold mb-2" style={{ color: COL_BRUN }}>
              CV enregistré
            </h3>
            <p className="text-sm mb-4" style={{ color: COL_BRUN }}>
              Que souhaitez-vous faire maintenant ?
            </p>
            <div className="grid grid-cols-2 gap-3">
              <button type="button" onClick={choixNouveauCV}
                      className="flex flex-col items-center gap-2 p-4 rounded border hover:bg-gray-50"
                      style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
                <Plus className="w-6 h-6" style={{ color: COL_PRIMARY }} />
                <span className="text-sm font-semibold">Saisir un nouveau CV</span>
              </button>
              <button type="button" onClick={choixOuvrirFiche}
                      className="flex flex-col items-center gap-2 p-4 rounded text-white hover:opacity-90"
                      style={{ backgroundColor: COL_PRIMARY }}>
                <ArrowRight className="w-6 h-6" />
                <span className="text-sm font-semibold">Ouvrir la fiche CV</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sous-modal picker coopteur */}
      {showCoopteurPicker && (
        <CoopteurPicker apiBase={apiBase}
                        onClose={() => setShowCoopteurPicker(false)}
                        onSelect={(s) => {
                          setIdElemSource(s.id_salarie)
                          setCoopteurLabel(`${s.nom.toUpperCase()} ${capitalize(s.prenom)}`)
                          setShowCoopteurPicker(false)
                        }} />
      )}
    </div>
  )
}

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).toLowerCase() : s
}

// Picker simple : input + bouton search + liste resultats
function CoopteurPicker({ apiBase, onClose, onSelect }: {
  apiBase: string
  onClose: () => void
  onSelect: (s: { id_salarie: string; nom: string; prenom: string }) => void
}) {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<Array<{ id_salarie: string; nom: string; prenom: string }>>([])
  const [searching, setSearching] = useState(false)

  const doSearch = () => {
    if (!q.trim()) return
    setSearching(true)
    fetch(`${apiBase}/salaries/search?q=${encodeURIComponent(q.trim())}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(setResults)
      .catch(() => setResults([]))
      .finally(() => setSearching(false))
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full max-h-[80vh] flex flex-col"
           style={{ border: `1px solid ${COL_BORDER}` }}>
        <div className="px-4 py-3 border-b flex items-center gap-2"
             style={{ borderColor: COL_BORDER }}>
          <User className="w-5 h-5" style={{ color: COL_PRIMARY }} />
          <h3 className="text-sm font-bold flex-1" style={{ color: COL_BRUN }}>
            Choisir un coopteur
          </h3>
          <button type="button" onClick={onClose}
                  className="p-1 rounded hover:bg-gray-100">
            <X className="w-4 h-4" style={{ color: COL_BRUN }} />
          </button>
        </div>
        <div className="p-3 border-b flex gap-2" style={{ borderColor: COL_BORDER }}>
          <input type="text" value={q} autoFocus
                 onChange={e => setQ(e.target.value.toUpperCase())}
                 onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); doSearch() } }}
                 placeholder="Nom du salarié"
                 className="flex-1 px-2 py-1.5 rounded border text-sm"
                 style={{ borderColor: COL_BORDER }} />
          <button type="button" onClick={doSearch} disabled={searching}
                  className="px-3 rounded border"
                  style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
            {searching ? <Loader2 className="w-4 h-4 animate-spin" />
                       : <FileSearch className="w-4 h-4" />}
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {results.length === 0 ? (
            <p className="text-xs italic text-center py-4" style={{ color: '#A68D8A' }}>
              {searching ? '...' : 'Saisis un nom et lance la recherche.'}
            </p>
          ) : (
            <div className="space-y-1">
              {results.map(s => (
                <button key={s.id_salarie} type="button"
                        onClick={() => onSelect(s)}
                        className="w-full text-left px-3 py-2 rounded hover:bg-blue-50 border"
                        style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
                  <strong>{s.nom.toUpperCase()}</strong> {capitalize(s.prenom)}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
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

// Petit picker ville (input + recherche)
function VillePicker({ apiBase, value, label, onChange }: {
  apiBase: string; value: string; label: string
  onChange: (id: string, cp: string, ville: string) => void
}) {
  const [query, setQuery] = useState('')
  const [props, setProps] = useState<Array<{
    id_communes_france: string; code_postal: string; nom_ville: string
  }>>([])
  const [searching, setSearching] = useState(false)

  const search = async () => {
    if (query.length < 2) return
    setSearching(true)
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/communes?q=${encodeURIComponent(query)}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (r.ok) setProps(await r.json())
    } finally { setSearching(false) }
  }

  if (value && value !== '0') {
    return (
      <div className="flex items-center gap-1">
        <div className="flex-1 px-2 py-1.5 rounded border bg-gray-50 text-sm"
             style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
          {label}
        </div>
        <button type="button" onClick={() => onChange('', '', '')}
                className="p-1 text-red-600 hover:text-red-800">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <div className="flex gap-1">
        <input type="text" value={query}
               onChange={e => setQuery(e.target.value.toUpperCase())}
               onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); search() } }}
               placeholder="CP ou ville"
               className="flex-1 px-2 py-1.5 rounded border text-sm"
               style={{ borderColor: COL_BORDER }} />
        <button type="button" onClick={search}
                className="px-2 rounded border"
                style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
          {searching ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                     : <FileSearch className="w-3.5 h-3.5" />}
        </button>
      </div>
      {props.length > 0 && (
        <div className="border rounded max-h-40 overflow-y-auto"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          {props.map(p => (
            <button key={p.id_communes_france} type="button"
                    onClick={() => {
                      onChange(p.id_communes_france, p.code_postal, p.nom_ville)
                      setProps([]); setQuery('')
                    }}
                    className="block w-full text-left px-2 py-1 text-xs hover:bg-white"
                    style={{ color: COL_BRUN }}>
              {p.code_postal} {p.nom_ville}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
