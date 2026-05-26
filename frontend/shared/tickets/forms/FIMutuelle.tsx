import { useCallback, useEffect, useState } from 'react'
import {
  Download, ExternalLink, FileText, Loader2, Save, Send,
} from 'lucide-react'

import type { FIProps } from './index'
import { showToast } from '../../ui/dialog'

// FI_Mutuelle (type 27) — Demande Mutuelle.
export default function FIMutuelle({ apiBase, getToken, idTicket }: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // Champs éditables
  const [affiliation, setAffiliation] = useState(false)
  const [affiliationDate, setAffiliationDate] = useState('')
  const [obser, setObser] = useState('')
  const [checked, setChecked] = useState<Record<string, boolean>>({})

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => {
        const dd = d?.data?.found ? d.data : null
        setData(dd)
        if (dd) {
          setAffiliation(!!dd.demande_affiliation)
          setAffiliationDate(dd.demande_affiliation_date || '')
          setChecked({})
        }
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, idTicket])

  useEffect(() => {
    reload()
  }, [reload])

  const post = async (body: any): Promise<any> => {
    setSaving(true)
    try {
      const resp = await fetch(`${apiBase}/tickets/${idTicket}/form`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(body),
      })
      const j = await resp.json().catch(() => null)
      if (!resp.ok) {
        showToast(`Erreur : ${j?.detail || resp.status}`, 'error')
        return null
      }
      return j ?? {}
    } catch {
      showToast('Erreur réseau.', 'error')
      return null
    } finally {
      setSaving(false)
    }
  }

  const fetchBlob = async (nom: string): Promise<Blob | null> => {
    try {
      const resp = await fetch(
        `${apiBase}/tickets/${idTicket}/form/file?name=${encodeURIComponent(nom)}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!resp.ok) {
        showToast(`Fichier introuvable : ${nom}`, 'error')
        return null
      }
      return await resp.blob()
    } catch {
      showToast('Erreur réseau (fichier).', 'error')
      return null
    }
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-c-ink-icon animate-spin" />
      </div>
    )
  }
  if (!data) {
    return (
      <div className="h-full flex items-center justify-center text-c-ink-faint text-sm">
        Aucune demande mutuelle pour ce ticket.
      </div>
    )
  }

  const pieces: any[] = data.pieces || []
  const selected = pieces.filter((p) => checked[p.id])

  const fmtDateFr = (iso: string) => {
    if (!iso || iso.length < 10) return ''
    return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
  }

  const enregistrer = async () => {
    const r = await post({
      action: 'enregistrer',
      demande_affiliation: affiliation,
      demande_affiliation_date: affiliationDate,
    })
    if (r) showToast('Informations enregistrées', 'success')
  }

  const ajouterObser = async () => {
    if (!obser.trim()) return
    const r = await post({ action: 'add_obser', observation: obser })
    if (r) {
      setObser('')
      setData((d: any) => ({ ...d, info_cplt: r.info_cplt }))
    }
  }

  const ouvrir = async () => {
    const cible = selected.length ? selected : pieces.slice(0, 1)
    for (const p of cible) {
      const blob = await fetchBlob(p.nom)
      if (blob) window.open(URL.createObjectURL(blob), '_blank')
    }
  }

  const telechargerSelection = async () => {
    if (!selected.length) {
      showToast('Cochez au moins un document.', 'error')
      return
    }
    for (const p of selected) {
      const blob = await fetchBlob(p.nom)
      if (blob) {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = p.nom
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
      }
    }
  }

  const toggleAll = (v: boolean) => {
    const m: Record<string, boolean> = {}
    if (v) pieces.forEach((p) => (m[p.id] = true))
    setChecked(m)
  }
  const allChecked = pieces.length > 0 && pieces.every((p) => checked[p.id])

  return (
    <div className="space-y-4">
      {/* En-tête salarié */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-c-ink-soft w-20">Nom</span>
          <span className="text-c-ink font-medium">{data.nom}</span>
        </div>
        <div className="row-span-3 text-right">
          <button
            disabled
            title="À venir avec le module Fiche salarié"
            className="inline-flex items-center gap-2 text-sm text-c-ink-faint cursor-not-allowed"
          >
            <FileText className="w-4 h-4" />
            Voir la fiche salarié
          </button>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-c-ink-soft w-20">Époux(se)</span>
          <span className="text-c-ink">{data.nom_marital || '—'}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-c-ink-soft w-20">Prénom</span>
          <span className="text-c-ink">{data.prenom}</span>
        </div>
        <div className="flex items-center gap-4 col-span-2">
          <label className="flex items-center gap-2 text-c-ink-soft">
            <input type="checkbox" checked={!!data.en_activite} disabled />
            En Activité
          </label>
          <span className="text-c-ink-soft">Date Début</span>
          <span className="text-c-ink">{fmtDateFr(data.date_debut) || '—'}</span>
        </div>
      </div>

      {/* INFOS TICKET MUTUELLE */}
      <div className="border-t border-c-line pt-3">
        <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide mb-2">
          Infos ticket mutuelle
        </h3>

        <div className="flex items-center gap-3 flex-wrap">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={affiliation}
              onChange={(e) => setAffiliation(e.target.checked)}
            />
            Demande Affiliation faite
          </label>
          <span className="text-sm text-c-ink-soft">Le</span>
          <input
            type="date"
            value={affiliationDate}
            onChange={(e) => setAffiliationDate(e.target.value)}
            className="px-2 py-1 border border-c-line-strong rounded-md text-sm"
          />
          <button
            onClick={enregistrer}
            disabled={saving}
            className="ml-auto flex items-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            Enregistrer
          </button>
        </div>

        {/* Journal d'observations (lecture seule) */}
        <label className="block text-sm mt-3">
          <span className="text-c-ink-soft">Info Cplt</span>
          <textarea
            value={data.info_cplt || ''}
            readOnly
            className="mt-1 w-full min-h-[120px] px-2 py-1 border border-c-line rounded-md text-sm resize-none bg-c-surface-soft"
          />
        </label>

        {/* Saisie d'une observation */}
        <div className="flex items-end gap-2 mt-2">
          <label className="block text-sm flex-1">
            <span className="text-c-ink-soft">Saisir Obser :</span>
            <input
              value={obser}
              onChange={(e) => setObser(e.target.value)}
              placeholder="1ère lettre en majuscule"
              onKeyDown={(e) => {
                if (e.key === 'Enter') ajouterObser()
              }}
              className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
            />
          </label>
          <button
            onClick={ajouterObser}
            disabled={saving || !obser.trim()}
            title="Ajouter l'observation"
            className="p-2 rounded-md bg-c-brand text-white hover:brightness-110 disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Pièces jointes */}
      <div className="border-t border-c-line pt-3">
        <div className="flex items-center gap-4 mb-2">
          <button
            onClick={telechargerSelection}
            disabled={!selected.length}
            className="flex items-center gap-2 text-sm text-c-brand hover:underline disabled:opacity-40 disabled:no-underline"
          >
            <Download className="w-4 h-4" />
            Télécharger la sélection
          </button>
          <button
            onClick={ouvrir}
            disabled={!pieces.length}
            className="flex items-center gap-2 text-sm text-c-brand hover:underline disabled:opacity-40 disabled:no-underline"
          >
            <ExternalLink className="w-4 h-4" />
            Ouvrir le document
          </button>
        </div>
        <div className="border border-c-line rounded-lg overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-c-surface-soft text-c-ink-soft text-left">
              <tr>
                <th className="px-2 py-2 w-16 text-center">
                  <input
                    type="checkbox"
                    checked={allChecked}
                    onChange={(e) => toggleAll(e.target.checked)}
                  />
                </th>
                <th className="px-2 py-2">NomFichier</th>
              </tr>
            </thead>
            <tbody>
              {pieces.length === 0 ? (
                <tr>
                  <td colSpan={2} className="px-2 py-4 text-center text-c-ink-faint">
                    Aucun document.
                  </td>
                </tr>
              ) : (
                pieces.map((p) => (
                  <tr
                    key={p.id}
                    className="border-t border-c-line hover:bg-c-surface-soft"
                  >
                    <td className="px-2 py-1.5 text-center">
                      <input
                        type="checkbox"
                        checked={!!checked[p.id]}
                        onChange={(e) =>
                          setChecked((m) => ({ ...m, [p.id]: e.target.checked }))
                        }
                      />
                    </td>
                    <td
                      className="px-2 py-1.5 cursor-pointer"
                      onClick={async () => {
                        const blob = await fetchBlob(p.nom)
                        if (blob) window.open(URL.createObjectURL(blob), '_blank')
                      }}
                    >
                      {p.nom}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
