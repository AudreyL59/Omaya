// Export CSV compatible Excel FR (separateur ';', BOM UTF-8 pour les accents).

type CellValue = string | number | boolean | null | undefined

function escapeCell(v: CellValue): string {
  if (v === null || v === undefined) return ''
  const s = typeof v === 'boolean' ? (v ? 'Oui' : 'Non') : String(v)
  // CSV FR : separateur ';' → on echappe les ';', guillemets et sauts de ligne
  if (/[";\n\r]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`
  }
  return s
}

export function exportToCSV(
  filename: string,
  headers: string[],
  rows: CellValue[][],
): void {
  const BOM = '﻿' // pour qu'Excel detecte l'UTF-8
  const lines: string[] = []
  lines.push(headers.map(escapeCell).join(';'))
  for (const row of rows) {
    lines.push(row.map(escapeCell).join(';'))
  }
  const content = BOM + lines.join('\r\n')

  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename.endsWith('.csv') ? filename : `${filename}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// Format date YYYYMMDD[HHMMSS] en JJ/MM/AAAA pour Excel
export function csvDate(raw: string | undefined | null): string {
  if (!raw) return ''
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (iso) return `${iso[3]}/${iso[2]}/${iso[1]}`
  if (raw.length >= 8 && /^\d+$/.test(raw.slice(0, 8))) {
    return `${raw.slice(6, 8)}/${raw.slice(4, 6)}/${raw.slice(0, 4)}`
  }
  return raw
}
