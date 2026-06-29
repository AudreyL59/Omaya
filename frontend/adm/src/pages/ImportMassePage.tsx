/**
 * Fen_ImportMasse — Import en masse multi-partenaire (5 onglets).
 *
 * Onglets : Modif État / Modif Produit / Modif Options / Ajout Infos Internes
 * / Modif Vendeur. Chaque onglet : combo partenaire + paramètres spécifiques
 * + fichier Excel (col A = num_bs).
 */
import { useEffect, useRef, useState } from 'react'
import { FileUp, Loader2, Play } from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'
const API_BASE = '/api/adm'

interface Partenaire {
  id_partenaire: string; prefixe_bdd: string;
  lib_partenaire: string; is_actif: boolean
}
interface Etat { id_etat: number; lib_complet: string }
interface Produit { id_produit: number; lib_produit: string }
interface Ligne {
  num_ctt: string; id_contrat: number; produit: string;
  ancien_etat: string; nouvel_etat: string; mois_paiement: string;
  statut: string
}
interface Result {
  ok: boolean; message: string;
  resume: { nb_lignes: number; nb_modifies: number; nb_deja_statues: number;
            nb_non_modifies: number; nb_introuvables: number; nb_erreurs: number }
  lignes: Ligne[]
}

type Tab = 'etat' | 'produit' | 'options' | 'infos' | 'vendeur'

export default function ImportMassePage() {
  useDocumentTitle('Import en Masse')
  const [tab, setTab] = useState<Tab>('etat')
  const [partenaires, setPartenaires] = useState<Partenaire[]>([])
  const [partenaire, setPartenaire] = useState('')
  const [etats, setEtats] = useState<Etat[]>([])
  const [produits, setProduits] = useState<Produit[]>([])

  const [colNum, setColNum] = useState('A')
  const [colComment, setColComment] = useState('B')
  const [simulation, setSimulation] = useState(true)
  const [file, setFile] = useState<File | null>(null)
  const fileRef = useRef<HTMLInputElement | null>(null)

  // Onglet Etat
  const [idEtat, setIdEtat] = useState(0)
  const [moisPaiement, setMoisPaiement] = useState('')
  const [mode, setMode] = useState<'vendeur' | 'operateur'>('vendeur')
  const [modifDejaStatues, setModifDejaStatues] = useState(false)
  const [modifAttente, setModifAttente] = useState(true)
  const [recocheEnergies, setRecocheEnergies] = useState(false)
  // Onglet Produit
  const [idProduit, setIdProduit] = useState(0)
  // Onglet Options SFR
  const [horsCluster, setHorsCluster] = useState(true)
  // Onglet Vendeur
  const [idSalarie, setIdSalarie] = useState(0)
  const [nomSalarie, setNomSalarie] = useState('')

  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<Result | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/imports/masse/partenaires`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then((d: Partenaire[]) => setPartenaires(Array.isArray(d) ? d : []))
  }, [])

  useEffect(() => {
    if (!partenaire) { setEtats([]); setProduits([]); return }
    fetch(`${API_BASE}/imports/masse/etats/${partenaire}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    }).then(r => r.ok ? r.json() : []).then((d: Etat[]) => setEtats(d || []))
    fetch(`${API_BASE}/imports/masse/produits/${partenaire}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    }).then(r => r.ok ? r.json() : []).then((d: Produit[]) => setProduits(d || []))
  }, [partenaire])

  const demarrer = async () => {
    if (!file) { showToast('Choisis un fichier.', 'info'); return }
    if (tab !== 'options' && !partenaire) {
      showToast('Choisis un partenaire.', 'info'); return
    }
    let confirmMsg = ''
    let endpoint = ''
    const fd = new FormData()
    fd.append('file', file)
    fd.append('col_num', colNum)
    fd.append('simulation', String(simulation))

    if (tab === 'etat') {
      if (!idEtat) { showToast('Choisis un état.', 'info'); return }
      const e = etats.find(x => x.id_etat === idEtat)
      confirmMsg = `Modifier les contrats vers : ${e?.lib_complet} ${moisPaiement ? `(mois ${moisPaiement})` : ''} ?`
      endpoint = '/imports/masse/etat'
      fd.append('partenaire', partenaire); fd.append('id_etat_new', String(idEtat))
      fd.append('mois_paiement', moisPaiement); fd.append('mode', mode)
      fd.append('modif_deja_statues', String(modifDejaStatues))
      fd.append('modif_uniquement_attente', String(modifAttente))
      fd.append('recoche_energies', String(recocheEnergies))
    } else if (tab === 'produit') {
      if (!idProduit) { showToast('Choisis un produit.', 'info'); return }
      const pr = produits.find(x => x.id_produit === idProduit)
      confirmMsg = `Modifier les contrats vers le produit : ${pr?.lib_produit} ?`
      endpoint = '/imports/masse/produit'
      fd.append('partenaire', partenaire); fd.append('id_produit_new', String(idProduit))
    } else if (tab === 'options') {
      confirmMsg = `Modifier les options SFR (Hors cluster = ${horsCluster}) ?`
      endpoint = '/imports/masse/option-sfr'
      fd.append('hors_cluster', String(horsCluster))
    } else if (tab === 'infos') {
      confirmMsg = `Ajouter le commentaire (col ${colComment}) à info_interne ?`
      endpoint = '/imports/masse/info-interne'
      fd.append('partenaire', partenaire); fd.append('col_comment', colComment)
    } else if (tab === 'vendeur') {
      if (!idSalarie) { showToast('Choisis un vendeur.', 'info'); return }
      confirmMsg = `Réattribuer les contrats à : ${nomSalarie} ?`
      endpoint = '/imports/masse/vendeur'
      fd.append('partenaire', partenaire); fd.append('id_salarie_new', String(idSalarie))
    }

    const ok = await showConfirm({ title: 'Confirmation', message: confirmMsg })
    if (!ok) return

    setBusy(true); setResult(null)
    try {
      const r = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST', headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      if (!r.ok) throw new Error(String(r.status))
      const d: Result = await r.json()
      setResult(d)
      showToast(d.message || (d.ok ? 'OK' : 'Échec'),
                d.ok ? 'success' : 'error')
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setBusy(false) }
  }

  const partOpt = partenaires.map(p => (
    <option key={p.id_partenaire} value={p.prefixe_bdd?.toLowerCase()}>
      {p.lib_partenaire}
    </option>
  ))

  return (
    <div className="p-4 flex flex-col h-[calc(100vh-120px)]"
         style={{ color: COL_BRUN }}>
      <h1 className="text-xl font-bold mb-3">
        Import en masse{simulation && (
          <span className="ml-2 text-xs px-2 py-0.5 rounded"
                style={{ backgroundColor: '#fef3c7', color: '#92400e' }}>
            SIMULATION
          </span>
        )}
      </h1>

      {/* Bandeau commun */}
      <div className="border rounded p-3 mb-3 flex items-end gap-3 flex-wrap"
           style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
        {tab !== 'options' && (
          <div className="flex flex-col">
            <label className="text-[10px] mb-1">Partenaire</label>
            <select value={partenaire}
                    onChange={e => setPartenaire(e.target.value)}
                    className="px-2 py-1.5 rounded border text-sm h-9"
                    style={{ borderColor: COL_BORDER, minWidth: '180px' }}>
              <option value="">—</option>
              {partOpt}
            </select>
          </div>
        )}
        <div className="flex flex-col">
          <label className="text-[10px] mb-1">Fichier Excel</label>
          <input ref={fileRef} type="file" accept=".xlsx,.xls,.xlsm"
                 onChange={e => setFile(e.target.files?.[0] || null)}
                 className="hidden" />
          <button type="button" onClick={() => fileRef.current?.click()}
                  className="flex items-center gap-1 px-3 py-1.5 rounded border text-xs h-9"
                  style={{ borderColor: COL_BORDER, color: COL_PRIMARY,
                           minWidth: '220px' }}>
            <FileUp className="w-3.5 h-3.5" />
            <span className="truncate">{file?.name || 'Choisir un fichier'}</span>
          </button>
        </div>
        <div className="flex flex-col">
          <label className="text-[10px] mb-1">Col Num</label>
          <input type="text" value={colNum}
                 onChange={e => setColNum(e.target.value.toUpperCase())}
                 className="px-2 py-1.5 rounded border text-sm w-14 text-center"
                 style={{ borderColor: COL_BORDER }} />
        </div>
        <label className="flex items-center gap-2 text-sm h-9">
          <input type="checkbox" checked={simulation}
                 onChange={e => setSimulation(e.target.checked)} />
          Faire une simulation
        </label>
      </div>

      {/* Onglets */}
      <div className="flex border-b mb-2" style={{ borderColor: COL_BORDER }}>
        {([
          ['etat', 'Modif État'], ['produit', 'Modif Produit'],
          ['options', 'Modif Options'], ['infos', 'Ajout Infos Internes'],
          ['vendeur', 'Modif Vendeur'],
        ] as [Tab, string][]).map(([k, lbl]) => (
          <button key={k} type="button" onClick={() => setTab(k)}
                  className="px-3 py-2 text-sm border-b-2"
                  style={{
                    borderColor: tab === k ? COL_PRIMARY : 'transparent',
                    color: tab === k ? COL_PRIMARY : '#A68D8A',
                    fontWeight: tab === k ? 'bold' : 'normal',
                  }}>{lbl}</button>
        ))}
      </div>

      {/* Onglet Etat */}
      {tab === 'etat' && (
        <div className="border rounded p-3 mb-3 space-y-2"
             style={{ borderColor: COL_BORDER }}>
          <div className="flex gap-3 items-end flex-wrap">
            <select value={idEtat} onChange={e => setIdEtat(Number(e.target.value))}
                    className="px-2 py-1.5 rounded border text-sm flex-1"
                    style={{ borderColor: COL_BORDER, minWidth: '280px' }}>
              <option value={0}>— État cible —</option>
              {etats.map(e => (
                <option key={e.id_etat} value={e.id_etat}>{e.lib_complet}</option>
              ))}
            </select>
            <input type="text" value={moisPaiement}
                   onChange={e => setMoisPaiement(e.target.value)}
                   placeholder="MM-AAAA"
                   className="px-2 py-1.5 rounded border text-sm w-28 text-center"
                   style={{ borderColor: COL_BORDER }} />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={modifDejaStatues}
                   onChange={e => setModifDejaStatues(e.target.checked)} />
            Modifier aussi les Déjà statués
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={modifAttente}
                   onChange={e => setModifAttente(e.target.checked)} />
            Modifier UNIQUEMENT les contrats en ATTENTE ou TEMPORAIRE
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={recocheEnergies}
                   onChange={e => setRecocheEnergies(e.target.checked)} />
            Recocher les énergies et recalculer les points (ENI valide uniquement)
          </label>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => { setMode('vendeur'); demarrer() }}
                    disabled={busy} className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm disabled:opacity-50"
                    style={{ backgroundColor: COL_PRIMARY }}>
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Modif État Vendeur
            </button>
            <button type="button" onClick={() => { setMode('operateur'); demarrer() }}
                    disabled={busy} className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm disabled:opacity-50"
                    style={{ backgroundColor: COL_PRIMARY }}>
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Modif État Opérateur (SFR/OEN)
            </button>
          </div>
        </div>
      )}

      {/* Onglet Produit */}
      {tab === 'produit' && (
        <div className="border rounded p-3 mb-3 flex items-end gap-3 flex-wrap"
             style={{ borderColor: COL_BORDER }}>
          <select value={idProduit}
                  onChange={e => setIdProduit(Number(e.target.value))}
                  className="px-2 py-1.5 rounded border text-sm flex-1"
                  style={{ borderColor: COL_BORDER, minWidth: '320px' }}>
            <option value={0}>— Produit cible —</option>
            {produits.map(p => (
              <option key={p.id_produit} value={p.id_produit}>{p.lib_produit}</option>
            ))}
          </select>
          <button type="button" onClick={demarrer} disabled={busy}
                  className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Démarrer
          </button>
        </div>
      )}

      {/* Onglet Options SFR */}
      {tab === 'options' && (
        <div className="border rounded p-3 mb-3 flex items-end gap-3 flex-wrap"
             style={{ borderColor: COL_BORDER }}>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={horsCluster}
                   onChange={e => setHorsCluster(e.target.checked)} />
            SFR Hors cluster
          </label>
          <button type="button" onClick={demarrer} disabled={busy}
                  className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Mettre à jour l'option
          </button>
        </div>
      )}

      {/* Onglet Infos Internes */}
      {tab === 'infos' && (
        <div className="border rounded p-3 mb-3 flex items-end gap-3 flex-wrap"
             style={{ borderColor: COL_BORDER }}>
          <div className="flex flex-col">
            <label className="text-[10px] mb-1">Col Commentaire</label>
            <input type="text" value={colComment}
                   onChange={e => setColComment(e.target.value.toUpperCase())}
                   className="px-2 py-1.5 rounded border text-sm w-14 text-center"
                   style={{ borderColor: COL_BORDER }} />
          </div>
          <button type="button" onClick={demarrer} disabled={busy}
                  className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Importer les commentaires
          </button>
        </div>
      )}

      {/* Onglet Vendeur */}
      {tab === 'vendeur' && (
        <div className="border rounded p-3 mb-3 flex items-end gap-3 flex-wrap"
             style={{ borderColor: COL_BORDER }}>
          <div className="flex flex-col">
            <label className="text-[10px] mb-1">ID Salarié cible</label>
            <input type="number" value={idSalarie || ''}
                   onChange={e => setIdSalarie(Number(e.target.value))}
                   className="px-2 py-1.5 rounded border text-sm w-48"
                   style={{ borderColor: COL_BORDER }} />
          </div>
          <div className="flex flex-col">
            <label className="text-[10px] mb-1">Nom affiché</label>
            <input type="text" value={nomSalarie}
                   onChange={e => setNomSalarie(e.target.value)}
                   placeholder="NOM Prénom"
                   className="px-2 py-1.5 rounded border text-sm w-64"
                   style={{ borderColor: COL_BORDER }} />
          </div>
          <button type="button" onClick={demarrer} disabled={busy}
                  className="flex items-center gap-2 px-4 py-1.5 rounded text-white text-sm disabled:opacity-50"
                  style={{ backgroundColor: COL_PRIMARY }}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Modif Vendeur
          </button>
        </div>
      )}

      {/* Tableau résultat */}
      <div className="flex-1 flex flex-col min-h-0 border rounded"
           style={{ borderColor: COL_BORDER }}>
        {result && (
          <div className="px-3 py-2 text-xs border-b"
               style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
            {result.message}
          </div>
        )}
        <div className="flex-1 overflow-auto">
          {!result ? (
            <p className="italic text-sm text-center mt-8"
               style={{ color: '#A68D8A' }}>
              Choisis un fichier et clique sur Démarrer.
            </p>
          ) : result.lignes.length === 0 ? (
            <p className="italic text-sm text-center mt-8"
               style={{ color: '#A68D8A' }}>
              Aucune ligne.
            </p>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0"
                     style={{ backgroundColor: COL_PRIMARY, color: 'white' }}>
                <tr>
                  <th className="px-2 py-1.5 text-left">IdContrat</th>
                  <th className="px-2 py-1.5 text-left">Produit</th>
                  <th className="px-2 py-1.5 text-left">Num CTT</th>
                  <th className="px-2 py-1.5 text-left">Ancien</th>
                  <th className="px-2 py-1.5 text-left">Nouveau</th>
                  <th className="px-2 py-1.5 text-left">Statut</th>
                </tr>
              </thead>
              <tbody>
                {result.lignes.map((l, i) => (
                  <tr key={i} className="border-b" style={{ borderColor: COL_BORDER }}>
                    <td className="px-2 py-1.5">{l.id_contrat || ''}</td>
                    <td className="px-2 py-1.5">{l.produit}</td>
                    <td className="px-2 py-1.5">{l.num_ctt}</td>
                    <td className="px-2 py-1.5">{l.ancien_etat}</td>
                    <td className="px-2 py-1.5">{l.nouvel_etat}</td>
                    <td className="px-2 py-1.5">{l.statut}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
