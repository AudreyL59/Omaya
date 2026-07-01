/**
 * Modal 'Contenu du ticket Call' Energie - cf WinDev
 * OuvreSoeur(Fen_ContenuTicketCall, id_tk_liste, "Call").
 *
 * Affiche :
 *   - Header ticket : cree le, statut, date report, cloturee
 *   - Bloc infos client (readonly) : civilite, nom/prenom/marital,
 *     naiss, adresse, cp/ville, type logement (Maison/Apt),
 *     mobile, mail, ref appel, info vente, options
 *   - Boutons droite : Fiche Client, Voir le justif, Voir le justif SOS
 *   - Tableau paniers editable : NUM, statut prod (combo),
 *     partenaire, lib offre, date activation, ref client, options
 *   - Bouton 'Convertir la selection en contrat' (partie C)
 */
import { useCallback, useEffect, useState } from 'react'
import {
  X, Loader2, Save, User, ExternalLink, IdCard, Package,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'

const API_BASE = '/api/adm'

interface Panier {
  id_tk_call_panier: string
  id_produit: number
  partenaire: string; lib_offre: string
  num_bs: string; num_date_saisie: string
  statut_prod: number; motif_annulation: string
  date_entree: string; observations: string
  opt_mail: boolean; opt_e_facture: boolean; opt_e_communication: boolean
  opt_optin_commercial: boolean
  opt_consent_consult_distri: boolean; opt_accept_com_parte: boolean
  opt_mandat: boolean
  opt_energie_verte_gaz: boolean; opt_reforestation: boolean
  format_numerique: boolean
  a_creer: boolean
}
interface Detail {
  id_tk_liste: string; id_tk_call: string; id_client: string
  date_crea: string; lib_statut: string
  date_report: string; cloturee: boolean; date_cloture: string
  op_dest: number; nom_dest: string
  civilite: number
  nom_client: string; prenom_client: string; nom_marital_client: string
  date_naiss: string; dep_naiss: string
  adresse1: string; adresse2: string; cp: string; ville: string
  type_logement: string
  mobile1: string; adr_mail: string
  date_sign: string; ref_appel: string; info_vente: string
  opt_partenaire: boolean; intervention_vend: boolean
  id_salarie: number; nom_operateur: string
  paniers: Panier[]
}

interface Props {
  idTkListe: string
  onClose: () => void
  onChanged?: () => void
}

const CIVILITE_LABEL: Record<number, string> = {
  1: 'M.', 2: 'Mme', 3: 'Mlle',
}

const STATUT_PROD_OPTIONS: Array<{ v: number; l: string }> = [
  { v: 0, l: 'Non défini' },
  { v: 1, l: 'Validé' },
  { v: 2, l: 'Annulé' },
  { v: 3, l: 'Num BS ajouté' },
]

const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? '' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
const shortDT = (iso: string): string =>
  !iso || iso.length < 16 ? shortDate(iso)
    : `${shortDate(iso)} ${iso.slice(11, 16)}`

export default function TicketCallEnergieContenuModal({
  idTkListe, onClose, onChanged,
}: Props) {
  const [detail, setDetail] = useState<Detail | null>(null)
  const [loading, setLoading] = useState(true)
  const [paniers, setPaniers] = useState<Panier[]>([])
  const [saving, setSaving] = useState<string>('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/suivi-energie/ticket-call/detail/${idTkListe}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d: Detail = await r.json()
      setDetail(d); setPaniers(d.paniers)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [idTkListe])

  useEffect(() => { void load() }, [load])

  const savePanier = async (p: Panier) => {
    setSaving(p.id_tk_call_panier)
    try {
      const r = await fetch(
        `${API_BASE}/suivi-energie/ticket-call/panier/${p.id_tk_call_panier}`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ num: p.num_bs, statut_prod: p.statut_prod }),
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      onChanged?.()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setSaving('') }
  }

  const updatePanier = (id: string, patch: Partial<Panier>) => {
    setPaniers(prev => prev.map(p => p.id_tk_call_panier === id
      ? { ...p, ...patch,
          a_creer: (patch.num_bs !== undefined ? patch.num_bs : p.num_bs) !== ''
                    && (patch.statut_prod !== undefined ? patch.statut_prod : p.statut_prod) === 1 }
      : p,
    ))
  }

  const openJustif = async (p: Panier, source: 'normal' | 'sos') => {
    if (!detail?.id_tk_call) return
    try {
      const r = await fetch(
        `${API_BASE}/suivi-energie/ticket-call/${detail.id_tk_call}/justif-url`
        + `?id_panier=${p.id_tk_call_panier}&partenaire=${encodeURIComponent(p.partenaire)}`
        + `&source=${source}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d: { url: string } = await r.json()
      if (d.url) window.open(d.url, '_blank', 'noopener,noreferrer')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const openFicheClient = () => {
    if (!detail?.id_client || detail.id_client === '0') {
      showToast('Aucun client associé.', 'info'); return
    }
    showToast('Fen_ClientFiche : à venir', 'info')
  }

  const [converting, setConverting] = useState(false)

  const handleConvertir = async () => {
    if (!detail) return
    const idsPaniers = paniers.filter(p => p.a_creer)
      .map(p => parseInt(p.id_tk_call_panier, 10))
    if (idsPaniers.length === 0) {
      showToast('Aucun panier à créer (NUM non vide + statut Validé).', 'info')
      return
    }
    const ok = await showConfirm({
      title: 'Convertir la sélection en contrat',
      message: `Voulez-vous vraiment valider le(s) ${idsPaniers.length} contrat(s) sélectionné(s) ?`,
    })
    if (!ok) return

    setConverting(true)
    try {
      const r = await fetch(
        `${API_BASE}/suivi-energie/ticket-call/convert-selection`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id_tk_liste: parseInt(detail.id_tk_liste, 10),
            ids_paniers: idsPaniers,
          }),
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d: {
        nb_crees: number; nb_updates: number
        nb_erreurs: number; nb_skipped: number
      } = await r.json()
      showToast(
        `${d.nb_crees} créé(s), ${d.nb_updates} maj, ${d.nb_skipped} skip${d.nb_erreurs ? `, ${d.nb_erreurs} erreur(s)` : ''}`,
        d.nb_erreurs > 0 ? 'info' : 'success',
      )

      // 2e OuiNon : cloture
      const doClose = await showConfirm({
        title: 'Clôturer le ticket',
        message: 'Souhaitez-vous clôturer le ticket ?',
      })
      if (doClose) {
        const r2 = await fetch(
          `${API_BASE}/suivi-energie/ticket-call/cloture/${detail.id_tk_liste}`,
          {
            method: 'POST',
            headers: { Authorization: `Bearer ${getToken()}` },
          },
        )
        if (r2.ok) showToast('Ticket clôturé', 'success')
      }
      onChanged?.()
      await load()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setConverting(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-[1400px] max-w-full max-h-[95vh] flex flex-col"
           onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-c-line">
          <h2 className="text-sm font-bold flex items-center gap-2">
            <Package className="w-4 h-4 text-c-brand" />
            Contenu du ticket Call
            <span className="text-xs text-c-ink-faint-2 font-normal">
              — {idTkListe}
            </span>
          </h2>
          <button onClick={onClose}
            className="p-1 hover:bg-c-surface-soft rounded text-c-ink-faint">
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading || !detail ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-c-brand" />
          </div>
        ) : (
          <div className="flex-1 overflow-auto p-4">
            {/* Bandeau info ticket */}
            <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs px-3 py-2 bg-c-surface-soft rounded">
              <span><b>Créé le :</b> {shortDT(detail.date_crea)}</span>
              <span><b>Statut :</b> {detail.lib_statut}</span>
              <span><b>Op créa :</b> {detail.nom_operateur}</span>
              <span><b>Destinataire :</b> {detail.nom_dest || '—'}</span>
              {detail.cloturee && (
                <span className="text-red-600"><b>Clôturé le :</b> {shortDT(detail.date_cloture)}</span>
              )}
            </div>

            <div className="grid grid-cols-[1fr_1fr_240px] gap-4">
              {/* Bloc gauche : infos client */}
              <div className="col-span-2 border border-c-line rounded-lg p-3">
                <h3 className="text-xs font-bold text-c-ink-faint uppercase tracking-wide mb-2">
                  Contenu du ticket
                </h3>
                <div className="grid grid-cols-4 gap-3 text-xs">
                  <InfoField label="Civilité" value={CIVILITE_LABEL[detail.civilite] || String(detail.civilite || '')} />
                  <InfoField label="Nom" value={detail.nom_client} />
                  <InfoField label="Prénom" value={detail.prenom_client} />
                  <InfoField label="Nom Marital" value={detail.nom_marital_client} />
                  <InfoField label="Né(e) le" value={shortDate(detail.date_naiss)} />
                  <InfoField label="Dép naiss" value={detail.dep_naiss} />
                  <InfoField label="Type logement"
                    value={detail.type_logement === '1' ? 'Maison'
                          : detail.type_logement === '2' ? 'Appartement'
                          : detail.type_logement} />
                  <InfoField label="Date Sign" value={shortDate(detail.date_sign)} />
                  <div className="col-span-4">
                    <label className="text-[10px] text-c-ink-faint">Adresse</label>
                    <div className="px-2 py-1 border border-c-line rounded bg-c-surface-soft h-7 flex items-center truncate">
                      {detail.adresse1 || '—'}
                    </div>
                  </div>
                  {detail.adresse2 && (
                    <div className="col-span-4">
                      <label className="text-[10px] text-c-ink-faint">Cplt</label>
                      <div className="px-2 py-1 border border-c-line rounded bg-c-surface-soft h-7 flex items-center truncate">
                        {detail.adresse2}
                      </div>
                    </div>
                  )}
                  <InfoField label="CP" value={detail.cp} />
                  <div className="col-span-3">
                    <label className="text-[10px] text-c-ink-faint">Ville</label>
                    <div className="px-2 py-1 border border-c-line rounded bg-c-surface-soft h-7 flex items-center truncate">
                      {detail.ville || '—'}
                    </div>
                  </div>
                  <InfoField label="Mobile 1" value={detail.mobile1} />
                  <div className="col-span-3">
                    <label className="text-[10px] text-c-ink-faint">Adr Mail</label>
                    <div className="px-2 py-1 border border-c-line rounded bg-c-surface-soft h-7 flex items-center truncate">
                      {detail.adr_mail || '—'}
                    </div>
                  </div>
                  <InfoField label="Réf Appel" value={detail.ref_appel} />
                  <div className="col-span-3">
                    <label className="text-[10px] text-c-ink-faint">Info Vente</label>
                    <div className="px-2 py-1 border border-c-line rounded bg-c-surface-soft min-h-[3.5rem] flex items-start">
                      <span className="whitespace-pre-line">{detail.info_vente || '—'}</span>
                    </div>
                  </div>
                  <div className="col-span-2 flex items-center gap-2">
                    <input type="checkbox" checked={detail.intervention_vend} readOnly
                      className="cursor-not-allowed" />
                    <span>Intervention Vendeur</span>
                  </div>
                  <div className="col-span-2 flex items-center gap-2">
                    <input type="checkbox" checked={detail.opt_partenaire} readOnly
                      className="cursor-not-allowed" />
                    <span>Consent rappel des partenaires</span>
                  </div>
                </div>
              </div>

              {/* Bloc droite : actions */}
              <div className="border border-c-line rounded-lg p-3 space-y-2">
                <button type="button" onClick={openFicheClient}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
                  <User className="w-4 h-4" />
                  Fiche Client
                </button>
                <div className="text-[10px] text-c-ink-faint pt-2 border-t border-c-line-soft">
                  Justif (par panier sélectionné) :
                </div>
                <button type="button"
                  onClick={() => {
                    const first = paniers[0]
                    if (!first) { showToast('Aucun panier.', 'info'); return }
                    void openJustif(first, 'normal')
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
                  <IdCard className="w-4 h-4" />
                  Voir le justif
                </button>
                <button type="button"
                  onClick={() => {
                    const first = paniers[0]
                    if (!first) { showToast('Aucun panier.', 'info'); return }
                    void openJustif(first, 'sos')
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
                  <IdCard className="w-4 h-4" />
                  Voir le justif SOS
                </button>
              </div>
            </div>

            {/* Tableau paniers */}
            <div className="mt-4 border border-c-line rounded-lg overflow-hidden">
              <div className="px-3 py-1.5 border-b border-c-line-soft text-xs font-medium text-c-ink-faint bg-c-surface-soft">
                Paniers ({paniers.length})
              </div>
              <div className="overflow-auto max-h-[300px]">
                <table className="w-full text-xs">
                  <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0">
                    <tr>
                      <th className="px-2 py-2 text-center w-12">À créer</th>
                      <th className="px-2 py-2 text-left w-32">Statut Prod</th>
                      <th className="px-2 py-2 text-left w-36">Num BS</th>
                      <th className="px-2 py-2 text-left">Saisie le</th>
                      <th className="px-2 py-2 text-left w-16">Partenaire</th>
                      <th className="px-2 py-2 text-left">Lib Offre</th>
                      <th className="px-2 py-2 text-left">Date Activ.</th>
                      <th className="px-2 py-2 text-left">Réf Client</th>
                      <th className="px-2 py-2 text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-c-line-soft">
                    {paniers.length === 0 ? (
                      <tr><td colSpan={9} className="text-center py-8 text-c-ink-faint-2 italic">
                        Aucun panier.
                      </td></tr>
                    ) : paniers.map(p => (
                      <tr key={p.id_tk_call_panier}
                        className={p.a_creer ? 'bg-green-50' : ''}>
                        <td className="px-2 py-1 text-center">
                          <input type="checkbox" checked={p.a_creer} readOnly
                            className="cursor-not-allowed" />
                        </td>
                        <td className="px-2 py-1">
                          <select value={p.statut_prod}
                            onChange={(e) => updatePanier(p.id_tk_call_panier,
                              { statut_prod: parseInt(e.target.value, 10) || 0 })}
                            onBlur={() => savePanier(p)}
                            className="w-full px-1 py-0.5 border border-c-line rounded text-xs h-6">
                            {STATUT_PROD_OPTIONS.map(o => (
                              <option key={o.v} value={o.v}>{o.l}</option>
                            ))}
                          </select>
                        </td>
                        <td className="px-2 py-1">
                          <input type="text" value={p.num_bs}
                            onChange={(e) => updatePanier(p.id_tk_call_panier,
                              { num_bs: e.target.value.toUpperCase() })}
                            onBlur={() => savePanier(p)}
                            className="w-full px-1 py-0.5 border border-c-line rounded text-xs tabular-nums h-6" />
                        </td>
                        <td className="px-2 py-1">{shortDT(p.num_date_saisie)}</td>
                        <td className="px-2 py-1">
                          <span className="px-1.5 py-0.5 rounded bg-c-brand/10 text-c-brand text-[10px] font-medium">
                            {p.partenaire}
                          </span>
                        </td>
                        <td className="px-2 py-1">{p.lib_offre}</td>
                        <td className="px-2 py-1">{shortDate(p.date_entree)}</td>
                        <td className="px-2 py-1 truncate max-w-[160px]" title={p.observations}>
                          {p.observations}
                        </td>
                        <td className="px-2 py-1 text-center flex items-center justify-center gap-1">
                          {saving === p.id_tk_call_panier && (
                            <Loader2 className="w-3 h-3 animate-spin text-c-brand" />
                          )}
                          <button type="button"
                            onClick={() => openJustif(p, 'normal')}
                            title="Voir le justif"
                            className="p-0.5 hover:bg-c-surface-soft rounded text-c-ink-faint">
                            <ExternalLink className="w-3 h-3" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        {detail && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-c-line">
            <button type="button" onClick={onClose}
              className="px-3 py-1.5 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
              Fermer
            </button>
            <button type="button" onClick={handleConvertir}
              disabled={!paniers.some(p => p.a_creer) || converting}
              className="flex items-center gap-2 px-4 py-1.5 rounded bg-c-brand text-white text-xs font-medium hover:opacity-90 disabled:opacity-50">
              {converting
                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                : <Save className="w-3.5 h-3.5" />}
              {converting ? 'Conversion…' : 'Convertir la sélection en contrat'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label className="text-[10px] text-c-ink-faint block">{label}</label>
      <div className="px-2 py-1 border border-c-line rounded bg-c-surface-soft h-7 flex items-center truncate">
        {value || '—'}
      </div>
    </div>
  )
}
