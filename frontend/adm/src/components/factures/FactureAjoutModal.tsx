/**
 * Fen_FactureAjout (modale Nouvel achat).
 *
 * Crée une nouvelle commande dans pgt_commande puis prévient le parent
 * (callback onCreated avec l'id_commande) — qui pourra ouvrir
 * Fen_FactureFiche pour saisir/uploader les factures associées.
 *
 * Bouton "+" à côté Enseigne : popup saisie d'une nouvelle enseigne
 * (normalisée MAJ + sans accent + sans espace, ajoutée à la combo et
 * sélectionnée). La nouvelle valeur apparaîtra naturellement dans la
 * liste DISTINCT au prochain chargement (quand la commande sera créée).
 */
import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Save, Plus, Loader2, Calendar, Receipt, User,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import BeneficiairePicker from './BeneficiairePicker'

const API_BASE = '/api/adm'

interface Operateur { id_salarie: string; nom_prenom: string }
interface Enseigne { enseigne: string }
interface Societe {
  id_ste: string; raison_sociale: string; rs_interne: string
}

interface Props {
  onClose: () => void
  onCreated: (idCommande: string) => void
}

const MODES_PAIEMENT = [
  { code: 'CB', label: 'CB' },
  { code: 'CBL', label: 'Carte Logée' },
  { code: 'CH', label: 'Chèque' },
  { code: 'PRLV', label: 'Prélèvement' },
  { code: 'ESP', label: 'Espèce' },
]

const todayIso = (): string => new Date().toISOString().slice(0, 10)

// MAJ + sans accent + sans espace (cf ChaineFormate WinDev)
const normalizeEnseigne = (s: string): string =>
  s.normalize('NFKD').replace(/[̀-ͯ]/g, '')
    .toUpperCase().replace(/\s+/g, '')

export default function FactureAjoutModal({ onClose, onCreated }: Props) {
  const [operateurs, setOperateurs] = useState<Operateur[]>([])
  const [enseignes, setEnseignes] = useState<Enseigne[]>([])
  const [societes, setSocietes] = useState<Societe[]>([])

  const [dateAchat, setDateAchat] = useState(todayIso())
  const [opeAchat, setOpeAchat] = useState('')          // id_salarie (combo)
  const [opeAchatLabel, setOpeAchatLabel] = useState('')
  const [opePickerOpen, setOpePickerOpen] = useState(false)
  const [idSte, setIdSte] = useState('')
  const [enseigne, setEnseigne] = useState('')
  const [modePaiement, setModePaiement] = useState('CB')
  const [description, setDescription] = useState('')
  const [numCommande, setNumCommande] = useState('')
  const [montantTtc, setMontantTtc] = useState(0)
  const [beneServiceMode, setBeneServiceMode] = useState(false)
  const [beneId, setBeneId] = useState(0)
  const [beneLabel, setBeneLabel] = useState('')
  const [benePickerOpen, setBenePickerOpen] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const h = { Authorization: `Bearer ${getToken()}` }
    Promise.all([
      fetch(`${API_BASE}/factures/operateurs`, { headers: h }).then(r => r.json()),
      fetch(`${API_BASE}/factures/enseignes`, { headers: h }).then(r => r.json()),
      fetch(`${API_BASE}/factures/societes`, { headers: h }).then(r => r.json()),
    ]).then(([o, e, s]) => {
      setOperateurs(Array.isArray(o) ? o : [])
      setEnseignes(Array.isArray(e) ? e : [])
      setSocietes(Array.isArray(s) ? s : [])
    })
  }, [])

  const handleAjoutEnseigne = () => {
    const saisie = window.prompt("Veuillez saisir le nom de l'enseigne :", '')
    if (saisie === null) return  // cancel
    const norm = normalizeEnseigne(saisie.trim())
    if (!norm) {
      showToast('Nom d\'enseigne invalide.', 'info'); return
    }
    // Ajoute en local (sera persisté au prochain chargement après save)
    if (!enseignes.some(e => e.enseigne === norm)) {
      const next = [...enseignes, { enseigne: norm }].sort(
        (a, b) => a.enseigne.localeCompare(b.enseigne),
      )
      setEnseignes(next)
    }
    setEnseigne(norm)
  }

  const handleEnregistrer = async () => {
    if (!opeAchat) {
      showToast('Choisis un acheteur.', 'info'); return
    }
    if (!enseigne) {
      showToast('Choisis une enseigne.', 'info'); return
    }
    if (!montantTtc || montantTtc <= 0) {
      showToast('Montant TTC requis.', 'info'); return
    }
    if (!beneId) {
      showToast('Choisis un bénéficiaire.', 'info'); return
    }
    setBusy(true)
    try {
      const r = await fetch(`${API_BASE}/factures/commandes`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          date_achat: dateAchat,
          ope_achat: parseInt(opeAchat, 10),
          id_ste: idSte ? parseInt(idSte, 10) : 0,
          enseigne,
          mode_paiement: modePaiement,
          description,
          montant_ttc: montantTtc,
          num_commande: numCommande,
          bene_service: beneServiceMode,
          bene_id: beneId,
        }),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      showToast('Commande créée.', 'success')
      onCreated(d.id_commande)
      onClose()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setBusy(false) }
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
          className="bg-white rounded-xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="px-4 py-3 border-b border-c-line flex items-center gap-2">
            <Receipt className="w-4 h-4 text-c-brand" />
            <h3 className="font-bold text-c-ink flex-1">Nouvel achat</h3>
            <button onClick={onClose}
              className="p-1 hover:bg-c-surface-soft rounded">
              <X className="w-4 h-4 text-c-ink-faint" />
            </button>
          </div>

          <div className="p-4 space-y-3 text-sm">
            {/* Date */}
            <div className="flex items-center gap-2">
              <label className="text-c-ink-faint w-20 shrink-0">Le</label>
              <div className="flex-1 relative">
                <Calendar className="w-3.5 h-3.5 text-c-ink-faint absolute left-2 top-1/2 -translate-y-1/2" />
                <input type="date" value={dateAchat}
                  onChange={e => setDateAchat(e.target.value)}
                  className="w-full pl-7 pr-2 py-1.5 border border-c-line rounded text-sm" />
              </div>
            </div>

            {/* N° commande */}
            <input type="text" value={numCommande}
              onChange={e => setNumCommande(e.target.value.toUpperCase())}
              placeholder="TOUT EN MAJUSCULE (SANS ACCENT)"
              className="w-full px-2 py-1.5 border border-c-line rounded text-sm" />

            {/* Acheteur (combo searchable via picker pour rester homogène) */}
            <button type="button" onClick={() => setOpePickerOpen(true)}
              className="w-full flex items-center gap-2 px-2 py-1.5 border border-c-line rounded text-left text-sm hover:bg-c-surface-soft">
              <User className="w-4 h-4 text-c-brand" />
              <span className={opeAchatLabel ? 'flex-1' : 'flex-1 text-c-ink-faint-2'}>
                {opeAchatLabel || "Choisir l'acheteur…"}
              </span>
            </button>
            {opePickerOpen && (
              <div className="-mt-2 border border-c-line rounded p-2 bg-c-surface-soft max-h-48 overflow-y-auto">
                <select size={8}
                  value={opeAchat}
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

            {/* Société */}
            <select value={idSte}
              onChange={e => setIdSte(e.target.value)}
              className="w-full px-2 py-1.5 border border-c-line rounded text-sm">
              <option value="">Toutes</option>
              {societes.map(s => (
                <option key={s.id_ste} value={s.id_ste}>
                  {s.rs_interne || s.raison_sociale}
                </option>
              ))}
            </select>

            {/* Enseigne + bouton + */}
            <div className="flex gap-1">
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
                <Plus className="w-4 h-4" />
              </button>
            </div>

            {/* Mode paiement */}
            <select value={modePaiement}
              onChange={e => setModePaiement(e.target.value)}
              className="w-full px-2 py-1.5 border border-c-line rounded text-sm">
              {MODES_PAIEMENT.map(m => (
                <option key={m.code} value={m.code}>{m.label}</option>
              ))}
            </select>

            {/* Description */}
            <textarea value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Description"
              rows={2}
              className="w-full px-2 py-1.5 border border-c-line rounded text-sm" />

            {/* Montant TTC */}
            <div className="flex items-center gap-2">
              <label className="text-c-ink-faint w-20 shrink-0">Montant TTC</label>
              <input type="number" step="0.01" value={montantTtc || ''}
                onChange={e => setMontantTtc(parseFloat(e.target.value) || 0)}
                className="flex-1 px-2 py-1.5 border border-c-line rounded text-sm text-right" />
              <span className="text-c-ink-faint">€</span>
            </div>

            {/* Glissière salarié / service */}
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

            {/* Bouton Enregistrer */}
            <button type="button" onClick={handleEnregistrer} disabled={busy}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-c-brand text-white rounded font-medium hover:opacity-90 disabled:opacity-50">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" />
                    : <Save className="w-4 h-4" />}
              Enregistrer
            </button>
          </div>
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
