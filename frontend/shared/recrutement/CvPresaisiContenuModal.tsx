/**
 * Fen_CvPreSaisiContenu — modal de conversion d'un mail CV en CV.
 *
 * Pre-rempli depuis le mail (NOM/PRENOM/MAIL/GSM/ville/objet/contenu HTML).
 * Onglets : CV (form + upload) / Corps de mail (HTML).
 * Boutons : Restaurer ce mail / Enregistrer.
 *
 * Au save :
 *  1) Check doublon par GSM (reuse check_doublon de CVSaisieModal)
 *  2) Si OK -> create_cv (id_cv_source=2 'Mail') + link_mail_to_cv
 *  3) Propose 'Ouvrir la fiche CV'
 */

import { useEffect, useRef, useState } from 'react'
import {
  AlertCircle, Calendar, FileText, Loader2, Mail, RotateCcw,
  Save, Search, Upload, X,
} from 'lucide-react'
import { getToken } from '@/api'
import { showConfirm, showToast } from '../ui/dialog'
import VilleAutocomplete from './VilleAutocomplete'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface ComboItem { id: string; label: string }
interface Mail {
  id_mail: string
  nom: string; prenom: string; mail: string; gsm: string
  cp: string; ville: string
  mail_objet: string; mail_contenu: string; mail_date: string
  adr_mail_rh: string; fic_cv: string; observ: string
}

interface CvPresaisiContenuModalProps {
  apiBase: string
  idMail: string
  docsBaseUrl?: string                  // base URL des fichiers (defaut interne)
  onClose: (cvCreatedId?: string, openFiche?: boolean) => void
  onDeleted?: () => void
}

const fmtDateTime = (iso: string): string => {
  if (!iso) return ''
  const [d, t] = iso.split(' ')
  if (!d) return iso
  const [y, m, day] = d.split('-')
  return `${day}/${m}/${y} ${(t || '').slice(0, 5)}`
}

export default function CvPresaisiContenuModal({
  apiBase, idMail,
  docsBaseUrl = 'https://interne.omaya.fr',
  onClose, onDeleted,
}: CvPresaisiContenuModalProps) {
  const [loading, setLoading] = useState(true)
  const [mail, setMail] = useState<Mail | null>(null)
  const [tab, setTab] = useState<'cv' | 'mail'>('cv')

  // Form
  const [nom, setNom] = useState('')
  const [prenom, setPrenom] = useState('')
  const [adresse, setAdresse] = useState('')
  const [idCom, setIdCom] = useState('')
  const [villeLabel, setVilleLabel] = useState('')
  const [pays, setPays] = useState('FRANCE')
  const [dateNaiss, setDateNaiss] = useState('')
  const [permisB, setPermisB] = useState(false)
  const [vehicule, setVehicule] = useState(false)
  const [mailCand, setMailCand] = useState('')
  const [gsm, setGsm] = useState('')
  const [idCvposte, setIdCvposte] = useState('')
  const [idCvstatut, setIdCvstatut] = useState('1')
  const [idSte, setIdSte] = useState('')
  const [idAnnonceur, setIdAnnonceur] = useState('')
  const [observ, setObserv] = useState('')
  const [ficCV, setFicCV] = useState('')
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const fileRef = useRef<HTMLInputElement | null>(null)

  // Combos
  const [postes, setPostes] = useState<ComboItem[]>([])
  const [statuts, setStatuts] = useState<ComboItem[]>([])
  const [societes, setSocietes] = useState<ComboItem[]>([])
  const [annonceurs, setAnnonceurs] = useState<ComboItem[]>([])

  const [busy, setBusy] = useState(false)

  // ---- Load mail + combos ----
  useEffect(() => {
    const h = { headers: { Authorization: `Bearer ${getToken()}` } }
    Promise.all([
      fetch(`${apiBase}/recrutement/cv/cv-presaisis/${idMail}/contenu`, h)
        .then(r => r.ok ? r.json() : null),
      fetch(`${apiBase}/recrutement/cv/postes`, h).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/statuts`, h).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/societes`, h).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/annonceurs`, h).then(r => r.json()),
    ]).then(([m, p, st, so, an]) => {
      setPostes(Array.isArray(p) ? p : [])
      setStatuts(Array.isArray(st) ? st : [])
      setSocietes(Array.isArray(so) ? so : [])
      setAnnonceurs(Array.isArray(an) ? an : [])
      if (m) {
        setMail(m)
        setNom((m.nom || '').toUpperCase())
        setPrenom(m.prenom || '')
        setMailCand((m.mail || '').toLowerCase())
        setGsm(m.gsm || '')
        setObserv(m.observ || '')
        setFicCV(m.fic_cv || '')
        // L'orga rh mail->id_ste / id_cv_poste : on essaie de charger
        // depuis la liste sources (cf list_mail_sources backend)
        fetch(`${apiBase}/recrutement/cv/cv-presaisis/sources`, h)
          .then(r => r.json())
          .then((srcs: { adr: string; id_ste: string; id_cv_poste: string }[]) => {
            const src = srcs.find(s => s.adr === m.adr_mail_rh)
            if (src) {
              if (src.id_ste && src.id_ste !== '0') setIdSte(src.id_ste)
              if (src.id_cv_poste && src.id_cv_poste !== '0') setIdCvposte(src.id_cv_poste)
            }
          }).catch(() => {})
      }
    }).finally(() => setLoading(false))
  }, [apiBase, idMail])

  // ---- Restaurer ----
  const restore = async () => {
    const ok = await showConfirm({
      title: 'Restaurer ce mail ?',
      message: 'Le mail repassera dans la liste "À traiter". Continuer ?',
      confirmLabel: 'Restaurer',
    })
    if (!ok) return
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/cv-presaisis/${idMail}/restore`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Mail restauré.', 'success')
      onDeleted?.()
      onClose()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }

  // ---- Save = check doublon + create CV + link mail ----
  const save = async () => {
    if (!idCom) {
      showToast('Merci de saisir la ville.', 'info')
      return
    }
    setBusy(true)
    try {
      // 1) Check doublon par GSM
      const dR = await fetch(`${apiBase}/recrutement/cv/check-doublon`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ gsm, mail: mailCand, nom, prenom }),
      })
      if (dR.ok) {
        const dd = await dR.json()
        if (dd.found) {
          const force = await showConfirm({
            title: 'Doublon détecté',
            message: `${dd.candidats?.length || 0} CV existant(s) avec ce mobile/mail. Créer quand même ?`,
            confirmLabel: 'Créer',
          })
          if (!force) { setBusy(false); return }
        }
      }

      // 2) Create CV (id_cv_source = 2 = Mail)
      const cR = await fetch(`${apiBase}/recrutement/cv`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          nom, prenom, adresse,
          id_communes_france: idCom,
          pays, date_naissance: dateNaiss,
          permis_b: permisB, vehicule,
          mail: mailCand, gsm,
          id_cvposte: idCvposte, id_cvsource: '2',         // = Mail
          id_elem_source: idAnnonceur,
          id_ste: idSte,
          id_cv_statut: idCvstatut,
          observ,
          fic_cv: ficCV,
        }),
      })
      if (!cR.ok) throw new Error('Create CV KO')
      const cd = await cR.json()
      const newId = cd.id_cvtheque || cd.id_cv || ''
      if (!newId) throw new Error('Pas d\'id retourne')

      // 3) Upload du CV si fichier choisi
      if (uploadedFile) {
        const fd = new FormData()
        fd.append('file', uploadedFile)
        fd.append('nom', nom)
        await fetch(`${apiBase}/recrutement/cv/${newId}/upload-cv`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
          body: fd,
        }).catch(() => {})
      }

      // 4) Link mail -> CV (marque le mail temp en suppr + lie l'id)
      await fetch(`${apiBase}/recrutement/cv/cv-presaisis/${idMail}/link-cv/${newId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      })

      showToast('CV ajouté.', 'success')
      onDeleted?.()

      // 5) Propose ouverture fiche
      const open = await showConfirm({
        title: 'Que souhaitez-vous faire ?',
        message: 'Ouvrir la fiche CV créée ?',
        confirmLabel: 'Oui, ouvrir',
        cancelLabel: 'Non, fermer',
      })
      onClose(newId, open)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl flex flex-col"
           style={{
             border: `1px solid ${COL_BORDER}`,
             width: 'min(95vw, 1700px)',
             height: 'min(95vh, 1100px)',
           }}>
        <div className="px-4 py-3 border-b flex items-center gap-2"
             style={{ borderColor: COL_BORDER }}>
          <Mail className="w-5 h-5" style={{ color: COL_PRIMARY }} />
          <h2 className="text-lg font-bold flex-1" style={{ color: COL_BRUN }}>
            Fiche CV pré-saisi
          </h2>
          <button type="button" onClick={restore}
                  title="Restaurer ce mail dans la liste À traiter"
                  className="flex items-center gap-1 px-3 py-1 rounded border text-xs"
                  style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
            <RotateCcw className="w-3.5 h-3.5" />
            Restaurer ce mail
          </button>
          <button type="button" onClick={() => onClose()}
                  className="p-1.5 rounded hover:bg-gray-100">
            <X className="w-5 h-5" style={{ color: COL_BRUN }} />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin"
                     style={{ color: COL_PRIMARY }} />
          </div>
        ) : !mail ? (
          <p className="p-8 italic">Mail introuvable.</p>
        ) : (
          <div className="flex-1 overflow-hidden flex flex-col min-h-0">
            {/* Bandeau infos mail */}
            <div className="px-4 py-2 border-b grid grid-cols-2 gap-x-6 gap-y-1 text-xs"
                 style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT, color: COL_BRUN }}>
              <div><strong>A postulé le :</strong> {fmtDateTime(mail.mail_date)}</div>
              <div><strong>Reçu sur :</strong> {mail.adr_mail_rh}</div>
              <div className="col-span-2"><strong>Objet :</strong> {mail.mail_objet}</div>
              <div><strong>Adresse trouvée :</strong> CP {mail.cp} Ville {mail.ville}</div>
            </div>

            <div className="flex-1 flex min-h-0">
              {/* Form gauche */}
              <div className="flex-1 overflow-y-auto p-4 space-y-2 border-r"
                   style={{ borderColor: COL_BORDER }}>
                <Row2>
                  <Row label="Nom*">
                    <input value={nom} onChange={e => setNom(e.target.value.toUpperCase())}
                           className="w-full px-2 py-1.5 rounded border text-sm uppercase"
                           style={{ borderColor: COL_BORDER }} />
                  </Row>
                  <Row label="Prénom*">
                    <input value={prenom} onChange={e => setPrenom(e.target.value)}
                           className="w-full px-2 py-1.5 rounded border text-sm"
                           style={{ borderColor: COL_BORDER }} />
                  </Row>
                </Row2>
                <Row label="Adresse">
                  <input value={adresse} onChange={e => setAdresse(e.target.value)}
                         className="w-full px-2 py-1.5 rounded border text-sm"
                         style={{ borderColor: COL_BORDER }} />
                </Row>
                <Row label="Ville">
                  <VilleAutocomplete apiBase={apiBase}
                                     value={idCom} label={villeLabel}
                                     onChange={(id, cp, v) => {
                                       setIdCom(id)
                                       setVilleLabel(id ? `${cp} ${v}` : '')
                                     }} />
                  {!idCom && (
                    <div className="text-xs flex items-center gap-1 mt-1"
                         style={{ color: '#B91C1C' }}>
                      <AlertCircle className="w-3 h-3" /> Ville non renseignée
                    </div>
                  )}
                </Row>
                <Row label="Pays">
                  <input value={pays} onChange={e => setPays(e.target.value.toUpperCase())}
                         className="w-full px-2 py-1.5 rounded border text-sm uppercase"
                         style={{ borderColor: COL_BORDER }} />
                </Row>
                <Row label="Date Naiss">
                  <div className="relative">
                    <input type="date" value={dateNaiss}
                           onChange={e => setDateNaiss(e.target.value)}
                           className="w-full px-2 py-1.5 rounded border text-sm pr-7"
                           style={{ borderColor: COL_BORDER }} />
                    <Calendar className="w-3.5 h-3.5 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none"
                              style={{ color: COL_PRIMARY }} />
                  </div>
                </Row>
                <div className="flex gap-4 ml-32 text-sm" style={{ color: COL_BRUN }}>
                  <label className="flex items-center gap-1">
                    <input type="checkbox" checked={permisB}
                           onChange={e => setPermisB(e.target.checked)} />
                    Permis B
                  </label>
                  <label className="flex items-center gap-1">
                    <input type="checkbox" checked={vehicule}
                           onChange={e => setVehicule(e.target.checked)} />
                    Véhicule
                  </label>
                </div>
                <Row label="MAIL">
                  <input type="email" value={mailCand}
                         onChange={e => setMailCand(e.target.value.toLowerCase())}
                         className="w-full px-2 py-1.5 rounded border text-sm"
                         style={{ borderColor: COL_BORDER }} />
                </Row>
                <Row label="Mobile">
                  <div className="flex gap-1">
                    <input type="tel" value={gsm}
                           onChange={e => setGsm(e.target.value)}
                           className="flex-1 px-2 py-1.5 rounded border text-sm"
                           style={{ borderColor: COL_BORDER }} />
                    <button type="button" onClick={save} disabled={busy || loading}
                            title="Enregistrer (raccourci)"
                            className="px-2 rounded border disabled:opacity-40"
                            style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
                      <Search className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </Row>
                <Row2>
                  <Row label="Poste visé">
                    <Select value={idCvposte} onChange={setIdCvposte} options={postes} />
                  </Row>
                  <Row label="Statut du CV">
                    <Select value={idCvstatut} onChange={setIdCvstatut} options={statuts} />
                  </Row>
                </Row2>
                <Row2>
                  <Row label="Société">
                    <Select value={idSte} onChange={setIdSte} options={societes} />
                  </Row>
                  <Row label="Annonceur">
                    <Select value={idAnnonceur} onChange={setIdAnnonceur} options={annonceurs} />
                  </Row>
                </Row2>
                <Row label="Observation">
                  <textarea value={observ} onChange={e => setObserv(e.target.value)}
                            rows={3}
                            className="w-full px-2 py-1.5 rounded border text-sm"
                            style={{ borderColor: COL_BORDER }} />
                </Row>
                <Row label="Charger CV">
                  <div className="flex items-center gap-1">
                    <input ref={fileRef} type="file" accept=".pdf,.doc,.docx"
                           onChange={e => setUploadedFile(e.target.files?.[0] || null)}
                           className="hidden" />
                    <button type="button" onClick={() => fileRef.current?.click()}
                            className="flex items-center gap-1 px-2 py-1.5 rounded border text-xs"
                            style={{ borderColor: COL_BORDER, color: COL_PRIMARY }}>
                      <Upload className="w-3.5 h-3.5" />
                      {uploadedFile ? uploadedFile.name : 'Choisir un fichier'}
                    </button>
                  </div>
                </Row>
              </div>

              {/* Onglet CV / Corps de mail droit - largeur fixe ancree */}
              <div className="shrink-0 flex flex-col min-h-0 bg-white"
                   style={{ width: '720px' }}>
                <div className="flex border-b" style={{ borderColor: COL_BORDER }}>
                  <TabBtn active={tab === 'cv'} onClick={() => setTab('cv')}
                          icon={FileText}>CV</TabBtn>
                  <TabBtn active={tab === 'mail'} onClick={() => setTab('mail')}
                          icon={Mail}>Corps de mail</TabBtn>
                </div>
                {tab === 'cv' ? (
                  <div className="flex-1 flex flex-col min-h-0">
                    {mail.fic_cv ? (
                      <>
                        <div className="px-3 py-1.5 text-[10px] border-b truncate"
                             style={{ borderColor: COL_BORDER, color: COL_BRUN,
                                      backgroundColor: COL_BG_SOFT }}
                             title={mail.fic_cv}>
                          <strong>CV joint : </strong>{mail.fic_cv}
                        </div>
                        <iframe src={`${docsBaseUrl}/cvtheque/${encodeURIComponent(mail.fic_cv)}`}
                                title="Aperçu CV"
                                className="flex-1 w-full"
                                style={{ border: 0, minHeight: '300px' }} />
                      </>
                    ) : uploadedFile ? (
                      <div className="p-4 text-sm" style={{ color: COL_BRUN }}>
                        <strong>Fichier choisi :</strong><br />
                        {uploadedFile.name} ({Math.round(uploadedFile.size / 1024)} ko)
                        <p className="mt-2 italic text-xs" style={{ color: '#A68D8A' }}>
                          (sera uploadé à l'enregistrement)
                        </p>
                      </div>
                    ) : (
                      <p className="p-4 italic text-sm" style={{ color: '#A68D8A' }}>
                        Aucun CV joint dans le mail.
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="flex-1 overflow-y-auto p-3 text-xs"
                       style={{ color: COL_BRUN }}>
                    <div dangerouslySetInnerHTML={{ __html: mail.mail_contenu || '' }} />
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="px-4 py-3 border-t flex items-center justify-end gap-2"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          <button type="button" onClick={() => onClose()}
                  className="px-3 py-1.5 rounded border text-sm"
                  style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
            Annuler
          </button>
          <button type="button" onClick={save} disabled={busy || loading}
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

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[120px_1fr] items-start gap-2 min-h-8">
      <label className="text-xs text-right mt-2"
             style={{ color: COL_BRUN }}>{label}</label>
      <div className="min-w-0">{children}</div>
    </div>
  )
}

function Row2({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-2">{children}</div>
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

function TabBtn({ active, onClick, icon: Icon, children }: {
  active: boolean
  onClick: () => void
  icon: React.ComponentType<{ className?: string }>
  children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick}
            className="flex-1 flex items-center justify-center gap-1 px-3 py-2 text-sm border-b-2"
            style={{
              borderColor: active ? COL_PRIMARY : 'transparent',
              color: active ? COL_PRIMARY : '#A68D8A',
              fontWeight: active ? 'bold' : 'normal',
            }}>
      <Icon className="w-3.5 h-3.5" />
      {children}
    </button>
  )
}
