/**
 * SendEmailModal : popup partagee d'envoi d'email (transposition Fen_EnvoieEmail).
 *
 * Composant utilisable depuis n'importe quel intranet :
 *   <SendEmailModal
 *     open={open}
 *     onClose={() => setOpen(false)}
 *     getToken={getToken}
 *     to={['x@y.fr']}
 *     subject="Sujet"
 *     html="<p>Bonjour</p>"
 *   />
 *
 * Envoi via POST /api/shared/email/send. SMTP par defaut = Gmail RH.
 * Pour utiliser le SMTP OVH FPE, passer expediteur="fpe@exosphere.fr".
 *
 * Editeur HTML : contentEditable + petit toolbar (gras / italique / souligne /
 * lien) via document.execCommand (deprecated mais largement supporte, OK MVP).
 *
 * Bouton "Annuaire" : placeholder en attendant la transposition de
 * Fen_Annuaire (autre fenetre partagee WinDev).
 */

import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Bold,
  BookUser,
  Italic,
  Link as LinkIcon,
  Loader2,
  Paperclip,
  Send,
  Underline,
  X,
} from 'lucide-react'
import { showToast } from '../ui/dialog'

interface AttachmentItem {
  name: string
  size: number
  contentB64: string
}

interface SendEmailModalProps {
  open: boolean
  onClose: () => void
  getToken: () => string | null
  /** Pre-remplissages */
  to?: string[]
  cc?: string[]
  cci?: string[]
  subject?: string
  html?: string
  /** Expediteur. 'fpe@exosphere.fr' -> SMTP OVH FPE, sinon Gmail RH (defaut). */
  expediteur?: string
  /** Appele en cas d'envoi reussi (apres fermeture de la modal). */
  onSent?: () => void
}

export default function SendEmailModal({
  open,
  onClose,
  getToken,
  to = [],
  cc = [],
  cci = [],
  subject = '',
  html = '',
  expediteur,
  onSent,
}: SendEmailModalProps) {
  const [toStr, setToStr] = useState('')
  const [ccStr, setCcStr] = useState('')
  const [cciStr, setCciStr] = useState('')
  const [sujet, setSujet] = useState('')
  const [pjList, setPjList] = useState<AttachmentItem[]>([])
  const [sending, setSending] = useState(false)
  const editorRef = useRef<HTMLDivElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  // Reinitialisation a chaque ouverture
  useEffect(() => {
    if (!open) return
    setToStr(to.join(', '))
    setCcStr(cc.join(', '))
    setCciStr(cci.join(', '))
    setSujet(subject)
    setPjList([])
    if (editorRef.current) editorRef.current.innerHTML = html || ''
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  if (!open) return null

  const exec = (cmd: string, value?: string) => {
    // document.execCommand est deprecated mais largement supporte
    // (pas de meilleur fallback sans library externe pour le MVP).
    document.execCommand(cmd, false, value)
    editorRef.current?.focus()
  }

  const handleInsertLink = () => {
    const url = window.prompt('URL du lien :', 'https://')
    if (url) exec('createLink', url)
  }

  const handleAddPJ = () => fileInputRef.current?.click()

  const handlePJChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    const tasks = Array.from(files).map(
      (f) =>
        new Promise<AttachmentItem>((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => {
            // Extrait la base64 du data URI 'data:...;base64,XXXX'
            const result = reader.result as string
            const b64 = result.includes(',') ? result.split(',', 2)[1] : result
            resolve({ name: f.name, size: f.size, contentB64: b64 })
          }
          reader.onerror = () => reject(reader.error)
          reader.readAsDataURL(f)
        }),
    )
    Promise.all(tasks)
      .then((items) => setPjList((prev) => [...prev, ...items]))
      .catch(() => showToast("Echec de lecture de la piece jointe", 'error'))
    // Reset pour permettre re-ajout du meme fichier
    e.target.value = ''
  }

  const handleRemovePJ = (i: number) =>
    setPjList((prev) => prev.filter((_, idx) => idx !== i))

  const splitAddresses = (s: string): string[] =>
    s
      .split(/[,;\s]+/)
      .map((x) => x.trim())
      .filter(Boolean)

  const handleSend = async () => {
    const toArr = splitAddresses(toStr)
    if (toArr.length === 0) {
      showToast('Au moins un destinataire est requis.', 'error')
      return
    }
    const ccArr = splitAddresses(ccStr)
    const cciArr = splitAddresses(cciStr)
    const htmlContent = editorRef.current?.innerHTML || ''

    setSending(true)
    try {
      const r = await fetch('/api/shared/email/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          to: toArr,
          cc: ccArr,
          cci: cciArr,
          sujet: sujet,
          html: htmlContent,
          expediteur: expediteur || null,
          attachments: pjList.map((p) => ({ name: p.name, content_b64: p.contentB64 })),
        }),
      })
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        showToast(`Echec : ${(j as { detail?: string })?.detail || r.status}`, 'error')
        return
      }
      showToast('Mail envoyé', 'success')
      onSent?.()
      onClose()
    } catch {
      showToast('Erreur réseau (envoi mail).', 'error')
    } finally {
      setSending(false)
    }
  }

  const handleAnnuaire = () => {
    // TODO : transposition Fen_Annuaire (autre fenetre partagee WinDev)
    showToast('Annuaire : à brancher', 'info')
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-[#E5DDDC]">
          <div className="flex items-center gap-2">
            <Send className="w-4 h-4 text-[#17494E]" />
            <h2 className="text-base font-semibold text-[#4E1D17]">Envoi Email</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleAnnuaire}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded border border-[#E5DDDC] hover:bg-[#ECF1F2] text-[#4E1D17]"
            >
              <BookUser className="w-3.5 h-3.5" />
              Annuaire
            </button>
            <button
              type="button"
              onClick={handleSend}
              disabled={sending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded text-white hover:opacity-90 disabled:opacity-50"
              style={{ backgroundColor: '#17494E' }}
            >
              {sending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
              Envoyer
            </button>
            <button
              onClick={onClose}
              className="p-1 rounded hover:bg-[#EFE9E7] text-[#A68D8A]/80 hover:text-[#4E1D17]"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3 text-sm">
          <FieldRow label="À" value={toStr} onChange={setToStr} placeholder="email1@x.fr, email2@y.fr" />
          <FieldRow label="CC" value={ccStr} onChange={setCcStr} />
          <FieldRow label="CCI" value={cciStr} onChange={setCciStr} />
          <FieldRow label="Objet" value={sujet} onChange={setSujet} />

          {/* Toolbar editeur */}
          <div className="flex items-center gap-1 border-b border-[#E5DDDC] pb-2">
            <ToolbarBtn onClick={() => exec('bold')} title="Gras"><Bold className="w-4 h-4" /></ToolbarBtn>
            <ToolbarBtn onClick={() => exec('italic')} title="Italique"><Italic className="w-4 h-4" /></ToolbarBtn>
            <ToolbarBtn onClick={() => exec('underline')} title="Souligne"><Underline className="w-4 h-4" /></ToolbarBtn>
            <ToolbarBtn onClick={handleInsertLink} title="Lien"><LinkIcon className="w-4 h-4" /></ToolbarBtn>
          </div>

          {/* Editeur contentEditable */}
          <div
            ref={editorRef}
            contentEditable
            suppressContentEditableWarning
            className="min-h-[200px] p-3 rounded border border-[#E5DDDC] text-sm leading-relaxed focus:outline-none focus:ring-1 focus:ring-[#17494E]"
            style={{ color: '#4E1D17' }}
          />

          {/* Pieces jointes */}
          <div className="pt-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-[#4E1D17]">Pièces jointes</span>
              <button
                type="button"
                onClick={handleAddPJ}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded border border-[#E5DDDC] hover:bg-[#ECF1F2] text-[#4E1D17]"
              >
                <Paperclip className="w-3.5 h-3.5" />
                Ajouter un fichier
              </button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={handlePJChange}
              />
            </div>
            {pjList.length === 0 ? (
              <div className="text-xs text-[#A68D8A] italic py-2">Aucune pièce jointe.</div>
            ) : (
              <ul className="space-y-1">
                {pjList.map((p, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between px-2 py-1.5 rounded bg-[#EFE9E7] text-xs text-[#4E1D17]"
                  >
                    <span className="truncate">
                      <Paperclip className="w-3 h-3 inline mr-1" />
                      {p.name} <span className="text-[#A68D8A]">({Math.round(p.size / 1024)} KB)</span>
                    </span>
                    <button
                      type="button"
                      onClick={() => handleRemovePJ(i)}
                      className="p-0.5 hover:text-red-600"
                      title="Retirer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

// --- Helpers UI ---------------------------------------------------------

function FieldRow({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <div className="grid grid-cols-[60px_1fr] gap-2 items-center">
      <span className="text-xs font-medium text-[#4E1D17]">{label}</span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="min-w-0 w-full px-2 py-1 rounded border border-[#E5DDDC] text-sm focus:outline-none focus:ring-1 focus:ring-[#17494E]"
        style={{ color: '#4E1D17' }}
      />
    </div>
  )
}

function ToolbarBtn({
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
      title={title}
      className="p-1.5 rounded hover:bg-[#ECF1F2] text-[#4E1D17]"
    >
      {children}
    </button>
  )
}
