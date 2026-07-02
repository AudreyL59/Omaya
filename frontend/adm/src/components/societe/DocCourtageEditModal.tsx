/**
 * Fen_EditionDocCourtage - edition d'un template DOCX de courtage.
 *
 * Version simplifiee (pas d'editeur WYSIWYG DOCX cote web) :
 *   - Metadonnees editables : Groupe, Titre, Société, Info Cplt,
 *     Doc Actif, Favori
 *   - Zone contenu : afficher la taille + boutons Telecharger / Uploader
 *   - Bouton 'Tester mise en page' : combo distrib + genere le DOCX
 *     rempli via l'endpoint publipostage (creer_suivi=false)
 *   - Bouton Enregistrer : PUT metadonnees
 *
 * Pour editer le contenu, le user telecharge le DOCX, le modifie
 * dans Word/LibreOffice, puis re-uploade.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  X, Save, Loader2, FileText, Download, Upload, Play,
  CheckSquare, Star,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'

const API_BASE = '/api/adm'

interface GroupeOpItem { id_groupe_operateur: number; lib_groupe: string }
interface SocieteInterneItem { id_ste: string; rs_interne: string; raison_sociale: string }
interface DistribTestItem { id_ste: string; rs_interne: string; id_gerant: number }
interface Detail {
  id_doc_courtage: string
  titre: string; info_cpl: string
  id_groupe_operateur: number; lib_groupe_operateur: string
  id_ste: string; rs_interne_ste: string
  doc_actif: boolean; prioritaire: boolean
  datecrea: string; modif_date: string
  has_contenu: boolean; taille_contenu: number
}

interface Props {
  idDoc: string | null    // null = creer nouveau
  onClose: () => void
  onSaved?: () => void
}

const EMPTY: Detail = {
  id_doc_courtage: '0',
  titre: '', info_cpl: '',
  id_groupe_operateur: 0, lib_groupe_operateur: '',
  id_ste: '0', rs_interne_ste: '',
  doc_actif: true, prioritaire: false,
  datecrea: '', modif_date: '',
  has_contenu: false, taille_contenu: 0,
}

export default function DocCourtageEditModal({
  idDoc, onClose, onSaved,
}: Props) {
  const isNew = !idDoc || idDoc === '0'
  const [d, setD] = useState<Detail>(EMPTY)
  const [groupes, setGroupes] = useState<GroupeOpItem[]>([])
  const [societes, setSocietes] = useState<SocieteInterneItem[]>([])
  const [distribsTest, setDistribsTest] = useState<DistribTestItem[]>([])
  const [selDistribTest, setSelDistribTest] = useState<string>('')
  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [testing, setTesting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Combos communes
  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/distrib-courtage/combos/groupes-operateur`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then(r => r.ok ? r.json() : []),
      fetch(`${API_BASE}/doc-courtage/combos/societes-interne`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then(r => r.ok ? r.json() : []),
      fetch(`${API_BASE}/doc-courtage/combos/distribs-test`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      }).then(r => r.ok ? r.json() : []),
    ]).then(([g, s, dt]: [GroupeOpItem[], SocieteInterneItem[], DistribTestItem[]]) => {
      setGroupes(g); setSocietes(s); setDistribsTest(dt)
    })
  }, [])

  // Charge le doc si edit
  const loadDoc = useCallback(async () => {
    if (isNew) { setD(EMPTY); setLoading(false); return }
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/doc-courtage/${idDoc}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      setD(await r.json())
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [idDoc, isNew])

  useEffect(() => { void loadDoc() }, [loadDoc])

  const update = (patch: Partial<Detail>) => setD(p => ({ ...p, ...patch }))

  const enregistrer = async () => {
    if (!d.titre.trim()) {
      showToast('Le titre est obligatoire.', 'error'); return
    }
    setSaving(true)
    try {
      const payload = {
        titre: d.titre, info_cpl: d.info_cpl,
        id_groupe_operateur: d.id_groupe_operateur,
        id_ste: 0,   // remplace en query pour precision bigint
        doc_actif: d.doc_actif, prioritaire: d.prioritaire,
      }
      // hack pour id_ste bigint via replace() sur JSON stringify
      const body = JSON.stringify(payload).replace(
        '"id_ste":0', `"id_ste":${d.id_ste}`,
      )
      const url = isNew
        ? `${API_BASE}/doc-courtage`
        : `${API_BASE}/doc-courtage/${d.id_doc_courtage}`
      const method = isNew ? 'POST' : 'PUT'
      const r = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body,
      })
      if (!r.ok) throw new Error(String(r.status))
      if (isNew) {
        const res = await r.json() as { id_doc_courtage: string }
        // Reload en mode edit pour l'id nouveau
        setD(p => ({ ...p, id_doc_courtage: res.id_doc_courtage }))
      }
      showToast(isNew ? 'Document créé' : 'Métadonnées enregistrées', 'success')
      onSaved?.()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setSaving(false) }
  }

  const telecharger = async () => {
    if (!d.has_contenu) { showToast('Aucun contenu à télécharger.', 'info'); return }
    try {
      const r = await fetch(`${API_BASE}/doc-courtage/${d.id_doc_courtage}/contenu`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${d.titre || 'doc'}.docx`
      document.body.appendChild(a); a.click()
      document.body.removeChild(a); URL.revokeObjectURL(url)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const uploader = async (file: File) => {
    if (isNew && d.id_doc_courtage === '0') {
      showToast('Enregistre d\'abord les métadonnées.', 'info'); return
    }
    if (!file.name.toLowerCase().endsWith('.docx')) {
      showToast('Seuls les fichiers .docx sont acceptés.', 'error'); return
    }
    const ok = await showConfirm({
      title: 'Uploader ce fichier ?',
      message: `Remplacer le contenu actuel par "${file.name}" ?`,
    })
    if (!ok) return
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const r = await fetch(
        `${API_BASE}/doc-courtage/${d.id_doc_courtage}/contenu`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
          body: fd,
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      const res = await r.json() as { size: number }
      showToast(`Contenu uploadé (${res.size} octets)`, 'success')
      await loadDoc()
      onSaved?.()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setUploading(false) }
  }

  const testerMiseEnPage = async () => {
    if (!d.has_contenu) {
      showToast('Uploadez d\'abord un DOCX.', 'info'); return
    }
    if (!selDistribTest) {
      showToast('Choisis un distributeur de test.', 'info'); return
    }
    const distrib = distribsTest.find(x => x.id_ste === selDistribTest)
    if (!distrib) return
    setTesting(true)
    try {
      const payload = {
        id_doc_courtage: parseInt(d.id_doc_courtage, 10),
        id_distrib: 0,   // remplacé via replace()
        id_gerant: distrib.id_gerant,
        secteur: 'Test secteur',
        date_signature: new Date().toISOString().slice(0, 10),
        date_avenant: '',
        creer_suivi: false,   // test seul, pas de suivi cree
      }
      const body = JSON.stringify(payload).replace(
        '"id_distrib":0', `"id_distrib":${distrib.id_ste}`,
      )
      const r = await fetch(
        `${API_BASE}/distrib-courtage/generate-contrat`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body,
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `TEST-${d.titre || 'doc'}-${distrib.rs_interne}.docx`
      document.body.appendChild(a); a.click()
      document.body.removeChild(a); URL.revokeObjectURL(url)
      showToast('DOCX de test généré et téléchargé', 'success')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setTesting(false) }
  }

  const formatSize = (n: number): string => {
    if (n < 1024) return `${n} o`
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} ko`
    return `${(n / 1024 / 1024).toFixed(2)} Mo`
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-[900px] max-w-full max-h-[95vh] flex flex-col"
           onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-c-line">
          <h2 className="text-sm font-bold flex items-center gap-2">
            <FileText className="w-4 h-4 text-c-brand" />
            {isNew ? 'Nouveau document de courtage' : 'Édition doc courtage'}
            {!isNew && (
              <span className="text-xs text-c-ink-faint-2 font-normal">
                Id : {d.id_doc_courtage}
              </span>
            )}
          </h2>
          <button onClick={onClose}
            className="p-1 hover:bg-c-surface-soft rounded text-c-ink-faint">
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-c-brand" />
          </div>
        ) : (
          <div className="flex-1 overflow-auto p-4 space-y-4">
            {/* Metadonnees */}
            <section className="border border-c-line rounded-lg p-3">
              <h3 className="text-xs font-bold text-c-ink-faint uppercase tracking-wide mb-2">
                Métadonnées
              </h3>
              <div className="grid grid-cols-4 gap-3 text-xs">
                <Field label="Groupe">
                  <select value={d.id_groupe_operateur}
                    onChange={e => update({ id_groupe_operateur: parseInt(e.target.value, 10) || 0 })}
                    className="w-full px-2 py-1 border border-c-line rounded text-xs h-7">
                    <option value={0}>—</option>
                    {groupes.map(g => (
                      <option key={g.id_groupe_operateur} value={g.id_groupe_operateur}>
                        {g.lib_groupe}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Titre *" cols={3}>
                  <Input value={d.titre} onChange={v => update({ titre: v })} />
                </Field>
                <Field label="Société" cols={2}>
                  <select value={d.id_ste}
                    onChange={e => update({ id_ste: e.target.value })}
                    className="w-full px-2 py-1 border border-c-line rounded text-xs h-7">
                    <option value="0">— Aucune —</option>
                    {societes.map(s => (
                      <option key={s.id_ste} value={s.id_ste}>{s.rs_interne}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Info Cplt" cols={2}>
                  <Input value={d.info_cpl} onChange={v => update({ info_cpl: v })} />
                </Field>
                <div className="col-span-2 flex items-center gap-2 self-end pb-1">
                  <input type="checkbox" checked={d.doc_actif}
                    onChange={e => update({ doc_actif: e.target.checked })}
                    id="doc_actif" />
                  <label htmlFor="doc_actif" className="flex items-center gap-1">
                    <CheckSquare className="w-3.5 h-3.5" /> Doc Actif
                  </label>
                </div>
                <div className="col-span-2 flex items-center gap-2 self-end pb-1">
                  <input type="checkbox" checked={d.prioritaire}
                    onChange={e => update({ prioritaire: e.target.checked })}
                    id="prioritaire" />
                  <label htmlFor="prioritaire" className="flex items-center gap-1">
                    <Star className="w-3.5 h-3.5" /> Favori
                  </label>
                </div>
              </div>
            </section>

            {/* Contenu DOCX */}
            <section className="border border-c-line rounded-lg p-3">
              <h3 className="text-xs font-bold text-c-ink-faint uppercase tracking-wide mb-2">
                Contenu DOCX
              </h3>
              <div className="flex items-center gap-3 text-xs">
                <div className="flex-1">
                  {d.has_contenu ? (
                    <span className="text-c-ink-soft">
                      Fichier actuel : <b>{d.titre || 'doc'}.docx</b>
                      <span className="ml-2 text-c-ink-faint">
                        ({formatSize(d.taille_contenu)})
                      </span>
                    </span>
                  ) : (
                    <span className="italic text-c-ink-faint">
                      Aucun contenu. Uploadez un fichier .docx pour commencer.
                    </span>
                  )}
                </div>
                <input ref={fileInputRef} type="file" accept=".docx"
                  onChange={e => {
                    const f = e.target.files?.[0]
                    if (f) void uploader(f)
                    e.target.value = ''
                  }}
                  className="hidden" />
                <button type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading || isNew || d.id_doc_courtage === '0'}
                  className="flex items-center gap-1.5 px-3 py-1 rounded border border-c-line text-c-ink-soft hover:bg-c-surface-soft text-xs disabled:opacity-30">
                  {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                             : <Upload className="w-3.5 h-3.5" />}
                  Uploader
                </button>
                <button type="button" onClick={telecharger} disabled={!d.has_contenu}
                  className="flex items-center gap-1.5 px-3 py-1 rounded border border-c-line text-c-ink-soft hover:bg-c-surface-soft text-xs disabled:opacity-30">
                  <Download className="w-3.5 h-3.5" /> Télécharger
                </button>
              </div>
              {isNew && d.id_doc_courtage === '0' && (
                <div className="mt-2 text-[10px] text-c-ink-faint italic">
                  Enregistrez d'abord les métadonnées, puis vous pourrez uploader le DOCX.
                </div>
              )}
            </section>

            {/* Tester mise en page */}
            <section className="border border-c-line rounded-lg p-3">
              <h3 className="text-xs font-bold text-c-ink-faint uppercase tracking-wide mb-2">
                Tester la mise en page
              </h3>
              <div className="flex items-center gap-2 text-xs">
                <label className="text-c-ink-faint">Test avec</label>
                <select value={selDistribTest}
                  onChange={e => setSelDistribTest(e.target.value)}
                  className="flex-1 px-2 py-1 border border-c-line rounded text-xs h-7">
                  <option value="">— Choisir un distributeur —</option>
                  {distribsTest.map(dt => (
                    <option key={dt.id_ste} value={dt.id_ste}>
                      {dt.rs_interne}
                    </option>
                  ))}
                </select>
                <button type="button" onClick={testerMiseEnPage}
                  disabled={!d.has_contenu || !selDistribTest || testing}
                  className="flex items-center gap-1.5 px-3 py-1 rounded bg-c-brand text-white hover:opacity-90 text-xs disabled:opacity-30">
                  {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                           : <Play className="w-3.5 h-3.5" />}
                  Tester
                </button>
              </div>
              <div className="mt-2 text-[10px] text-c-ink-faint italic">
                Génère un DOCX de test avec les données du distributeur sélectionné (sans créer de suivi).
              </div>
            </section>
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end gap-2 px-4 py-3 border-t border-c-line">
          <button type="button" onClick={onClose}
            className="px-3 py-1.5 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
            Fermer
          </button>
          <button type="button" onClick={enregistrer} disabled={saving || loading}
            className="flex items-center gap-2 px-4 py-1.5 rounded bg-c-brand text-white text-xs font-medium hover:opacity-90 disabled:opacity-50">
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                     : <Save className="w-3.5 h-3.5" />}
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children, cols = 1 }: {
  label: string; children: React.ReactNode; cols?: number
}) {
  return (
    <div className={cols === 4 ? 'col-span-4' : cols === 3 ? 'col-span-3' : cols === 2 ? 'col-span-2' : ''}>
      <label className="text-[10px] text-c-ink-faint block">{label}</label>
      {children}
    </div>
  )
}

function Input({
  value, onChange, placeholder,
}: {
  value: string; onChange: (v: string) => void; placeholder?: string
}) {
  return (
    <input type="text" value={value ?? ''}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full px-2 py-1 border border-c-line rounded text-xs h-7" />
  )
}
