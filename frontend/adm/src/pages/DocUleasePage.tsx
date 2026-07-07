/**
 * Fen_ListeDocUlease (WinDev) - Ulease -> Liste des documents Ulease.
 *
 * Calque de CttTravailPage : Titre | Info Cplt | Société | Prioritaire |
 * Dern. modif. + glissière Actifs/Archivés + 5 boutons (Nouveau /
 * Dupliquer / Supprimer / Modifier / Archiver).
 *
 * Modal d'édition : DocUleaseEditModal (placeholder pour l'instant,
 * sera basé sur DocRHEditModal).
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Archive,
  Copy,
  FileText,
  Loader2,
  Pencil,
  Plus,
  RotateCcw,
  Trash2,
} from 'lucide-react'

import { getToken } from '@/api'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import PageHeader from '@/components/PageHeader'
import { showConfirm, showToast } from '@shared/ui/dialog'
import DocUleaseEditModal from '@/components/DocUleaseEditModal'

interface DocUlease {
  id_doc_ulease: string
  lib_type: string
  titre: string
  info_cpl: string
  ste_lib: string
  prioritaire: boolean
  datecrea: string
  modif_date: string
}

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_PRIMARY_LIGHT = '#6a8d91'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

export default function DocUleasePage() {
  useDocumentTitle('Documents Ulease')
  const [actif, setActif] = useState(true)
  const [rows, setRows] = useState<DocUlease[]>([])
  const [selected, setSelected] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState<string | null>(null)

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`/api/adm/ctt-ulease/list?actif=${actif ? 1 : 0}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: DocUlease[]) => setRows(Array.isArray(d) ? d : []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }, [actif])

  useEffect(() => { reload() }, [reload])

  const selectedRow = rows.find((r) => r.id_doc_ulease === selected)

  const handleNouveau = () => setEditing('')
  const handleModifier = () => {
    if (!selectedRow) return
    setEditing(selectedRow.id_doc_ulease)
  }

  const handleDupliquer = async () => {
    if (!selectedRow) return
    const ok = await showConfirm({
      title: 'Dupliquer ce document ?',
      message: `« ${selectedRow.titre} » va être copié.`,
      confirmLabel: 'Dupliquer',
    })
    if (!ok) return
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/ctt-ulease/${selectedRow.id_doc_ulease}/duplicate`,
        { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast('Document dupliqué.', 'success')
      reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally { setBusy(false) }
  }

  const handleSupprimer = async () => {
    if (!selectedRow) return
    const ok = await showConfirm({
      title: 'Supprimer ce document ?',
      message: `« ${selectedRow.titre} » va être supprimé.`,
      confirmLabel: 'Supprimer',
    })
    if (!ok) return
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/ctt-ulease/${selectedRow.id_doc_ulease}`,
        { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast('Document supprimé.', 'success')
      setSelected('')
      reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally { setBusy(false) }
  }

  const handleArchiver = async () => {
    if (!selectedRow) return
    const isArchive = !actif
    const ok = await showConfirm({
      title: isArchive ? 'Restaurer ce document ?' : 'Archiver ce document ?',
      message: `« ${selectedRow.titre} »`,
      confirmLabel: isArchive ? 'Restaurer' : 'Archiver',
    })
    if (!ok) return
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/ctt-ulease/${selectedRow.id_doc_ulease}/${isArchive ? 'restore' : 'archive'}`,
        { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast(isArchive ? 'Document restauré.' : 'Document archivé.', 'success')
      setSelected('')
      reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally { setBusy(false) }
  }

  const hasSel = !!selectedRow

  return (
    <div className="p-6 max-w-7xl mx-auto font-normal">
      <PageHeader
        icon={FileText}
        title="Liste des documents Ulease"
        right={<ActifToggle value={actif} onChange={setActif} />}
      />

      <div className="flex items-center gap-2 p-3 mb-4 bg-white rounded-lg border"
        style={{ borderColor: COL_BORDER }}>
        <ToolbarBtn icon={<Plus className="w-4 h-4" />} label="Nouveau" onClick={handleNouveau} />
        <ToolbarBtn icon={<Copy className="w-4 h-4" />} label="Dupliquer"
          onClick={handleDupliquer} disabled={!hasSel || busy} />
        <ToolbarBtn icon={<Trash2 className="w-4 h-4" />} label="Supprimer"
          onClick={handleSupprimer} disabled={!hasSel || busy} danger />
        <ToolbarBtn icon={<Pencil className="w-4 h-4" />} label="Modifier"
          onClick={handleModifier} disabled={!hasSel || busy} />
        <ToolbarBtn
          icon={actif ? <Archive className="w-4 h-4" /> : <RotateCcw className="w-4 h-4" />}
          label={actif ? 'Archiver' : 'Restaurer'}
          onClick={handleArchiver} disabled={!hasSel || busy} />
      </div>

      <div className="bg-white rounded-lg shadow-sm border overflow-hidden"
        style={{ borderColor: COL_BORDER }}>
        {loading ? (
          <div className="p-10 flex justify-center">
            <Loader2 className="w-5 h-5 animate-spin text-[#A68D8A]" />
          </div>
        ) : rows.length === 0 ? (
          <div className="p-10 text-center text-sm italic text-[#A68D8A]">
            Aucun document {actif ? 'actif' : 'archivé'}.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
              <tr>
                <Th>Type</Th>
                <Th>Titre</Th>
                <Th>Info cplt</Th>
                <Th>Société</Th>
                <Th className="text-center">Prio</Th>
                <Th>Dern. modif</Th>
              </tr>
            </thead>
            <tbody>
              {(() => {
                const blocks: React.ReactNode[] = []
                let currentGroup: string | null = null
                rows.forEach((r) => {
                  const grp = r.lib_type || 'Sans type'
                  if (grp !== currentGroup) {
                    currentGroup = grp
                    blocks.push(
                      <tr key={`grp-${grp}`}>
                        <td colSpan={6}
                          className="px-3 py-1.5 text-xs font-bold uppercase tracking-wide"
                          style={{
                            backgroundColor: COL_BG_SOFT,
                            color: COL_BRUN,
                            borderTop: `1px solid ${COL_BORDER}`,
                          }}>
                          {grp}
                        </td>
                      </tr>,
                    )
                  }
                  const isSel = selected === r.id_doc_ulease
                  blocks.push(
                    <tr key={r.id_doc_ulease}
                      onClick={() => setSelected(r.id_doc_ulease)}
                      onDoubleClick={handleModifier}
                      className="cursor-pointer border-b"
                      style={{
                        backgroundColor: isSel ? COL_PRIMARY_LIGHT : 'white',
                        color: isSel ? 'white' : COL_BRUN,
                        borderColor: COL_BORDER,
                      }}>
                      <Td>{r.lib_type}</Td>
                      <Td>{r.titre}</Td>
                      <Td>{r.info_cpl}</Td>
                      <Td>{r.ste_lib}</Td>
                      <Td className="text-center">{r.prioritaire ? '✓' : ''}</Td>
                      <Td>{fmtDate(r.modif_date)}</Td>
                    </tr>,
                  )
                })
                return blocks
              })()}
            </tbody>
          </table>
        )}
      </div>

      {editing !== null && (
        <DocUleaseEditModal
          idDocUlease={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            reload()
          }}
        />
      )}
    </div>
  )
}

function ActifToggle({
  value, onChange,
}: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center rounded overflow-hidden"
      style={{ border: `1px solid ${COL_BORDER}` }}>
      {[{ v: true, l: 'Actifs' }, { v: false, l: 'Archivés' }].map((o) => {
        const active = value === o.v
        return (
          <button key={String(o.v)} type="button" onClick={() => onChange(o.v)}
            className="px-4 py-1.5 text-sm"
            style={{
              backgroundColor: active ? COL_PRIMARY : 'white',
              color: active ? 'white' : COL_BRUN,
              fontWeight: active ? 600 : 400,
            }}>
            {o.l}
          </button>
        )
      })}
    </div>
  )
}

function ToolbarBtn({
  icon, label, onClick, disabled, danger,
}: {
  icon: React.ReactNode; label: string; onClick: () => void
  disabled?: boolean; danger?: boolean
}) {
  return (
    <button type="button" onClick={onClick} disabled={disabled}
      className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm border disabled:opacity-50"
      style={{
        borderColor: danger ? '#B91C1C' : COL_BORDER,
        color: danger ? '#B91C1C' : COL_BRUN,
        backgroundColor: COL_BG_SOFT,
      }}>
      {icon}{label}
    </button>
  )
}

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <th className={`px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide ${className}`}>
      {children}
    </th>
  )
}

function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2 whitespace-nowrap ${className}`}>{children}</td>
}
