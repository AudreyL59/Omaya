// Page Gestion Code OHM (Vendeur) : gestion des demandes de code
// partenaire OHM Énergie pour les vendeurs (nouvelles demandes ou
// désactivations). Portage de Page_GestionCodeOhm WinDev.
//
// V1 : liste 2 onglets + modal "Voir contenu" (fichiers, code/login/mdp)
//      + bouton Rejet manque documents.
// V2 : export XLSX + ZIP FTP (bouton "Exporter la sélection"), import
//      XLSX pour renseigner les codes en masse (bouton "Importer les
//      code vendeurs" avec mapping colonnes A/B/C/D).

import { useCallback, useEffect, useState } from 'react'
import { Eye, X } from 'lucide-react'
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
        <button onClick={() => showToast('Export XLSX + ZIP — à venir (V2)', 'info')}
          className="px-3 py-1.5 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
          Exporter la sélection
        </button>
        <button onClick={() => showToast('Import XLSX — à venir (V2)', 'info')}
          className="px-3 py-1.5 rounded bg-orange-600 text-white text-sm font-semibold hover:brightness-110">
          Importer les codes vendeurs
        </button>
      </div>

      {/* Tableau */}
      <div className="flex-1 bg-white border border-c-line-soft rounded overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-900 text-white text-xs uppercase sticky top-0">
            <tr>
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
              <tr><td colSpan={8} className="text-center py-4 text-c-ink-soft">Chargement…</td></tr>
            )}
            {!loading && demandes.length === 0 && (
              <tr><td colSpan={8} className="text-center py-4 italic text-c-ink-faint">
                Aucune demande
              </td></tr>
            )}
            {demandes.map(d => (
              <tr key={d.IDTK_Liste}
                onDoubleClick={() => setSelected(d)}
                className="border-t border-c-line-soft hover:bg-c-surface-soft">
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
