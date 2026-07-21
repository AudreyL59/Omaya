// Page principale du module Dialogues (chat + workflow ticket).
// Partagee entre les intranets Vendeur et ADM via factory props
// (apiBase, getToken, userCial).
//
// Layout : 2 colonnes
//   - Gauche : liste dialogues + tabs (a traiter / clos) + bouton "Nouveau"
//   - Droite : conversation du dialogue selectionne (bulles + zone de saisie)
//
// Notif nouveau message : polling toutes les 30s + Notification API
// browser (voir useDialoguesNotif dans un fichier separe si besoin d'usage
// global depuis la sidebar).

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowLeft, CheckCheck, Lock, Paperclip, Plus, Search, Send, Smile, Trash2,
} from 'lucide-react'
import EmojiPicker from 'emoji-picker-react'
import type { EmojiClickData } from 'emoji-picker-react'

import { showConfirm, showToast } from '../ui/dialog'
import {
  deleteMessage, fetchListeJson, fetchStatuts, marquerLu, registerPJ,
  sendMessage, uploadFichier,
} from './api'
import { PjInline } from './PjInline'
import type {
  Dialogue, DialogueMsg, DialoguePageProps, DialoguePJ, DialogueStatut,
} from './types'

const decodeContent = (m: DialogueMsg): string => {
  if (m.MsgSuppr) return m.Contenu || m.ContenuUni || ''
  if (m.ContenuUni) return m.ContenuUni
  if (m.Contenu && m.Contenu !== 'JSON') {
    try { return decodeURIComponent(m.Contenu) } catch { return m.Contenu }
  }
  return ''
}

const fmtDateHeure = (raw: string): string => {
  if (!raw) return ''
  const clean = raw.replace(/[^0-9]/g, '')
  if (clean.length < 12) return raw
  const y = clean.slice(0, 4), mo = clean.slice(4, 6), d = clean.slice(6, 8)
  const h = clean.slice(8, 10), mi = clean.slice(10, 12)
  const dt = new Date(+y, +mo - 1, +d, +h, +mi)
  const jours = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam']
  const mois = ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Juin',
                'Juil', 'Aou', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${jours[dt.getDay()]} ${dt.getDate().toString().padStart(2, '0')} ` +
         `${mois[dt.getMonth()]} ${dt.getFullYear()}, ${h}:${mi}`
}

// WinDev stocke les couleurs en integer format COLORREF (R + G*256 + B*65536).
// Conversion vers CSS hex #RRGGBB. 0 = pas de couleur -> default gris.
const wdColorToCss = (n: number): string => {
  if (!n) return '#9ca3af'  // gray-400
  const r = n & 0xff
  const g = (n >> 8) & 0xff
  const b = (n >> 16) & 0xff
  const h = (v: number) => v.toString(16).padStart(2, '0')
  return `#${h(r)}${h(g)}${h(b)}`
}

const dateHeureSys = (): string => {
  const n = new Date()
  const pad = (v: number, w = 2) => v.toString().padStart(w, '0')
  return `${n.getFullYear()}${pad(n.getMonth() + 1)}${pad(n.getDate())}` +
         `${pad(n.getHours())}${pad(n.getMinutes())}${pad(n.getSeconds())}` +
         `${pad(n.getMilliseconds(), 3)}`
}

// ---------------------------------------------------------------------------
//  Composant principal
// ---------------------------------------------------------------------------

export default function DialoguesPage(props: DialoguePageProps) {
  const { apiBase, getToken, userCial } = props
  const ctx = useMemo(() => ({ apiBase, getToken }), [apiBase, getToken])

  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<0 | 1>(0)  // 0=actifs, 1=clos
  const [dialogues, setDialogues] = useState<Dialogue[]>([])
  const [statuts, setStatuts] = useState<DialogueStatut[]>([])
  const [idOuvert, setIdOuvert] = useState<string>('')
  const [msgTexte, setMsgTexte] = useState('')
  const [pjs, setPjs] = useState<DialoguePJ[]>([])  // PJs attachees pour ce message
  const [showEmoji, setShowEmoji] = useState(false)
  const [search, setSearch] = useState('')

  const inputRef = useRef<HTMLTextAreaElement>(null)
  const scrollBottomRef = useRef<HTMLDivElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const dialogueOuvert = useMemo(
    () => dialogues.find(d => d.IDDialogue === idOuvert),
    [dialogues, idOuvert],
  )

  // -- Chargement liste ---------------------------------------------------

  const chargerListe = useCallback(async () => {
    setLoading(true)
    const r = await fetchListeJson(ctx, tab, userCial)
    setDialogues(Array.isArray(r) ? r : [])
    setLoading(false)
  }, [ctx, tab, userCial])

  useEffect(() => { chargerListe() }, [chargerListe])

  // Charge le referentiel des statuts une fois au montage
  useEffect(() => {
    void fetchStatuts(ctx).then(r => { if (Array.isArray(r)) setStatuts(r) })
  }, [ctx])

  const couleurParStatut = useMemo(() => {
    const m = new Map<number, string>()
    for (const s of statuts) m.set(s.IdStatut, wdColorToCss(s.CouleurStatut))
    return m
  }, [statuts])

  // Polling notif : toutes les 30s, recharge la liste et affiche une
  // Notification API browser si un nouveau MsgNonLu apparait.
  const knownIds = useRef<Set<string>>(new Set())
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().catch(() => { /* ignore */ })
    }
    const tick = async () => {
      const r = await fetchListeJson(ctx, tab, userCial)
      if (!Array.isArray(r)) return
      const newUnread = r.filter(d => d.MsgNonLu && !knownIds.current.has(d.IDDialogue))
      for (const d of newUnread) {
        knownIds.current.add(d.IDDialogue)
        if ('Notification' in window && Notification.permission === 'granted') {
          try {
            new Notification(`Nouveau message : ${d.Sujet || '(sans sujet)'}`, {
              body: d.Echanges?.slice(-1)[0]?.ContenuUni?.slice(0, 100) || '',
              tag: `dialogue-${d.IDDialogue}`,
            })
          } catch { /* ignore */ }
        }
      }
      setDialogues(r)
    }
    // Peuple knownIds au 1er tick sans notif (evite de notifier a l'ouverture)
    knownIds.current = new Set(dialogues.filter(d => d.MsgNonLu).map(d => d.IDDialogue))
    const iv = setInterval(tick, 30_000)
    return () => clearInterval(iv)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ctx, tab, userCial])

  // Auto-scroll vers le bas quand un dialogue s'ouvre ou un msg arrive
  useEffect(() => {
    scrollBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [idOuvert, dialogueOuvert?.Echanges?.length])

  // -- Ouverture dialogue -------------------------------------------------

  const ouvrir = async (d: Dialogue) => {
    setIdOuvert(d.IDDialogue)
    setMsgTexte('')
    setPjs([])
    setShowEmoji(false)
    if (d.MsgNonLu) {
      await marquerLu(ctx, d.IDDialogue, userCial)
      // Optimistic : marque MsgNonLu=false dans la liste locale
      setDialogues(prev => prev.map(x =>
        x.IDDialogue === d.IDDialogue ? { ...x, MsgNonLu: false } : x))
    }
  }

  // -- Emoji picker -------------------------------------------------------

  const onEmoji = (e: EmojiClickData) => {
    const emoji = e.emoji
    setMsgTexte(t => t + emoji)
    setShowEmoji(false)
    setTimeout(() => inputRef.current?.focus(), 0)
  }

  // -- Upload fichier -----------------------------------------------------

  const onPickFile = () => fileRef.current?.click()

  const onFileChosen = async (files: FileList | null) => {
    if (!files || !files.length || !dialogueOuvert) return
    for (const f of Array.from(files)) {
      const up = await uploadFichier(ctx, dialogueOuvert.IDDialogue, f, f.name)
      if (!up || !up.ResEnvoi) {
        showToast(`Upload échoué : ${f.name}`, 'error')
        continue
      }
      const pj = await registerPJ(ctx, {
        IDPJ: '0',
        IDDialogue: dialogueOuvert.IDDialogue,
        Expediteur: userCial,
        NomFic: up.fileName,
      })
      if (pj) setPjs(prev => [...prev, pj])
    }
    if (fileRef.current) fileRef.current.value = ''
  }

  // -- Envoi message ------------------------------------------------------

  const envoyer = async () => {
    if (!dialogueOuvert) return
    const texte = msgTexte.trim()
    if (!texte && pjs.length === 0) {
      showToast('Saisir un message', 'info')
      return
    }
    const contenu = texte || (pjs.length ? `Ajout de ${pjs.length} PJ(s)` : '')
    const r = await sendMessage(ctx, {
      IDMessage: '0',
      IDDialogue: dialogueOuvert.IDDialogue,
      ContenuUni: contenu,
      Contenu: 'JSON',
      DateHeureCreation: dateHeureSys(),
      Expediteur: userCial,
      NomExp: '',
      MsgSuppr: false,
      mesPJs: pjs.map(p => ({
        IDPJ: p.IDPJ,
        IDDialogue: dialogueOuvert.IDDialogue,
        Expediteur: userCial,
        NomFic: p.NomFic,
        DateHeureCreation: dateHeureSys(),
        NomExp: '',
      })),
    })
    if (!r || !r.IDMessage || r.IDMessage === '0') {
      showToast('Échec envoi', 'error')
      return
    }
    // Optimistic update : append au dialogue local
    setDialogues(prev => prev.map(d =>
      d.IDDialogue === dialogueOuvert.IDDialogue
        ? { ...d, Echanges: [...(d.Echanges || []), r] }
        : d))
    setMsgTexte('')
    setPjs([])
  }

  // -- Suppression message ------------------------------------------------

  const supprimerMsg = async (m: DialogueMsg) => {
    if (!dialogueOuvert) return
    const ok = await showConfirm({
      title: 'Supprimer ce message ?',
      message: 'Cette action est definitive.',
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    const r = await deleteMessage(ctx, {
      IDMessage: m.IDMessage,
      IDDialogue: dialogueOuvert.IDDialogue,
    })
    if (!r) return
    setDialogues(prev => prev.map(d =>
      d.IDDialogue === dialogueOuvert.IDDialogue
        ? {
            ...d,
            Echanges: d.Echanges.map(x =>
              x.IDMessage === m.IDMessage
                ? { ...x, MsgSuppr: true, ContenuUni: r.ContenuUni, Contenu: r.Contenu }
                : x),
          }
        : d))
  }

  // -- Rendu --------------------------------------------------------------

  const dialoguesAffiches = useMemo(() => {
    const s = search.trim().toUpperCase()
    if (!s) return dialogues
    return dialogues.filter(d =>
      (d.Sujet || '').toUpperCase().includes(s) ||
      d.Dests?.some(x => (x.LibDest || '').toUpperCase().includes(s)))
  }, [dialogues, search])

  return (
    <div className="flex h-full min-h-0 gap-3 p-3">
      {/* Liste gauche */}
      <aside className="w-96 flex flex-col bg-white border border-c-line-soft rounded overflow-hidden">
        <div className="p-3 border-b border-c-line-soft space-y-2">
          <div className="flex gap-2">
            <button
              className={`flex-1 px-3 py-1.5 text-sm rounded font-semibold ${
                tab === 0 ? 'bg-c-brand text-white' : 'bg-gray-100 text-c-ink-soft'}`}
              onClick={() => setTab(0)}>À traiter</button>
            <button
              className={`flex-1 px-3 py-1.5 text-sm rounded font-semibold ${
                tab === 1 ? 'bg-c-brand text-white' : 'bg-gray-100 text-c-ink-soft'}`}
              onClick={() => setTab(1)}>Clos</button>
          </div>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-2 top-2.5 text-c-ink-soft" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Rechercher..."
              className="w-full pl-8 pr-2 py-1.5 text-sm border border-c-line rounded bg-white" />
          </div>
          <button
            onClick={() => showToast('TODO: Nouveau dialogue (à venir)', 'info')}
            className="w-full flex items-center justify-center gap-1 px-3 py-2 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
            <Plus className="w-4 h-4" /> Nouveau dialogue
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="p-4 text-sm text-c-ink-soft text-center">Chargement…</div>
          )}
          {!loading && dialoguesAffiches.length === 0 && (
            <div className="p-4 text-sm text-c-ink-faint text-center italic">
              Aucun dialogue
            </div>
          )}
          {dialoguesAffiches.map(d => {
            const lastMsg = d.Echanges?.slice(-1)[0]
            const preview = lastMsg ? decodeContent(lastMsg).slice(0, 60) : ''
            const couleur = couleurParStatut.get(d.IdStatut) || '#9ca3af'
            return (
              <button key={d.IDDialogue} onClick={() => ouvrir(d)}
                className={`w-full text-left px-3 py-2 border-b border-c-line-soft hover:bg-c-brand-soft relative ${
                  idOuvert === d.IDDialogue ? 'bg-c-brand-soft' : ''}`}
                style={{ borderLeft: `4px solid ${couleur}` }}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className={`text-sm truncate flex items-center gap-1 ${
                      d.MsgNonLu ? 'font-bold text-c-brand' : 'font-medium'}`}>
                      {d.IsPrive && (
                        <Lock className="w-3 h-3 shrink-0 text-c-ink-soft"
                              aria-label="Dialogue privé" />
                      )}
                      <span className="truncate">{d.Sujet || '(sans sujet)'}</span>
                    </div>
                    <div className="text-xs text-c-ink-soft truncate">{preview}</div>
                    <div className="text-[10px] text-c-ink-faint mt-0.5">
                      {d.LibTheme}
                      {d.Dests?.length > 0 && ` · ${d.Dests[0].LibDest}`}
                      {d.Dests?.length > 1 && ` +${d.Dests.length - 1}`}
                    </div>
                  </div>
                  {d.MsgNonLu && (
                    <span className="w-2 h-2 rounded-full bg-red-600 mt-1.5 shrink-0" />
                  )}
                </div>
              </button>
            )
          })}
        </div>
      </aside>

      {/* Chat droite */}
      <main className="flex-1 flex flex-col bg-white border border-c-line-soft rounded overflow-hidden">
        {!dialogueOuvert && (
          <div className="flex-1 flex items-center justify-center text-c-ink-faint italic">
            Sélectionne un dialogue à gauche
          </div>
        )}
        {dialogueOuvert && (
          <>
            <header className="p-3 border-b border-c-line-soft flex items-center gap-2">
              <button onClick={() => setIdOuvert('')}
                className="lg:hidden p-1 hover:bg-gray-100 rounded">
                <ArrowLeft className="w-4 h-4" />
              </button>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-sm truncate">
                  {dialogueOuvert.Sujet || '(sans sujet)'}
                </div>
                <div className="text-xs text-c-ink-soft truncate">
                  {dialogueOuvert.LibTheme} ·{' '}
                  {dialogueOuvert.Dests?.map(x => x.LibDest).filter(Boolean).join(', ')}
                </div>
              </div>
            </header>

            <div className="flex-1 overflow-y-auto p-3 space-y-2 bg-gray-50">
              {dialogueOuvert.Echanges?.map(m => {
                const mine = m.Expediteur === userCial
                return (
                  <div key={m.IDMessage}
                    className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[75%] group relative ${
                      mine ? 'bg-blue-100' : 'bg-white'} border border-c-line-soft rounded-lg p-2`}>
                      {!mine && (
                        <div className="text-[10px] text-c-brand font-semibold mb-0.5">
                          {m.NomExp || `#${m.Expediteur}`}
                        </div>
                      )}
                      <div className={`text-sm whitespace-pre-wrap ${
                        m.MsgSuppr ? 'italic text-c-ink-faint' : ''}`}>
                        {decodeContent(m)}
                      </div>
                      {/* PJs regroupees dans ce msg */}
                      {m.mesPJs?.length > 0 && (
                        <div className="mt-1 space-y-1">
                          {m.mesPJs.map(pj => (
                            <PjInline key={pj.IDPJ} pj={pj} ctx={ctx}
                              idDialogue={dialogueOuvert.IDDialogue} />
                          ))}
                        </div>
                      )}
                      <div className="text-[10px] text-c-ink-faint mt-1 flex items-center gap-1">
                        {fmtDateHeure(m.DateHeureCreation)}
                        {mine && <CheckCheck className="w-3 h-3" />}
                      </div>
                      {mine && !m.MsgSuppr && (
                        <button onClick={() => supprimerMsg(m)}
                          className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-100 rounded">
                          <Trash2 className="w-3 h-3 text-red-600" />
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
              <div ref={scrollBottomRef} />
            </div>

            {/* Zone de saisie */}
            <div className="border-t border-c-line-soft bg-white p-2">
              {pjs.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {pjs.map(pj => (
                    <span key={pj.IDPJ}
                      className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-blue-50 border border-blue-200 rounded">
                      <Paperclip className="w-3 h-3" />{pj.NomFic}
                      <button onClick={() => setPjs(prev => prev.filter(x => x.IDPJ !== pj.IDPJ))}
                        className="text-red-600 hover:underline">×</button>
                    </span>
                  ))}
                </div>
              )}
              <div className="flex items-end gap-1 relative">
                <button onClick={() => setShowEmoji(v => !v)}
                  className="p-2 rounded hover:bg-gray-100 text-c-ink-soft"
                  title="Emoji">
                  <Smile className="w-5 h-5" />
                </button>
                <button onClick={onPickFile}
                  className="p-2 rounded hover:bg-gray-100 text-c-ink-soft"
                  title="Joindre un fichier">
                  <Paperclip className="w-5 h-5" />
                </button>
                <input ref={fileRef} type="file" multiple hidden
                  onChange={e => onFileChosen(e.target.files)} />
                <textarea ref={inputRef} value={msgTexte}
                  onChange={e => setMsgTexte(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault(); envoyer()
                    }
                  }}
                  placeholder="Rédige un message... (Entrée pour envoyer, Maj+Entrée pour nouvelle ligne)"
                  rows={1}
                  className="flex-1 resize-none border border-c-line rounded px-3 py-2 text-sm max-h-32 focus:border-c-brand focus:ring-1 focus:ring-c-brand focus:outline-none" />
                <button onClick={envoyer}
                  className="px-4 py-2 rounded bg-c-brand text-white text-sm font-semibold hover:brightness-110 flex items-center gap-1">
                  <Send className="w-4 h-4" />
                </button>
                {showEmoji && (
                  <div className="absolute bottom-12 left-0 z-50 shadow-xl">
                    <EmojiPicker onEmojiClick={onEmoji} width={320} height={380} />
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}

