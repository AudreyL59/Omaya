/**
 * Onglet 'Accès Omaya' (Droits d'accès) de la fiche salarie ADM.
 *
 * Transposition de FI_SalarieDroitAcces.
 *
 * Etape 1 (ce commit) :
 *   - Tableau hierarchique (rupture par Categorie) avec checkbox de
 *     selection multiple.
 *   - Bouton 'Activer/desactiver la selection' : toggle droit_actif.
 *   - Bouton 'Supprimer' : soft delete.
 *
 * Etapes suivantes (commits dedies) :
 *   - Bouton 'Droit Intranet/Appli' : popup ajout (ADM=0, FDV=1) +
 *     combo Profil + Choisir ce profil.
 *   - Bouton 'Droit Omaya Software' : popup ajout (ADM=1, FDV=0,
 *     restreint aux droits de l'operateur connecte).
 *   - Bouton 'Envoyer code Omaya' : genere/recupere MDP + envoie mail
 *     + SMS.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2, Plus, Power, Send, Trash2 } from 'lucide-react'

import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'
import DroitAccesAjoutModal from './DroitAccesAjoutModal'

interface DroitRow {
  id_salarie_droit_acces: string
  id_type_droit_acces: number
  lib_droit: string
  code_interne: string
  description: string
  adm: boolean
  fdv: boolean
  categorie: string
  droit_actif: boolean
}

interface Props {
  idSalarie: string
}

export default function AccesOmayaTab({ idSalarie }: Props) {
  const [rows, setRows] = useState<DroitRow[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [busy, setBusy] = useState(false)
  const [ajoutVariant, setAjoutVariant] = useState<'intranet' | 'software' | null>(null)
  const [sendingCodes, setSendingCodes] = useState(false)

  const reload = useCallback(async () => {
    if (!idSalarie) return
    setLoading(true)
    try {
      const r = await fetch(`/api/adm/fiche-salarie/${idSalarie}/droit-acces`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as { items: DroitRow[] }
      setRows(j.items || [])
    } catch (e) {
      showToast(`Échec chargement : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idSalarie])

  useEffect(() => {
    void reload()
  }, [reload])

  const groups = useMemo(() => {
    const map = new Map<string, DroitRow[]>()
    for (const r of rows) {
      const k = r.categorie || '(sans catégorie)'
      const arr = map.get(k) || []
      arr.push(r)
      map.set(k, arr)
    }
    return Array.from(map.entries()).map(([key, items]) => ({ key, items }))
  }, [rows])

  const toggleRow = (id_type: number) => {
    const next = new Set(selected)
    if (next.has(id_type)) next.delete(id_type)
    else next.add(id_type)
    setSelected(next)
  }

  const toggleAll = () => {
    if (selected.size === rows.length) setSelected(new Set())
    else setSelected(new Set(rows.map((r) => r.id_type_droit_acces)))
  }

  const handleActiverDesactiver = async () => {
    if (selected.size === 0) {
      showToast('Sélectionner au moins une ligne.', 'info')
      return
    }
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/droit-acces/toggle`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({ id_types: Array.from(selected) }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const j = (await r.json()) as { nb_toggled: number }
      showToast(`${j.nb_toggled} droit(s) basculé(s).`, 'success')
      await reload()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleSupprimer = async () => {
    if (selected.size === 0) {
      showToast('Sélectionner au moins une ligne.', 'info')
      return
    }
    const ok = await showConfirm({
      title: 'Supprimer les droits sélectionnés ?',
      message: `Vous êtes sur le point de supprimer ${selected.size} droit(s) d'accès. Voulez-vous continuer ?`,
      confirmLabel: 'Supprimer',
      variant: 'danger',
    })
    if (!ok) return
    setBusy(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/droit-acces/delete`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({ id_types: Array.from(selected) }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const j = (await r.json()) as { nb_deleted: number }
      showToast(`${j.nb_deleted} droit(s) supprimé(s).`, 'success')
      setSelected(new Set())
      await reload()
    } catch (e) {
      showToast(`Échec suppression : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleEnvoyerCodes = async () => {
    const ok = await showConfirm({
      title: 'Envoyer les codes ?',
      message: "Envoyer le login et le mot de passe Omaya par mail (et SMS si numéro mobile présent) au salarié ?",
      confirmLabel: 'Envoyer',
    })
    if (!ok) return
    setSendingCodes(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/droit-acces/send-codes`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const j = (await r.json()) as {
        ok: boolean
        mail_envoye: boolean
        sms_envoye: boolean
        sms_result: string
        error?: string
      }
      if (!j.ok) {
        showToast(j.error || 'Échec', 'error')
        return
      }
      const parts: string[] = []
      if (j.mail_envoye) parts.push('mail envoyé')
      if (j.sms_envoye) parts.push('SMS envoyé')
      if (parts.length === 0) {
        showToast(`Aucun envoi (${j.sms_result || 'pas de mail ni GSM'})`, 'info')
      } else {
        showToast(`Codes : ${parts.join(' + ')}`, 'success')
      }
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSendingCodes(false)
    }
  }

  const template = '36px 70px 220px 1fr 70px 90px 90px'

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <ToolBtn
          icon={Plus}
          label="Droit Intranet/Appli"
          onClick={() => setAjoutVariant('intranet')}
          primary
        />
        <ToolBtn
          icon={Plus}
          label="Droit Omaya Software"
          onClick={() => setAjoutVariant('software')}
          primary
        />
        <ToolBtn
          icon={Power}
          label="Activer/désactiver la sélection"
          onClick={handleActiverDesactiver}
          disabled={selected.size === 0 || busy}
        />
        <ToolBtn
          icon={sendingCodes ? Loader2 : Send}
          spin={sendingCodes}
          label="Envoyer code Omaya"
          onClick={handleEnvoyerCodes}
          disabled={sendingCodes}
        />
        <ToolBtn
          icon={Trash2}
          label="Supprimer"
          onClick={handleSupprimer}
          disabled={selected.size === 0 || busy}
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
        <div
          className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
          style={{
            gridTemplateColumns: template,
            color: COLOR_BRUN,
            backgroundColor: COLOR_BG_SOFT,
            borderColor: COLOR_BG_SOFT,
          }}
        >
          <div className="flex justify-center">
            <input
              type="checkbox"
              checked={rows.length > 0 && selected.size === rows.length}
              onChange={toggleAll}
            />
          </div>
          <div>ID</div>
          <div>Libellé</div>
          <div>Description</div>
          <div className="text-center">Actif</div>
          <div className="text-center">Software</div>
          <div className="text-center">Intranet</div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {!loading && rows.length === 0 && (
            <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
              Aucun droit d'accès attribué.
            </div>
          )}
          {groups.map((g) => (
            <div key={g.key}>
              <div
                className="px-3 py-1 text-xs font-bold"
                style={{ backgroundColor: '#F7EEEB', color: COLOR_BRUN }}
              >
                {g.key}
              </div>
              {g.items.map((it) => {
                const sel = selected.has(it.id_type_droit_acces)
                return (
                  <div
                    key={it.id_type_droit_acces}
                    onClick={() => toggleRow(it.id_type_droit_acces)}
                    className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
                    style={{
                      gridTemplateColumns: template,
                      backgroundColor: sel ? COLOR_BG_SOFT : 'white',
                      borderColor: COLOR_BG_SOFT,
                      color: COLOR_BRUN,
                    }}
                  >
                    <div className="flex justify-center">
                      <input
                        type="checkbox"
                        checked={sel}
                        onChange={() => toggleRow(it.id_type_droit_acces)}
                      />
                    </div>
                    <div className="font-mono">{it.id_type_droit_acces}</div>
                    <div className="truncate" title={it.lib_droit}>
                      {it.lib_droit}
                    </div>
                    <div
                      className="truncate"
                      title={it.description.replace(/<[^>]+>/g, '')}
                      dangerouslySetInnerHTML={{ __html: it.description }}
                    />
                    <div className="text-center">
                      {it.droit_actif ? '✓' : ''}
                    </div>
                    <div className="text-center">{it.adm ? '✓' : ''}</div>
                    <div className="text-center">{it.fdv ? '✓' : ''}</div>
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>

      {ajoutVariant && (
        <DroitAccesAjoutModal
          idSalarie={idSalarie}
          variant={ajoutVariant}
          onClose={() => setAjoutVariant(null)}
          onSaved={() => {
            setAjoutVariant(null)
            setSelected(new Set())
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
  spin,
}: {
  icon: typeof Plus
  label: string
  onClick: () => void
  disabled?: boolean
  primary?: boolean
  danger?: boolean
  spin?: boolean
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
      <Icon className={`w-4 h-4 ${spin ? 'animate-spin' : ''}`} />
      {label}
    </button>
  )
}
