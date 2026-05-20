import { useCallback, useEffect, useState } from 'react'
import {
  CheckCircle2, ExternalLink, Loader2, Plus, RefreshCw, Save, Trash2,
} from 'lucide-react'

import type { FIProps } from './index'

// FI_CdeExoCash (type 24) — Commande ExoCash.
const TRANSPORTEURS = ['COLISSIMO', 'DPD', 'CHRONOPOST']

export default function FICdeExoCash({ apiBase, getToken, idTicket }: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [addLotId, setAddLotId] = useState(0)
  const [editEnvoi, setEditEnvoi] = useState<any | null>(null)

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => setData(d?.data?.found ? d.data : null))
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
        window.alert(`Erreur : ${j?.detail || resp.status}`)
        return null
      }
      return j ?? {}
    } catch {
      window.alert('Erreur réseau.')
      return null
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
  if (!data) {
    return (
      <div className="h-full flex items-center justify-center text-c-ink-faint text-sm">
        Aucune commande ExoCash pour ce ticket.
      </div>
    )
  }

  const panier: any[] = data.panier || []
  const envois: any[] = data.envois || []
  const lotsDispos: any[] = data.lots_dispos || []
  const validee = !!data.commande_validee
  const solde = Number(data.solde || 0)
  const montant = Number(data.montant_global || 0)
  const soldeInsuffisant = montant > solde

  // ExoCash = monnaie virtuelle interne (unité EC, pas €)
  const fmt = (n: number) => `${(n || 0).toFixed(2)} EC`

  const valider = async () => {
    if (
      !window.confirm(
        'Vous êtes sur le point de valider la commande.\n' +
          'Les stocks et le livret ExoCash du salarié seront mis à jour.\n' +
          'Continuer ?',
      )
    )
      return
    const r = await post({ action: 'valider' })
    if (r) {
      window.alert('Commande validée. SMS au salarié : ' + (r.sms_result || 'envoyé'))
      reload()
    }
  }

  const actualiserSolde = async () => {
    const r = await post({ action: 'actualiser_solde' })
    if (r) reload()
  }

  const addLot = async () => {
    if (!addLotId) return
    const r = await post({ action: 'add_lot', id_lot: addLotId })
    if (r) {
      setAddLotId(0)
      reload()
    }
  }

  const delLot = async (idPanier: string) => {
    if (!window.confirm('Supprimer ce lot du panier ?')) return
    const r = await post({ action: 'del_lot', id_panier: idPanier })
    if (r) reload()
  }

  const updateLotQte = async (idPanier: string, qte: number, numSuivi: string) => {
    const r = await post({
      action: 'update_lot', id_panier: idPanier, qte, num_suivi: numSuivi,
    })
    if (r) reload()
  }

  const submitEnvoi = async () => {
    if (!editEnvoi) return
    const r = await post({
      action: editEnvoi.id_envoi ? 'update_envoi' : 'add_envoi',
      id_envoi: editEnvoi.id_envoi,
      num_suivi: editEnvoi.num_suivi,
      date_envoi: editEnvoi.date_envoi,
      transporteur: editEnvoi.transporteur,
      adresse: editEnvoi.adresse,
    })
    if (r) {
      setEditEnvoi(null)
      reload()
    }
  }

  const delEnvoi = async (idEnvoi: string) => {
    if (!window.confirm('Supprimer ce suivi ?')) return
    const r = await post({ action: 'del_envoi', id_envoi: idEnvoi })
    if (r) reload()
  }

  const trackingUrl = (transporteur: string, num: string) => {
    if (!num) return ''
    const t = (transporteur || '').toUpperCase()
    if (t.includes('COLIS'))
      return `https://www.laposte.fr/outils/suivre-vos-envois?code=${encodeURIComponent(num)}`
    if (t.includes('CHRONO'))
      return `https://www.chronopost.fr/tracking-no-cms/suivi-page?listeNumerosLT=${encodeURIComponent(num)}`
    if (t.includes('DPD'))
      return `https://www.dpd.fr/trace/${encodeURIComponent(num)}`
    return ''
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="grid grid-cols-3 gap-3 items-center">
        <div className="text-sm">
          <div className="text-c-ink-soft">Commande faite le</div>
          <div className="text-c-ink">{data.date_commande || '—'}</div>
        </div>
        <div className="text-sm">
          <div className="text-c-ink-soft">Montant global</div>
          <div className="text-c-ink font-semibold">{fmt(montant)}</div>
          <div className="text-c-ink-soft mt-1">Solde du salarié</div>
          <div
            className={
              'font-semibold ' + (soldeInsuffisant ? 'text-red-600' : 'text-c-ink')
            }
          >
            {fmt(solde)}
          </div>
          <button
            onClick={actualiserSolde}
            className="text-xs text-c-brand hover:underline flex items-center gap-1 mt-1"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Actualiser solde
          </button>
        </div>
        <div className="text-right">
          {validee ? (
            <div className="text-sm bg-c-brand-soft text-c-brand-strong rounded-lg px-3 py-2 inline-block">
              ✓ Commande validée le {data.date_validation || '—'}
              {data.op_validation_nom && (
                <> par {data.op_validation_nom}</>
              )}
            </div>
          ) : (
            <button
              onClick={valider}
              disabled={saving || soldeInsuffisant || panier.length === 0}
              title={soldeInsuffisant ? 'Solde insuffisant' : ''}
              className="px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
            >
              <CheckCircle2 className="w-4 h-4 inline mr-1" />
              Valider la commande
            </button>
          )}
        </div>
      </div>

      {/* Panier */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide flex-1">
            Panier
          </h3>
          {!validee && (
            <>
              <select
                value={addLotId}
                onChange={(e) => setAddLotId(Number(e.target.value))}
                className="px-2 py-1 border border-c-line-strong rounded-md text-xs bg-white"
              >
                <option value={0}>— Ajouter un lot —</option>
                {lotsDispos.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.libfam} / {l.marque} / {l.liblot}
                    {l.pour ? ` (${l.pour})` : ''} — {fmt(l.montant)}
                    {l.stock > 0 ? ` (stock ${l.stock})` : ' (rupture)'}
                  </option>
                ))}
              </select>
              <button
                onClick={addLot}
                disabled={!addLotId || saving}
                className="p-1.5 rounded-md border border-c-line-strong hover:bg-c-brand-soft disabled:opacity-50"
              >
                <Plus className="w-4 h-4 text-c-brand" />
              </button>
            </>
          )}
        </div>
        <div className="border border-c-line rounded-lg overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-c-surface-soft text-c-ink-soft text-left">
              <tr>
                <th className="px-2 py-2">Famille</th>
                <th className="px-2 py-2">Marque</th>
                <th className="px-2 py-2">Lot</th>
                <th className="px-2 py-2">Pour</th>
                <th className="px-2 py-2 w-24 text-right">Montant U</th>
                <th className="px-2 py-2 w-16 text-center">Qté</th>
                <th className="px-2 py-2 w-16 text-center">Sur Cde</th>
                <th className="px-2 py-2 w-24 text-right">Total</th>
                {validee && <th className="px-2 py-2 w-32">N° Suivi</th>}
                {!validee && <th className="px-2 py-2 w-8" />}
              </tr>
            </thead>
            <tbody>
              {panier.length === 0 ? (
                <tr>
                  <td
                    colSpan={validee ? 9 : 9}
                    className="px-2 py-4 text-center text-c-ink-faint"
                  >
                    Panier vide.
                  </td>
                </tr>
              ) : (
                panier.map((l) => {
                  const stockKo = l.stock < l.qte && !l.sur_commande
                  const surCde = l.stock === 0 && l.sur_commande
                  return (
                    <tr
                      key={l.id_panier}
                      className={
                        'border-t border-c-line ' +
                        (stockKo
                          ? 'bg-orange-50'
                          : surCde
                            ? 'bg-yellow-50'
                            : '')
                      }
                    >
                      <td className="px-2 py-1.5">{l.libfam}</td>
                      <td className="px-2 py-1.5">{l.marque}</td>
                      <td className="px-2 py-1.5">{l.liblot}</td>
                      <td className="px-2 py-1.5">{l.pour}</td>
                      <td className="px-2 py-1.5 text-right">
                        {fmt(l.montant_unitaire)}
                      </td>
                      <td className="px-2 py-1.5 text-center">
                        {validee ? (
                          l.qte
                        ) : (
                          <input
                            type="number"
                            min={1}
                            value={l.qte}
                            onChange={(e) =>
                              updateLotQte(
                                l.id_panier,
                                Math.max(1, Number(e.target.value)),
                                l.num_suivi,
                              )
                            }
                            className="w-12 px-1 py-0.5 border border-c-line-strong rounded text-center text-xs"
                          />
                        )}
                      </td>
                      <td className="px-2 py-1.5 text-center">
                        {l.sur_commande ? '✓' : ''}
                      </td>
                      <td className="px-2 py-1.5 text-right font-semibold">
                        {fmt(l.montant_total)}
                      </td>
                      {validee && (
                        <td className="px-2 py-1.5">
                          <input
                            type="text"
                            value={l.num_suivi || ''}
                            onChange={(e) =>
                              updateLotQte(l.id_panier, l.qte, e.target.value)
                            }
                            className="w-full px-1 py-0.5 border border-c-line-strong rounded text-xs"
                          />
                        </td>
                      )}
                      {!validee && (
                        <td className="px-2 py-1.5">
                          <button
                            onClick={() => delLot(l.id_panier)}
                            disabled={saving}
                            className="text-c-ink-faint hover:text-red-600"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      )}
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
        <div className="mt-1 flex gap-3 text-[11px] text-c-ink-faint">
          <span className="px-2 py-0.5 rounded bg-orange-50 border border-orange-200">
            Pb de stock
          </span>
          <span className="px-2 py-0.5 rounded bg-yellow-50 border border-yellow-200">
            Sur commande
          </span>
        </div>
      </div>

      {/* Envois */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide flex-1">
            Envois / Suivi colis
          </h3>
          <button
            onClick={() =>
              setEditEnvoi({
                id_envoi: '',
                num_suivi: '',
                date_envoi: '',
                transporteur: '',
                adresse: data.adresse_defaut || '',
              })
            }
            className="text-xs text-c-brand hover:underline flex items-center gap-1"
          >
            <Plus className="w-3.5 h-3.5" /> Ajouter un envoi
          </button>
        </div>
        <div className="border border-c-line rounded-lg overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-c-surface-soft text-c-ink-soft text-left">
              <tr>
                <th className="px-2 py-2 w-32">Date Envoi</th>
                <th className="px-2 py-2">N° Suivi</th>
                <th className="px-2 py-2 w-32">Transporteur</th>
                <th className="px-2 py-2 w-24" />
              </tr>
            </thead>
            <tbody>
              {envois.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-2 py-3 text-center text-c-ink-faint">
                    Aucun envoi.
                  </td>
                </tr>
              ) : (
                envois.map((e) => (
                  <tr
                    key={e.id_envoi}
                    onClick={() => setEditEnvoi({ ...e })}
                    className="border-t border-c-line cursor-pointer hover:bg-c-surface-soft"
                  >
                    <td className="px-2 py-1.5">{e.date_envoi}</td>
                    <td className="px-2 py-1.5">{e.num_suivi}</td>
                    <td className="px-2 py-1.5">{e.transporteur}</td>
                    <td className="px-2 py-1.5">
                      <div className="flex items-center gap-2 justify-end">
                        {trackingUrl(e.transporteur, e.num_suivi) && (
                          <a
                            href={trackingUrl(e.transporteur, e.num_suivi)}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(ev) => ev.stopPropagation()}
                            title="Suivre le colis"
                            className="text-c-brand hover:underline"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        )}
                        <button
                          onClick={(ev) => {
                            ev.stopPropagation()
                            delEnvoi(e.id_envoi)
                          }}
                          className="text-c-ink-faint hover:text-red-600"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Edit envoi form */}
        {editEnvoi && (
          <div className="mt-2 border border-c-line rounded-lg p-3 space-y-2">
            <div className="grid grid-cols-3 gap-2 text-sm">
              <label>
                <span className="text-c-ink-soft">N° Suivi</span>
                <input
                  value={editEnvoi.num_suivi}
                  onChange={(e) =>
                    setEditEnvoi({ ...editEnvoi, num_suivi: e.target.value })
                  }
                  className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
                />
              </label>
              <label>
                <span className="text-c-ink-soft">Date Envoi</span>
                <input
                  type="date"
                  value={editEnvoi.date_envoi}
                  onChange={(e) =>
                    setEditEnvoi({ ...editEnvoi, date_envoi: e.target.value })
                  }
                  className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
                />
              </label>
              <label>
                <span className="text-c-ink-soft">Transporteur</span>
                <input
                  list="transporteurs"
                  value={editEnvoi.transporteur}
                  onChange={(e) =>
                    setEditEnvoi({ ...editEnvoi, transporteur: e.target.value })
                  }
                  placeholder="COLISSIMO, DPD, CHRONOPOST…"
                  className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
                />
                <datalist id="transporteurs">
                  {TRANSPORTEURS.map((t) => (
                    <option key={t} value={t} />
                  ))}
                </datalist>
              </label>
            </div>
            <label className="block text-sm">
              <span className="text-c-ink-soft">Adresse de Livraison</span>
              <textarea
                value={editEnvoi.adresse}
                onChange={(e) =>
                  setEditEnvoi({ ...editEnvoi, adresse: e.target.value })
                }
                className="mt-1 w-full min-h-[80px] px-2 py-1 border border-c-line-strong rounded-md text-sm resize-none"
              />
            </label>
            <div className="flex gap-2">
              <button
                onClick={submitEnvoi}
                disabled={saving}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                Enregistrer
              </button>
              <button
                onClick={() => setEditEnvoi(null)}
                className="px-3 py-2 rounded-lg border border-c-line-strong text-sm hover:bg-c-surface-soft"
              >
                Annuler
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
