/**
 * Fen_ContenuTicketCallSFR (modale Contenu du ticket SFR).
 *
 * Affiche le detail complet d'un ticket Call SFR :
 *  - Info generale (statut, date, cloturee, op crea)
 *  - Info client (civilite, nom/prenom, naissance, adresse, contact, options)
 *  - Date sign + ref appel + info vente
 *  - Tableau Table_CallPanier (statut prod, NUM, saisie le, type, lib offre,
 *    opt TV, portab, num portab, prise RIO, prise optique, opt choisies, A créer)
 *
 * Actions (etape suivante) :
 *  - Modif colonne NUM : update + bascule TK_Liste.statut=17
 *  - Bouton 'Convertir la selection en contrat' : EnregistrerClient +
 *    EnregistrerCttSFR + proposition cloture ticket
 *  - Boutons CIN / CIN SOS (visu doc d'identite)
 */
import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Loader2, PhoneCall, IdCard, Save,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'

const API_BASE = '/api/adm'

interface PanierLine {
  id_tk_call_sfr_panier: string; id_offres_sfr: number
  lib_offre: string; type: string; type_vente: number
  num: string; num_date_saisie: string
  portabilite: boolean; num_portabilite: string
  num_prise_rio: string; num_prise_optique: string
  opt_tv: string; opt_choisies: string
  test_eligibilite: string; motif_annulation: string
  statut_prod: number; a_creer: boolean
}

interface TicketDetail {
  id_tk_liste: string; date_crea: string
  id_tk_statut: number; lib_statut: string
  cloturee: boolean; date_cloture: string; date_report: string
  op_crea: number; op_crea_nom: string
  id_tk_call_sfr: string
  id_salarie: number; id_salarie_nom: string
  nom_client: string; prenom_client: string; nom_marital_client: string
  civilite_client: number; date_naiss: string; dep_naiss: string
  adresse1: string; adresse2: string
  cp: string; ville: string
  mobile1: string; adr_mail: string
  type_logement: number
  opt_rappel: boolean; opt_partenaire: boolean
  intervention_vend: boolean; info_vente: string
  ref_appel: string; motif_annulation: string
  code_valid: string
  paniers: PanierLine[]
}

interface Props {
  idTkListe: string
  onClose: () => void
  onChanged?: () => void
}

const STATUT_PROD_LABELS: Record<number, string> = {
  0: 'Non défini', 1: 'Validé', 2: 'Annulé',
  3: 'Num BS ajouté', 4: 'Validé - Différé',
}
const CIVILITE: Record<number, string> = {
  0: '—', 1: 'M.', 2: 'Mme', 3: 'Melle',
}
const TYPE_LOG: Record<number, string> = {
  0: '—', 1: 'Maison', 2: 'Appartement',
}

const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? '' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function TicketCallContenuModal({
  idTkListe, onClose, onChanged,
}: Props) {
  const [loading, setLoading] = useState(true)
  const [detail, setDetail] = useState<TicketDetail | null>(null)
  const [paniers, setPaniers] = useState<PanierLine[]>([])
  const [savingNum, setSavingNum] = useState<string>('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/ticket-call/detail/${idTkListe}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d: TicketDetail = await r.json()
      setDetail(d)
      setPaniers(d.paniers)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [idTkListe])

  useEffect(() => { void load() }, [load])

  const handleSaveNum = async (panier: PanierLine, newNum: string) => {
    const trimmed = newNum.trim().toUpperCase()
    if (trimmed === panier.num) return
    if (!window.confirm(
      `Voulez-vous vraiment valider le num "${trimmed}" pour ce contrat ?`,
    )) {
      // restore
      setPaniers(prev => prev.map(p => p.id_tk_call_sfr_panier === panier.id_tk_call_sfr_panier
        ? { ...p, num: panier.num } : p))
      return
    }
    setSavingNum(panier.id_tk_call_sfr_panier)
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/ticket-call/panier/${panier.id_tk_call_sfr_panier}/num`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ num: trimmed, id_tk_liste: idTkListe }),
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast('NUM enregistré', 'success')
      await load()
      onChanged?.()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setSavingNum('') }
  }

  const handleConvertir = () => {
    showToast(
      'Convertir la sélection en contrat : à venir (étape D)',
      'info',
    )
  }

  const handleVoirCin = async (source: 'normal' | 'sos') => {
    if (!detail?.id_tk_call_sfr) {
      showToast('Pas de ticket Call SFR associé.', 'info'); return
    }
    try {
      const r = await fetch(
        `${API_BASE}/suivi-sfr/ticket-call/${detail.id_tk_call_sfr}/cin-url?source=${source}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      if (d.url) window.open(d.url, '_blank', 'noopener,noreferrer')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.96, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.96, opacity: 0 }}
          className="bg-white rounded-xl shadow-xl w-full max-w-6xl h-[95vh] flex flex-col overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="px-4 py-3 border-b border-c-line flex items-center gap-2 shrink-0">
            <PhoneCall className="w-4 h-4 text-c-brand" />
            <h3 className="font-bold text-c-ink flex-1">
              Contenu du ticket SFR
              {detail && <span className="ml-2 text-xs text-c-ink-faint">— {detail.id_tk_liste}</span>}
            </h3>
            <button onClick={onClose}
              className="p-1 hover:bg-c-surface-soft rounded">
              <X className="w-4 h-4 text-c-ink-faint" />
            </button>
          </div>

          {loading || !detail ? (
            <div className="flex-1 flex justify-center items-center">
              <Loader2 className="w-6 h-6 animate-spin text-c-brand" />
            </div>
          ) : (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Bandeau info ticket */}
              <div className="px-4 py-2 border-b border-c-line-soft bg-c-surface-soft text-xs flex items-center gap-4 flex-wrap">
                <span><b>Créé le :</b> {shortDate(detail.date_crea)}</span>
                <span><b>Statut :</b> {detail.lib_statut}</span>
                <span><b>Op créa :</b> {detail.op_crea_nom}</span>
                <span><b>Destinataire :</b> {detail.id_salarie_nom || '—'}</span>
                {detail.cloturee && (
                  <span className="text-red-600">
                    <b>Clôturé le :</b> {shortDate(detail.date_cloture)}
                  </span>
                )}
                {detail.date_report && (
                  <span><b>Date de Report :</b> {shortDate(detail.date_report)}</span>
                )}
              </div>

              <div className="flex-1 grid grid-cols-5 gap-4 p-4 overflow-hidden">
                {/* Colonne gauche : info client (2/5) */}
                <div className="col-span-2 space-y-2 overflow-y-auto text-sm pr-2">
                  <h4 className="font-bold text-c-ink mb-2">Contenu du ticket</h4>

                  <div className="grid grid-cols-2 gap-2">
                    <Field label="Civilité" value={CIVILITE[detail.civilite_client] || '—'} />
                    <Field label="Nom" value={detail.nom_client} />
                    <Field label="Prénom" value={detail.prenom_client} />
                    <Field label="Nom Marital" value={detail.nom_marital_client} />
                    <Field label="Né(e) le" value={shortDate(detail.date_naiss)} />
                    <Field label="Dép" value={detail.dep_naiss} />
                  </div>

                  <Field label="Adresse" value={detail.adresse1} />
                  <Field label="Cplt" value={detail.adresse2} />
                  <div className="grid grid-cols-3 gap-2">
                    <Field label="CP" value={detail.cp} />
                    <div className="col-span-2">
                      <Field label="Ville" value={detail.ville} />
                    </div>
                  </div>
                  <Field label="Type logement" value={TYPE_LOG[detail.type_logement] || '—'} />

                  <div className="grid grid-cols-2 gap-2">
                    <Field label="Mobile 1" value={detail.mobile1} />
                    <Field label="Adr Mail" value={detail.adr_mail} />
                  </div>

                  <Field label="Réf Appel" value={detail.ref_appel} />
                  <div>
                    <label className="text-[10px] text-c-ink-faint">Info Vente</label>
                    <div className="px-2 py-1.5 border border-c-line rounded text-sm bg-c-surface-soft min-h-[60px] whitespace-pre-wrap">
                      {detail.info_vente || '—'}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 pt-2 text-xs">
                    <Check label="Rappel Call" value={detail.opt_rappel} />
                    <Check label="Rappel partenaires" value={detail.opt_partenaire} />
                    <Check label="Intervention Vendeur" value={detail.intervention_vend} />
                  </div>

                  {detail.motif_annulation && (
                    <div className="pt-2 text-red-600">
                      <b>Motif annulation :</b> {detail.motif_annulation}
                    </div>
                  )}
                </div>

                {/* Colonne droite : tableau panier (3/5) */}
                <div className="col-span-3 flex flex-col overflow-hidden">
                  <div className="flex items-center justify-end gap-2 mb-2">
                    <button type="button"
                      onClick={() => handleVoirCin('normal')}
                      className="flex items-center gap-1.5 px-2 py-1 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
                      <IdCard className="w-3.5 h-3.5" /> Voir la CIN
                    </button>
                    <button type="button"
                      onClick={() => handleVoirCin('sos')}
                      className="flex items-center gap-1.5 px-2 py-1 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
                      <IdCard className="w-3.5 h-3.5" /> Voir la CIN SOS
                    </button>
                  </div>

                  <div className="flex-1 overflow-auto border border-c-line rounded">
                    <table className="w-full text-xs">
                      <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0">
                        <tr>
                          <th className="px-2 py-2 text-center">À créer</th>
                          <th className="px-2 py-2 text-left">Statut Prod</th>
                          <th className="px-2 py-2 text-left">NUM</th>
                          <th className="px-2 py-2 text-left">Saisie le</th>
                          <th className="px-2 py-2 text-left">Type</th>
                          <th className="px-2 py-2 text-left">Lib Offre</th>
                          <th className="px-2 py-2 text-center">Opt TV</th>
                          <th className="px-2 py-2 text-center">Portabilité</th>
                          <th className="px-2 py-2 text-left">Num Portab</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-c-line-soft">
                        {paniers.length === 0 ? (
                          <tr>
                            <td colSpan={9} className="text-center py-12 text-c-ink-faint-2 italic">
                              Aucune ligne panier.
                            </td>
                          </tr>
                        ) : paniers.map(p => (
                          <tr key={p.id_tk_call_sfr_panier}>
                            <td className="px-2 py-1.5 text-center">
                              <input type="checkbox" checked={p.a_creer}
                                onChange={(e) => setPaniers(prev => prev.map(x =>
                                  x.id_tk_call_sfr_panier === p.id_tk_call_sfr_panier
                                    ? { ...x, a_creer: e.target.checked } : x))} />
                            </td>
                            <td className="px-2 py-1.5">{STATUT_PROD_LABELS[p.statut_prod] || p.statut_prod}</td>
                            <td className="px-2 py-1.5">
                              <input type="text" value={p.num}
                                onChange={(e) => setPaniers(prev => prev.map(x =>
                                  x.id_tk_call_sfr_panier === p.id_tk_call_sfr_panier
                                    ? { ...x, num: e.target.value.toUpperCase() } : x))}
                                onBlur={(e) => handleSaveNum(p, e.target.value)}
                                disabled={savingNum === p.id_tk_call_sfr_panier}
                                className="w-32 px-1 py-0.5 border border-c-line rounded text-xs font-mono" />
                              {savingNum === p.id_tk_call_sfr_panier && (
                                <Loader2 className="w-3 h-3 animate-spin inline ml-1" />
                              )}
                            </td>
                            <td className="px-2 py-1.5">{shortDate(p.num_date_saisie)}</td>
                            <td className="px-2 py-1.5">{p.type}</td>
                            <td className="px-2 py-1.5 max-w-[180px] truncate" title={p.lib_offre}>
                              {p.lib_offre}
                            </td>
                            <td className="px-2 py-1.5 text-center">{p.opt_tv || '—'}</td>
                            <td className="px-2 py-1.5 text-center">
                              {p.portabilite ? '✓' : ''}
                            </td>
                            <td className="px-2 py-1.5">{p.num_portabilite}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <button type="button" onClick={handleConvertir}
                    disabled={!paniers.some(p => p.a_creer)}
                    className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2 bg-c-brand text-white rounded font-medium hover:opacity-90 disabled:opacity-50">
                    <Save className="w-4 h-4" />
                    Convertir la sélection en contrat
                  </button>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label className="text-[10px] text-c-ink-faint">{label}</label>
      <div className="px-2 py-1 border border-c-line rounded text-sm bg-c-surface-soft truncate"
        title={value || '—'}>
        {value || '—'}
      </div>
    </div>
  )
}

function Check({ label, value }: { label: string; value: boolean }) {
  return (
    <label className="flex items-center gap-1.5 text-c-ink-soft">
      <input type="checkbox" checked={value} readOnly className="pointer-events-none" />
      {label}
    </label>
  )
}
