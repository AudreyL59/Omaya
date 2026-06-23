/**
 * Menu contextuel (clic-droit) pour les tableaux d'un editeur
 * contentEditable. Gere l'insertion/suppression de lignes/colonnes,
 * la suppression du tableau et la mise en forme des bordures.
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
  MoveHorizontal,
  Palette,
  Table as TableIcon,
  Trash2,
} from 'lucide-react'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'

const NEW_CELL_STYLE = 'border:1px solid #888;padding:6px;min-width:40px;'

type BorderTarget = 'cell' | 'row' | 'col' | 'table'

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
  const [borderState, setBorderState] = useState<MenuState | null>(null)
  const [widthState, setWidthState] = useState<MenuState | null>(null)

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
    if (!menu) return
    const tr = menu.td.parentElement as HTMLTableRowElement | null
    if (!tr) return
    const nbCols = tr.children.length
    const newTr = document.createElement('tr')
    for (let i = 0; i < nbCols; i++) newTr.appendChild(makeCell())
    tr.parentElement!.insertBefore(newTr, above ? tr : tr.nextSibling)
    finish()
  }

  const insertCol = (left: boolean) => {
    if (!menu) return
    const table = findTable(menu.td)
    if (!table) return
    const idx = cellIndex(menu.td) + (left ? 0 : 1)
    Array.from(table.querySelectorAll('tr')).forEach((tr) => {
      tr.insertBefore(makeCell(), tr.children[idx] || null)
    })
    finish()
  }

  const deleteRow = () => {
    if (!menu) return
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
    if (!menu) return
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
    if (!menu) return
    const table = findTable(menu.td)
    table?.remove()
    finish()
  }

  const openBorderEditor = () => {
    if (!menu) return
    setBorderState(menu)
    setMenu(null)
  }

  const openWidthEditor = () => {
    if (!menu) return
    setWidthState(menu)
    setMenu(null)
  }

  const finish = () => {
    setMenu(null)
    onChange?.()
  }

  // Si l'editeur de bordures est ouvert, on ne render que lui.
  if (borderState) {
    return (
      <BorderEditor
        x={borderState.x}
        y={borderState.y}
        td={borderState.td}
        findTable={findTable}
        cellIndex={cellIndex}
        onClose={() => setBorderState(null)}
        onApplied={() => {
          setBorderState(null)
          onChange?.()
        }}
      />
    )
  }

  if (widthState) {
    return (
      <ColumnWidthEditor
        x={widthState.x}
        y={widthState.y}
        td={widthState.td}
        findTable={findTable}
        cellIndex={cellIndex}
        onClose={() => setWidthState(null)}
        onApplied={() => {
          setWidthState(null)
          onChange?.()
        }}
      />
    )
  }

  if (!menu) return null

  const W = 240
  const H = 340
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
      <Item icon={<Palette className="w-3.5 h-3.5" />} onClick={openBorderEditor}>
        Bordures…
      </Item>
      <Item icon={<MoveHorizontal className="w-3.5 h-3.5" />} onClick={openWidthEditor}>
        Largeur de la colonne…
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

// ============================================================================
// BorderEditor : mini popup pour appliquer une bordure (couleur + epaisseur)
// sur une cible (cellule / ligne / colonne / tableau entier).
// ============================================================================

function BorderEditor({
  x, y, td, findTable, cellIndex, onClose, onApplied,
}: {
  x: number
  y: number
  td: HTMLTableCellElement
  findTable: (td: HTMLTableCellElement) => HTMLTableElement | null
  cellIndex: (td: HTMLTableCellElement) => number
  onClose: () => void
  onApplied: () => void
}) {
  const [width, setWidth] = useState<number>(() => {
    const cs = window.getComputedStyle(td)
    const w = parseFloat(cs.borderTopWidth || '1')
    return isNaN(w) ? 1 : Math.round(w)
  })
  const [color, setColor] = useState<string>(() => {
    const cs = window.getComputedStyle(td)
    return rgbToHex(cs.borderTopColor || '#888888')
  })
  const [target, setTarget] = useState<BorderTarget>('cell')

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const collectCells = (): HTMLTableCellElement[] => {
    const table = findTable(td)
    if (!table) return [td]
    if (target === 'cell') return [td]
    if (target === 'row') {
      const tr = td.parentElement
      if (!tr) return [td]
      return Array.from(tr.querySelectorAll('td, th')) as HTMLTableCellElement[]
    }
    if (target === 'col') {
      const idx = cellIndex(td)
      return Array.from(table.querySelectorAll('tr'))
        .map((tr) => tr.children[idx] as HTMLTableCellElement | undefined)
        .filter(Boolean) as HTMLTableCellElement[]
    }
    // table
    return Array.from(table.querySelectorAll('td, th')) as HTMLTableCellElement[]
  }

  const apply = () => {
    const cells = collectCells()
    const value = width === 0 ? 'none' : `${width}px solid ${color}`
    cells.forEach((c) => {
      c.style.border = value
      c.style.padding = c.style.padding || '6px'
      c.style.minWidth = c.style.minWidth || '40px'
    })
    // Si la cible est table, on met aussi le border-collapse pour eviter
    // les double bordures internes (cf. style inline d'origine).
    if (target === 'table') {
      const table = findTable(td)
      if (table) table.style.borderCollapse = 'collapse'
    }
    onApplied()
  }

  const W = 280
  const H = 220
  const xc = Math.min(x, window.innerWidth - W - 4)
  const yc = Math.min(y, window.innerHeight - H - 4)

  return (
    <>
      {/* Overlay pour absorber les clics ailleurs */}
      <div
        className="fixed inset-0 z-[100]"
        onMouseDown={onClose}
      />
      <div
        className="fixed z-[101] bg-white border rounded-md shadow-lg p-3 text-sm space-y-2"
        style={{ left: xc, top: yc, borderColor: COL_BORDER, color: COL_BRUN, width: W }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="font-semibold mb-1">Bordures du tableau</div>
        <div className="flex items-center gap-2">
          <label className="w-20 text-xs">Appliquer :</label>
          <select
            value={target}
            onChange={(e) => setTarget(e.target.value as BorderTarget)}
            className="flex-1 px-2 py-1 rounded border text-xs"
            style={{ borderColor: COL_BORDER }}
          >
            <option value="cell">à la cellule</option>
            <option value="row">à la ligne</option>
            <option value="col">à la colonne</option>
            <option value="table">à tout le tableau</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="w-20 text-xs">Épaisseur :</label>
          <input
            type="number"
            min={0}
            max={10}
            value={width}
            onChange={(e) =>
              setWidth(Math.max(0, Math.min(10, Number(e.target.value) || 0)))
            }
            className="w-16 px-2 py-1 rounded border text-xs"
            style={{ borderColor: COL_BORDER }}
          />
          <span className="text-xs italic" style={{ color: '#A68D8A' }}>
            (0 = pas de bordure)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <label className="w-20 text-xs">Couleur :</label>
          <input
            type="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="w-10 h-6 rounded border cursor-pointer"
            style={{ borderColor: COL_BORDER }}
          />
          <input
            type="text"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="flex-1 px-2 py-1 rounded border text-xs font-mono"
            style={{ borderColor: COL_BORDER }}
          />
        </div>
        {/* Apercu */}
        <div
          className="text-xs px-2 py-3 text-center"
          style={{
            border: width === 0 ? '1px dashed #ccc' : `${width}px solid ${color}`,
            color: '#999',
          }}
        >
          Aperçu
        </div>
        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 rounded border text-xs"
            style={{ borderColor: COL_BORDER, color: COL_BRUN }}
          >
            Annuler
          </button>
          <button
            type="button"
            onClick={apply}
            className="px-3 py-1 rounded text-white text-xs"
            style={{ backgroundColor: COL_PRIMARY }}
          >
            Appliquer
          </button>
        </div>
      </div>
    </>
  )
}

// ============================================================================
// ColumnWidthEditor : largeur de la colonne (auto / % / px).
// Applique la largeur a TOUTES les cellules de la colonne (memes index)
// pour eviter les conflits CSS quand plusieurs lignes ont des largeurs
// differentes sur la meme colonne.
// ============================================================================

type WidthUnit = '%' | 'px' | 'auto'

function ColumnWidthEditor({
  x, y, td, findTable, cellIndex, onClose, onApplied,
}: {
  x: number
  y: number
  td: HTMLTableCellElement
  findTable: (td: HTMLTableCellElement) => HTMLTableElement | null
  cellIndex: (td: HTMLTableCellElement) => number
  onClose: () => void
  onApplied: () => void
}) {
  // Initialise depuis la valeur courante de la cellule.
  const [unit, setUnit] = useState<WidthUnit>(() => {
    const w = td.style.width
    if (!w || w === 'auto') return 'auto'
    if (w.endsWith('%')) return '%'
    return 'px'
  })
  const [value, setValue] = useState<number>(() => {
    const w = td.style.width
    if (!w || w === 'auto') return 20
    const n = parseFloat(w)
    return isNaN(n) ? 20 : n
  })

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const apply = () => {
    const table = findTable(td)
    if (!table) return
    const idx = cellIndex(td)
    const cssValue =
      unit === 'auto' ? '' :
      unit === '%' ? `${value}%` : `${value}px`
    Array.from(table.querySelectorAll('tr')).forEach((tr) => {
      const cell = tr.children[idx] as HTMLTableCellElement | undefined
      if (!cell) return
      cell.style.width = cssValue
    })
    // S'assure que la table a width:100% si on utilise des %
    if (unit === '%' && !table.style.width) {
      table.style.width = '100%'
    }
    onApplied()
  }

  const reset = () => {
    const table = findTable(td)
    if (!table) return
    const idx = cellIndex(td)
    Array.from(table.querySelectorAll('tr')).forEach((tr) => {
      const cell = tr.children[idx] as HTMLTableCellElement | undefined
      if (!cell) return
      cell.style.width = ''
    })
    onApplied()
  }

  const W = 320
  const H = 200
  const xc = Math.min(x, window.innerWidth - W - 4)
  const yc = Math.min(y, window.innerHeight - H - 4)

  return (
    <>
      <div className="fixed inset-0 z-[100]" onMouseDown={onClose} />
      <div
        className="fixed z-[101] bg-white border rounded-md shadow-lg p-3 text-sm space-y-2"
        style={{ left: xc, top: yc, borderColor: COL_BORDER, color: COL_BRUN, width: W }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="font-semibold mb-1">Largeur de la colonne</div>
        <div className="flex items-center gap-2">
          <label className="w-16 text-xs">Unité :</label>
          <select
            value={unit}
            onChange={(e) => setUnit(e.target.value as WidthUnit)}
            className="flex-1 px-2 py-1 rounded border text-xs"
            style={{ borderColor: COL_BORDER }}
          >
            <option value="auto">Auto (laisser le navigateur décider)</option>
            <option value="%">Pourcentage de la table (%)</option>
            <option value="px">Pixels (px)</option>
          </select>
        </div>
        {unit !== 'auto' && (
          <div className="flex items-center gap-2">
            <label className="w-16 text-xs">Valeur :</label>
            <input
              type="number"
              min={1}
              max={unit === '%' ? 100 : 2000}
              value={value}
              onChange={(e) => setValue(Number(e.target.value) || 0)}
              className="w-20 px-2 py-1 rounded border text-xs"
              style={{ borderColor: COL_BORDER }}
            />
            <span className="text-xs">{unit}</span>
          </div>
        )}
        <div className="text-xs italic" style={{ color: '#A68D8A' }}>
          Appliqué à toutes les cellules de cette colonne.
        </div>
        <div className="flex justify-between gap-2 pt-1">
          <button
            type="button"
            onClick={reset}
            className="px-3 py-1 rounded border text-xs"
            style={{ borderColor: COL_BORDER, color: COL_BRUN }}
            title="Reinitialise (largeur auto)"
          >
            Réinitialiser
          </button>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1 rounded border text-xs"
              style={{ borderColor: COL_BORDER, color: COL_BRUN }}
            >
              Annuler
            </button>
            <button
              type="button"
              onClick={apply}
              className="px-3 py-1 rounded text-white text-xs"
              style={{ backgroundColor: COL_PRIMARY }}
            >
              Appliquer
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

function rgbToHex(rgb: string): string {
  if (rgb.startsWith('#')) return rgb
  const m = rgb.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
  if (!m) return '#888888'
  const [, r, g, b] = m
  return (
    '#' +
    [r, g, b].map((x) => parseInt(x, 10).toString(16).padStart(2, '0')).join('')
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
