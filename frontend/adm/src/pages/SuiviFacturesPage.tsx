/**
 * Fen_FacturesSuivi (ADM > Suivi des factures).
 *
 * Bandeau filtres a gauche + tableau resultats a droite.
 * Indicateur visuel par ligne (icone + couleur) :
 *   - vert  : facture presente avec montant = commande
 *   - orange: facture presente mais montant !=
 *   - rouge : pas de facture ou montant 0
 *
 * Note : les 2 boutons d'action (ajout/edit/suppr) au-dessus du tableau
 * seront ajoutes plus tard.
 */
import { useEffect, useState } from 'react'
import {
  Search, FileDown, Loader2, CheckCircle2, AlertCircle, XCircle, Receipt,
  Plus, Pencil, Trash2, X,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import BeneficiairePicker from '@/components/factures/BeneficiairePicker'
import FactureAjoutModal from '@/components/factures/FactureAjoutModal'
import FactureFicheModal from '@/components/factures/FactureFicheModal'

const API_BASE = '/api/adm'

interface Operateur { id_salarie: string; nom_prenom: string }
interface Enseigne { enseigne: string }
interface Societe {
  id_ste: string; raison_sociale: string; rs_interne: string
}
interface Ligne {
  id_commande: string; date_achat: string; ope_achat_nom: string
  enseigne: string; num_commande: string; description: string
  montant_ttc: number; mode_paiement: string
  bene_nom: string; bene_service: boolean
  etat: 'ok' | 'partiel' | 'ko'
  montant_facture: number
}

const MODES_PAIEMENT = [
  { code: '', label: '-- Tous --' },
  { code: 'CB', label: 'CB' },
  { code: 'CBL', label: 'Carte Logée' },
  { code: 'CH', label: 'Chèque' },
  { code: 'PRLV', label: 'Prélèvement' },
  { code: 'ESP', label: 'Espèce' },
]

const todayIso = (): string => new Date().toISOString().slice(0, 10)
const oneYearAgoIso = (): string => {
  const d = new Date(); d.setFullYear(d.getFullYear() - 1)
  return d.toISOString().slice(0, 10)
}

const formatEur = (n: number): string =>
  n.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })

const shortDate = (iso: string): string => {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

const EtatBadge = ({ etat }: { etat: Ligne['etat'] }) => {
  if (etat === 'ok') return (
    <CheckCircle2 className="w-4 h-4 text-c-brand inline" />
  )
  if (etat === 'partiel') return (
    <AlertCircle className="w-4 h-4 text-orange-500 inline" />
  )
  return <XCircle className="w-4 h-4 text-red-600 inline" />
}

export default function SuiviFacturesPage() {
  useDocumentTitle('Suivi des factures')

  const [operateurs, setOperateurs] = useState<Operateur[]>([])
  const [enseignes, setEnseignes] = useState<Enseigne[]>([])
  const [societes, setSocietes] = useState<Societe[]>([])
  const [du, setDu] = useState(oneYearAgoIso())
  const [au, setAu] = useState(todayIso())
  const [numCommande, setNumCommande] = useState('')
  const [opeAchat, setOpeAchat] = useState('')
  const [idSte, setIdSte] = useState('')
  const [enseigne, setEnseigne] = useState('')
  const [modePaiement, setModePaiement] = useState('')
  const [description, setDescription] = useState('')
  const [montantMin, setMontantMin] = useState(0)
  const [montantMax, setMontantMax] = useState(0)
  const [beneServiceMode, setBeneServiceMode] = useState(false)
  const [beneId, setBeneId] = useState(0)
  const [beneLabel, setBeneLabel] = useState('')
  const [pickerOpen, setPickerOpen] = useState(false)

  const [busy, setBusy] = useState(false)
  const [lignes, setLignes] = useState<Ligne[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [ajoutOpen, setAjoutOpen] = useState(false)
  const [ficheOpenId, setFicheOpenId] = useState<string>('')

  useEffect(() => {
    const headers = { Authorization: `Bearer ${getToken()}` }
    Promise.all([
      fetch(`${API_BASE}/factures/operateurs`, { headers }).then(r => r.json()),
      fetch(`${API_BASE}/factures/enseignes`, { headers }).then(r => r.json()),
      fetch(`${API_BASE}/factures/societes`, { headers }).then(r => r.json()),
    ]).then(([ops, ens, ste]) => {
      setOperateurs(Array.isArray(ops) ? ops : [])
      setEnseignes(Array.isArray(ens) ? ens : [])
      setSocietes(Array.isArray(ste) ? ste : [])
    })
  }, [])

  const rechercher = async () => {
    if (du > au) {
      showToast('Dates incohérentes (Du > Au)', 'error'); return
    }
    setBusy(true)
    try {
      const body = {
        du: numCommande ? null : du,
        au: numCommande ? null : au,
        num_commande: numCommande,
        id_ope_achat: opeAchat ? parseInt(opeAchat, 10) : 0,
        id_ste: idSte ? parseInt(idSte, 10) : 0,
        enseigne, mode_paiement: modePaiement,
        description,
        montant_min: montantMin, montant_max: montantMax,
        bene_service: beneServiceMode, bene_id: beneId,
      }
      const r = await fetch(`${API_BASE}/factures/search`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })
      if (!r.ok) throw new Error(String(r.status))
      const d: Ligne[] = await r.json()
      setLignes(d)
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  const handleAjouter = () => setAjoutOpen(true)

  const handleEditer = () => {
    if (!selectedId) {
      showToast('Sélectionne une ligne dans le tableau.', 'info'); return
    }
    setFicheOpenId(selectedId)
  }

  const handleSupprimer = async () => {
    if (!selectedId) {
      showToast('Sélectionne une ligne dans le tableau.', 'info'); return
    }
    const ok = await showConfirm({
      title: 'Supprimer cet enregistrement',
      message: 'Vous êtes sur le point de supprimer cet enregistrement.\nVoulez-vous continuer ?',
    })
    if (!ok) return
    try {
      const r = await fetch(
        `${API_BASE}/factures/commandes/${selectedId}`,
        {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      )
      if (!r.ok) throw new Error(String(r.status))
      setLignes(prev => prev.filter(l => l.id_commande !== selectedId))
      setSelectedId('')
      showToast('Commande supprimée.', 'success')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    }
  }

  const exportXlsx = async () => {
    const { exportRowsToXlsx } = await import(
      '@shared/production/_tableHelpers'
    )
    exportRowsToXlsx(
      [
        { key: 'etat', label: 'État' },
        { key: 'date_achat', label: 'Date Achat' },
        { key: 'ope_achat_nom', label: 'Opé Achat' },
        { key: 'enseigne', label: 'Enseigne' },
        { key: 'num_commande', label: 'N° Commande' },
        { key: 'description', label: 'Description' },
        { key: 'montant_ttc', label: 'Montant TTC' },
        { key: 'montant_facture', label: 'Montant facture' },
        { key: 'mode_paiement', label: 'Mode Paiement' },
        { key: 'bene_nom', label: 'Bénéficiaire' },
      ],
      lignes as unknown as Array<Record<string, unknown>>,
      'suivi-factures', 'Factures',
    )
  }

  return (
    <div className="p-4 flex gap-4 h-[calc(100vh-110px)] text-c-ink">
      {/* Filtres a gauche */}
      <div className="w-72 shrink-0 bg-white rounded-xl border border-c-line p-3 overflow-y-auto">
        <h2 className="text-sm font-bold mb-3 flex items-center gap-2">
          <Receipt className="w-4 h-4 text-c-brand" /> Suivi Factures
        </h2>

        <div className="space-y-2.5 text-sm">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-c-ink-faint">Du</label>
              <input type="date" value={du}
                onChange={e => setDu(e.target.value)}
                className="w-full px-2 py-1 border border-c-line rounded text-xs" />
            </div>
            <div>
              <label className="text-[10px] text-c-ink-faint">Au</label>
              <input type="date" value={au}
                onChange={e => setAu(e.target.value)}
                className="w-full px-2 py-1 border border-c-line rounded text-xs" />
            </div>
          </div>

          <div>
            <label className="text-[10px] text-c-ink-faint">N° Commande</label>
            <input type="text" value={numCommande}
              onChange={e => setNumCommande(e.target.value.toUpperCase())}
              placeholder="TOUT EN MAJUSCULE (SANS ACCENT)"
              className="w-full px-2 py-1 border border-c-line rounded text-xs" />
          </div>

          <div>
            <label className="text-[10px] text-c-ink-faint">Par</label>
            <select value={opeAchat}
              onChange={e => setOpeAchat(e.target.value)}
              className="w-full px-2 py-1 border border-c-line rounded text-xs">
              <option value="">Tous</option>
              {operateurs.map(o => (
                <option key={o.id_salarie} value={o.id_salarie}>{o.nom_prenom}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[10px] text-c-ink-faint">Société</label>
            <select value={idSte}
              onChange={e => setIdSte(e.target.value)}
              className="w-full px-2 py-1 border border-c-line rounded text-xs">
              <option value="">Toutes</option>
              {societes.map(s => (
                <option key={s.id_ste} value={s.id_ste}>
                  {s.rs_interne || s.raison_sociale}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[10px] text-c-ink-faint">Enseigne</label>
            <select value={enseigne}
              onChange={e => setEnseigne(e.target.value)}
              className="w-full px-2 py-1 border border-c-line rounded text-xs">
              <option value="">---- Toutes ----</option>
              {enseignes.map(e => (
                <option key={e.enseigne} value={e.enseigne}>{e.enseigne}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[10px] text-c-ink-faint">Mode Paiement</label>
            <select value={modePaiement}
              onChange={e => setModePaiement(e.target.value)}
              className="w-full px-2 py-1 border border-c-line rounded text-xs">
              {MODES_PAIEMENT.map(m => (
                <option key={m.code} value={m.code}>{m.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[10px] text-c-ink-faint">Description</label>
            <input type="text" value={description}
              onChange={e => setDescription(e.target.value)}
              className="w-full px-2 py-1 border border-c-line rounded text-xs" />
          </div>

          <div>
            <label className="text-[10px] text-c-ink-faint">
              Montant TTC (€) entre / et
            </label>
            <div className="grid grid-cols-2 gap-2">
              <input type="number" step="0.01" value={montantMin || ''}
                onChange={e => setMontantMin(parseFloat(e.target.value) || 0)}
                className="w-full px-2 py-1 border border-c-line rounded text-xs" />
              <input type="number" step="0.01" value={montantMax || ''}
                onChange={e => setMontantMax(parseFloat(e.target.value) || 0)}
                className="w-full px-2 py-1 border border-c-line rounded text-xs" />
            </div>
            <p className="text-[10px] text-c-ink-faint italic mt-1">
              TTC global ou d'une facture
            </p>
          </div>

          {/* Glissière salarié/service + picker bénéficiaire */}
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
            <div className="flex gap-1 items-center">
              <button type="button" onClick={() => setPickerOpen(true)}
                className="flex-1 px-2 py-1.5 bg-white border border-c-line rounded text-xs text-left truncate"
                title={beneLabel || 'Choisir le bénéficiaire'}>
                {beneLabel || (beneServiceMode
                  ? 'Choisir le service…' : 'Choisir le salarié…')}
              </button>
              {beneId > 0 && (
                <button type="button"
                  onClick={() => { setBeneId(0); setBeneLabel('') }}
                  className="p-1.5 hover:bg-red-100 rounded text-red-600"
                  title="Effacer">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          <button type="button" onClick={rechercher} disabled={busy}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded bg-c-brand text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 mt-3">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Search className="w-4 h-4" />}
            Rechercher
          </button>
        </div>
      </div>

      {/* Tableau resultats */}
      <div className="flex-1 bg-white rounded-xl border border-c-line overflow-hidden flex flex-col">
        <div className="px-3 py-2 border-b border-c-line-soft flex items-center gap-2 text-xs">
          {/* 3 boutons d'action sur la ligne sélectionnée */}
          <button type="button" onClick={handleAjouter}
            title="Ajouter une facture"
            className="p-1.5 rounded text-c-brand hover:bg-c-brand/10">
            <Plus className="w-4 h-4" />
          </button>
          <button type="button" onClick={handleEditer} disabled={!selectedId}
            title="Éditer la facture sélectionnée"
            className="p-1.5 rounded text-c-brand hover:bg-c-brand/10 disabled:opacity-30 disabled:cursor-not-allowed">
            <Pencil className="w-4 h-4" />
          </button>
          <button type="button" onClick={handleSupprimer} disabled={!selectedId}
            title="Supprimer la facture sélectionnée"
            className="p-1.5 rounded text-red-600 hover:bg-red-50 disabled:opacity-30 disabled:cursor-not-allowed">
            <Trash2 className="w-4 h-4" />
          </button>
          <span className="w-px h-5 bg-c-line mx-1" />
          <span className="text-c-ink-faint">{lignes.length} commande(s)</span>
          {lignes.length > 0 && (
            <>
              <span className="ml-2 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-c-brand" />
                {lignes.filter(l => l.etat === 'ok').length}
              </span>
              <span className="flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5 text-orange-500" />
                {lignes.filter(l => l.etat === 'partiel').length}
              </span>
              <span className="flex items-center gap-1">
                <XCircle className="w-3.5 h-3.5 text-red-600" />
                {lignes.filter(l => l.etat === 'ko').length}
              </span>
            </>
          )}
          <div className="flex-1" />
          {lignes.length > 0 && (
            <button onClick={exportXlsx}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
              <FileDown className="w-3.5 h-3.5" /> Export XLSX
            </button>
          )}
        </div>

        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-c-surface-soft text-xs text-c-ink-faint uppercase tracking-wide sticky top-0">
              <tr>
                <th className="px-2 py-2 text-center w-10"></th>
                <th className="px-2 py-2 text-left">Date Achat</th>
                <th className="px-2 py-2 text-left">Opé Achat</th>
                <th className="px-2 py-2 text-left">Enseigne</th>
                <th className="px-2 py-2 text-left">N° Commande</th>
                <th className="px-2 py-2 text-left">Description</th>
                <th className="px-2 py-2 text-right">Montant TTC</th>
                <th className="px-2 py-2 text-left">Mode Paiement</th>
                <th className="px-2 py-2 text-left">Bénéficiaire</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-c-line-soft">
              {lignes.length === 0 ? (
                <tr>
                  <td colSpan={9} className="text-center py-12 text-c-ink-faint-2 italic">
                    Aucun résultat — choisis tes filtres et clique Rechercher.
                  </td>
                </tr>
              ) : lignes.map(l => (
                <tr key={l.id_commande}
                  onClick={() => setSelectedId(l.id_commande)}
                  className={`cursor-pointer hover:bg-c-surface-soft ${
                    selectedId === l.id_commande ? 'bg-c-brand/10' : ''
                  }`}>
                  <td className="px-2 py-1.5 text-center"><EtatBadge etat={l.etat} /></td>
                  <td className="px-2 py-1.5 tabular-nums">{shortDate(l.date_achat)}</td>
                  <td className="px-2 py-1.5">{l.ope_achat_nom}</td>
                  <td className="px-2 py-1.5">{l.enseigne}</td>
                  <td className="px-2 py-1.5 tabular-nums">{l.num_commande}</td>
                  <td className="px-2 py-1.5 max-w-md truncate" title={l.description}>
                    {l.description}
                  </td>
                  <td className="px-2 py-1.5 text-right tabular-nums font-medium">
                    {formatEur(l.montant_ttc)}
                  </td>
                  <td className="px-2 py-1.5">{l.mode_paiement}</td>
                  <td className="px-2 py-1.5">
                    {l.bene_nom}
                    {l.bene_service && (
                      <span className="ml-1 text-[10px] text-c-ink-faint">(service)</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {pickerOpen && (
        <BeneficiairePicker
          mode={beneServiceMode ? 'service' : 'salarie'}
          onSelect={(item) => {
            setBeneId(parseInt(item.id, 10) || 0)
            setBeneLabel(item.label)
          }}
          onClose={() => setPickerOpen(false)}
        />
      )}

      {ajoutOpen && (
        <FactureAjoutModal
          onClose={() => setAjoutOpen(false)}
          onCreated={(idCommande) => {
            // Apres creation : ouvrir Fen_FactureFiche pour ajouter les
            // factures (cf WinDev OuvreSoeur(Fen_FactureFiche, idNew))
            setFicheOpenId(idCommande)
          }}
        />
      )}

      {ficheOpenId && (
        <FactureFicheModal
          idCommande={ficheOpenId}
          onClose={() => setFicheOpenId('')}
          onChanged={rechercher}
        />
      )}
    </div>
  )
}
