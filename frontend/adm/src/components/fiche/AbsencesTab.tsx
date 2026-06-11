/**
 * Onglet 'Absences' de la fiche salarie ADM.
 *
 * Transposition de la fenetre WinDev FI_SalarieAbsences :
 *  - Tableau hierarchique groupe par Periode (AnneeConge, du 1er juin N
 *    au 31 mai N+1) puis par Type d'absence.
 *  - 4 boutons : Nouveau, Modifier, Dupliquer, Supprimer.
 *
 * Pour ce commit on a tableau + Dupliquer + Supprimer. Nouveau/Modifier
 * en placeholder en attendant le commit qui code Fen_SalarieAbsence.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Copy, Loader2, Pencil, Plus, Trash2 } from 'lucide-react'

import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'
import SalarieAbsenceModal from './SalarieAbsenceModal'

interface AbsenceItem {
  id_absence: string
  id_type_absence: number
  lib_absence: string
  date_debut: string
  date_fin: string
  nbj: number
  nbj_ouvres: number
  nb_samedi: number
  periode: string
}

interface Props {
  idSalarie: string
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

interface Group {
  key: string
  label: string
  types: { id_type: number; label: string; items: AbsenceItem[]; totals: { nbj: number; nbj_ouvres: number; nb_samedi: number } }[]
  totals: { nbj: number; nbj_ouvres: number; nb_samedi: number }
}

export default function AbsencesTab({ idSalarie }: Props) {
  const [items, setItems] = useState<AbsenceItem[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [editingId, setEditingId] = useState<string>('')

  const reload = useCallback(async () => {
    if (!idSalarie) return
    setLoading(true)
    try {
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/absences`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as { items: AbsenceItem[] }
      setItems(j.items || [])
      if (selected && !j.items.some((i) => i.id_absence === selected)) {
        setSelected(null)
      }
    } catch (e) {
      showToast(`Échec chargement absences : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idSalarie, selected])

  useEffect(() => {
    void reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idSalarie])

  // Groupage hierarchique : Periode > Type d'absence
  const groups = useMemo<Group[]>(() => {
    const map = new Map<string, Group>()
    for (const it of items) {
      const pkey = it.periode || '(sans période)'
      let g = map.get(pkey)
      if (!g) {
        g = {
          key: pkey,
          label: pkey,
          types: [],
          totals: { nbj: 0, nbj_ouvres: 0, nb_samedi: 0 },
        }
        map.set(pkey, g)
      }
      let t = g.types.find((x) => x.id_type === it.id_type_absence)
      if (!t) {
        t = {
          id_type: it.id_type_absence,
          label: it.lib_absence || `Type ${it.id_type_absence}`,
          items: [],
          totals: { nbj: 0, nbj_ouvres: 0, nb_samedi: 0 },
        }
        g.types.push(t)
      }
      t.items.push(it)
      t.totals.nbj += it.nbj
      t.totals.nbj_ouvres += it.nbj_ouvres
      t.totals.nb_samedi += it.nb_samedi
      g.totals.nbj += it.nbj
      g.totals.nbj_ouvres += it.nbj_ouvres
      g.totals.nb_samedi += it.nb_samedi
    }
    return Array.from(map.values())
  }, [items])

  const selectedItem = useMemo(
    () => items.find((i) => i.id_absence === selected) || null,
    [items, selected],
  )

  const handleNouveau = () => {
    setEditingId('')
    setEditOpen(true)
  }

  const handleModifier = () => {
    if (!selectedItem) {
      showToast('Sélectionner une absence à modifier.', 'info')
      return
    }
    setEditingId(selectedItem.id_absence)
    setEditOpen(true)
  }

  const handleDupliquer = async () => {
    if (!selectedItem) {
      showToast('Sélectionner une absence à dupliquer.', 'info')
      return
    }
    const ok = await showConfirm({
      title: 'Dupliquer cette absence ?',
      message: 'Vous êtes sur le point de dupliquer cette absence. Voulez-vous continuer ?',
      confirmLabel: 'Dupliquer',
    })
    if (!ok) return
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/absences/${selectedItem.id_absence}/duplicate`,
        { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      await reload()
      showToast('Absence dupliquée.', 'success')
    } catch (e) {
      showToast(`Échec duplication : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleSupprimer = async () => {
    if (!selectedItem) {
      showToast('Sélectionner une absence à supprimer.', 'info')
      return
    }
    const ok = await showConfirm({
      title: 'Supprimer cette absence ?',
      message: 'Vous êtes sur le point de supprimer cette absence. Voulez-vous continuer ?',
      confirmLabel: 'Supprimer',
      variant: 'danger',
    })
    if (!ok) return
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/absences/${selectedItem.id_absence}`,
        { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      setSelected(null)
      await reload()
      showToast('Absence supprimée.', 'success')
    } catch (e) {
      showToast(`Échec suppression : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const template = '1fr 90px 90px 100px 130px 100px'

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <ToolBtn icon={Plus} label="Nouveau" onClick={handleNouveau} primary />
        <ToolBtn
          icon={Pencil}
          label="Modifier"
          onClick={handleModifier}
          disabled={!selectedItem || busy}
        />
        <ToolBtn
          icon={Copy}
          label="Dupliquer"
          onClick={handleDupliquer}
          disabled={!selectedItem || busy}
        />
        <ToolBtn
          icon={Trash2}
          label="Supprimer"
          onClick={handleSupprimer}
          disabled={!selectedItem || busy}
          danger
        />
        {(loading || busy) && (
          <Loader2 className="w-4 h-4 animate-spin ml-2" style={{ color: COLOR_PRIMARY }} />
        )}
      </div>

      <p className="text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
        * Période du 1er juin N au 31 mai N+1
      </p>

      {/* Tableau hierarchique */}
      <div
        className="flex-1 border rounded overflow-hidden flex flex-col"
        style={{ borderColor: COLOR_BG_SOFT }}
      >
        {/* Header */}
        <div
          className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
          style={{
            gridTemplateColumns: template,
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div>Motif</div>
          <div>Du</div>
          <div>Au</div>
          <div className="text-right">Nb Jours cal.</div>
          <div className="text-right">Nb Jours ouvrés (HS)</div>
          <div className="text-right">Nb Samedi</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {!loading && groups.length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucune absence enregistrée.
            </div>
          )}
          {groups.map((g) => (
            <div key={g.key}>
              {/* Bandeau Periode */}
              <div
                className="px-3 py-1.5 text-xs font-bold"
                style={{ backgroundColor: '#F7EEEB', color: COLOR_BRUN }}
              >
                Période {g.label}
              </div>
              {g.types.map((t) => (
                <div key={`${g.key}-${t.id_type}`}>
                  {/* Bandeau Type */}
                  <div
                    className="px-3 py-1 text-xs italic"
                    style={{ backgroundColor: '#FBF6F4', color: COLOR_BRUN, opacity: 0.85 }}
                  >
                    — {t.label}
                  </div>
                  {t.items.map((it) => {
                    const selectedRow = selected === it.id_absence
                    return (
                      <div
                        key={it.id_absence}
                        onClick={() => setSelected(it.id_absence)}
                        onDoubleClick={() => {
                          setSelected(it.id_absence)
                          handleModifier()
                        }}
                        className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
                        style={{
                          gridTemplateColumns: template,
                          backgroundColor: selectedRow ? COLOR_BG_SOFT : 'white',
                          borderColor: COLOR_BG_SOFT,
                          color: COLOR_BRUN,
                        }}
                      >
                        <div className="truncate font-medium" title={it.lib_absence}>
                          {it.lib_absence || '—'}
                        </div>
                        <div>{fmtDate(it.date_debut)}</div>
                        <div>{fmtDate(it.date_fin)}</div>
                        <div className="text-right">{it.nbj || ''}</div>
                        <div className="text-right">{it.nbj_ouvres || ''}</div>
                        <div className="text-right">{it.nb_samedi || ''}</div>
                      </div>
                    )
                  })}
                  {/* Total Type */}
                  <div
                    className="grid items-center gap-2 px-3 py-1 text-xs border-b"
                    style={{
                      gridTemplateColumns: template,
                      backgroundColor: '#FBF9F8',
                      borderColor: COLOR_BG_SOFT,
                      color: COLOR_BRUN,
                      fontStyle: 'italic',
                    }}
                  >
                    <div>Total {t.label}</div>
                    <div />
                    <div />
                    <div className="text-right">{t.totals.nbj}</div>
                    <div className="text-right">{t.totals.nbj_ouvres}</div>
                    <div className="text-right">{t.totals.nb_samedi}</div>
                  </div>
                </div>
              ))}
              {/* Total Periode */}
              <div
                className="grid items-center gap-2 px-3 py-1.5 text-xs border-b font-semibold"
                style={{
                  gridTemplateColumns: template,
                  backgroundColor: '#F0E6E2',
                  borderColor: COLOR_BG_SOFT,
                  color: COLOR_BRUN,
                }}
              >
                <div>Total période {g.label}</div>
                <div />
                <div />
                <div className="text-right">{g.totals.nbj}</div>
                <div className="text-right">{g.totals.nbj_ouvres}</div>
                <div className="text-right">{g.totals.nb_samedi}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {editOpen && (
        <SalarieAbsenceModal
          idSalarie={idSalarie}
          idAbsence={editingId}
          onClose={() => setEditOpen(false)}
          onSaved={() => {
            setEditOpen(false)
            void reload()
          }}
        />
      )}
    </div>
  )
}

function ToolBtn({
  icon: Icon,
  label,
  onClick,
  disabled,
  primary,
  danger,
}: {
  icon: typeof Plus
  label: string
  onClick: () => void
  disabled?: boolean
  primary?: boolean
  danger?: boolean
}) {
  const color = primary ? 'white' : danger ? '#B91C1C' : COLOR_PRIMARY
  const bg = primary ? COLOR_PRIMARY : 'white'
  const border = primary ? COLOR_PRIMARY : danger ? '#B91C1C' : COLOR_PRIMARY
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border disabled:opacity-40"
      style={{ backgroundColor: bg, color, borderColor: border }}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  )
}
