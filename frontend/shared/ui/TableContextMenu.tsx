/**
 * Menu contextuel (clic-droit) pour les tableaux d'un editeur
 * contentEditable. Gere l'insertion/suppression de lignes/colonnes et
 * la suppression du tableau entier.
 *
 * Usage :
 *   <TableContextMenu editorRef={editorRef} onChange={() => setIsDirty(true)} />
 *
 * Le menu n'apparait que si le clic-droit est dans une cellule <td>/<th>
 * d'un tableau contenu dans editorRef.
 */

import { useEffect, useState } from 'react'
import type { RefObject } from 'react'
import {
  ArrowDownToLine,
  ArrowLeftToLine,
  ArrowRightToLine,
  ArrowUpToLine,
  Table as TableIcon,
  Trash2,
} from 'lucide-react'

const COL_BRUN = '#4E1D17'
const COL_BORDER = '#E5DDDC'

const NEW_CELL_STYLE = 'border:1px solid #888;padding:6px;min-width:40px;'

interface MenuState {
  x: number
  y: number
  td: HTMLTableCellElement
}

interface Props {
  editorRef: RefObject<HTMLDivElement | null>
  onChange?: () => void
}

export default function TableContextMenu({ editorRef, onChange }: Props) {
  const [menu, setMenu] = useState<MenuState | null>(null)

  // Listener contextmenu sur le document (phase capture). On filtre via
  // editorRef.current.contains(target) : 1) le ref peut etre null au
  // mount initial (editor pas encore rendu si parent en loading), 2) on
  // veut intercepter avant que le menu natif ne s'affiche.
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const ed = editorRef.current
      if (!ed) return
      const target = e.target as HTMLElement | null
      if (!target || !ed.contains(target)) return
      let el: HTMLElement | null = target
      while (el && el !== ed) {
        if (el.tagName === 'TD' || el.tagName === 'TH') {
          e.preventDefault()
          e.stopPropagation()
          setMenu({ x: e.clientX, y: e.clientY, td: el as HTMLTableCellElement })
          return
        }
        el = el.parentElement
      }
    }
    document.addEventListener('contextmenu', handler, true)
    return () => document.removeEventListener('contextmenu', handler, true)
  }, [editorRef])

  // Fermeture du menu au clic ailleurs / Escape.
  useEffect(() => {
    if (!menu) return
    const close = () => setMenu(null)
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setMenu(null) }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', onKey)
    }
  }, [menu])

  if (!menu) return null

  const findTable = (td: HTMLTableCellElement): HTMLTableElement | null => {
    let el: HTMLElement | null = td
    while (el) {
      if (el.tagName === 'TABLE') return el as HTMLTableElement
      el = el.parentElement
    }
    return null
  }

  const cellIndex = (td: HTMLTableCellElement): number => {
    const tr = td.parentElement
    if (!tr) return 0
    return Array.from(tr.children).indexOf(td)
  }

  const makeCell = (): HTMLTableCellElement => {
    const td = document.createElement('td')
    td.setAttribute('style', NEW_CELL_STYLE)
    td.innerHTML = '&nbsp;'
    return td
  }

  const insertRow = (above: boolean) => {
    const tr = menu.td.parentElement as HTMLTableRowElement | null
    if (!tr) return
    const nbCols = tr.children.length
    const newTr = document.createElement('tr')
    for (let i = 0; i < nbCols; i++) newTr.appendChild(makeCell())
    tr.parentElement!.insertBefore(newTr, above ? tr : tr.nextSibling)
    finish()
  }

  const insertCol = (left: boolean) => {
    const table = findTable(menu.td)
    if (!table) return
    const idx = cellIndex(menu.td) + (left ? 0 : 1)
    Array.from(table.querySelectorAll('tr')).forEach((tr) => {
      tr.insertBefore(makeCell(), tr.children[idx] || null)
    })
    finish()
  }

  const deleteRow = () => {
    const table = findTable(menu.td)
    if (!table) return
    const tr = menu.td.parentElement
    if (!tr) return
    if (table.querySelectorAll('tr').length <= 1) {
      table.remove()
    } else {
      tr.remove()
    }
    finish()
  }

  const deleteCol = () => {
    const table = findTable(menu.td)
    if (!table) return
    const idx = cellIndex(menu.td)
    const firstTr = table.querySelector('tr')
    if (!firstTr) return
    if (firstTr.children.length <= 1) {
      table.remove()
    } else {
      Array.from(table.querySelectorAll('tr')).forEach((tr) => {
        tr.children[idx]?.remove()
      })
    }
    finish()
  }

  const deleteTable = () => {
    const table = findTable(menu.td)
    table?.remove()
    finish()
  }

  const finish = () => {
    setMenu(null)
    onChange?.()
  }

  // Position : on clamp pour eviter de sortir du viewport.
  const W = 240
  const H = 296
  const x = Math.min(menu.x, window.innerWidth - W - 4)
  const y = Math.min(menu.y, window.innerHeight - H - 4)

  return (
    <div
      className="fixed z-[100] bg-white border rounded-md shadow-lg text-sm py-1"
      style={{ left: x, top: y, borderColor: COL_BORDER, color: COL_BRUN, minWidth: W }}
      onMouseDown={(e) => e.stopPropagation()}
    >
      <Item icon={<ArrowUpToLine className="w-3.5 h-3.5" />}
            onClick={() => insertRow(true)}>
        Insérer ligne au-dessus
      </Item>
      <Item icon={<ArrowDownToLine className="w-3.5 h-3.5" />}
            onClick={() => insertRow(false)}>
        Insérer ligne en-dessous
      </Item>
      <Sep />
      <Item icon={<ArrowLeftToLine className="w-3.5 h-3.5" />}
            onClick={() => insertCol(true)}>
        Insérer colonne à gauche
      </Item>
      <Item icon={<ArrowRightToLine className="w-3.5 h-3.5" />}
            onClick={() => insertCol(false)}>
        Insérer colonne à droite
      </Item>
      <Sep />
      <Item icon={<Trash2 className="w-3.5 h-3.5" />} onClick={deleteRow} danger>
        Supprimer la ligne
      </Item>
      <Item icon={<Trash2 className="w-3.5 h-3.5" />} onClick={deleteCol} danger>
        Supprimer la colonne
      </Item>
      <Sep />
      <Item icon={<TableIcon className="w-3.5 h-3.5" />} onClick={deleteTable} danger>
        Supprimer le tableau
      </Item>
    </div>
  )
}

function Item({
  icon, children, onClick, danger,
}: {
  icon: React.ReactNode
  children: React.ReactNode
  onClick: () => void
  danger?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-gray-100"
      style={{ color: danger ? '#B91C1C' : COL_BRUN }}
    >
      {icon}
      {children}
    </button>
  )
}

function Sep() {
  return <div className="h-px my-1 bg-gray-200" />
}
