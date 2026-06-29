/**
 * Helpers réutilisables pour les tableaux de la page de suivi de production.
 *
 * Trois utilitaires :
 *  - useTableSortFilter : hook qui gère tri (clic header) + filtre (string contient)
 *      sur un tableau d'objets génériques.
 *  - <SortableTh> : composant header de colonne avec icône tri (asc/desc/none).
 *  - exportRowsToXlsx : génère un fichier XLSX en pur JavaScript (sans
 *      dépendance externe, format minimal SpreadsheetML 2003 compatible
 *      Excel + LibreOffice). Suffisant pour les exports tabulaires simples
 *      (pas de styles, pas de formules).
 *
 * Le format XLSX "vrai" (Open XML zip) demanderait une lib (SheetJS ~500ko).
 * Pour les tableaux de stats de cette page (qq centaines de lignes max),
 * SpreadsheetML 2003 fait le job et ouvre nativement dans Excel/LibreOffice
 * avec extension .xls (et .xlsx selon paramétrage).
 *
 * Cf. https://learn.microsoft.com/fr-fr/previous-versions/office/developer/office-xp/aa140066(v=office.10)
 */

import { useMemo, useState } from 'react'
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react'

// ---------- Tri + filtre ----------

export type SortDir = 'asc' | 'desc' | null

export interface SortState {
  key: string
  dir: SortDir
}

export interface TableSortFilterState<T> {
  rows: T[]                     // rows finales (filtrees + triees)
  sort: SortState
  toggleSort: (key: string) => void
  filter: string                // texte de recherche global
  setFilter: (val: string) => void
}

/**
 * Hook tri + filtre client-side pour un tableau d'objets.
 * @param data      lignes brutes
 * @param defaultSort  tri par défaut (ex: { key: 'nb', dir: 'desc' })
 * @param getSearchableString  fonction qui retourne le string sur lequel
 *   le filtre s'applique pour une row donnée. Par défaut : concat de toutes
 *   les values stringifiees.
 */
export function useTableSortFilter<T extends Record<string, unknown>>(
  data: T[],
  defaultSort: SortState = { key: '', dir: null },
  getSearchableString?: (row: T) => string,
): TableSortFilterState<T> {
  const [sort, setSort] = useState<SortState>(defaultSort)
  const [filter, setFilter] = useState('')

  const toggleSort = (key: string) => {
    setSort((prev) => {
      if (prev.key !== key) return { key, dir: 'asc' }
      if (prev.dir === 'asc') return { key, dir: 'desc' }
      if (prev.dir === 'desc') return { key: '', dir: null }
      return { key, dir: 'asc' }
    })
  }

  const rows = useMemo(() => {
    let result = data
    if (filter.trim()) {
      const needle = filter.trim().toLowerCase()
      const toStr = getSearchableString
        ?? ((r: T) => Object.values(r).map((v) => String(v ?? '')).join(' '))
      result = result.filter((r) => toStr(r).toLowerCase().includes(needle))
    }
    if (sort.key && sort.dir) {
      const key = sort.key
      const dir = sort.dir
      result = [...result].sort((a, b) => {
        const va = a[key]; const vb = b[key]
        if (typeof va === 'number' && typeof vb === 'number') {
          return dir === 'asc' ? va - vb : vb - va
        }
        const sa = String(va ?? ''); const sb = String(vb ?? '')
        return dir === 'asc' ? sa.localeCompare(sb) : sb.localeCompare(sa)
      })
    }
    return result
  }, [data, sort, filter, getSearchableString])

  return { rows, sort, toggleSort, filter, setFilter }
}

// ---------- Header de colonne triable ----------

export function SortableTh({
  label, sortKey, sort, onSort, align = 'left', className = '',
}: {
  label: string
  sortKey: string
  sort: SortState
  onSort: (key: string) => void
  align?: 'left' | 'right' | 'center'
  className?: string
}) {
  const active = sort.key === sortKey && sort.dir
  const alignClass = align === 'right' ? 'text-right justify-end'
    : align === 'center' ? 'text-center justify-center'
    : 'text-left justify-start'
  return (
    <th
      className={`px-3 py-2.5 font-medium cursor-pointer select-none ${className}`}
      onClick={() => onSort(sortKey)}
    >
      <div className={`flex items-center gap-1 ${alignClass}`}>
        <span>{label}</span>
        {!active && <ArrowUpDown className="w-3 h-3 opacity-30" />}
        {active === 'asc' && <ArrowUp className="w-3 h-3" />}
        {active === 'desc' && <ArrowDown className="w-3 h-3" />}
      </div>
    </th>
  )
}

// ---------- Export XLSX (SpreadsheetML 2003, sans dépendance) ----------

const xmlEscape = (s: string): string =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&apos;')

/**
 * Génère un XLSX SpreadsheetML 2003 (format texte XML) compatible Excel
 * et LibreOffice. Sans dépendance externe.
 *
 * @param columns  liste {key, label} (label = en-tête, key = champ row)
 * @param rows     lignes
 * @param filename  nom de fichier (sera force en .xls si .xlsx absent)
 * @param sheetName  nom de la feuille (defaut: 'Export')
 */
export function exportRowsToXlsx<T extends Record<string, unknown>>(
  columns: Array<{ key: string; label: string }>,
  rows: T[],
  filename: string,
  sheetName: string = 'Export',
): void {
  const header = columns.map((c) =>
    `<Cell><Data ss:Type="String">${xmlEscape(c.label)}</Data></Cell>`
  ).join('')
  const body = rows.map((r) => {
    const cells = columns.map((c) => {
      const v = r[c.key]
      if (v === null || v === undefined || v === '') {
        return '<Cell><Data ss:Type="String"></Data></Cell>'
      }
      if (typeof v === 'number') {
        return `<Cell><Data ss:Type="Number">${v}</Data></Cell>`
      }
      return `<Cell><Data ss:Type="String">${xmlEscape(String(v))}</Data></Cell>`
    }).join('')
    return `<Row>${cells}</Row>`
  }).join('')

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
<Worksheet ss:Name="${xmlEscape(sheetName)}">
<Table>
<Row>${header}</Row>
${body}
</Table>
</Worksheet>
</Workbook>`

  const blob = new Blob([xml], { type: 'application/vnd.ms-excel' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  // Excel ouvre nativement les .xls en SpreadsheetML.
  // Forcer .xls si l'utilisateur a passé .xlsx (sinon Excel peut afficher
  // un warning "le format diffère de l'extension").
  const finalName = filename.replace(/\.xlsx?$/i, '') + '.xls'
  a.href = url
  a.download = finalName
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ---------- Petit input de filtre commun ----------

export function FilterInput({
  value, onChange, placeholder = 'Filtrer…',
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="px-2 py-1.5 rounded border border-c-line text-sm w-48"
    />
  )
}
