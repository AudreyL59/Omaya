/**
 * Onglet 'Exo Cash' (livret) de la fiche salarie ADM.
 *
 * Transposition de FI_SalarieLivret :
 *  - Tableau Date / Operateur / Type / Debit / Credit
 *  - 3 boutons : Nouveau, Modifier, Supprimer (soft delete)
 *  - Pied : Somme Debit / Somme Credit
 *  - 3 lignes resultat : Solde Actuel, Commande en cours, Solde apres commande
 *    (vert si >0, rouge sinon)
 *
 * NB: Nouveau/Modifier sont en placeholder en attendant la transposition
 * de Fen_SalarieLivretFiche.
 */

import { useCallback, useEffect, useState } from 'react'
import { Loader2, Pencil, Plus, Trash2 } from 'lucide-react'

import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'
import SalarieLivretModal from './SalarieLivretModal'

interface LivretItem {
  id_salarie_livret: string
  date_operation: string
  id_type_operation_livret: number
  lib_type: string
  montant_debit: number
  montant_credit: number
  nom_prenom: string
}

interface Soldes {
  solde_actuel: number
  cde_en_cours: number
  solde_apres_cde: number
  somme_debit: number
  somme_credit: number
}

interface Props {
  idSalarie: string
}

const VERT_FONCE = '#15803D'
const ROUGE_FONCE = '#B91C1C'

function fmtDate(iso: string): string {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

function fmtMoney(v: number): string {
  if (!v) return ''
  return v.toLocaleString('fr-FR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function fmtMoneyAlways(v: number): string {
  return v.toLocaleString('fr-FR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export default function ExoCashTab({ idSalarie }: Props) {
  const [items, setItems] = useState<LivretItem[]>([])
  const [soldes, setSoldes] = useState<Soldes>({
    solde_actuel: 0,
    cde_en_cours: 0,
    solde_apres_cde: 0,
    somme_debit: 0,
    somme_credit: 0,
  })
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [editingId, setEditingId] = useState<string>('')

  const reload = useCallback(async () => {
    if (!idSalarie) return
    setLoading(true)
    try {
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/exo-cash`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as { items: LivretItem[]; soldes: Soldes }
      setItems(j.items || [])
      setSoldes(
        j.soldes || {
          solde_actuel: 0,
          cde_en_cours: 0,
          solde_apres_cde: 0,
          somme_debit: 0,
          somme_credit: 0,
        },
      )
      if (selected && !j.items?.some((i) => i.id_salarie_livret === selected)) {
        setSelected(null)
      }
    } catch (e) {
      showToast(`Échec chargement livret : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idSalarie, selected])

  useEffect(() => {
    void reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idSalarie])

  const selectedItem = items.find((i) => i.id_salarie_livret === selected) || null

  const handleNouveau = () => {
    setEditingId('')
    setEditOpen(true)
  }

  const handleModifier = () => {
    if (!selectedItem) {
      showToast('Sélectionner une opération à modifier.', 'info')
      return
    }
    setEditingId(selectedItem.id_salarie_livret)
    setEditOpen(true)
  }

  const handleSupprimer = async () => {
    if (!selectedItem) {
      showToast('Sélectionner une opération à supprimer.', 'info')
      return
    }
    const ok = await showConfirm({
      title: 'Supprimer cette ligne de livret ?',
      message: 'Vous êtes sur le point de supprimer cette ligne de livret. Voulez-vous continuer ?',
      confirmLabel: 'Supprimer',
      variant: 'danger',
    })
    if (!ok) return
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/exo-cash/${selectedItem.id_salarie_livret}`,
        { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      setSelected(null)
      await reload()
      showToast('Ligne supprimée.', 'success')
    } catch (e) {
      showToast(`Échec suppression : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const template = '110px 1fr 1fr 110px 110px'
  const colorSolde = (v: number) => (v > 0 ? VERT_FONCE : ROUGE_FONCE)

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

      {/* Tableau */}
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
          <div>Date opération</div>
          <div>Opérateur</div>
          <div>Type</div>
          <div className="text-right">Débit</div>
          <div className="text-right">Crédit</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {!loading && items.length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucune opération enregistrée.
            </div>
          )}
          {items.map((it) => {
            const sel = selected === it.id_salarie_livret
            return (
              <div
                key={it.id_salarie_livret}
                onClick={() => setSelected(it.id_salarie_livret)}
                onDoubleClick={() => {
                  setSelected(it.id_salarie_livret)
                  handleModifier()
                }}
                className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
                style={{
                  gridTemplateColumns: template,
                  backgroundColor: sel ? COLOR_BG_SOFT : 'white',
                  borderColor: COLOR_BG_SOFT,
                  color: COLOR_BRUN,
                }}
              >
                <div>{fmtDate(it.date_operation)}</div>
                <div className="truncate" title={it.nom_prenom}>
                  {it.nom_prenom}
                </div>
                <div className="truncate" title={it.lib_type}>
                  {it.lib_type}
                </div>
                <div className="text-right">{fmtMoney(it.montant_debit)}</div>
                <div className="text-right">{fmtMoney(it.montant_credit)}</div>
              </div>
            )
          })}
        </div>
        {/* Pied Somme */}
        <div
          className="grid items-center gap-2 px-3 py-1.5 text-xs font-semibold border-t"
          style={{
            gridTemplateColumns: template,
            backgroundColor: '#F0E6E2',
            borderColor: COLOR_BG_SOFT,
            color: COLOR_BRUN,
          }}
        >
          <div>Somme</div>
          <div />
          <div />
          <div className="text-right">{fmtMoneyAlways(soldes.somme_debit)} €</div>
          <div className="text-right">{fmtMoneyAlways(soldes.somme_credit)} €</div>
        </div>
      </div>

      {/* 3 lignes resultat */}
      <div
        className="flex-shrink-0 border rounded p-3 flex flex-col gap-1.5"
        style={{ borderColor: COLOR_BG_SOFT, backgroundColor: 'white' }}
      >
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-right font-semibold" style={{ color: COLOR_BRUN }}>
            Solde actuel
          </div>
          <div
            className="text-right font-bold"
            style={{ color: colorSolde(soldes.solde_actuel) }}
          >
            {fmtMoneyAlways(soldes.solde_actuel)} €
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-right font-semibold" style={{ color: COLOR_BRUN }}>
            Commande en cours
          </div>
          <div className="text-right font-bold" style={{ color: COLOR_BRUN }}>
            {fmtMoneyAlways(soldes.cde_en_cours)} €
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-right font-semibold" style={{ color: COLOR_BRUN }}>
            Solde après commande
          </div>
          <div
            className="text-right font-bold"
            style={{ color: colorSolde(soldes.solde_apres_cde) }}
          >
            {fmtMoneyAlways(soldes.solde_apres_cde)} €
          </div>
        </div>
      </div>

      {editOpen && (
        <SalarieLivretModal
          idSalarie={idSalarie}
          idLivret={editingId}
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
