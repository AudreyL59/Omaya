/**
 * Fen_ListeDocRH (WinDev) - Salaries -> Liste des contrats de travail.
 *
 * Tableau : Type Doc | Titre | Info Cplt | Société | Prioritaire | DPAE |
 *           Dern. modif.
 * Glissière Actif / Archivés en haut a droite.
 * Boutons : Nouveau / Dupliquer / Supprimer / Modifier / Archiver.
 *
 * Fen_EditionDocRH (open via Nouveau / Modifier) : module dedie a coder.
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Archive,
  Copy,
  FileSignature,
  Loader2,
  Pencil,
  Plus,
  RotateCcw,
  Trash2,
} from 'lucide-react'

import { getToken } from '@/api'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { showConfirm, showToast } from '@shared/ui/dialog'
import DocRHEditModal from '@/components/DocRHEditModal'

interface DocRH {
  id_doc_rh: string
  lib_type: string
  titre: string
  info_cpl: string
  lib_produit: string
  doc_dpae: boolean
  prioritaire: boolean
  datecrea: string
  modif_date: string
}

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

export default function CttTravailPage() {
  useDocumentTitle('Contrats de travail')
  const [actif, setActif] = useState(true)
  const [rows, setRows] = useState<DocRH[]>([])
  const [selected, setSelected] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [editing, setEditing] = useState<string | null>(null)  // null=closed, ''=nouveau, '<id>'=modifier

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`/api/adm/ctt-travail/list?actif=${actif ? 1 : 0}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d: DocRH[]) => setRows(Array.isArray(d) ? d : []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }, [actif])

  useEffect(() => {
    reload()
  }, [reload])

  const selectedRow = rows.find((r) => r.id_doc_rh === selected)

  // ---- Actions ----------------------------------------------------------
  const handleNouveau = () => setEditing('')
  const handleModifier = () => {
    if (!selectedRow) return
    setEditing(selectedRow.id_doc_rh)
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
        `/api/adm/ctt-travail/${selectedRow.id_doc_rh}/duplicate`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast('Document dupliqué.', 'success')
      reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
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
        `/api/adm/ctt-travail/${selectedRow.id_doc_rh}`,
        {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast('Document supprimé.', 'success')
      setSelected('')
      reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
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
        `/api/adm/ctt-travail/${selectedRow.id_doc_rh}/${isArchive ? 'restore' : 'archive'}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast(isArchive ? 'Document restauré.' : 'Document archivé.', 'success')
      setSelected('')
      reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const hasSel = !!selectedRow

  return (
    <div className="p-6 max-w-7xl mx-auto font-normal">
      <div className="flex items-center gap-3 mb-5">
        <FileSignature className="w-6 h-6" style={{ color: COL_BRUN }} />
        <h1 className="text-xl font-bold flex-1" style={{ color: COL_BRUN }}>
          Liste des documents RH
        </h1>
        <ActifToggle value={actif} onChange={setActif} />
      </div>

      {/* Toolbar actions */}
      <div
        className="flex items-center gap-2 p-3 mb-4 bg-white rounded-lg border"
        style={{ borderColor: COL_BORDER }}
      >
        <ToolbarBtn icon={<Plus className="w-4 h-4" />} label="Nouveau" onClick={handleNouveau} />
        <ToolbarBtn
          icon={<Copy className="w-4 h-4" />}
          label="Dupliquer"
          onClick={handleDupliquer}
          disabled={!hasSel || busy}
        />
        <ToolbarBtn
          icon={<Trash2 className="w-4 h-4" />}
          label="Supprimer"
          onClick={handleSupprimer}
          disabled={!hasSel || busy}
          danger
        />
        <ToolbarBtn
          icon={<Pencil className="w-4 h-4" />}
          label="Modifier"
          onClick={handleModifier}
          disabled={!hasSel || busy}
        />
        <ToolbarBtn
          icon={actif ? <Archive className="w-4 h-4" /> : <RotateCcw className="w-4 h-4" />}
          label={actif ? 'Archiver' : 'Restaurer'}
          onClick={handleArchiver}
          disabled={!hasSel || busy}
        />
      </div>

      {/* Table */}
      <div
        className="bg-white rounded-lg shadow-sm border overflow-hidden"
        style={{ borderColor: COL_BORDER }}
      >
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
                <Th>Type Doc RH</Th>
                <Th>Titre</Th>
                <Th>Info cplt</Th>
                <Th className="text-center">Prio</Th>
                <Th className="text-center">DPAE</Th>
                <Th>Dern. modif</Th>
              </tr>
            </thead>
            <tbody>
              {(() => {
                // Regroupement par produit (cf. ruptures WinDev).
                // Les rows sont deja triees par lib_produit cote backend.
                const blocks: React.ReactNode[] = []
                let currentGroup: string | null = null
                rows.forEach((r) => {
                  const grp = r.lib_produit || 'Sans produit'
                  if (grp !== currentGroup) {
                    currentGroup = grp
                    blocks.push(
                      <tr key={`grp-${grp}`}>
                        <td
                          colSpan={6}
                          className="px-3 py-1.5 text-xs font-bold uppercase tracking-wide"
                          style={{
                            backgroundColor: COL_BG_SOFT,
                            color: COL_BRUN,
                            borderTop: `1px solid ${COL_BORDER}`,
                          }}
                        >
                          {grp}
                        </td>
                      </tr>,
                    )
                  }
                  const isSel = selected === r.id_doc_rh
                  blocks.push(
                    <tr
                      key={r.id_doc_rh}
                      onClick={() => setSelected(r.id_doc_rh)}
                      onDoubleClick={handleModifier}
                      className="cursor-pointer border-b"
                      style={{
                        backgroundColor: isSel ? COL_PRIMARY : 'white',
                        color: isSel ? 'white' : COL_BRUN,
                        borderColor: COL_BORDER,
                      }}
                    >
                      <Td>{r.lib_type}</Td>
                      <Td>{r.titre}</Td>
                      <Td>{r.info_cpl}</Td>
                      <Td className="text-center">{r.prioritaire ? '✓' : ''}</Td>
                      <Td className="text-center">{r.doc_dpae ? '✓' : ''}</Td>
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
        <DocRHEditModal
          idDocRh={editing}
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
        { v: true, l: 'Actifs' },
        { v: false, l: 'Archivés' },
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

function ToolbarBtn({
  icon,
  label,
  onClick,
  disabled,
  danger,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
  disabled?: boolean
  danger?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm border disabled:opacity-50"
      style={{
        borderColor: danger ? '#B91C1C' : COL_BORDER,
        color: danger ? '#B91C1C' : COL_BRUN,
        backgroundColor: COL_BG_SOFT,
      }}
    >
      {icon}
      {label}
    </button>
  )
}

function Th({
  children,
  className = '',
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <th className={`px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide ${className}`}>
      {children}
    </th>
  )
}

function Td({
  children,
  className = '',
}: {
  children: React.ReactNode
  className?: string
}) {
  return <td className={`px-3 py-2 whitespace-nowrap ${className}`}>{children}</td>
}
