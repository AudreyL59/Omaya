import { useCallback, useEffect, useState } from 'react'
import { Loader2, Save } from 'lucide-react'

import type { FIProps } from './index'

interface LigneFourniture {
  id: string
  id_type_commande: string
  lib_type_commande: string
  qte: number
  date_envoi: string // ISO YYYY-MM-DD ou ''
  priorite_haute: boolean
  num_suivi: string
  adr_livraison: string
}

export default function FIFourniture({ apiBase, getToken, idTicket }: FIProps) {
  const [lignes, setLignes] = useState<LigneFourniture[]>([])
  const [loading, setLoading] = useState(true)
  const [selId, setSelId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  // Champs d'édition (FichierVersEcran sur la ligne sélectionnée)
  const [qte, setQte] = useState(0)
  const [dateEnvoi, setDateEnvoi] = useState('')
  const [numSuivi, setNumSuivi] = useState('')
  const [adrLivraison, setAdrLivraison] = useState('')

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => {
        const ls: LigneFourniture[] = d?.data?.lignes || []
        setLignes(ls)
        if (ls.length > 0) selectLigne(ls[0])
        else setSelId(null)
      })
      .catch(() => setLignes([]))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, idTicket])

  useEffect(() => {
    reload()
  }, [reload])

  const selectLigne = (l: LigneFourniture) => {
    setSelId(l.id)
    setQte(l.qte)
    setDateEnvoi(l.date_envoi || '')
    setNumSuivi(l.num_suivi || '')
    setAdrLivraison(l.adr_livraison || '')
  }

  const enregistrer = async () => {
    if (!selId) return
    setSaving(true)
    try {
      const resp = await fetch(`${apiBase}/tickets/${idTicket}/form`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id_ligne: selId,
          qte,
          date_envoi: dateEnvoi,
          num_suivi: numSuivi,
          adr_livraison: adrLivraison,
        }),
      })
      if (!resp.ok) {
        const e = await resp.json().catch(() => null)
        window.alert(`Erreur : ${e?.detail || resp.status}`)
        return
      }
      reload()
    } catch {
      window.alert('Erreur réseau lors de l’enregistrement.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-c-ink-icon animate-spin" />
      </div>
    )
  }

  if (lignes.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-c-ink-faint text-sm">
        Aucune ligne de fourniture pour ce ticket.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Tableau des lignes */}
      <div className="border border-c-line rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-c-surface-soft text-xs text-c-ink-faint uppercase tracking-wide">
            <tr>
              <th className="px-3 py-2 text-left">Type Commande</th>
              <th className="px-3 py-2 text-center w-16">Qté</th>
              <th className="px-3 py-2 text-left w-36">Date Envoi/Récup</th>
              <th className="px-3 py-2 text-center w-20">Prioritaire</th>
              <th className="px-3 py-2 text-left">Num de Suivi</th>
            </tr>
          </thead>
          <tbody>
            {lignes.map((l) => (
              <tr
                key={l.id}
                onClick={() => selectLigne(l)}
                className={`border-t border-c-line-soft cursor-pointer transition-colors ${
                  selId === l.id
                    ? 'bg-c-brand-soft'
                    : 'hover:bg-c-surface-soft'
                }`}
              >
                <td className="px-3 py-2 text-c-ink">{l.lib_type_commande}</td>
                <td className="px-3 py-2 text-center tabular-nums">{l.qte}</td>
                <td className="px-3 py-2 tabular-nums text-c-ink-soft">
                  {fmtDate(l.date_envoi)}
                </td>
                <td className="px-3 py-2 text-center">
                  {l.priorite_haute ? '⚠️' : ''}
                </td>
                <td className="px-3 py-2 text-c-ink-soft">{l.num_suivi}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Formulaire d'édition de la ligne sélectionnée */}
      {selId && (
        <div className="border border-c-line rounded-lg p-4 bg-c-surface-soft space-y-3 max-w-md">
          <Field label="Qté">
            <input
              type="number"
              value={qte}
              onChange={(e) => setQte(Number(e.target.value))}
              className="w-28 px-2 py-1 border border-c-line-strong rounded-md text-sm"
            />
          </Field>
          <Field label="Date Envoi/Récupération">
            <input
              type="date"
              value={dateEnvoi}
              onChange={(e) => setDateEnvoi(e.target.value)}
              className="px-2 py-1 border border-c-line-strong rounded-md text-sm"
            />
          </Field>
          <Field label="Num de Suivi">
            <input
              value={numSuivi}
              onChange={(e) => setNumSuivi(e.target.value)}
              className="w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
            />
          </Field>
          <Field label="Adresse de livraison">
            <textarea
              value={adrLivraison}
              onChange={(e) => setAdrLivraison(e.target.value)}
              rows={3}
              className="w-full px-2 py-1 border border-c-line-strong rounded-md text-sm resize-y"
            />
          </Field>
          <button
            onClick={enregistrer}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50 transition-all"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Enregistrer
          </button>
        </div>
      )}
    </div>
  )
}

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-c-ink-soft">{label}</span>
      {children}
    </div>
  )
}

function fmtDate(iso: string): string {
  if (!iso) return ''
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/)
  return m ? `${m[3]}/${m[2]}/${m[1]}` : iso
}
