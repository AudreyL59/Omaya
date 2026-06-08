/**
 * Onglet 'Organigramme' de la fiche salarie ADM.
 *
 * Transposition de la fenetre WinDev FI_SalarieOrgaSuivi :
 *  - Tableau 1 : rattachements (pgt_salarie_organigramme)
 *  - Tableau 2 : suivis (pgt_salarie_suivi)
 *  - Boutons : Nouveau / Dupliquer / Supprimer / Modifier
 *
 * Le Nouveau / Modifier ouvre SalarieOrgaModal (popup d'edition avec arbre).
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Copy, Pencil, Plus, Trash2, Loader2 } from 'lucide-react'

import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'
import SalarieOrgaModal from './SalarieOrgaModal'

interface OrgaItem {
  id_salarie_organigramme: string
  id_organigramme: string
  lib_orga: string
  type_produit_lib: string
  date_debut: string
  date_fin: string
  aff_actif: boolean
}

interface SuiviItem {
  id_suivi: string
  type: number
  type_lib: string
  id_organigramme: string
  lib_orga: string
  id_type_poste: number
  lib_poste: string
  date_debut: string
  date_fin: string
  modif_date: string
}

interface OrgaSuiviData {
  organigrammes: OrgaItem[]
  suivis: SuiviItem[]
}

interface Props {
  idSalarie: string
}

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

function fmtDateTime(iso: string): string {
  if (!iso || iso.length < 10) return ''
  const d = fmtDate(iso)
  if (iso.length < 16) return d
  return `${d} ${iso.slice(11, 16)}`
}

export default function OrgaSuiviTab({ idSalarie }: Props) {
  const [data, setData] = useState<OrgaSuiviData | null>(null)
  const [loading, setLoading] = useState(false)
  const [selectedOrga, setSelectedOrga] = useState<string | null>(null)
  const [editOpen, setEditOpen] = useState(false)
  const [editingId, setEditingId] = useState<string>('')

  const reload = useCallback(async () => {
    if (!idSalarie) return
    setLoading(true)
    try {
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/orga`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as OrgaSuiviData
      setData(j)
      if (selectedOrga && !j.organigrammes.some((o) => o.id_salarie_organigramme === selectedOrga)) {
        setSelectedOrga(null)
      }
    } catch (e) {
      showToast(`Échec chargement organigramme : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idSalarie, selectedOrga])

  useEffect(() => {
    void reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idSalarie])

  const selectedItem = useMemo(
    () =>
      data?.organigrammes.find((o) => o.id_salarie_organigramme === selectedOrga) || null,
    [data, selectedOrga],
  )

  const handleNouveau = () => {
    setEditingId('')
    setEditOpen(true)
  }

  const handleModifier = () => {
    if (!selectedItem) {
      showToast('Sélectionner un rattachement à modifier.', 'info')
      return
    }
    setEditingId(selectedItem.id_salarie_organigramme)
    setEditOpen(true)
  }

  const handleDupliquer = async () => {
    if (!selectedItem) {
      showToast('Sélectionner un rattachement à dupliquer.', 'info')
      return
    }
    const ok = await showConfirm({
      title: 'Dupliquer ce rattachement ?',
      message: 'Vous êtes sur le point de dupliquer ce document. Voulez-vous continuer ?',
      confirmLabel: 'Dupliquer',
    })
    if (!ok) return
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/orga/${selectedItem.id_salarie_organigramme}/duplicate`,
        { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      await reload()
      showToast('Rattachement dupliqué.', 'success')
    } catch (e) {
      showToast(`Échec duplication : ${(e as Error).message}`, 'error')
    }
  }

  const handleSupprimer = async () => {
    if (!selectedItem) {
      showToast('Sélectionner un rattachement à supprimer.', 'info')
      return
    }
    const ok = await showConfirm({
      title: 'Supprimer ce rattachement ?',
      message: 'Vous êtes sur le point de supprimer ce rattachement. Voulez-vous continuer ?',
      confirmLabel: 'Supprimer',
      variant: 'danger',
    })
    if (!ok) return
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/orga/${selectedItem.id_salarie_organigramme}`,
        { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      setSelectedOrga(null)
      await reload()
      showToast('Rattachement supprimé.', 'success')
    } catch (e) {
      showToast(`Échec suppression : ${(e as Error).message}`, 'error')
    }
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <ToolBtn icon={Plus} label="Nouveau" onClick={handleNouveau} primary />
        <ToolBtn
          icon={Copy}
          label="Dupliquer"
          onClick={handleDupliquer}
          disabled={!selectedItem}
        />
        <ToolBtn
          icon={Trash2}
          label="Supprimer"
          onClick={handleSupprimer}
          disabled={!selectedItem}
          danger
        />
        <ToolBtn
          icon={Pencil}
          label="Modifier"
          onClick={handleModifier}
          disabled={!selectedItem}
        />
        {loading && <Loader2 className="w-4 h-4 animate-spin ml-2" style={{ color: COLOR_PRIMARY }} />}
      </div>

      {/* Table 1 : Rattachements */}
      <div className="border rounded overflow-hidden" style={{ borderColor: COLOR_BG_SOFT }}>
        <div
          className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
          style={{
            gridTemplateColumns: '110px 1fr 110px 110px 70px',
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div>Type Produit</div>
          <div>Nom Equipe/Agence</div>
          <div>Date de début</div>
          <div>Date de fin</div>
          <div className="text-center">Actif</div>
        </div>
        <div className="max-h-[280px] overflow-y-auto">
          {(data?.organigrammes || []).length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucun rattachement.
            </div>
          )}
          {data?.organigrammes.map((o) => {
            const selected = selectedOrga === o.id_salarie_organigramme
            return (
              <div
                key={o.id_salarie_organigramme}
                onClick={() => setSelectedOrga(o.id_salarie_organigramme)}
                onDoubleClick={() => {
                  setSelectedOrga(o.id_salarie_organigramme)
                  setEditingId(o.id_salarie_organigramme)
                  setEditOpen(true)
                }}
                className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
                style={{
                  gridTemplateColumns: '110px 1fr 110px 110px 70px',
                  backgroundColor: selected ? COLOR_BG_SOFT : 'white',
                  borderColor: COLOR_BG_SOFT,
                  color: COLOR_BRUN,
                }}
              >
                <div className="truncate" title={o.type_produit_lib}>
                  {o.type_produit_lib}
                </div>
                <div className="truncate font-medium" title={o.lib_orga}>
                  {o.lib_orga}
                </div>
                <div>{fmtDate(o.date_debut)}</div>
                <div>{fmtDate(o.date_fin)}</div>
                <div className="text-center">{o.aff_actif ? '✓' : ''}</div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Table 2 : Suivis */}
      <div className="border rounded overflow-hidden" style={{ borderColor: COLOR_BG_SOFT }}>
        <div
          className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
          style={{
            gridTemplateColumns: '160px 1fr 90px 90px 130px',
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div>TYPE Suivi</div>
          <div>Nouv. Equipe/Poste/Entité</div>
          <div>Du*</div>
          <div>Au*</div>
          <div>Dernière modif</div>
        </div>
        <div className="max-h-[280px] overflow-y-auto">
          {(data?.suivis || []).length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucun suivi enregistré.
            </div>
          )}
          {data?.suivis.map((s) => (
            <div
              key={s.id_suivi}
              className="grid items-center gap-2 px-3 py-1.5 text-xs border-b"
              style={{
                gridTemplateColumns: '160px 1fr 90px 90px 130px',
                borderColor: COLOR_BG_SOFT,
                color: COLOR_BRUN,
              }}
            >
              <div className="truncate" title={s.type_lib}>
                {s.type_lib}
              </div>
              <div className="truncate" title={s.lib_orga || s.lib_poste}>
                {s.lib_orga || s.lib_poste}
              </div>
              <div>{fmtDate(s.date_debut)}</div>
              <div>{fmtDate(s.date_fin)}</div>
              <div>{fmtDateTime(s.modif_date)}</div>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs italic flex-shrink-0" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
        * Date d'exécution du changement
      </p>

      {editOpen && (
        <SalarieOrgaModal
          idSalarie={idSalarie}
          idSalarieOrga={editingId}
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
