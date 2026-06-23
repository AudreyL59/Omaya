/**
 * Fen_EditionDocUlease (transposition WinDev) - edition d'un doc Ulease.
 *
 * Clonee de DocRHEditModal :
 *  - Metadonnees + editeur WYSIWYG contentEditable + import/export DOCX.
 *  - Btn 'Tester Mise en page' substitue les variables (S_NOM, STE_RS, etc.)
 *    avec des donnees fictives + une societe + un salarie + un vehicule
 *    optionnel choisis -> ouvre le PDF publiposte dans un nouvel onglet.
 *  - Differences vs DocRH :
 *    * Pas de id_type_produit / pas de doc_dpae / pas de tk_type_photo_dpae.
 *    * Checkbox "prioritaire" affichee en "Favori".
 *    * Combo "Avec vehicule" en plus du combo "Test avec : <salarie>".
 *    * Variables vehicule supplementaires : AUTO_IMMA, AUTO_TYPE, AUTO_CV,
 *      AUTO_KM, DATE_DEB, DATE_FIN.
 */

import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  AlignCenter,
  AlignJustify,
  AlignLeft,
  AlignRight,
  Bold,
  Download,
  Eye,
  FileText,
  Italic,
  List,
  ListOrdered,
  Loader2,
  RotateCcw,
  Save,
  Search as SearchIcon,
  Table as TableIcon,
  Underline as UnderlineIcon,
  Upload,
  X,
} from 'lucide-react'

import { getToken } from '@/api'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { showConfirm, showPrompt, showToast } from '@shared/ui/dialog'
import TableContextMenu from '@shared/ui/TableContextMenu'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface Lookups {
  types_doc: { id_type_doc: string; lib: string }[]
  societes: {
    id_ste: string
    raison_sociale: string
    rs_interne: string
  }[]
  salaries: { id_salarie: string; lib: string }[]
}

interface VehiculeAttribution {
  id_vehicule_pc: string
  lib: string
}

interface DocMeta {
  id_doc_ulease: string
  id_type_doc: string
  titre: string
  info_cpl: string
  doc_actif: boolean
  prioritaire: boolean
  id_ste: string
  taille_contenu: number
}

interface Props {
  idDocUlease: string  // '' pour creation
  onClose: () => void
  onSaved: () => void
}

const EMPTY: DocMeta = {
  id_doc_ulease: '',
  id_type_doc: '',
  titre: '',
  info_cpl: '',
  doc_actif: true,
  prioritaire: false,
  id_ste: '0',
  taille_contenu: 0,
}

export default function DocUleaseEditModal({
  idDocUlease: initialId,
  onClose,
  onSaved,
}: Props) {
  const [docId, setDocId] = useState(initialId)
  const [meta, setMeta] = useState<DocMeta>(EMPTY)
  useDocumentTitle(meta.titre ? `Doc Ulease — ${meta.titre}` : 'Doc Ulease')
  // Detection des modifications non sauvegardees (champs meta + contenu HTML).
  const [isDirty, setIsDirty] = useState(false)
  const [lookups, setLookups] = useState<Lookups | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [steTest, setSteTest] = useState('')
  const [idSalarieTest, setIdSalarieTest] = useState('')
  const [salarieTestLib, setSalarieTestLib] = useState('')
  const [pickerOpen, setPickerOpen] = useState(false)
  const [idVehiculePc, setIdVehiculePc] = useState('')
  const [vehiculesAttrib, setVehiculesAttrib] = useState<VehiculeAttribution[]>([])
  const [testing, setTesting] = useState(false)
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState<string | null>(null)
  const editorRef = useRef<HTMLDivElement | null>(null)
  // Memorise la selection courante avant qu'un controle de la toolbar
  // (color picker natif, combo) ne fasse perdre le focus du contentEditable.
  const savedRange = useRef<Range | null>(null)
  const memorizeSelection = () => {
    const sel = window.getSelection()
    if (sel && sel.rangeCount > 0) {
      savedRange.current = sel.getRangeAt(0).cloneRange()
    }
  }

  // ---- Synchronisation toolbar -> selection courante -------------------
  // Quand la selection change dans l'editeur, met a jour les controles
  // (Police, Taille, Couleur) pour refleter le style du texte selectionne.
  const [currentFont, setCurrentFont] = useState('')
  const [currentSize, setCurrentSize] = useState('')
  const [currentColor, setCurrentColor] = useState('#000000')
  const [currentLineHeight, setCurrentLineHeight] = useState('')

  // Trouve le bloc englobant (p/div/h1-6/li/blockquote/pre) le plus proche.
  const findBlockAncestor = (node: Node | null): HTMLElement | null => {
    if (!node) return null
    let el: HTMLElement | null =
      node.nodeType === Node.TEXT_NODE
        ? node.parentElement
        : (node as HTMLElement)
    const BLOCK_TAGS = new Set([
      'p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'blockquote', 'pre', 'td', 'th',
    ])
    while (el && editorRef.current?.contains(el)) {
      if (BLOCK_TAGS.has(el.tagName.toLowerCase())) return el
      el = el.parentElement
    }
    return null
  }

  // Applique line-height a tous les blocs touches par la selection.
  const applyLineHeight = (lh: string) => {
    if (!editorRef.current) return
    const sel = window.getSelection()
    let range: Range | null = null
    if (sel && sel.rangeCount > 0) range = sel.getRangeAt(0)
    else if (savedRange.current) range = savedRange.current
    if (!range) {
      editorRef.current.focus()
      return
    }
    const startBlock = findBlockAncestor(range.startContainer)
    const endBlock = findBlockAncestor(range.endContainer)
    const blocks = new Set<HTMLElement>()
    if (startBlock) blocks.add(startBlock)
    if (endBlock) blocks.add(endBlock)
    // Si selection couvre plusieurs blocs : ajouter ceux entre start et end
    if (startBlock && endBlock && startBlock !== endBlock) {
      const walker = document.createTreeWalker(
        editorRef.current,
        NodeFilter.SHOW_ELEMENT,
      )
      let inRange = false
      let node: Node | null = walker.currentNode
      while (node) {
        if (node === startBlock) inRange = true
        if (inRange && node instanceof HTMLElement) {
          const t = node.tagName.toLowerCase()
          if (['p','div','li','h1','h2','h3','h4','h5','h6','blockquote','pre','td','th'].includes(t)) {
            blocks.add(node)
          }
        }
        if (node === endBlock) break
        node = walker.nextNode()
      }
    }
    blocks.forEach((b) => (b.style.lineHeight = lh))
    editorRef.current.focus()
    setCurrentLineHeight(lh)
    setIsDirty(true)
  }

  useEffect(() => {
    const rgbToHex = (rgb: string): string => {
      const m = rgb.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
      if (!m) return '#000000'
      const [, r, g, b] = m
      return (
        '#' +
        [r, g, b]
          .map((x) => parseInt(x, 10).toString(16).padStart(2, '0'))
          .join('')
      )
    }
    const findFontOption = (ff: string): string => {
      // ff = '"Calibri", "Segoe UI", sans-serif' ou 'Calibri, Segoe UI, ...'
      const first = ff.split(',')[0].replace(/['"]/g, '').trim().toLowerCase()
      for (const opt of FONT_OPTIONS) {
        const optFirst = opt.value.split(',')[0]
          .replace(/['"]/g, '').trim().toLowerCase()
        if (optFirst === first) return opt.value
      }
      return ''
    }
    const handler = () => {
      const sel = window.getSelection()
      if (!sel || sel.rangeCount === 0) return
      const node = sel.anchorNode
      if (!node || !editorRef.current?.contains(node)) return
      // Memorise la range courante : utilise par exec() comme fallback
      // si l'editeur perd le focus (clic sur un bouton de la toolbar).
      savedRange.current = sel.getRangeAt(0).cloneRange()
      const el =
        node.nodeType === 3
          ? (node.parentElement as HTMLElement | null)
          : (node as HTMLElement)
      if (!el) return
      const cs = window.getComputedStyle(el)
      setCurrentFont(findFontOption(cs.fontFamily))
      const fsPx = parseFloat(cs.fontSize)
      if (fsPx) setCurrentSize(`${Math.round(fsPx / 1.333)}pt`)
      setCurrentColor(rgbToHex(cs.color))
      // Interligne : lit le line-height du bloc parent
      const block = findBlockAncestor(node)
      if (block) {
        const blockCs = window.getComputedStyle(block)
        const lh = blockCs.lineHeight
        const fs = parseFloat(blockCs.fontSize)
        let lhVal = ''
        if (lh && lh !== 'normal' && fs) {
          const ratio = parseFloat(lh) / fs
          // Match contre les options disponibles
          for (const opt of LINE_HEIGHT_OPTIONS) {
            if (Math.abs(parseFloat(opt) - ratio) < 0.05) {
              lhVal = opt
              break
            }
          }
        }
        setCurrentLineHeight(lhVal)
      }
    }
    document.addEventListener('selectionchange', handler)
    return () => document.removeEventListener('selectionchange', handler)
  }, [])
  const [editorReady, setEditorReady] = useState(false)
  // HTML a injecter dans l'editeur une fois qu'il est rendu (sinon
  // editorRef.current est null pendant le useEffect d'init).
  const [pendingHtml, setPendingHtml] = useState<string | null>(null)

  const update = (patch: Partial<DocMeta>) => {
    setMeta((m) => ({ ...m, ...patch }))
    setIsDirty(true)
  }

  // ---- Init -------------------------------------------------------------
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const lk = await fetch('/api/adm/ctt-ulease/lookups', {
          headers: { Authorization: `Bearer ${getToken()}` },
        }).then((r) => r.json())
        if (cancelled) return
        setLookups(lk as Lookups)

        let id = initialId
        if (!id) {
          const created = await fetch('/api/adm/ctt-ulease/new', {
            method: 'POST',
            headers: { Authorization: `Bearer ${getToken()}` },
          }).then((r) => r.json())
          id = created.id_doc_ulease
          setDocId(id)
        }
        const m = await fetch(`/api/adm/ctt-ulease/${id}`, {
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

  // ---- Chargement des vehicules attribues au salarie test ---------------
  useEffect(() => {
    let cancelled = false
    if (!idSalarieTest) {
      setVehiculesAttrib([])
      setIdVehiculePc('')
      return
    }
    ;(async () => {
      try {
        const r = await fetch(
          `/api/adm/ctt-ulease/salaries/${idSalarieTest}/attributions`,
          { headers: { Authorization: `Bearer ${getToken()}` } },
        )
        if (!r.ok) {
          if (!cancelled) {
            setVehiculesAttrib([])
            setIdVehiculePc('')
          }
          return
        }
        const arr = (await r.json()) as VehiculeAttribution[]
        if (cancelled) return
        setVehiculesAttrib(arr)
        // Si l'ancien vehicule choisi n'est plus dans la liste, on reset
        if (!arr.some((v) => v.id_vehicule_pc === idVehiculePc)) {
          setIdVehiculePc('')
        }
      } catch (e) {
        if (!cancelled) {
          setVehiculesAttrib([])
          setIdVehiculePc('')
        }
        console.error('[doc-ulease] load attributions', e)
      }
    })()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idSalarieTest])

  // ---- Chargement du contenu (DOCX -> HTML via mammoth, ou HTML brut) ---
  const loadContentToEditor = async (id: string) => {
    try {
      const r = await fetch(`/api/adm/ctt-ulease/${id}/content`, {
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
      console.error('[doc-ulease] loadContent', e)
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

  // Cleanup de l'URL blob du preview PDF
  useEffect(() => {
    return () => {
      if (pdfPreviewUrl) URL.revokeObjectURL(pdfPreviewUrl)
    }
  }, [pdfPreviewUrl])

  // ---- Fermeture avec detection modifications -------------------------
  const handleClose = async () => {
    if (!isDirty) {
      onClose()
      return
    }
    const yes = await showConfirm({
      title: 'Modifications non enregistrées',
      message:
        'Vous avez des modifications non enregistrées. ' +
        'Voulez-vous les enregistrer avant de fermer ?',
      confirmLabel: 'Enregistrer et fermer',
      cancelLabel: 'Fermer sans enregistrer',
    })
    if (yes) {
      await saveMeta(true)
    }
    onClose()
  }

  // ---- Toolbar contenteditable -----------------------------------------
  // Restaure d'abord la selection memorisee (si elle est toujours dans
  // l'editeur) ou focus l'editeur, puis exec la commande. Sinon
  // execCommand est ignoree si activeElement n'est pas dans le
  // contentEditable (cas typique : on clique 'souligner' sans avoir
  // d'abord clique dans le texte).
  const exec = (cmd: string, value?: string) => {
    const ed = editorRef.current
    if (!ed) return
    if (document.activeElement !== ed) {
      const sel = window.getSelection()
      if (
        savedRange.current &&
        ed.contains(savedRange.current.commonAncestorContainer)
      ) {
        if (sel) {
          sel.removeAllRanges()
          sel.addRange(savedRange.current)
        }
      } else {
        ed.focus()
      }
    }
    document.execCommand(cmd, false, value)
    ed.focus()
  }

  // Liste a puces/numerotee : implementation custom (sans execCommand
  // qui est capricieux avec des HTML imbriques ou non-standards).
  // 1) Restaure la selection si l'editeur a perdu le focus.
  // 2) Trouve tous les blocs touches par la selection (p/div/h*/li/etc.).
  // 3) Construit un <ul>/<ol> contenant un <li> par bloc + le 'inner HTML'.
  // 4) Insere la liste avant le 1er bloc et supprime les blocs originaux.
  const insertList = (kind: 'ul' | 'ol') => {
    const ed = editorRef.current
    if (!ed) return
    // Restaure selection si necessaire
    if (document.activeElement !== ed) {
      const s = window.getSelection()
      if (
        savedRange.current &&
        ed.contains(savedRange.current.commonAncestorContainer)
      ) {
        if (s) {
          s.removeAllRanges()
          s.addRange(savedRange.current)
        }
      } else {
        ed.focus()
      }
    }
    const sel = window.getSelection()
    if (!sel || sel.rangeCount === 0) return
    const range = sel.getRangeAt(0)

    const BLOCK = new Set([
      'p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'blockquote', 'pre',
    ])
    const findBlock = (node: Node | null): HTMLElement | null => {
      let el: HTMLElement | null =
        node?.nodeType === Node.TEXT_NODE
          ? (node.parentElement as HTMLElement | null)
          : (node as HTMLElement | null)
      while (el && ed.contains(el)) {
        if (BLOCK.has(el.tagName.toLowerCase())) return el
        el = el.parentElement
      }
      return null
    }

    const startBlock = findBlock(range.startContainer)
    const endBlock = findBlock(range.endContainer)
    if (!startBlock) {
      // Pas de bloc trouve : fallback execCommand (cas vide ou texte
      // brut sans paragraphe).
      document.execCommand(
        kind === 'ul' ? 'insertUnorderedList' : 'insertOrderedList',
      )
      setIsDirty(true)
      return
    }

    // Collecte tous les blocs touches (entre startBlock et endBlock).
    const blocks: HTMLElement[] = []
    if (startBlock === endBlock || !endBlock) {
      blocks.push(startBlock)
    } else {
      const walker = document.createTreeWalker(ed, NodeFilter.SHOW_ELEMENT)
      let inRange = false
      let n: Node | null = walker.currentNode
      while (n) {
        if (n === startBlock) inRange = true
        if (inRange && n instanceof HTMLElement) {
          const t = n.tagName.toLowerCase()
          if (BLOCK.has(t)) blocks.push(n)
        }
        if (n === endBlock) break
        n = walker.nextNode()
      }
      // Filtre : on enleve les blocs dont un ancetre est deja dans la
      // liste (pour eviter de wrapper p>span>p deux fois si bizarre).
      const filtered: HTMLElement[] = []
      for (const b of blocks) {
        if (!filtered.some((p) => p.contains(b))) filtered.push(b)
      }
      blocks.splice(0, blocks.length, ...filtered)
    }
    if (blocks.length === 0) return

    // ----- Toggle off / switch kind ---------------------------------
    // Si tous les blocs collectes sont des <li> d'une meme liste :
    //   - meme tag (kind) -> on enleve la liste (transforme en <p>)
    //   - tag different    -> on switche le tag de la liste
    const allLi = blocks.every((b) => b.tagName.toLowerCase() === 'li')
    if (allLi) {
      const parentList = blocks[0].parentElement
      const parentTag = parentList?.tagName.toLowerCase() || ''
      const sameParent = blocks.every((b) => b.parentElement === parentList)
      if (sameParent && (parentTag === 'ul' || parentTag === 'ol') && parentList) {
        if (parentTag === kind) {
          // Toggle off : unwrap chaque <li> en <p>
          const fragments: HTMLElement[] = []
          blocks.forEach((li) => {
            const p = document.createElement('p')
            p.innerHTML = li.innerHTML || '&nbsp;'
            fragments.push(p)
          })
          // Insertion avant la liste, suppression des li
          fragments.forEach((p) =>
            parentList.parentNode!.insertBefore(p, parentList),
          )
          blocks.forEach((li) => li.remove())
          // Si la liste est vide -> on l'enleve
          if (parentList.children.length === 0) parentList.remove()
          // Replace le curseur sur le 1er fragment
          const newSel = window.getSelection()
          if (newSel && fragments[0]) {
            const r = document.createRange()
            r.selectNodeContents(fragments[0])
            r.collapse(false)
            newSel.removeAllRanges()
            newSel.addRange(r)
          }
          setIsDirty(true)
          ed.focus()
          return
        }
        // Switch kind : on remplace le tag de la liste entiere
        // (cas typique : user a une <ul> et clique 'liste num' ou
        // l'inverse).
        const newList = document.createElement(kind)
        newList.style.listStyle = kind === 'ul' ? 'disc' : 'decimal'
        newList.style.paddingLeft = '40px'
        newList.style.margin = '8px 0'
        while (parentList.firstChild) {
          newList.appendChild(parentList.firstChild)
        }
        parentList.parentNode!.replaceChild(newList, parentList)
        setIsDirty(true)
        ed.focus()
        return
      }
    }

    // Construit la liste. Style inline obligatoire pour overrider le
    // reset Tailwind (preflight) qui met list-style:none + padding:0.
    const list = document.createElement(kind)
    list.style.listStyle = kind === 'ul' ? 'disc' : 'decimal'
    list.style.paddingLeft = '40px'
    list.style.margin = '8px 0'
    // 1 <li> par 'ligne' : on splitte chaque bloc par <br> (mammoth
    // produit parfois un seul <p> avec des <br/> entre les lignes,
    // au lieu d'un <p> par ligne).
    blocks.forEach((b) => {
      const html = b.innerHTML || ''
      const parts = html
        .split(/<br\s*\/?>/i)
        .map((s) => s.trim())
        .filter((s) => s.length > 0)
      if (parts.length <= 1) {
        const li = document.createElement('li')
        li.innerHTML = html || '&nbsp;'
        list.appendChild(li)
      } else {
        parts.forEach((line) => {
          const li = document.createElement('li')
          li.innerHTML = line
          list.appendChild(li)
        })
      }
    })
    // Insertion : avant le 1er bloc, puis suppression des blocs sources.
    blocks[0].parentNode!.insertBefore(list, blocks[0])
    blocks.forEach((b) => b.remove())

    // Replace la selection sur le 1er <li> de la nouvelle liste.
    const newSel = window.getSelection()
    if (newSel && list.firstChild) {
      const r = document.createRange()
      r.selectNodeContents(list.firstChild)
      r.collapse(false)
      newSel.removeAllRanges()
      newSel.addRange(r)
    }
    setIsDirty(true)
    ed.focus()
  }

  // Insertion d'un tableau (HTML brut via execCommand insertHTML).
  // Une fois inseré, le user peut editer les cellules en cliquant dedans
  // (contentEditable est recursif). Bords visibles et restitues a
  // l'identique dans WeasyPrint (CSS inline).
  const insertTable = async () => {
    memorizeSelection()
    const v = await showPrompt({
      title: 'Insérer un tableau',
      message: 'Dimensions (lignes × colonnes) :',
      defaultValue: '3x3',
      placeholder: 'ex: 3x4',
      validator: (s) =>
        /^\s*\d+\s*[xX×]\s*\d+\s*$/.test(s) ? null : 'Format : NxM (ex 3x4)',
    })
    if (!v) return
    const m = v.match(/^\s*(\d+)\s*[xX×]\s*(\d+)\s*$/)
    if (!m) return
    const rows = Math.min(50, Math.max(1, parseInt(m[1], 10)))
    const cols = Math.min(20, Math.max(1, parseInt(m[2], 10)))
    let html =
      '<table style="border-collapse:collapse;border:1px solid #888;' +
      'width:100%;margin:8px 0;">'
    for (let r = 0; r < rows; r++) {
      html += '<tr>'
      for (let c = 0; c < cols; c++) {
        html += '<td style="border:1px solid #888;padding:6px;' +
          'min-width:40px;">&nbsp;</td>'
      }
      html += '</tr>'
    }
    html += '</table><p>&nbsp;</p>'

    editorRef.current?.focus()
    if (savedRange.current) {
      const sel = window.getSelection()
      if (sel) {
        sel.removeAllRanges()
        sel.addRange(savedRange.current)
      }
    }
    document.execCommand('insertHTML', false, html)
    setIsDirty(true)
  }

  // Applique font-family / font-size / color sur la selection via span style.
  // (execCommand fontSize ne supporte que 1-7 et foreColor produit du
  // <font color="..."> mal supporte par WeasyPrint.)
  // Utilise savedRange.current en fallback si la selection courante est
  // perdue (cas color picker qui vole le focus).
  const applyInlineStyle = (style: Partial<CSSStyleDeclaration>) => {
    let range: Range | null = null
    const sel = window.getSelection()
    if (sel && sel.rangeCount > 0 && !sel.isCollapsed) {
      range = sel.getRangeAt(0)
    } else if (savedRange.current && !savedRange.current.collapsed) {
      // Restaure la selection memorisee (cas color picker)
      range = savedRange.current.cloneRange()
      editorRef.current?.focus()
      const s = window.getSelection()
      s?.removeAllRanges()
      s?.addRange(range)
    }
    if (!range || range.collapsed) {
      editorRef.current?.focus()
      return
    }
    const span = document.createElement('span')
    if (style.fontFamily) span.style.fontFamily = String(style.fontFamily)
    if (style.fontSize) span.style.fontSize = String(style.fontSize)
    if (style.color) span.style.color = String(style.color)
    try {
      span.appendChild(range.extractContents())
      range.insertNode(span)
      // Re-select pour garder le visuel
      const s2 = window.getSelection()
      s2?.removeAllRanges()
      const newRange = document.createRange()
      newRange.selectNodeContents(span)
      s2?.addRange(newRange)
      // Met a jour savedRange pour les actions suivantes
      savedRange.current = newRange.cloneRange()
      setIsDirty(true)
    } catch (e) {
      console.error('[applyInlineStyle]', e)
    }
    editorRef.current?.focus()
  }

  // ---- Save -------------------------------------------------------------
  const saveMeta = async (silent = false) => {
    setSaving(true)
    try {
      // 1. Metadonnees
      const r = await fetch(`/api/adm/ctt-ulease/${docId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_type_doc: Number(meta.id_type_doc) || 0,
          titre: meta.titre,
          info_cpl: meta.info_cpl,
          id_ste: Number(meta.id_ste) || 0,
          doc_actif: meta.doc_actif,
          prioritaire: meta.prioritaire,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))

      // 2. Contenu HTML (si l'editeur a du contenu)
      const html = editorRef.current?.innerHTML || ''
      if (html.trim()) {
        const blob = new Blob([html], { type: 'text/html' })
        const fd = new FormData()
        fd.append('file', blob, 'content.html')
        const rh = await fetch(`/api/adm/ctt-ulease/${docId}/content`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
          body: fd,
        })
        if (!rh.ok) throw new Error(`content: ${rh.status}`)
        const j = await rh.json()
        update({ taille_contenu: j.taille })
      }

      setIsDirty(false)
      if (!silent) {
        showToast('Doc Ulease enregistré.', 'success')
        onSaved()
      }
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
        const r = await fetch(`/api/adm/ctt-ulease/${docId}/content`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
          body: fd,
        })
        const j = await r.json()
        if (!r.ok) throw new Error(j?.detail || String(r.status))
        update({ taille_contenu: j.taille })
        // Recharge le contenu dans l'editeur (conversion DOCX -> HTML)
        await loadContentToEditor(docId)
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
    a.href = `/api/adm/ctt-ulease/${docId}/content?_t=${Date.now()}`
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
      await saveMeta(true)
      const r = await fetch(
        `/api/adm/ctt-ulease/${docId}/preview-pdf`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({
            id_ste: Number(steTest) || 0,
            id_salarie: Number(idSalarieTest) || 0,
            id_vehicule_pc: Number(idVehiculePc) || 0,
            titre_doc: meta.titre || '',
          }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      // Affiche le PDF dans l'iframe + ouvre aussi dans un nouvel onglet
      if (pdfPreviewUrl) URL.revokeObjectURL(pdfPreviewUrl)
      setPdfPreviewUrl(url)
      window.open(url, '_blank')
      showToast('PDF de test généré.', 'success')
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
        className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white rounded-lg shadow-xl w-full max-w-[95vw] flex flex-col max-h-[95vh] font-normal"
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-4 py-3 border-b"
            style={{ borderColor: COL_BG_SOFT, backgroundColor: COL_BG_SOFT }}
          >
            <h3
              className="text-base font-bold flex items-center gap-2"
              style={{ color: COL_BRUN }}
            >
              <FileText className="w-4 h-4" />
              Édition Doc Ulease
            </h3>
            <div className="flex items-center gap-3">
              {meta.id_doc_ulease && (
                <span className="text-xs" style={{ color: COL_BRUN }}>
                  Id Doc Ulease : {meta.id_doc_ulease}
                </span>
              )}
              <button
                onClick={handleClose}
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
              {/* Toggle Actif / Archive + Save */}
              <div className="flex justify-between items-center mb-4">
                <ActifToggle
                  value={meta.doc_actif}
                  onChange={(v) => update({ doc_actif: v })}
                />
                <button
                  type="button"
                  onClick={() => saveMeta()}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 rounded-md text-white text-sm font-medium disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  Enregistrer
                </button>
              </div>

              {/* Layout 2 colonnes : 33% champs / 66% contenu */}
              <div className="grid grid-cols-3 gap-6">
              <div className="col-span-1 space-y-4">
              {/* Form metadonnees */}
              <div className="grid grid-cols-1 gap-3">
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
              </div>

              <div className="grid grid-cols-1 gap-3">
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

              <div className="grid grid-cols-1 gap-3">
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
                    label="Favori"
                    value={meta.prioritaire}
                    onChange={(v) => update({ prioritaire: v })}
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
                <div className="space-y-2">
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
                  <Field label="Test avec" wide>
                    <div className="flex gap-1.5 items-stretch">
                      <button
                        type="button"
                        onClick={() => setPickerOpen(true)}
                        className="flex-1 flex items-center gap-2 px-3 py-2 rounded border text-sm text-left"
                        style={{ borderColor: COL_BORDER, color: COL_BRUN, backgroundColor: 'white' }}
                      >
                        <SearchIcon className="w-4 h-4 shrink-0" />
                        <span className="truncate">{salarieTestLib || '— Salarié fictif —'}</span>
                      </button>
                      {idSalarieTest && (
                        <button
                          type="button"
                          onClick={() => {
                            setIdSalarieTest('')
                            setSalarieTestLib('')
                            setIdVehiculePc('')
                            setVehiculesAttrib([])
                          }}
                          title="Réinitialiser"
                          className="px-2 rounded border text-sm"
                          style={{ borderColor: COL_BORDER, color: COL_BRUN, backgroundColor: 'white' }}
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </Field>
                  {idSalarieTest && (
                    <Field label="Avec véhicule" wide>
                      <select
                        value={idVehiculePc}
                        onChange={(e) => setIdVehiculePc(e.target.value)}
                        className={inputCls}
                        disabled={vehiculesAttrib.length === 0}
                      >
                        <option value="">
                          {vehiculesAttrib.length === 0
                            ? '- Aucun véhicule attribué -'
                            : '- Aucun -'}
                        </option>
                        {vehiculesAttrib.map((v) => (
                          <option key={v.id_vehicule_pc} value={v.id_vehicule_pc}>
                            {v.lib}
                          </option>
                        ))}
                      </select>
                    </Field>
                  )}
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
                  Substitue les variables S_NOM / STE_* / AUTO_* avec des
                  données fictives + la société, le salarié et le véhicule
                  choisis. Génère un PDF de prévisualisation.
                </p>
              </div>

              </div>
              {/* === Colonne droite (2/3) : Contenu === */}
              <div className="col-span-2">
              {/* Contenu - editeur inline */}
              <div>
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
                  {/* Combo Police - refleter la selection courante */}
                  <select
                    value={currentFont}
                    onMouseDown={memorizeSelection}
                    onChange={(e) => {
                      const v = e.target.value
                      if (v) {
                        applyInlineStyle({ fontFamily: v })
                        setCurrentFont(v)
                      }
                    }}
                    title="Police (applique a la selection)"
                    className="text-xs px-1 py-0.5 rounded border bg-white"
                    style={{ borderColor: COL_BORDER, color: COL_BRUN }}
                  >
                    <option value="">Police</option>
                    {FONT_OPTIONS.map((f) => (
                      <option key={f.value} value={f.value}>{f.label}</option>
                    ))}
                  </select>
                  {/* Combo Taille - refleter la selection courante */}
                  <select
                    value={currentSize}
                    onMouseDown={memorizeSelection}
                    onChange={(e) => {
                      const v = e.target.value
                      if (v) {
                        applyInlineStyle({ fontSize: v })
                        setCurrentSize(v)
                      }
                    }}
                    title="Taille (applique a la selection)"
                    className="text-xs px-1 py-0.5 rounded border bg-white"
                    style={{ borderColor: COL_BORDER, color: COL_BRUN }}
                  >
                    <option value="">Taille</option>
                    {SIZE_OPTIONS.map((n) => (
                      <option key={n} value={`${n}pt`}>{n}</option>
                    ))}
                  </select>
                  {/* Couleur de police (input type=color) */}
                  <label
                    className="flex items-center gap-1 text-xs px-1 py-0.5 rounded border bg-white cursor-pointer"
                    style={{ borderColor: COL_BORDER, color: COL_BRUN }}
                    title="Couleur du texte (applique a la selection)"
                    onMouseDown={(e) => {
                      memorizeSelection()
                      e.preventDefault()
                    }}
                  >
                    <span
                      className="inline-block w-4 h-4 rounded border"
                      style={{ borderColor: COL_BORDER, backgroundColor: currentColor }}
                    />
                    <input
                      type="color"
                      value={currentColor}
                      className="w-0 h-0 opacity-0 absolute"
                      onChange={(e) => {
                        const c = e.target.value
                        setCurrentColor(c)
                        applyInlineStyle({ color: c })
                      }}
                    />
                  </label>
                  {/* Combo Interligne (s'applique aux blocs p/div/li/h*) */}
                  <select
                    value={currentLineHeight}
                    onMouseDown={memorizeSelection}
                    onChange={(e) => {
                      const v = e.target.value
                      if (v) applyLineHeight(v)
                    }}
                    title="Interligne (applique aux paragraphes)"
                    className="text-xs px-1 py-0.5 rounded border bg-white"
                    style={{ borderColor: COL_BORDER, color: COL_BRUN }}
                  >
                    <option value="">Interligne</option>
                    {LINE_HEIGHT_OPTIONS.map((lh) => (
                      <option key={lh} value={lh}>{lh}</option>
                    ))}
                  </select>
                  <div className="w-px h-4 bg-[#A68D8A]/30 mx-1" />
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
                  <ToolBtn onClick={() => insertList('ul')} title="Liste">
                    <List className="w-3.5 h-3.5" />
                  </ToolBtn>
                  <ToolBtn onClick={() => insertList('ol')} title="Liste num">
                    <ListOrdered className="w-3.5 h-3.5" />
                  </ToolBtn>
                  <div className="w-px h-4 bg-[#A68D8A]/30 mx-1" />
                  <ToolBtn
                    onClick={() => {
                      // Insere le marqueur SAUTDEPAGE a la position du curseur.
                      // Au moment de la generation PDF, ce marqueur sera
                      // remplace par un <div style='page-break-before:always'>.
                      exec('insertText', 'SAUTDEPAGE')
                    }}
                    title="Saut de page (insere 'SAUTDEPAGE')"
                  >
                    ⤓
                  </ToolBtn>
                  <div className="w-px h-4 bg-[#A68D8A]/30 mx-1" />
                  <ToolBtn
                    onClick={() => exec('justifyLeft')}
                    title="Aligner à gauche"
                  >
                    <AlignLeft className="w-4 h-4" />
                  </ToolBtn>
                  <ToolBtn onClick={() => exec('justifyCenter')} title="Centrer">
                    <AlignCenter className="w-4 h-4" />
                  </ToolBtn>
                  <ToolBtn
                    onClick={() => exec('justifyRight')}
                    title="Aligner à droite"
                  >
                    <AlignRight className="w-4 h-4" />
                  </ToolBtn>
                  <ToolBtn onClick={() => exec('justifyFull')} title="Justifier">
                    <AlignJustify className="w-4 h-4" />
                  </ToolBtn>
                  <div className="w-px h-4 bg-[#A68D8A]/30 mx-1" />
                  <ToolBtn onClick={insertTable} title="Insérer un tableau">
                    <TableIcon className="w-4 h-4" />
                  </ToolBtn>
                </div>
                {/* Zone d'edition : container gris + 'feuille A4' centree
                    pour donner un aspect document Word. */}
                <div
                  className="border-x border-b overflow-y-auto rounded-b"
                  style={{
                    borderColor: COL_BORDER,
                    backgroundColor: '#E5E5E5',
                    maxHeight: '60vh',
                    padding: '16px 0',
                  }}
                >
                  <div
                    ref={editorRef}
                    contentEditable={editorReady}
                    suppressContentEditableWarning
                    onInput={() => setIsDirty(true)}
                    className="docrh-page focus:outline-none"
                    style={{
                      width: '210mm',
                      minHeight: '297mm',
                      margin: '0 auto',
                      padding: '25mm',
                      backgroundColor: 'white',
                      boxShadow:
                        '0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)',
                      color: '#000',
                      fontFamily: 'Calibri, "Segoe UI", sans-serif',
                      fontSize: '11pt',
                      lineHeight: 1.4,
                    }}
                  />
                </div>
                <p
                  className="text-xs italic mt-1.5"
                  style={{ color: COL_BRUN }}
                >
                  Variables disponibles :
                  {' '}<strong>Salarié</strong> : S_TITRE, S_NOM, S_PRENOM,
                  S_LNAISS, S_DEPNAISS, S_NUMSS, S_DNAISS, S_ADRESSE, S_CP,
                  S_VILLE, S_GSM, DATE_CTS, FIN_PER_ESSAI, DATE_ANC,
                  DATE_AVENANT, SECTEURAGENCE, S_MENTION, S_SIGN.
                  {' '}<strong>Société</strong> : STE_LOGO, DOCTITRE, STE_RS,
                  STE_APE, STE_RCS, STE_CAPITAL, STE_ADR, STE_VILLE, STE_SIREN,
                  STE_SIRET, STE_GERANT_NOM, STE_GERANT_TYPE, GER_SIGN,
                  STE_CACHET, DATE_NOTE.
                  {' '}<strong>Véhicule</strong> : AUTO_IMMA, AUTO_TYPE,
                  AUTO_CV, AUTO_KM, DATE_DEB, DATE_FIN.
                </p>

                {/* Preview PDF dans iframe (apres un test mise en page) */}
                {pdfPreviewUrl && (
                  <div
                    className="mt-3 pt-2 border-t"
                    style={{ borderColor: COL_BORDER }}
                  >
                    <h4
                      className="text-xs font-bold uppercase mb-2 tracking-wide"
                      style={{ color: COL_BRUN }}
                    >
                      Aperçu PDF
                    </h4>
                    <iframe
                      src={pdfPreviewUrl}
                      title="Aperçu PDF Ulease"
                      className="w-full border rounded"
                      style={{ borderColor: COL_BORDER, height: '70vh' }}
                    />
                  </div>
                )}

                <div
                  className="mt-3 pt-2 border-t flex"
                  style={{ borderColor: COL_BORDER }}
                >
                  <button
                    type="button"
                    onClick={handleClose}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm border"
                    style={{ borderColor: COL_BORDER, color: COL_BRUN }}
                  >
                    <RotateCcw className="w-4 h-4" />
                    Fermer
                  </button>
                </div>
              </div>
              </div>{/* fin col-span-2 */}
              </div>{/* fin grid 2 col */}
            </div>
          )}
        </motion.div>

        {pickerOpen && (
          <SalariePicker
            onClose={() => setPickerOpen(false)}
            onPicked={(s) => {
              setIdSalarieTest(s.id_salarie)
              setSalarieTestLib(s.lib)
              setIdVehiculePc('')
              setPickerOpen(false)
            }}
          />
        )}
        <TableContextMenu
          editorRef={editorRef}
          onChange={() => setIsDirty(true)}
        />
      </motion.div>
    </AnimatePresence>
  )
}

// ============================================================================
// SalariePicker (Fen_RechercheNomSalarie) - meme pattern que AttributionModal
// ============================================================================

interface SalarieMatch {
  id_salarie: string
  lib: string
}

function SalariePicker({
  onClose,
  onPicked,
}: {
  onClose: () => void
  onPicked: (s: SalarieMatch) => void
}) {
  const [q, setQ] = useState('')
  const [list, setList] = useState<SalarieMatch[]>([])
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<number | null>(null)

  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current)
    debounceRef.current = window.setTimeout(() => {
      setLoading(true)
      fetch(`/api/adm/parc-auto/salaries/search?q=${encodeURIComponent(q)}&limit=100`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
        .then((r) => (r.ok ? r.json() : []))
        .then((d) => setList(Array.isArray(d) ? d : []))
        .finally(() => setLoading(false))
    }, 200)
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current)
    }
  }, [q])

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[80vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="flex items-center justify-between px-4 py-2 border-b"
          style={{ borderColor: COL_BORDER, color: 'white', backgroundColor: COL_PRIMARY }}
        >
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <SearchIcon className="w-4 h-4" />
            Rechercher un salarié
          </h3>
          <button onClick={onClose} className="text-white/80 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-3">
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Nom ou prénom..."
            autoFocus
            className="w-full px-3 py-2 rounded border text-sm"
            style={{ borderColor: COL_BORDER }}
          />
        </div>
        <div className="flex-1 overflow-auto border-t" style={{ borderColor: COL_BORDER }}>
          {loading ? (
            <div className="p-4 text-center">
              <Loader2 className="w-5 h-5 animate-spin inline" style={{ color: COL_PRIMARY }} />
            </div>
          ) : list.length === 0 ? (
            <div className="p-4 text-center text-sm italic" style={{ color: '#A68D8A' }}>
              Aucun résultat
            </div>
          ) : (
            list.map((s) => (
              <button
                key={s.id_salarie}
                type="button"
                onClick={() => onPicked(s)}
                className="w-full text-left px-3 py-2 hover:bg-gray-50 text-sm border-b"
                style={{ borderColor: COL_BORDER, color: COL_BRUN }}
              >
                {s.lib}
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// UI helpers
// ============================================================================

const FONT_OPTIONS: { value: string; label: string }[] = [
  { value: 'Calibri, "Segoe UI", sans-serif', label: 'Calibri' },
  { value: 'Arial, sans-serif', label: 'Arial' },
  { value: '"Times New Roman", Times, serif', label: 'Times' },
  { value: 'Verdana, sans-serif', label: 'Verdana' },
  { value: '"Trebuchet MS", sans-serif', label: 'Trebuchet' },
  { value: 'Georgia, serif', label: 'Georgia' },
  { value: '"Courier New", monospace', label: 'Courier New' },
]

const SIZE_OPTIONS = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48]

const LINE_HEIGHT_OPTIONS = ['1', '1.15', '1.5', '2', '2.5', '3']

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
  onPreClick,
}: {
  onClick: () => void
  title: string
  children: React.ReactNode
  /** Appele au mousedown AVANT preventDefault (memorize selection, etc.) */
  onPreClick?: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseDown={(e) => {
        onPreClick?.()
        e.preventDefault()
      }}
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
