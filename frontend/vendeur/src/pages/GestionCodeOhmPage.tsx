// Page Gestion Code OHM (Vendeur) : gestion des demandes de code
// partenaire OHM Énergie pour les vendeurs (nouvelles demandes ou
// désactivations). Portage de Page_GestionCodeOhm WinDev.
//
// V1 : liste 2 onglets + modal "Voir contenu" (fichiers, code/login/mdp)
//      + bouton Rejet manque documents.
// V2 : export XLSX + ZIP FTP (bouton "Exporter la sélection"), import
//      XLSX pour renseigner les codes en masse (bouton "Importer les
//      code vendeurs" avec mapping colonnes A/B/C/D).

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Download, Eye, Upload, X } from 'lucide-react'
import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'

interface Demande {
  IDTK_Liste: string
  IDTK_DemandeCodeVendeur: string
  IdElem: string
  TypeOri: string
  IDPartenaire: string
  Code: string
  Login: string
  MDP: string
  DateCrea: string
  IDTKStatut: number
  LibStatut: string
  Nom: string
  Prenom: string
  NomPrenom: string
  NumTel: string
}

interface Fichier {
  IDFichier: string
  NomFichier: string
  LienFichier: string
  Url: string
}

const API = '/api/vendeur/gestion-ohm'

// Couleurs statut WinDev
const couleurStatut = (id: number): string => {
  switch (id) {
    case 1:  return '#ffffff'
    case 35: return '#8ECDD4'  // bleu
    case 36: return '#8EC88E'  // vert
    case 38: return '#C08EC8'  // violet
    default: return '#e5e7eb'  // gris
  }
}

const fmtDate = (raw: string): string => {
  if (!raw) return ''
  const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})/)
  return m ? `${m[3]}/${m[2]}/${m[1]}` : raw
}

export default function GestionCodeOhmPage() {
  const [onglet, setOnglet] = useState<1 | 2>(1)  // 1=encours, 2=desactiver
  const [demandes, setDemandes] = useState<Demande[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Demande | null>(null)
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [showImport, setShowImport] = useState(false)
  const [exporting, setExporting] = useState(false)

  const toggleCheck = (id: string) => {
    setChecked(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }
  const allChecked = useMemo(
    () => demandes.length > 0 && demandes.every(d => checked.has(d.IDTK_Liste)),
    [demandes, checked])
  const toggleAll = () => {
    if (allChecked) setChecked(new Set())
    else setChecked(new Set(demandes.map(d => d.IDTK_Liste)))
  }

  const exporter = async () => {
    if (checked.size === 0) {
      showToast('Sélectionne au moins une ligne', 'info'); return
    }
    setExporting(true)
    try {
      const r = await fetch(`${API}/export-selection`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ids: Array.from(checked) }),
      })
      if (!r.ok) {
        showToast('Échec export', 'error')
      } else {
        const blob = await r.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        const stamp = new Date().toISOString().replace(/[:.]/g, '').slice(0, 15)
        a.href = url; a.download = `Demandes_Accreditations_${stamp}.zip`
        document.body.appendChild(a); a.click(); a.remove()
        setTimeout(() => URL.revokeObjectURL(url), 5000)
        setChecked(new Set())
        void charger()
        showToast('Export généré + statuts passés à "Envoyé"', 'success')
      }
    } catch {
      showToast('Échec export', 'error')
    }
    setExporting(false)
  }

  const charger = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API}/demandes?onglet=${onglet}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      const data = r.ok ? await r.json() : []
      setDemandes(Array.isArray(data) ? data : [])
    } catch {
      setDemandes([])
    }
    setLoading(false)
  }, [onglet])

  useEffect(() => { void charger() }, [charger])

  return (
    <div className="p-3 h-full flex flex-col gap-3 min-h-0">
      {/* Onglets */}
      <div className="flex items-center gap-2">
        <button onClick={() => setOnglet(1)}
          className={`px-4 py-2 rounded font-semibold text-sm ${
            onglet === 1 ? 'bg-c-brand text-white' : 'bg-gray-100 text-c-ink-soft'}`}>
          Demandes de code
        </button>
        <button onClick={() => setOnglet(2)}
          className={`px-4 py-2 rounded font-semibold text-sm ${
            onglet === 2 ? 'bg-c-brand text-white' : 'bg-gray-100 text-c-ink-soft'}`}>
          Vendeurs sortis
        </button>
        <div className="flex-1" />
        <button onClick={exporter} disabled={exporting || checked.size === 0}
          className={`flex items-center gap-1 px-3 py-1.5 rounded text-sm font-semibold ${
            exporting || checked.size === 0
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-gray-900 text-white hover:brightness-110'}`}>
          <Download className="w-4 h-4" />
          Exporter la sélection{checked.size > 0 && ` (${checked.size})`}
        </button>
        <button onClick={() => setShowImport(true)}
          className="flex items-center gap-1 px-3 py-1.5 rounded bg-orange-600 text-white text-sm font-semibold hover:brightness-110">
          <Upload className="w-4 h-4" />
          Importer les codes vendeurs
        </button>
      </div>

      {/* Tableau */}
      <div className="flex-1 bg-white border border-c-line-soft rounded overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-900 text-white text-xs uppercase sticky top-0">
            <tr>
              <th className="text-center px-2 py-2 w-8">
                <input type="checkbox" checked={allChecked} onChange={toggleAll}
                  className="accent-white" />
              </th>
              <th className="text-left px-3 py-2">Statut</th>
              <th className="text-left px-3 py-2">Date demande</th>
              <th className="text-left px-3 py-2">Nom</th>
              <th className="text-left px-3 py-2">Prénom</th>
              <th className="text-left px-3 py-2">Num Tél</th>
              <th className="text-left px-3 py-2">Code</th>
              <th className="text-left px-3 py-2">Mot de passe</th>
              <th className="text-center px-3 py-2 w-12"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={9} className="text-center py-4 text-c-ink-soft">Chargement…</td></tr>
            )}
            {!loading && demandes.length === 0 && (
              <tr><td colSpan={9} className="text-center py-4 italic text-c-ink-faint">
                Aucune demande
              </td></tr>
            )}
            {demandes.map(d => (
              <tr key={d.IDTK_Liste}
                onDoubleClick={() => setSelected(d)}
                className={`border-t border-c-line-soft hover:bg-c-surface-soft ${
                  checked.has(d.IDTK_Liste) ? 'bg-blue-50' : ''}`}>
                <td className="text-center px-2 py-1.5">
                  <input type="checkbox" checked={checked.has(d.IDTK_Liste)}
                    onChange={() => toggleCheck(d.IDTK_Liste)}
                    onClick={e => e.stopPropagation()} />
                </td>
                <td className="px-3 py-1.5">
                  <span className="inline-block px-2 py-0.5 text-xs font-semibold rounded"
                    style={{ backgroundColor: couleurStatut(d.IDTKStatut) }}>
                    {d.LibStatut || `#${d.IDTKStatut}`}
                  </span>
                </td>
                <td className="px-3 py-1.5">{fmtDate(d.DateCrea)}</td>
                <td className="px-3 py-1.5 font-semibold">{d.Nom}</td>
                <td className="px-3 py-1.5">{d.Prenom}</td>
                <td className="px-3 py-1.5">{d.NumTel}</td>
                <td className="px-3 py-1.5">{d.Code}</td>
                <td className="px-3 py-1.5">{d.MDP}</td>
                <td className="text-center">
                  <button onClick={() => setSelected(d)}
                    className="p-1.5 rounded hover:bg-gray-100 text-c-ink-soft"
                    title="Voir contenu">
                    <Eye className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <ContenuTicketModal demande={selected}
          onClose={() => setSelected(null)}
          onSaved={() => { void charger() }} />
      )}

      {showImport && (
        <ImportCodesModal onClose={() => setShowImport(false)}
          onImported={() => { void charger() }} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
//  Modal Contenu Ticket
// ---------------------------------------------------------------------------

function ContenuTicketModal({ demande, onClose, onSaved }: {
  demande: Demande
  onClose: () => void
  onSaved: () => void
}) {
  const [code, setCode] = useState(demande.Code)
  const [login, setLogin] = useState(demande.Login)
  const [mdp, setMdp] = useState(demande.MDP)
  const [fichiers, setFichiers] = useState<Fichier[]>([])
  const [selectedFic, setSelectedFic] = useState<Fichier | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    void fetch(`${API}/demandes/${demande.IDTK_Liste}/fichiers`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(d => setFichiers(Array.isArray(d) ? d : []))
      .catch(() => setFichiers([]))
  }, [demande.IDTK_Liste])

  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onEsc)
    return () => window.removeEventListener('keydown', onEsc)
  }, [onClose])

  const enregistrer = async () => {
    if (saving) return
    setSaving(true)
    try {
      const r = await fetch(`${API}/demandes/${demande.IDTK_Liste}/enregistrer`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code, login, mdp }),
      })
      if (r.ok) {
        showToast('Modifications enregistrées', 'success')
        onSaved()
      } else {
        showToast('Échec enregistrement', 'error')
      }
    } catch {
      showToast('Échec enregistrement', 'error')
    }
    setSaving(false)
  }

  const rejeter = async () => {
    const ok = await showConfirm({
      title: 'Rejet Manque Documents ?',
      message: `Passer la demande de ${demande.NomPrenom} en statut "Rejet — Manque Documents" et notifier le BO/RH ?`,
      confirmLabel: 'Rejeter', variant: 'danger',
    })
    if (!ok) return
    try {
      const r = await fetch(`${API}/demandes/${demande.IDTK_Liste}/rejet`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (r.ok) {
        showToast('Rejet enregistré', 'success')
        onSaved()
        onClose()
      } else {
        showToast('Échec rejet', 'error')
      }
    } catch {
      showToast('Échec rejet', 'error')
    }
  }

  return (
    <div className="fixed inset-0 z-[90] bg-black/50 flex items-center justify-center p-4"
      onClick={onClose}>
      <div onClick={e => e.stopPropagation()}
        className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        <header className="flex items-center justify-between px-4 py-3 border-b border-c-line-soft">
          <div>
            <h3 className="text-base font-semibold">{demande.NomPrenom}</h3>
            <div className="text-xs text-c-ink-soft">{demande.LibStatut}</div>
          </div>
          <button onClick={onClose}
            className="p-1 rounded hover:bg-gray-100">
            <X className="w-4 h-4" />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
          {/* 2 colonnes : formulaire + docs */}
          <div className="grid grid-cols-2 gap-4">
            <section className="space-y-2">
              <label className="block">
                <span className="block text-xs text-c-ink-soft mb-0.5">Code</span>
                <input value={code} onChange={e => setCode(e.target.value)}
                  className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white" />
              </label>
              <label className="block">
                <span className="block text-xs text-c-ink-soft mb-0.5">Login</span>
                <input value={login} onChange={e => setLogin(e.target.value)}
                  className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white" />
              </label>
              <label className="block">
                <span className="block text-xs text-c-ink-soft mb-0.5">MDP</span>
                <input value={mdp} onChange={e => setMdp(e.target.value)}
                  className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white" />
              </label>
              <div className="flex gap-2 pt-2">
                <button onClick={enregistrer} disabled={saving}
                  className="flex-1 px-3 py-2 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
                  Enregistrer
                </button>
                <button onClick={rejeter}
                  className="flex-1 px-3 py-2 rounded bg-purple-700 text-white text-sm font-semibold hover:brightness-110">
                  Rejet Manque Document
                </button>
              </div>
            </section>
            <section>
              <div className="text-xs text-c-ink-soft font-semibold mb-1">
                DOCUMENTS ({fichiers.length})
              </div>
              <div className="border border-c-line-soft rounded overflow-y-auto max-h-64">
                {fichiers.length === 0 && (
                  <div className="p-3 text-xs italic text-c-ink-faint text-center">
                    Aucun fichier
                  </div>
                )}
                {fichiers.map(f => (
                  <button key={f.IDFichier}
                    onClick={() => setSelectedFic(f)}
                    className={`w-full text-left px-3 py-1.5 text-sm border-b border-c-line-soft hover:bg-c-brand-soft ${
                      selectedFic?.IDFichier === f.IDFichier ? 'bg-c-brand-soft' : ''}`}>
                    {f.NomFichier}
                  </button>
                ))}
              </div>
            </section>
          </div>

          {/* Preview iframe */}
          {selectedFic && selectedFic.Url && (
            <div className="border border-c-line-soft rounded overflow-hidden flex-1 min-h-[400px]">
              <iframe src={selectedFic.Url}
                title={selectedFic.NomFichier}
                className="w-full h-[500px]" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
//  Modal Import Codes (XLSX + mapping colonnes)
// ---------------------------------------------------------------------------

function ImportCodesModal({ onClose, onImported }: {
  onClose: () => void
  onImported: () => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [colCode, setColCode] = useState('A')
  const [colMdp, setColMdp] = useState('B')
  const [colNom, setColNom] = useState('C')
  const [colPrenom, setColPrenom] = useState('D')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<null | { lignes_lues: number
    maj_effectuees: number; mails_envoyes: number }>(null)

  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => e.key === 'Escape' && !running && onClose()
    window.addEventListener('keydown', onEsc)
    return () => window.removeEventListener('keydown', onEsc)
  }, [onClose, running])

  const importer = async () => {
    if (!file || running) return
    if (!/^[A-Z]$/.test(colCode.toUpperCase()) || !/^[A-Z]$/.test(colMdp.toUpperCase()) ||
        !/^[A-Z]$/.test(colNom.toUpperCase()) || !/^[A-Z]$/.test(colPrenom.toUpperCase())) {
      showToast('Colonnes doivent être des lettres A à Z', 'error'); return
    }
    setRunning(true); setResult(null)
    try {
      const fd = new FormData()
      fd.append('file', file, file.name)
      fd.append('col_code', colCode.toUpperCase())
      fd.append('col_mdp', colMdp.toUpperCase())
      fd.append('col_nom', colNom.toUpperCase())
      fd.append('col_prenom', colPrenom.toUpperCase())
      const r = await fetch(`${API}/import-codes`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      })
      if (r.ok) {
        const data = await r.json()
        setResult(data)
        onImported()
        showToast(`Import OK : ${data.maj_effectuees} maj, ${data.mails_envoyes} mails`, 'success')
      } else {
        const err = await r.json().catch(() => ({}))
        showToast(`Échec : ${err.detail || 'erreur'}`, 'error')
      }
    } catch {
      showToast('Échec import', 'error')
    }
    setRunning(false)
  }

  return (
    <div className="fixed inset-0 z-[90] bg-black/50 flex items-center justify-center p-4"
      onClick={() => !running && onClose()}>
      <div onClick={e => e.stopPropagation()}
        className="bg-white rounded-lg shadow-xl w-full max-w-md flex flex-col">
        <header className="flex items-center justify-between px-4 py-3 border-b border-c-line-soft">
          <h3 className="text-base font-semibold">Importation Base Excel</h3>
          <button onClick={onClose} disabled={running}
            className="p-1 rounded hover:bg-gray-100">
            <X className="w-4 h-4" />
          </button>
        </header>
        <div className="p-4 space-y-3">
          <label className="block">
            <span className="block text-xs text-c-ink-soft mb-1">Fichier Excel (.xlsx)</span>
            <input type="file" accept=".xlsx,.xls"
              onChange={e => setFile(e.target.files?.[0] || null)}
              className="w-full text-sm border border-c-line rounded px-2 py-1.5 bg-white" />
          </label>
          <div className="grid grid-cols-4 gap-2">
            {[
              { label: 'Identifiant', v: colCode, s: setColCode },
              { label: 'MDP', v: colMdp, s: setColMdp },
              { label: 'Nom', v: colNom, s: setColNom },
              { label: 'Prénom', v: colPrenom, s: setColPrenom },
            ].map(f => (
              <label key={f.label} className="block">
                <span className="block text-xs text-c-ink-soft mb-0.5">{f.label}</span>
                <input value={f.v} maxLength={1}
                  onChange={e => f.s(e.target.value.toUpperCase())}
                  className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white text-center font-mono uppercase" />
              </label>
            ))}
          </div>
          <p className="text-[10px] text-c-ink-soft italic">
            Colonne Excel (A, B, C, D…). Ex : identifiant en col B → tape "B".
          </p>
          {result && (
            <div className="bg-green-50 border border-green-200 rounded p-2 text-xs">
              ✓ {result.lignes_lues} lignes lues,{' '}
              <b>{result.maj_effectuees}</b> maj effectuées,{' '}
              <b>{result.mails_envoyes}</b> mails envoyés
            </div>
          )}
          <button onClick={importer} disabled={!file || running}
            className={`w-full px-3 py-2 rounded text-sm font-semibold ${
              !file || running
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-gray-900 text-white hover:brightness-110'}`}>
            {running ? 'Importation en cours…' : 'Importer le fichier'}
          </button>
        </div>
      </div>
    </div>
  )
}
