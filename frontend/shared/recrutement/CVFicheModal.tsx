/**
 * Fen_CVFiche (WinDev) - Fiche CV (shared).
 *
 * Open : POST /cv/{id}/claim (deja fait par RechercheCVPage avant onOpenFiche)
 * Close : POST /cv/{id}/release
 *
 * Boutons :
 *  - Enregistrer : PUT /cv/{id} (avec statut + nouvelle_observation)
 *  - Reactualiser : POST /cv/{id}/reactualiser
 *  - Planifier RDV : V_later (Fen_EntretienAjout)
 *  - Voir le CV : ouvre cvtheque.fic_cv (URL ou fichier)
 *  - Restatuer : POST /cv/{id}/restatuer
 *  - Disquette obs : POST /cv/{id}/observation
 *  - 6 statuts rapides : POST /cv/{id}/statut-quick
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertCircle, ArrowLeft, Calendar, FileSearch, FilePlus, FileText,
  GraduationCap, Loader2, MessageSquareOff, PhoneOff, Play,
  RefreshCw, Save, ScanSearch, Trash2,
  UserX, X,
} from 'lucide-react'
import { getToken } from '@/api'
import { showConfirm, showToast } from '../ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface ComboItem { id: string; label: string }

interface CVFicheDetail {
  id_cvtheque: string
  nom: string
  prenom: string
  adresse: string
  id_communes_france: string
  code_postal: string
  nom_ville: string
  pays: string
  date_naissance: string
  age: number
  permis_b: boolean
  vehicule: boolean
  mail: string
  gsm: string
  id_cvposte: string
  id_cvsource: string
  id_elem_source: string
  id_ste: string
  id_cv_statut: string
  date_rappel: string
  observ: string
  fic_cv: string
  date_saisie: string
  date_reac: string
  coopteur_nom: string
}

interface CVSuiviRow {
  id_cv_suivi: string
  datecrea: string
  op_crea: string
  op_nom: string
  id_cv_statut: string
  statut_lib: string
  type_elem: string
  id_elem: string
  observation: string
}

interface CVFicheModalProps {
  apiBase: string
  idCv: string
  docsBaseUrl?: string         // ex: 'https://interne.omaya.fr'
  userDroits?: string[]        // pour gerer la visibilite du bouton Supprimer
  onClose: (modified?: boolean) => void
  onOpenMotsCles?: (idCv: string) => void  // Fen_CVEditMotsCles (autre module)
}

const QUICK_STATUTS = [
  { id: 4,  label: 'Refus Cand',   icon: UserX,            obs: '' },
  { id: 5,  label: 'Refus RH',     icon: UserX,            obs: '' },
  { id: 3,  label: 'Msg Rép',      icon: MessageSquareOff, obs: 'MESSAGE REP' },
  { id: 7,  label: 'Hors Cible',   icon: PhoneOff,         obs: '' },
  { id: 9,  label: 'Etudiant',     icon: GraduationCap,    obs: '' },
  { id: 2,  label: 'À recontacter', icon: Calendar,        obs: '', needsDate: true },
]

export default function CVFicheModal({
  apiBase, idCv, docsBaseUrl = 'https://interne.omaya.fr',
  userDroits = [], onClose, onOpenMotsCles,
}: CVFicheModalProps) {
  const [fiche, setFiche] = useState<CVFicheDetail | null>(null)
  const [suivi, setSuivi] = useState<CVSuiviRow[]>([])
  const [statuts, setStatuts] = useState<ComboItem[]>([])
  const [sources, setSources] = useState<ComboItem[]>([])
  const [postes, setPostes] = useState<ComboItem[]>([])
  const [annonceurs, setAnnonceurs] = useState<ComboItem[]>([])
  const [societes, setSocietes] = useState<ComboItem[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [nouvelleObs, setNouvelleObs] = useState('')
  const [viewerUrl, setViewerUrl] = useState('')   // panneau Voir le CV
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Au mount : claim (silencieux si 409 = deja ouvert par un autre)
  useEffect(() => {
    fetch(`${apiBase}/recrutement/cv/${idCv}/claim`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
    }).then(async r => {
      if (r.status === 409) {
        try {
          const presR = await fetch(`${apiBase}/recrutement/cv/presence`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${getToken()}`,
            },
            body: JSON.stringify({ ids: [idCv] }),
          })
          if (presR.ok) {
            const d = await presR.json()
            const opNom = d[idCv]?.op_nom || ''
            showToast(
              `Cette fiche est déjà ouverte par ${opNom || 'un autre opérateur'}.`,
              'info',
            )
          }
        } catch { /* silent */ }
      }
    }).catch(() => {})
  }, [apiBase, idCv])

  // Charge tout au mount
  useEffect(() => {
    const h = { Authorization: `Bearer ${getToken()}` }
    Promise.all([
      fetch(`${apiBase}/recrutement/cv/${idCv}`, { headers: h }).then(r => r.ok ? r.json() : null),
      fetch(`${apiBase}/recrutement/cv/${idCv}/cvsuivi`, { headers: h }).then(r => r.ok ? r.json() : []),
      fetch(`${apiBase}/recrutement/cv/statuts`, { headers: h }).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/sources`, { headers: h }).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/postes`, { headers: h }).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/annonceurs`, { headers: h }).then(r => r.json()),
      fetch(`${apiBase}/recrutement/cv/societes`, { headers: h }).then(r => r.json()),
    ])
      .then(([f, s, st, src, po, an, so]) => {
        setFiche(f)
        setSuivi(Array.isArray(s) ? s : [])
        setStatuts(st)
        setSources(src)
        setPostes(po)
        setAnnonceurs(an)
        setSocietes(so)
      })
      .finally(() => setLoading(false))
  }, [apiBase, idCv])

  // Au unmount : release la presence
  useEffect(() => {
    return () => {
      fetch(`${apiBase}/recrutement/cv/${idCv}/release`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      }).catch(() => {})
    }
  }, [apiBase, idCv])

  const setF = (patch: Partial<CVFicheDetail>) => {
    if (!fiche) return
    setFiche({ ...fiche, ...patch })
  }

  const reloadSuivi = useCallback(async () => {
    const r = await fetch(`${apiBase}/recrutement/cv/${idCv}/cvsuivi`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (r.ok) setSuivi(await r.json())
  }, [apiBase, idCv])

  const reloadFiche = useCallback(async () => {
    const r = await fetch(`${apiBase}/recrutement/cv/${idCv}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (r.ok) setFiche(await r.json())
  }, [apiBase, idCv])

  const enregistrer = async () => {
    if (!fiche) return
    if (!fiche.id_communes_france || fiche.id_communes_france === '0') {
      showToast('Merci de choisir une ville valide.', 'info')
      return
    }
    setSaving(true)
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/${idCv}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          nom: fiche.nom,
          prenom: fiche.prenom,
          adresse: fiche.adresse,
          id_communes_france: fiche.id_communes_france,
          pays: fiche.pays,
          date_naissance: fiche.date_naissance,
          permis_b: fiche.permis_b,
          vehicule: fiche.vehicule,
          mail: fiche.mail,
          gsm: fiche.gsm,
          id_cvposte: fiche.id_cvposte,
          id_cvsource: fiche.id_cvsource,
          id_elem_source: fiche.id_elem_source,
          id_ste: fiche.id_ste,
          id_cv_statut: fiche.id_cv_statut,
          date_rappel: fiche.date_rappel,
          nouvelle_observation: nouvelleObs,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      setNouvelleObs('')
      reloadFiche()
      reloadSuivi()
      showToast('Modifications enregistrées', 'success')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setSaving(false) }
  }

  const reactualiser = async () => {
    const ok = await showConfirm({
      title: 'Réactualiser',
      message: 'Réactualiser cette fiche en date du jour ?',
      confirmLabel: 'Réactualiser',
    })
    if (!ok) return
    const r = await fetch(`${apiBase}/recrutement/cv/${idCv}/reactualiser`, {
      method: 'POST', headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (r.ok) {
      reloadFiche()
      reloadSuivi()
      showToast('Fiche actualisée', 'success')
    }
  }

  const restatuer = async () => {
    const r = await fetch(`${apiBase}/recrutement/cv/${idCv}/restatuer`, {
      method: 'POST', headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (r.ok) {
      reloadSuivi()
      showToast('Re-statué', 'success')
    }
  }

  const saveObservation = async () => {
    if (!nouvelleObs.trim()) return
    const r = await fetch(`${apiBase}/recrutement/cv/${idCv}/observation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify({ observation: nouvelleObs }),
    })
    if (r.ok) {
      setNouvelleObs('')
      reloadFiche()
      showToast('Observation ajoutée', 'success')
    }
  }

  const quickStatut = async (st: typeof QUICK_STATUTS[number]) => {
    const ok = await showConfirm({
      title: 'Statuer',
      message: `Voulez-vous statuer ce CV en "${st.label}" ?`,
      confirmLabel: 'Statuer',
    })
    if (!ok) return
    let dateRap: string | undefined
    if (st.needsDate) {
      dateRap = window.prompt('Date de rappel (AAAA-MM-JJ) :', '') || undefined
      if (!dateRap) return
    }
    const r = await fetch(`${apiBase}/recrutement/cv/${idCv}/statut-quick`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify({
        id_cv_statut: st.id,
        observation: st.obs,
        date_rappel: dateRap,
      }),
    })
    if (r.ok) {
      reloadFiche()
      reloadSuivi()
      showToast(`Statué : ${st.label}`, 'success')
    }
  }

  const planifierRdv = () => {
    showToast('Planification RDV : à venir (Fen_EntretienAjout)', 'info')
  }

  const voirCV = () => {
    if (!fiche?.fic_cv) return
    let url = fiche.fic_cv
    if (url.toLowerCase().startsWith('http')) {
      url = url.split(',')[0].trim()
    } else {
      url = `${docsBaseUrl}/cvtheque/${url}`
    }
    setViewerUrl(url)
  }

  // Btn loupe : ouvre Fen_CVEditMotsCles (autre module)
  const ouvreMotsCles = () => {
    if (onOpenMotsCles) onOpenMotsCles(idCv)
    else showToast('Édition mots-clés : à venir', 'info')
  }

  // Btn poubelle : soft-delete si droit CVSuppr
  const supprimerFiche = async () => {
    const ok = await showConfirm({
      title: 'Supprimer la fiche ?',
      message: 'Vous êtes sur le point de supprimer cette fiche. Voulez-vous continuer ?',
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/${idCv}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) {
        if (r.status === 403) {
          showToast('Droit CVSuppr requis.', 'error')
        } else {
          throw new Error(String(r.status))
        }
        return
      }
      showToast('Fiche supprimée.', 'success')
      onClose(true)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  // Btn + : joindre un CV (file picker + upload + auto Voir le CV)
  const joindreCv = async () => {
    const ok = await showConfirm({
      title: 'Joindre un CV',
      message: 'Voulez-vous joindre un CV à cette fiche ?',
      confirmLabel: 'Choisir un fichier',
    })
    if (!ok) return
    fileInputRef.current?.click()
  }

  const onFileChosen = async (ev: React.ChangeEvent<HTMLInputElement>) => {
    const f = ev.target.files?.[0]
    if (!f || !fiche) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', f)
      fd.append('nom', fiche.nom || '')
      const r = await fetch(`${apiBase}/recrutement/cv/${idCv}/upload-cv`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      showToast('CV joint avec succès.', 'success')
      await reloadFiche()
      // Auto Voir le CV apres upload (comme WinDev)
      if (d.fic_cv) {
        setViewerUrl(`${docsBaseUrl}/cvtheque/${d.fic_cv}`)
      }
    } catch (e) {
      showToast(`Erreur chargement : ${(e as Error).message}`, 'error')
    } finally {
      setUploading(false)
      ev.target.value = ''
    }
  }

  const canDelete = userDroits.includes('CVSuppr')

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
         onClick={() => onClose(false)}>
      <div className={`bg-white rounded-xl shadow-2xl ${viewerUrl ? 'max-w-[95vw]' : 'max-w-5xl'} w-full max-h-[95vh] flex flex-col`}
           onClick={e => e.stopPropagation()}
           style={{ border: `1px solid ${COL_BORDER}` }}>
        {/* HEADER */}
        <div className="px-4 py-3 border-b flex items-center gap-2"
             style={{ borderColor: COL_BORDER }}>
          <FileText className="w-5 h-5" style={{ color: COL_PRIMARY }} />
          <h2 className="text-lg font-bold flex-1" style={{ color: COL_BRUN }}>
            Fiche CV {fiche && `— ${fiche.nom} ${fiche.prenom}`}
          </h2>
          <button type="button" onClick={() => onClose(false)}
                  className="p-1.5 rounded hover:bg-gray-100">
            <X className="w-5 h-5" style={{ color: COL_BRUN }} />
          </button>
        </div>

        {loading || !fiche ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin" style={{ color: COL_PRIMARY }} />
          </div>
        ) : (
          <>
            {/* TOOLBAR */}
            <div className="px-4 py-2 border-b flex items-center gap-2 flex-wrap"
                 style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
              <ActionBtn onClick={enregistrer} icon={Save} primary disabled={saving}>
                Enregistrer
              </ActionBtn>
              <ActionBtn onClick={reactualiser} icon={RefreshCw}>
                Réactualiser la fiche
              </ActionBtn>
              <ActionBtn onClick={planifierRdv} icon={Calendar}>
                Planifier un RDV
              </ActionBtn>
              <div className="flex-1" />
              {/* 4 boutons icone-only de droite */}
              <ActionBtn onClick={ouvreMotsCles} icon={ScanSearch}
                         title="Édition mots-clés (Fen_CVEditMotsClés)" />
              {canDelete && (
                <ActionBtn onClick={supprimerFiche} icon={Trash2} variant="danger"
                           title="Supprimer cette fiche" />
              )}
              <ActionBtn onClick={joindreCv} icon={FilePlus} disabled={uploading}
                         title="Joindre un CV (fichier)" />
              <ActionBtn onClick={voirCV} icon={Play} disabled={!fiche.fic_cv}
                         title="Voir le CV à droite">
                Voir le CV
              </ActionBtn>
              <input ref={fileInputRef} type="file" onChange={onFileChosen}
                     className="hidden" />
            </div>

            {/* BODY - split avec viewer optionnel a droite */}
            <div className="flex-1 flex min-h-0">
            <div className={`${viewerUrl ? 'w-[700px] shrink-0 border-r' : 'flex-1'} overflow-y-auto p-4 grid grid-cols-2 gap-4`}
                 style={{ borderColor: COL_BORDER }}>
              {/* Colonne gauche : identite + coordonnees */}
              <div className="space-y-2">
                <FieldRow label="Nom">
                  <input type="text" value={fiche.nom}
                         onChange={e => setF({ nom: e.target.value })}
                         className="w-full px-2 py-1.5 rounded border text-sm uppercase"
                         style={{ borderColor: COL_BORDER }} />
                </FieldRow>
                <FieldRow label="Prénom">
                  <input type="text" value={fiche.prenom}
                         onChange={e => setF({ prenom: e.target.value })}
                         className="w-full px-2 py-1.5 rounded border text-sm"
                         style={{ borderColor: COL_BORDER }} />
                </FieldRow>
                <FieldRow label="Adresse">
                  <input type="text" value={fiche.adresse}
                         onChange={e => setF({ adresse: e.target.value })}
                         className="w-full px-2 py-1.5 rounded border text-sm"
                         style={{ borderColor: COL_BORDER }} />
                </FieldRow>
                <FieldRow label="Ville">
                  <CommunePicker apiBase={apiBase}
                                 value={fiche.id_communes_france}
                                 label={`${fiche.code_postal} ${fiche.nom_ville}`.trim()}
                                 onChange={(id, cp, ville) => setF({
                                   id_communes_france: id,
                                   code_postal: cp,
                                   nom_ville: ville,
                                 })} />
                </FieldRow>
                <FieldRow label="Pays">
                  <input type="text" value={fiche.pays}
                         onChange={e => setF({ pays: e.target.value.toUpperCase() })}
                         className="w-full px-2 py-1.5 rounded border text-sm uppercase"
                         style={{ borderColor: COL_BORDER }} />
                </FieldRow>
                <FieldRow label="Date naissance">
                  <div className="flex gap-2 items-center">
                    <input type="date" value={fiche.date_naissance}
                           onChange={e => setF({ date_naissance: e.target.value })}
                           className="flex-1 px-2 py-1.5 rounded border text-sm"
                           style={{ borderColor: COL_BORDER }} />
                    {fiche.age > 0 && (
                      <span className="text-xs" style={{ color: COL_PRIMARY }}>
                        {fiche.age} ans
                      </span>
                    )}
                  </div>
                </FieldRow>
                <div className="flex items-center gap-4 pl-32">
                  <label className="text-xs flex items-center gap-1" style={{ color: COL_BRUN }}>
                    <input type="checkbox" checked={fiche.permis_b}
                           onChange={e => setF({ permis_b: e.target.checked })} />
                    Permis B
                  </label>
                  <label className="text-xs flex items-center gap-1" style={{ color: COL_BRUN }}>
                    <input type="checkbox" checked={fiche.vehicule}
                           onChange={e => setF({ vehicule: e.target.checked })} />
                    Véhicule
                  </label>
                </div>
                <FieldRow label="Courriel">
                  <input type="email" value={fiche.mail}
                         onChange={e => setF({ mail: e.target.value })}
                         className="w-full px-2 py-1.5 rounded border text-sm"
                         style={{ borderColor: COL_BORDER }} />
                </FieldRow>
                <FieldRow label="Mobile">
                  <input type="tel" value={fiche.gsm}
                         onChange={e => setF({ gsm: e.target.value })}
                         className="w-full px-2 py-1.5 rounded border text-sm"
                         style={{ borderColor: COL_BORDER }} />
                </FieldRow>
              </div>

              {/* Colonne droite : statut + source + societe + observ */}
              <div className="space-y-2">
                <FieldRow label="Poste visé">
                  <select value={fiche.id_cvposte}
                          onChange={e => setF({ id_cvposte: e.target.value })}
                          className="w-full px-2 py-1.5 rounded border text-sm"
                          style={{ borderColor: COL_BORDER }}>
                    <option value="">—</option>
                    {postes.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
                  </select>
                </FieldRow>
                <FieldRow label="Source du CV">
                  <select value={fiche.id_cvsource}
                          onChange={e => setF({ id_cvsource: e.target.value, id_elem_source: '' })}
                          className="w-full px-2 py-1.5 rounded border text-sm"
                          style={{ borderColor: COL_BORDER }}>
                    <option value="">—</option>
                    {sources.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
                  </select>
                </FieldRow>
                {fiche.id_cvsource === '1' && (
                  <FieldRow label="Coopteur">
                    <div className="text-sm px-2 py-1.5 rounded border bg-gray-50"
                         style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
                      {fiche.coopteur_nom || `#${fiche.id_elem_source}`}
                    </div>
                  </FieldRow>
                )}
                {fiche.id_cvsource === '2' && (
                  <FieldRow label="Annonceur">
                    <select value={fiche.id_elem_source}
                            onChange={e => setF({ id_elem_source: e.target.value })}
                            className="w-full px-2 py-1.5 rounded border text-sm"
                            style={{ borderColor: COL_BORDER }}>
                      <option value="">—</option>
                      {annonceurs.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}
                    </select>
                  </FieldRow>
                )}
                <FieldRow label="Société">
                  <select value={fiche.id_ste}
                          onChange={e => setF({ id_ste: e.target.value })}
                          className="w-full px-2 py-1.5 rounded border text-sm"
                          style={{ borderColor: COL_BORDER }}>
                    <option value="">—</option>
                    {societes.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
                  </select>
                </FieldRow>
                <FieldRow label="Statut du CV">
                  <div className="flex gap-2">
                    <select value={fiche.id_cv_statut}
                            onChange={e => setF({ id_cv_statut: e.target.value })}
                            className="flex-1 px-2 py-1.5 rounded border text-sm"
                            style={{ borderColor: COL_BORDER }}>
                      <option value="">—</option>
                      {statuts.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
                    </select>
                    <button type="button" onClick={restatuer}
                            className="px-2 py-1 rounded border text-xs"
                            style={{ borderColor: COL_PRIMARY, color: COL_PRIMARY }}
                            title="Restatuer le CV">
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </FieldRow>
                {fiche.id_cv_statut === '2' && (
                  <FieldRow label="Date de rappel">
                    <input type="date" value={fiche.date_rappel}
                           onChange={e => setF({ date_rappel: e.target.value })}
                           className="w-full px-2 py-1.5 rounded border text-sm"
                           style={{ borderColor: COL_BORDER }} />
                  </FieldRow>
                )}
              </div>

              {/* Observations (toute la largeur) */}
              <div className="col-span-2 space-y-2">
                <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>
                  Observation (historique)
                </label>
                <textarea value={fiche.observ} readOnly rows={4}
                          className="w-full px-2 py-1.5 rounded border text-xs bg-gray-50"
                          style={{ borderColor: COL_BORDER, color: COL_BRUN }} />
                <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>
                  Saisir Observation
                </label>
                <div className="flex gap-2">
                  <input type="text" value={nouvelleObs}
                         onChange={e => setNouvelleObs(e.target.value.toUpperCase())}
                         className="flex-1 px-2 py-1.5 rounded border text-sm uppercase"
                         style={{ borderColor: COL_BORDER }} />
                  <button type="button" onClick={saveObservation}
                          disabled={!nouvelleObs.trim()}
                          className="px-3 py-1.5 rounded text-white text-sm disabled:opacity-50"
                          style={{ backgroundColor: COL_PRIMARY }}
                          title="Ajouter cette observation">
                    <Save className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Statuts rapides */}
              <div className="col-span-2 flex items-center gap-2 flex-wrap pt-2 border-t"
                   style={{ borderColor: COL_BORDER }}>
                {QUICK_STATUTS.map(st => {
                  const Icon = st.icon
                  return (
                    <button key={st.id} type="button" onClick={() => quickStatut(st)}
                            className="flex items-center gap-1 px-3 py-1.5 rounded border text-xs"
                            style={{ borderColor: COL_BORDER, color: COL_BRUN, backgroundColor: 'white' }}>
                      <Icon className="w-3.5 h-3.5" />
                      {st.label}
                    </button>
                  )
                })}
              </div>

              {/* TABLE CvSuivi */}
              <div className="col-span-2">
                <label className="text-xs font-semibold" style={{ color: COL_BRUN }}>
                  Historique des statuts ({suivi.length})
                </label>
                <div className="border rounded mt-1 max-h-60 overflow-y-auto"
                     style={{ borderColor: COL_BORDER }}>
                  <table className="w-full text-xs">
                    <thead style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                      <tr>
                        <th className="px-2 py-1 text-left">Date Création</th>
                        <th className="px-2 py-1 text-left">Déposé par</th>
                        <th className="px-2 py-1 text-left">Statut</th>
                        <th className="px-2 py-1 text-left">Observation</th>
                      </tr>
                    </thead>
                    <tbody>
                      {suivi.length === 0 ? (
                        <tr><td colSpan={4} className="p-3 text-center italic"
                                style={{ color: '#A68D8A' }}>
                          Aucun historique.
                        </td></tr>
                      ) : (
                        suivi.map(s => (
                          <tr key={s.id_cv_suivi} className="border-b"
                              style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
                            <td className="px-2 py-1 whitespace-nowrap">
                              {s.datecrea.replace('T', ' ').slice(0, 16)}
                            </td>
                            <td className="px-2 py-1 whitespace-nowrap">{s.op_nom}</td>
                            <td className="px-2 py-1 whitespace-nowrap">{s.statut_lib}</td>
                            <td className="px-2 py-1">{s.observation}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* PANNEAU VIEWER (a droite) */}
            {viewerUrl && (
              <div className="flex-1 flex flex-col min-w-0">
                <div className="px-3 py-1.5 border-b flex items-center gap-2"
                     style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
                  <button type="button" onClick={() => setViewerUrl('')}
                          className="flex items-center gap-1 px-2 py-1 rounded border text-xs"
                          style={{ borderColor: COL_BORDER, color: COL_BRUN }}>
                    <ArrowLeft className="w-3.5 h-3.5" /> Retour
                  </button>
                  <a href={viewerUrl} target="_blank" rel="noopener noreferrer"
                     className="text-xs truncate flex-1 hover:underline"
                     style={{ color: COL_PRIMARY }} title={viewerUrl}>
                    {viewerUrl}
                  </a>
                </div>
                <iframe src={viewerUrl} className="flex-1 border-0 bg-white"
                        title="Aperçu du CV" />
              </div>
            )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// Sous-composants
// ============================================================================

function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-xs w-32 shrink-0" style={{ color: COL_BRUN }}>{label}</label>
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  )
}

function ActionBtn({ onClick, icon: Icon, children, primary, disabled, variant, title }: {
  onClick: () => void
  icon: React.ComponentType<{ className?: string }>
  children?: React.ReactNode
  primary?: boolean
  disabled?: boolean
  variant?: 'danger'
  title?: string
}) {
  const bg = variant === 'danger' ? '#B91C1C' : primary ? COL_PRIMARY : 'white'
  const fg = primary || variant === 'danger' ? 'white' : COL_BRUN
  return (
    <button type="button" onClick={onClick} disabled={disabled} title={title}
            className="flex items-center gap-1 px-3 py-1.5 rounded border text-sm disabled:opacity-50"
            style={{ borderColor: COL_BORDER, backgroundColor: bg, color: fg }}>
      <Icon className="w-3.5 h-3.5" />
      {children}
    </button>
  )
}

// Picker simple : input texte + propositions + selection unique
function CommunePicker({ apiBase, value, label, onChange }: {
  apiBase: string
  value: string
  label: string
  onChange: (id: string, cp: string, ville: string) => void
}) {
  const [query, setQuery] = useState('')
  const [propositions, setPropositions] = useState<Array<{
    id_communes_france: string; code_postal: string; nom_ville: string
  }>>([])
  const [searching, setSearching] = useState(false)

  const search = async () => {
    if (query.length < 2) return
    setSearching(true)
    try {
      const r = await fetch(
        `${apiBase}/recrutement/cv/communes?q=${encodeURIComponent(query)}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (r.ok) setPropositions(await r.json())
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
               onKeyDown={e => { if (e.key === 'Enter') search() }}
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
      {propositions.length > 0 && (
        <div className="border rounded max-h-40 overflow-y-auto"
             style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
          {propositions.map(p => (
            <button key={p.id_communes_france} type="button"
                    onClick={() => {
                      onChange(p.id_communes_france, p.code_postal, p.nom_ville)
                      setPropositions([])
                      setQuery('')
                    }}
                    className="block w-full text-left px-2 py-1 text-xs hover:bg-white"
                    style={{ color: COL_BRUN }}>
              {p.code_postal} {p.nom_ville}
            </button>
          ))}
        </div>
      )}
      {value === '0' && (
        <div className="text-xs flex items-center gap-1" style={{ color: '#B91C1C' }}>
          <AlertCircle className="w-3 h-3" /> Ville non renseignée
        </div>
      )}
    </div>
  )
}
