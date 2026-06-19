/**
 * Fen_EditionDocRH (transposition WinDev) - edition d'un doc RH.
 *
 * V1.2 : metadonnees + editeur inline contentEditable + import/export DOCX.
 * Btn 'Tester Mise en page' substitue les variables (S_NOM, STE_RS, etc.)
 * avec des donnees fictives + une societe choisie -> telecharge le
 * document publiposte (cf. Publipostage_TESTSalarie WinDev).
 *
 * V1.3 : insertion images logo/cachet/signatures dans le publipostage.
 */

import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Bold,
  Download,
  Eye,
  Italic,
  List,
  ListOrdered,
  Loader2,
  RotateCcw,
  Save,
  Underline as UnderlineIcon,
  Upload,
  X,
} from 'lucide-react'

import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface Lookups {
  types_doc: { id_type_doc: string; lib: string }[]
  types_produit: { id_type_produit: string; lib: string }[]
  societes: {
    id_ste: string
    raison_sociale: string
    rs_interne: string
  }[]
  types_photo_dpae: { id_tk_type_photo_dpae: string; lib: string }[]
}

interface DocMeta {
  id_doc_rh: string
  id_type_doc: string
  titre: string
  info_cpl: string
  id_type_produit: string
  doc_actif: boolean
  prioritaire: boolean
  id_ste: string
  doc_dpae: boolean
  doc_dpae_distrib: boolean
  id_tk_type_photo_dpae: string
  taille_contenu: number
}

interface Props {
  idDocRh: string  // '' pour creation
  onClose: () => void
  onSaved: () => void
}

const EMPTY: DocMeta = {
  id_doc_rh: '',
  id_type_doc: '',
  titre: '',
  info_cpl: '',
  id_type_produit: '1',
  doc_actif: true,
  prioritaire: false,
  id_ste: '0',
  doc_dpae: false,
  doc_dpae_distrib: false,
  id_tk_type_photo_dpae: '0',
  taille_contenu: 0,
}

export default function DocRHEditModal({
  idDocRh: initialId,
  onClose,
  onSaved,
}: Props) {
  const [docId, setDocId] = useState(initialId)
  const [meta, setMeta] = useState<DocMeta>(EMPTY)
  const [lookups, setLookups] = useState<Lookups | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [steTest, setSteTest] = useState('')
  const [testing, setTesting] = useState(false)
  const editorRef = useRef<HTMLDivElement | null>(null)
  const [editorReady, setEditorReady] = useState(false)
  // HTML a injecter dans l'editeur une fois qu'il est rendu (sinon
  // editorRef.current est null pendant le useEffect d'init).
  const [pendingHtml, setPendingHtml] = useState<string | null>(null)

  const update = (patch: Partial<DocMeta>) => setMeta((m) => ({ ...m, ...patch }))

  // ---- Init -------------------------------------------------------------
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const lk = await fetch('/api/adm/ctt-travail/lookups', {
          headers: { Authorization: `Bearer ${getToken()}` },
        }).then((r) => r.json())
        if (cancelled) return
        setLookups(lk as Lookups)

        let id = initialId
        if (!id) {
          const created = await fetch('/api/adm/ctt-travail/new', {
            method: 'POST',
            headers: { Authorization: `Bearer ${getToken()}` },
          }).then((r) => r.json())
          id = created.id_doc_rh
          setDocId(id)
        }
        const m = await fetch(`/api/adm/ctt-travail/${id}`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        }).then((r) => r.json())
        if (cancelled) return
        setMeta(m as DocMeta)

        // Charge et convertit le contenu pour l'editeur inline
        if ((m as DocMeta).taille_contenu > 0) {
          await loadContentToEditor(id)
        }
        if (!cancelled) setEditorReady(true)
      } catch (e) {
        showToast(`Échec chargement : ${(e as Error).message}`, 'error')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [initialId])

  // ---- Chargement du contenu (DOCX -> HTML via mammoth, ou HTML brut) ---
  const loadContentToEditor = async (id: string) => {
    try {
      const r = await fetch(`/api/adm/ctt-travail/${id}/content`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) {
        setPendingHtml('')
        return
      }
      const buf = await r.arrayBuffer()
      const bytes = new Uint8Array(buf)
      // Detect DOCX (magic PK\x03\x04)
      const isDocx =
        bytes.length >= 4 &&
        bytes[0] === 0x50 &&
        bytes[1] === 0x4b &&
        bytes[2] === 0x03 &&
        bytes[3] === 0x04
      let html = ''
      if (isDocx) {
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-ignore - pas de types officiels pour mammoth
        const mammoth = (await import('mammoth/mammoth.browser.js')).default
        const res = await mammoth.convertToHtml({ arrayBuffer: buf })
        html = res.value
      } else {
        html = new TextDecoder('utf-8').decode(buf)
      }
      // Stocke - sera injecte par le useEffect [pendingHtml, editorReady]
      // quand le contentEditable sera rendu.
      setPendingHtml(html)
    } catch (e) {
      console.error('[doc-rh] loadContent', e)
      setPendingHtml('')
    }
  }

  // Injecte le HTML dans l'editeur APRES que contentEditable soit rendu
  // (editorRef.current est null tant que loading=true et div d'attente est
  // affiche).
  useEffect(() => {
    if (!editorReady || pendingHtml === null) return
    if (editorRef.current) {
      editorRef.current.innerHTML = pendingHtml
      setPendingHtml(null)
    }
  }, [editorReady, pendingHtml])

  // ---- Toolbar contenteditable -----------------------------------------
  const exec = (cmd: string, value?: string) => {
    document.execCommand(cmd, false, value)
    editorRef.current?.focus()
  }

  // ---- Save -------------------------------------------------------------
  const saveMeta = async () => {
    setSaving(true)
    try {
      // 1. Metadonnees
      const r = await fetch(`/api/adm/ctt-travail/${docId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_type_doc: Number(meta.id_type_doc) || 0,
          titre: meta.titre,
          info_cpl: meta.info_cpl,
          id_type_produit: Number(meta.id_type_produit) || 1,
          id_ste: Number(meta.id_ste) || 0,
          doc_actif: meta.doc_actif,
          prioritaire: meta.prioritaire,
          doc_dpae: meta.doc_dpae,
          doc_dpae_distrib: meta.doc_dpae_distrib,
          id_tk_type_photo_dpae: Number(meta.id_tk_type_photo_dpae) || 0,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))

      // 2. Contenu HTML (si l'editeur a du contenu)
      const html = editorRef.current?.innerHTML || ''
      if (html.trim()) {
        const rh = await fetch(`/api/adm/ctt-travail/${docId}/content-html`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({ html }),
        })
        if (!rh.ok) throw new Error(`content: ${rh.status}`)
        const j = await rh.json()
        update({ taille_contenu: j.taille })
      }

      showToast('Doc RH enregistré.', 'success')
      onSaved()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  // ---- Upload docx ------------------------------------------------------
  const uploadDocx = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.docx'
    input.onchange = async () => {
      const f = input.files?.[0]
      if (!f) return
      setSaving(true)
      try {
        const fd = new FormData()
        fd.append('file', f)
        const r = await fetch(`/api/adm/ctt-travail/${docId}/content`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
          body: fd,
        })
        const j = await r.json()
        if (!r.ok) throw new Error(j?.detail || String(r.status))
        update({ taille_contenu: j.taille })
        showToast(`Document chargé (${(j.taille / 1024).toFixed(1)} Ko).`, 'success')
      } catch (e) {
        showToast(`Échec upload : ${(e as Error).message}`, 'error')
      } finally {
        setSaving(false)
      }
    }
    input.click()
  }

  const downloadDocx = () => {
    const a = document.createElement('a')
    a.href = `/api/adm/ctt-travail/${docId}/content?_t=${Date.now()}`
    // L'auth header ne se passe pas via <a>. On force le fetch + blob.
    fetch(a.href, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `${meta.titre || 'document'}.docx`
        link.click()
        URL.revokeObjectURL(url)
      })
      .catch(() => showToast('Téléchargement échoué.', 'error'))
  }

  // ---- Test mise en page ------------------------------------------------
  const testMep = async () => {
    if (!steTest) {
      showToast('Sélectionne une société pour le test.', 'info')
      return
    }
    setTesting(true)
    try {
      await saveMeta()
      const r = await fetch(
        `/api/adm/ctt-travail/${docId}/publipostage-test?id_ste=${steTest}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `test_${meta.titre || docId}.docx`
      link.click()
      URL.revokeObjectURL(url)
      showToast('Document publiposté téléchargé.', 'success')
    } catch (e) {
      showToast(`Échec test : ${(e as Error).message}`, 'error')
    } finally {
      setTesting(false)
    }
  }

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
          className="bg-white rounded-lg shadow-xl w-full max-w-5xl flex flex-col max-h-[90vh] font-normal"
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-4 py-3 border-b"
            style={{ borderColor: COL_BG_SOFT, backgroundColor: COL_BG_SOFT }}
          >
            <h3 className="text-base font-bold" style={{ color: COL_BRUN }}>
              Édition doc RH
            </h3>
            <div className="flex items-center gap-3">
              {meta.id_doc_rh && (
                <span className="text-xs" style={{ color: COL_BRUN }}>
                  Id Doc RH : {meta.id_doc_rh}
                </span>
              )}
              <button
                onClick={onClose}
                className="p-1 hover:bg-white/40 rounded"
              >
                <X className="w-4 h-4" style={{ color: COL_BRUN }} />
              </button>
            </div>
          </div>

          {loading || !lookups ? (
            <div className="p-10 flex justify-center">
              <Loader2 className="w-5 h-5 animate-spin text-[#A68D8A]" />
            </div>
          ) : (
            <div className="overflow-y-auto p-4">
              {/* Toggle Actif / Archive */}
              <div className="flex justify-between items-center mb-4">
                <ActifToggle
                  value={meta.doc_actif}
                  onChange={(v) => update({ doc_actif: v })}
                />
                <button
                  type="button"
                  onClick={saveMeta}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 rounded-md text-white text-sm font-medium disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  Enregistrer
                </button>
              </div>

              {/* Form metadonnees */}
              <div className="grid grid-cols-3 gap-4 mb-4">
                <Field label="Type Doc">
                  <select
                    value={meta.id_type_doc}
                    onChange={(e) => update({ id_type_doc: e.target.value })}
                    className={inputCls}
                  >
                    <option value="">-</option>
                    {lookups.types_doc.map((t) => (
                      <option key={t.id_type_doc} value={t.id_type_doc}>
                        {t.lib}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Produit">
                  <select
                    value={meta.id_type_produit}
                    onChange={(e) => update({ id_type_produit: e.target.value })}
                    className={inputCls}
                  >
                    {lookups.types_produit.map((p) => (
                      <option key={p.id_type_produit} value={p.id_type_produit}>
                        {p.lib}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Type Photo (DPAE)">
                  <select
                    value={meta.id_tk_type_photo_dpae}
                    onChange={(e) =>
                      update({ id_tk_type_photo_dpae: e.target.value })
                    }
                    className={inputCls}
                  >
                    <option value="0">-</option>
                    {lookups.types_photo_dpae.map((p) => (
                      <option key={p.id_tk_type_photo_dpae} value={p.id_tk_type_photo_dpae}>
                        {p.lib}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-4">
                <Field label="Titre" wide>
                  <input
                    type="text"
                    value={meta.titre}
                    onChange={(e) => update({ titre: e.target.value })}
                    className={inputCls}
                  />
                </Field>
                <Field label="Info Cplt">
                  <input
                    type="text"
                    value={meta.info_cpl}
                    onChange={(e) => update({ info_cpl: e.target.value })}
                    className={inputCls}
                  />
                </Field>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-4">
                <Field label="Société" wide>
                  <select
                    value={meta.id_ste}
                    onChange={(e) => update({ id_ste: e.target.value })}
                    className={inputCls}
                  >
                    <option value="0">-</option>
                    {lookups.societes.map((s) => (
                      <option key={s.id_ste} value={s.id_ste}>
                        {s.rs_interne || s.raison_sociale}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="flex flex-col gap-1 self-end pb-1.5">
                  <Checkbox
                    label="Favori (prioritaire)"
                    value={meta.prioritaire}
                    onChange={(v) => update({ prioritaire: v })}
                  />
                </div>
              </div>

              <div
                className="mt-4 pt-3 border-t"
                style={{ borderColor: COL_BORDER }}
              >
                <h4
                  className="text-xs font-bold uppercase mb-2 tracking-wide"
                  style={{ color: COL_BRUN }}
                >
                  À faire signer au démarrage
                </h4>
                <div className="flex gap-6">
                  <Checkbox
                    label="Ticket DPAE"
                    value={meta.doc_dpae}
                    onChange={(v) => update({ doc_dpae: v })}
                  />
                  <Checkbox
                    label="Tk nouveau Distrib"
                    value={meta.doc_dpae_distrib}
                    onChange={(v) => update({ doc_dpae_distrib: v })}
                  />
                </div>
              </div>

              {/* Test de mise en page */}
              <div
                className="mt-5 pt-4 border-t"
                style={{ borderColor: COL_BORDER }}
              >
                <h4
                  className="text-xs font-bold uppercase mb-2 tracking-wide"
                  style={{ color: COL_BRUN }}
                >
                  Test de mise en page
                </h4>
                <div className="flex items-end gap-2">
                  <Field label="Société test" wide>
                    <select
                      value={steTest}
                      onChange={(e) => setSteTest(e.target.value)}
                      className={inputCls}
                    >
                      <option value="">- Choisir -</option>
                      {lookups.societes.map((s) => (
                        <option key={s.id_ste} value={s.id_ste}>
                          {s.rs_interne || s.raison_sociale}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <button
                    type="button"
                    onClick={testMep}
                    disabled={testing || !steTest || meta.taille_contenu === 0}
                    className="flex items-center gap-2 px-3 py-2 rounded-md text-white text-sm disabled:opacity-50"
                    style={{ backgroundColor: COL_PRIMARY }}
                  >
                    {testing ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                    Tester mise en page
                  </button>
                </div>
                <p
                  className="text-xs italic mt-1.5"
                  style={{ color: COL_BRUN }}
                >
                  Substitue les variables S_NOM / STE_* avec des données
                  fictives + la société choisie. Les images (logo / cachet /
                  signatures) ne sont pas encore traitées en V1.
                </p>
              </div>

              {/* Contenu - editeur inline */}
              <div
                className="mt-5 pt-4 border-t"
                style={{ borderColor: COL_BORDER }}
              >
                <div className="flex items-center justify-between mb-2">
                  <h4
                    className="text-xs font-bold uppercase tracking-wide"
                    style={{ color: COL_BRUN }}
                  >
                    Contenu du document
                  </h4>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={uploadDocx}
                      title="Charger un DOCX existant (remplace le contenu)"
                      className="flex items-center gap-1 px-2 py-1 rounded-md text-xs border"
                      style={{ borderColor: COL_BORDER, color: COL_BRUN }}
                    >
                      <Upload className="w-3.5 h-3.5" />
                      Importer DOCX
                    </button>
                    {meta.taille_contenu > 0 && (
                      <button
                        type="button"
                        onClick={downloadDocx}
                        className="flex items-center gap-1 px-2 py-1 rounded-md text-xs border"
                        style={{ borderColor: COL_BORDER, color: COL_BRUN }}
                      >
                        <Download className="w-3.5 h-3.5" />
                        Télécharger
                      </button>
                    )}
                  </div>
                </div>
                {/* Toolbar editeur */}
                <div
                  className="flex flex-wrap items-center gap-1 px-2 py-1 border-b border-x rounded-t"
                  style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}
                >
                  <ToolBtn onClick={() => exec('bold')} title="Gras">
                    <Bold className="w-3.5 h-3.5" />
                  </ToolBtn>
                  <ToolBtn onClick={() => exec('italic')} title="Italique">
                    <Italic className="w-3.5 h-3.5" />
                  </ToolBtn>
                  <ToolBtn onClick={() => exec('underline')} title="Souligné">
                    <UnderlineIcon className="w-3.5 h-3.5" />
                  </ToolBtn>
                  <div className="w-px h-4 bg-[#A68D8A]/30 mx-1" />
                  <ToolBtn
                    onClick={() => exec('formatBlock', '<h1>')}
                    title="Titre 1"
                  >
                    H1
                  </ToolBtn>
                  <ToolBtn
                    onClick={() => exec('formatBlock', '<h2>')}
                    title="Titre 2"
                  >
                    H2
                  </ToolBtn>
                  <ToolBtn
                    onClick={() => exec('formatBlock', '<p>')}
                    title="Paragraphe"
                  >
                    ¶
                  </ToolBtn>
                  <div className="w-px h-4 bg-[#A68D8A]/30 mx-1" />
                  <ToolBtn onClick={() => exec('insertUnorderedList')} title="Liste">
                    <List className="w-3.5 h-3.5" />
                  </ToolBtn>
                  <ToolBtn onClick={() => exec('insertOrderedList')} title="Liste num">
                    <ListOrdered className="w-3.5 h-3.5" />
                  </ToolBtn>
                  <div className="w-px h-4 bg-[#A68D8A]/30 mx-1" />
                  <ToolBtn
                    onClick={() => exec('justifyLeft')}
                    title="Aligner à gauche"
                  >
                    ⇤
                  </ToolBtn>
                  <ToolBtn onClick={() => exec('justifyCenter')} title="Centrer">
                    ↔
                  </ToolBtn>
                  <ToolBtn
                    onClick={() => exec('justifyRight')}
                    title="Aligner à droite"
                  >
                    ⇥
                  </ToolBtn>
                </div>
                <div
                  ref={editorRef}
                  contentEditable={editorReady}
                  suppressContentEditableWarning
                  className="border min-h-[300px] max-h-[400px] overflow-y-auto p-4 text-sm focus:outline-none rounded-b"
                  style={{
                    borderColor: COL_BORDER,
                    color: COL_BRUN,
                    fontFamily: 'Calibri, "Segoe UI", sans-serif',
                  }}
                />
                <p
                  className="text-xs italic mt-1.5"
                  style={{ color: COL_BRUN }}
                >
                  Variables disponibles : S_NOM, S_PRENOM, S_DNAISS, S_ADRESSE,
                  S_CP, S_VILLE, S_GSM, DATE_CTS, FIN_PER_ESSAI, STE_RS,
                  STE_SIRET, STE_GERANT_NOM, etc.
                </p>

                <div
                  className="mt-3 pt-2 border-t flex"
                  style={{ borderColor: COL_BORDER }}
                >
                  <button
                    type="button"
                    onClick={onClose}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm border"
                    style={{ borderColor: COL_BORDER, color: COL_BRUN }}
                  >
                    <RotateCcw className="w-4 h-4" />
                    Fermer
                  </button>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

// ============================================================================
// UI helpers
// ============================================================================

const inputCls =
  'w-full px-2 py-1.5 border rounded text-sm focus:outline-none focus:ring-1 focus:ring-[#17494E]'

function Field({
  label,
  children,
  wide,
}: {
  label: string
  children: React.ReactNode
  wide?: boolean
}) {
  return (
    <div className={wide ? 'col-span-2' : ''}>
      <label className="block text-xs mb-0.5" style={{ color: COL_BRUN }}>
        {label}
      </label>
      {children}
    </div>
  )
}

function Checkbox({
  label,
  value,
  onChange,
}: {
  label: string
  value: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label
      className="flex items-center gap-2 text-sm cursor-pointer"
      style={{ color: COL_BRUN }}
    >
      <input
        type="checkbox"
        checked={value}
        onChange={(e) => onChange(e.target.checked)}
      />
      {label}
    </label>
  )
}

function ToolBtn({
  onClick,
  title,
  children,
}: {
  onClick: () => void
  title: string
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseDown={(e) => e.preventDefault()}
      title={title}
      className="px-2 py-1 rounded hover:bg-white text-xs"
      style={{ color: COL_BRUN }}
    >
      {children}
    </button>
  )
}

function ActifToggle({
  value,
  onChange,
}: {
  value: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <div
      className="flex items-center rounded overflow-hidden"
      style={{ border: `1px solid ${COL_BORDER}` }}
    >
      {[
        { v: false, l: 'Doc Archivé' },
        { v: true, l: 'Doc Actif' },
      ].map((o) => {
        const active = value === o.v
        return (
          <button
            key={String(o.v)}
            type="button"
            onClick={() => onChange(o.v)}
            className="px-4 py-1.5 text-sm"
            style={{
              backgroundColor: active ? COL_PRIMARY : 'white',
              color: active ? 'white' : COL_BRUN,
              fontWeight: active ? 600 : 400,
            }}
          >
            {o.l}
          </button>
        )
      })}
    </div>
  )
}
