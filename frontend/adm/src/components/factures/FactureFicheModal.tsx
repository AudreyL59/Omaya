/**
 * Fen_FactureFiche (modale Fiche Facture).
 *
 * Affiche/édite une commande existante + permet d'ajouter/supprimer/
 * télécharger les factures liées (pgt_commande_facture).
 *
 * Calcule en live le "Montant restant" (commande.montant_ttc - SUM
 * des factures) avec couleur :
 *   - vert  : 0 (tout est facturé)
 *   - rouge : > 0 (incomplet)
 *
 * Notes :
 *  - Upload via multipart vers POST /commandes/{id}/factures (le
 *    backend stocke dans DOCS_BASE_PATH/factures/{id}/ et insère
 *    pgt_commande_facture).
 *  - Pas de FTP (le code WinDev passait par Fen_EnvoieFTP qui copiait
 *    le fichier vers un serveur distant ; ici stockage local).
 */
import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Save, Plus, Loader2, Calendar, Receipt, Download, Trash2,
  FileUp, User,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import BeneficiairePicker from './BeneficiairePicker'

const API_BASE = '/api/adm'

interface Operateur { id_salarie: string; nom_prenom: string }
interface Enseigne { enseigne: string }
interface Societe {
  id_ste: string; raison_sociale: string; rs_interne: string
}
interface CommandeDetail {
  id_commande: string; date_achat: string
  ope_achat: number; ope_achat_nom: string
  num_commande: string; montant_ttc: number
  enseigne: string; description: string
  id_ste: number; mode_paiement: string
  bene_service: boolean; bene_id: number; bene_nom: string
  somme_factures: number; montant_restant: number
}
interface Facture {
  id_commande_facture: string; date_ajout: string
  montant_ttc: number; nom_fic: string
}

interface Props {
  idCommande: string
  onClose: () => void
  onChanged?: () => void          // refresh liste parent
}

const MODES_PAIEMENT = [
  { code: 'CB', label: 'CB' },
  { code: 'CBL', label: 'Carte Logée' },
  { code: 'CH', label: 'Chèque' },
  { code: 'PRLV', label: 'Prélèvement' },
  { code: 'ESP', label: 'Espèce' },
]

const normalizeEnseigne = (s: string): string =>
  s.normalize('NFKD').replace(/[̀-ͯ]/g, '')
    .toUpperCase().replace(/\s+/g, '')

const formatEur = (n: number): string =>
  n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })

const shortDate = (iso: string): string => {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

export default function FactureFicheModal({
  idCommande, onClose, onChanged,
}: Props) {
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [operateurs, setOperateurs] = useState<Operateur[]>([])
  const [enseignes, setEnseignes] = useState<Enseigne[]>([])
  const [societes, setSocietes] = useState<Societe[]>([])
  const [factures, setFactures] = useState<Facture[]>([])

  // Champs commande (édition)
  const [dateAchat, setDateAchat] = useState('')
  const [opeAchat, setOpeAchat] = useState('')
  const [opeAchatLabel, setOpeAchatLabel] = useState('')
  const [opePickerOpen, setOpePickerOpen] = useState(false)
  const [numCommande, setNumCommande] = useState('')
  const [montantTtc, setMontantTtc] = useState(0)
  const [enseigne, setEnseigne] = useState('')
  const [description, setDescription] = useState('')
  const [idSte, setIdSte] = useState('')
  const [modePaiement, setModePaiement] = useState('CB')
  const [beneServiceMode, setBeneServiceMode] = useState(false)
  const [beneId, setBeneId] = useState(0)
  const [beneLabel, setBeneLabel] = useState('')
  const [benePickerOpen, setBenePickerOpen] = useState(false)

  // Ajout d'une facture
  const [factureMontant, setFactureMontant] = useState(0)
  const [factureFile, setFactureFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)

  // Charge le détail + référentiels
  const loadAll = useCallback(async () => {
    setLoading(true)
    const h = { Authorization: `Bearer ${getToken()}` }
    try {
      const [d, f, o, e, s] = await Promise.all([
        fetch(`${API_BASE}/factures/commandes/${idCommande}`, { headers: h })
          .then(r => r.json() as Promise<CommandeDetail>),
        fetch(`${API_BASE}/factures/commandes/${idCommande}/factures`, { headers: h })
          .then(r => r.json() as Promise<Facture[]>),
        fetch(`${API_BASE}/factures/operateurs`, { headers: h }).then(r => r.json()),
        fetch(`${API_BASE}/factures/enseignes`, { headers: h }).then(r => r.json()),
        fetch(`${API_BASE}/factures/societes`, { headers: h }).then(r => r.json()),
      ])
      setOperateurs(Array.isArray(o) ? o : [])
      setEnseignes(Array.isArray(e) ? e : [])
      setSocietes(Array.isArray(s) ? s : [])
      setFactures(Array.isArray(f) ? f : [])
      setDateAchat(d.date_achat?.slice(0, 10) || '')
      setOpeAchat(String(d.ope_achat || ''))
      setOpeAchatLabel(d.ope_achat_nom || '')
      setNumCommande(d.num_commande || '')
      setMontantTtc(d.montant_ttc || 0)
      setEnseigne(d.enseigne || '')
      setDescription(d.description || '')
      setIdSte(d.id_ste ? String(d.id_ste) : '')
      setModePaiement(d.mode_paiement || 'CB')
      setBeneServiceMode(!!d.bene_service)
      setBeneId(d.bene_id || 0)
      setBeneLabel(d.bene_nom || '')
    } catch (e) {
      showToast(`Erreur chargement : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [idCommande])

  useEffect(() => { void loadAll() }, [loadAll])

  // Calcul live montant restant (commande - sommes factures actuelles)
  const sommeFactures = factures.reduce((acc, f) => acc + f.montant_ttc, 0)
  const montantRestant = +(montantTtc - sommeFactures).toFixed(2)

  const handleEnregistrer = async () => {
    if (!opeAchat || !enseigne || !montantTtc || !beneId) {
      showToast('Champs obligatoires manquants.', 'info'); return
    }
    setBusy(true)
    try {
      const r = await fetch(`${API_BASE}/factures/commandes/${idCommande}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          date_achat: dateAchat,
          ope_achat: parseInt(opeAchat, 10),
          id_ste: idSte ? parseInt(idSte, 10) : 0,
          enseigne, mode_paiement: modePaiement,
          description, montant_ttc: montantTtc,
          num_commande: numCommande,
          bene_service: beneServiceMode, bene_id: beneId,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Modifications enregistrées', 'success')
      onChanged?.()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setBusy(false) }
  }

  const handleAjoutEnseigne = () => {
    const saisie = window.prompt("Veuillez saisir le nom de l'enseigne :", '')
    if (saisie === null) return
    const norm = normalizeEnseigne(saisie.trim())
    if (!norm) { showToast('Nom invalide.', 'info'); return }
    if (!enseignes.some(e => e.enseigne === norm)) {
      setEnseignes([...enseignes, { enseigne: norm }].sort(
        (a, b) => a.enseigne.localeCompare(b.enseigne)))
    }
    setEnseigne(norm)
  }

  const handleAjoutFacture = async () => {
    if (!factureFile) { showToast('Choisis un fichier.', 'info'); return }
    if (!factureMontant || factureMontant <= 0) {
      showToast('Montant TTC requis.', 'info'); return
    }
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', factureFile)
      fd.append('montant_ttc', String(factureMontant))
      const r = await fetch(
        `${API_BASE}/factures/commandes/${idCommande}/factures`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
          body: fd,
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      showToast('Facture ajoutée.', 'success')
      setFactureMontant(0); setFactureFile(null)
      // Reload juste les factures
      const fh = { Authorization: `Bearer ${getToken()}` }
      const f = await fetch(
        `${API_BASE}/factures/commandes/${idCommande}/factures`,
        { headers: fh },
      ).then(r => r.json())
      setFactures(Array.isArray(f) ? f : [])
      onChanged?.()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setUploading(false) }
  }

  const handleDownloadFacture = (id: string) => {
    // On utilise fetch + blob pour passer le Bearer token
    fetch(`${API_BASE}/factures/factures/${id}/download`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    }).then(async (r) => {
      if (!r.ok) throw new Error(String(r.status))
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const cd = r.headers.get('content-disposition') || ''
      const m = /filename="?([^";]+)"?/.exec(cd)
      a.download = m ? m[1] : `facture-${id}.pdf`
      document.body.appendChild(a); a.click()
      document.body.removeChild(a); URL.revokeObjectURL(url)
    }).catch(e => showToast(`Erreur : ${(e as Error).message}`, 'error'))
  }

  const handleDeleteFacture = async (id: string) => {
    // Double confirmation cf code WinDev
    const ok1 = await showConfirm({
      title: 'Vous allez supprimer une facture',
      message: 'Souhaitez-vous continuer ?',
    })
    if (!ok1) return
    const ok2 = await showConfirm({
      title: 'Confirmation',
      message: 'Êtes-vous sûr de vouloir supprimer cette facture ?',
    })
    if (!ok2) return
    try {
      const r = await fetch(`${API_BASE}/factures/factures/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      setFactures(factures.filter(f => f.id_commande_facture !== id))
      showToast('Facture supprimée.', 'success')
      onChanged?.()
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
          className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="px-4 py-3 border-b border-c-line flex items-center gap-2">
            <Receipt className="w-4 h-4 text-c-brand" />
            <h3 className="font-bold text-c-ink flex-1">Fiche Facture</h3>
            <button onClick={onClose}
              className="p-1 hover:bg-c-surface-soft rounded">
              <X className="w-4 h-4 text-c-ink-faint" />
            </button>
          </div>

          {loading ? (
            <div className="p-8 flex justify-center">
              <Loader2 className="w-6 h-6 animate-spin text-c-brand" />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4 p-4">
              {/* Colonne gauche : edition commande */}
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-2">
                  <label className="text-c-ink-faint w-24 shrink-0 text-xs">Le</label>
                  <div className="flex-1 relative">
                    <Calendar className="w-3.5 h-3.5 text-c-ink-faint absolute left-2 top-1/2 -translate-y-1/2" />
                    <input type="date" value={dateAchat}
                      onChange={e => setDateAchat(e.target.value)}
                      className="w-full pl-7 pr-2 py-1.5 border border-c-line rounded text-sm" />
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <label className="text-c-ink-faint w-24 shrink-0 text-xs">N° Commande</label>
                  <input type="text" value={numCommande}
                    onChange={e => setNumCommande(e.target.value.toUpperCase())}
                    className="flex-1 px-2 py-1.5 border border-c-line rounded text-sm" />
                </div>

                <button type="button" onClick={() => setOpePickerOpen(true)}
                  className="w-full flex items-center gap-2 px-2 py-1.5 border border-c-line rounded text-left text-sm hover:bg-c-surface-soft">
                  <User className="w-4 h-4 text-c-brand" />
                  <span className={opeAchatLabel ? 'flex-1' : 'flex-1 text-c-ink-faint-2'}>
                    {opeAchatLabel || "Choisir l'acheteur…"}
                  </span>
                </button>
                {opePickerOpen && (
                  <div className="-mt-2 border border-c-line rounded p-2 bg-c-surface-soft max-h-48 overflow-y-auto">
                    <select size={8} value={opeAchat}
                      onChange={(e) => {
                        const id = e.target.value
                        const op = operateurs.find(o => o.id_salarie === id)
                        setOpeAchat(id)
                        setOpeAchatLabel(op?.nom_prenom || '')
                        setOpePickerOpen(false)
                      }}
                      className="w-full text-xs border-0 bg-white rounded">
                      {operateurs.map(o => (
                        <option key={o.id_salarie} value={o.id_salarie}>
                          {o.nom_prenom}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <label className="text-c-ink-faint w-24 shrink-0 text-xs">Société</label>
                  <select value={idSte}
                    onChange={e => setIdSte(e.target.value)}
                    className="flex-1 px-2 py-1.5 border border-c-line rounded text-sm">
                    <option value="">Toutes</option>
                    {societes.map(s => (
                      <option key={s.id_ste} value={s.id_ste}>
                        {s.rs_interne || s.raison_sociale}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <label className="text-c-ink-faint w-24 shrink-0 text-xs">Enseigne</label>
                  <select value={enseigne}
                    onChange={e => setEnseigne(e.target.value)}
                    className="flex-1 px-2 py-1.5 border border-c-line rounded text-sm">
                    <option value="">Enseigne…</option>
                    {enseignes.map(e => (
                      <option key={e.enseigne} value={e.enseigne}>{e.enseigne}</option>
                    ))}
                  </select>
                  <button type="button" onClick={handleAjoutEnseigne}
                    title="Ajouter une enseigne"
                    className="p-1.5 bg-c-brand text-white rounded hover:opacity-90">
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <label className="text-c-ink-faint w-24 shrink-0 text-xs">Mode Paiement</label>
                  <select value={modePaiement}
                    onChange={e => setModePaiement(e.target.value)}
                    className="flex-1 px-2 py-1.5 border border-c-line rounded text-sm">
                    {MODES_PAIEMENT.map(m => (
                      <option key={m.code} value={m.code}>{m.label}</option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <label className="text-c-ink-faint w-24 shrink-0 text-xs">Montant TTC</label>
                  <input type="number" step="0.01" value={montantTtc || ''}
                    onChange={e => setMontantTtc(parseFloat(e.target.value) || 0)}
                    className="flex-1 px-2 py-1.5 border border-c-line rounded text-sm text-right" />
                  <span className="text-c-ink-faint">€</span>
                </div>

                <div>
                  <label className="text-c-ink-faint text-xs">Description</label>
                  <textarea value={description}
                    onChange={e => setDescription(e.target.value)}
                    rows={2}
                    className="w-full px-2 py-1.5 border border-c-line rounded text-sm" />
                </div>

                <div className="border border-c-line-soft rounded p-2 bg-c-surface-soft">
                  <div className="flex gap-1 mb-2">
                    <button type="button"
                      onClick={() => {
                        setBeneServiceMode(false); setBeneId(0); setBeneLabel('')
                      }}
                      className={`flex-1 py-1 rounded text-xs ${
                        !beneServiceMode ? 'bg-c-brand text-white' : 'bg-white text-c-ink-soft'
                      }`}>
                      Pour un salarié
                    </button>
                    <button type="button"
                      onClick={() => {
                        setBeneServiceMode(true); setBeneId(0); setBeneLabel('')
                      }}
                      className={`flex-1 py-1 rounded text-xs ${
                        beneServiceMode ? 'bg-c-brand text-white' : 'bg-white text-c-ink-soft'
                      }`}>
                      Pour un service
                    </button>
                  </div>
                  <button type="button" onClick={() => setBenePickerOpen(true)}
                    className="w-full px-2 py-1.5 bg-white border border-c-line rounded text-xs text-left truncate"
                    title={beneLabel || 'Choisir le bénéficiaire'}>
                    {beneLabel || (beneServiceMode
                      ? 'Choisir le service…' : 'Choisir le salarié…')}
                  </button>
                </div>

                <button type="button" onClick={handleEnregistrer} disabled={busy}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-c-brand text-white rounded font-medium hover:opacity-90 disabled:opacity-50">
                  {busy ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Save className="w-4 h-4" />}
                  Enregistrer
                </button>
              </div>

              {/* Colonne droite : factures liées + ajout */}
              <div className="space-y-3">
                <div className="border border-c-line rounded overflow-hidden">
                  <table className="w-full text-xs">
                    <thead className="bg-c-surface-soft text-c-ink-faint">
                      <tr>
                        <th className="px-2 py-1.5 text-left">Date Ajout</th>
                        <th className="px-2 py-1.5 text-right">Montant TTC</th>
                        <th className="px-2 py-1.5 w-14"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-c-line-soft">
                      {factures.length === 0 ? (
                        <tr>
                          <td colSpan={3} className="text-center py-6 text-c-ink-faint-2 italic">
                            Aucune facture
                          </td>
                        </tr>
                      ) : factures.map(f => (
                        <tr key={f.id_commande_facture}>
                          <td className="px-2 py-1.5">{shortDate(f.date_ajout)}</td>
                          <td className="px-2 py-1.5 text-right tabular-nums">
                            {formatEur(f.montant_ttc)}
                          </td>
                          <td className="px-2 py-1.5 flex gap-1">
                            <button onClick={() => handleDownloadFacture(f.id_commande_facture)}
                              className="p-1 text-c-brand hover:bg-c-brand/10 rounded"
                              title={f.nom_fic}>
                              <Download className="w-3.5 h-3.5" />
                            </button>
                            <button onClick={() => handleDeleteFacture(f.id_commande_facture)}
                              className="p-1 text-red-600 hover:bg-red-50 rounded">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                      <tr className="bg-c-surface-soft font-semibold">
                        <td className="px-2 py-1.5 text-right">Somme</td>
                        <td className="px-2 py-1.5 text-right tabular-nums">
                          {formatEur(sommeFactures)}
                        </td>
                        <td></td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="text-sm flex items-center justify-between">
                  <span className="text-c-ink-faint">Montant restant :</span>
                  <span className={`font-bold tabular-nums ${
                    montantRestant === 0 ? 'text-c-brand' : 'text-red-600'
                  }`}>
                    {formatEur(montantRestant)}
                  </span>
                </div>

                {/* Ajout facture */}
                <div className="border border-c-line rounded p-3 bg-c-surface-soft space-y-2">
                  <h4 className="text-sm font-semibold text-c-ink mb-1">
                    Ajouter une facture
                  </h4>
                  <div className="flex items-center gap-2">
                    <label className="text-xs text-c-ink-faint w-24 shrink-0">Montant TTC</label>
                    <input type="number" step="0.01" value={factureMontant || ''}
                      onChange={e => setFactureMontant(parseFloat(e.target.value) || 0)}
                      className="flex-1 px-2 py-1.5 border border-c-line rounded text-sm text-right bg-white" />
                    <span className="text-c-ink-faint">€</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-xs text-c-ink-faint w-24 shrink-0">Fichier</label>
                    <input type="file"
                      onChange={e => setFactureFile(e.target.files?.[0] || null)}
                      className="flex-1 text-xs" />
                  </div>
                  <button type="button" onClick={handleAjoutFacture}
                    disabled={uploading || !factureFile}
                    className="w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-c-brand text-white rounded text-sm font-medium hover:opacity-90 disabled:opacity-50">
                    {uploading ? <Loader2 className="w-4 h-4 animate-spin" />
                               : <FileUp className="w-4 h-4" />}
                    Ajouter la facture
                  </button>
                </div>
              </div>
            </div>
          )}
        </motion.div>

        {benePickerOpen && (
          <BeneficiairePicker
            mode={beneServiceMode ? 'service' : 'salarie'}
            onSelect={(item) => {
              setBeneId(parseInt(item.id, 10) || 0)
              setBeneLabel(item.label)
            }}
            onClose={() => setBenePickerOpen(false)}
          />
        )}
      </motion.div>
    </AnimatePresence>
  )
}
