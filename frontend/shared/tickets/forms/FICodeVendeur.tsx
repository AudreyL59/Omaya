import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Building2, Download, Loader2, Plus, Save, Send, Trash2, UserX,
} from 'lucide-react'

import type { FIProps } from './index'
import { showConfirm, showToast } from '../../ui/dialog'

// FI_DemandeCodeVendeur (types 38 Demande + 39 Désactivation).
// Même fenêtre, comportement piloté par data.is_desactivation
// renvoyé par le backend (déduit de IDTK_TypeDemande).
export default function FICodeVendeur({
  apiBase, getToken, idTicket, onClose,
}: FIProps) {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)

  // Champs éditables
  const [code, setCode] = useState('')
  const [login, setLogin] = useState('')
  const [mdp, setMdp] = useState('')
  const [idTypeDoc, setIdTypeDoc] = useState('')

  const fileInputRef = useRef<HTMLInputElement>(null)

  const reload = useCallback(() => {
    setLoading(true)
    fetch(`${apiBase}/tickets/${idTicket}/form`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.json())
      .then((d) => {
        const dd = d?.data || null
        setData(dd)
        if (dd && dd.found) {
          setCode(dd.code || '')
          setLogin(dd.login || '')
          setMdp(dd.mdp || '')
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
      if (!resp.ok || j?.ok === false) {
        showToast(`Erreur : ${j?.error || j?.detail || resp.status}`, 'error')
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

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-c-ink-icon animate-spin" />
      </div>
    )
  }
  if (!data || !data.found) {
    return (
      <div className="h-full flex items-center justify-center text-c-ink-faint text-sm">
        Aucune demande de code vendeur pour ce ticket.
      </div>
    )
  }

  const isDesactivation: boolean = !!data.is_desactivation
  const documents: any[] = data.documents || []
  const typesDoc: any[] = data.types_doc || []

  const enregistrer = async () => {
    const r = await post({
      action: 'enregistrer',
      code, login, mdp,
    })
    if (r) showToast('Informations enregistrées.', 'success')
  }

  const desactivation = async () => {
    if (
      !(await showConfirm({
        message:
          'Désactiver les accès du vendeur ?\n' +
          (data.type_ori === 'DPAE'
            ? 'Le mot de passe sera effacé côté salarié_partenaire.'
            : 'Aucune cascade (origine non DPAE).'),
        variant: 'danger',
        confirmLabel: 'Désactiver',
      }))
    )
      return
    const r = await post({
      action: 'desactivation',
      code, login, mdp,
    })
    if (r) {
      showToast(
        'Accès désactivés.' + (r.cascade ? ' (cascade salarié_partenaire OK)' : ''),
        'success',
      )
      setTimeout(() => onClose?.(), 1200)
    }
  }

  const renvoyerTraitement = async () => {
    if (
      !(await showConfirm({
        message: 'Renvoyer le ticket pour traitement (statut "Nouveau") ?',
        confirmLabel: 'Renvoyer',
      }))
    )
      return
    const r = await post({ action: 'renvoyer_traitement' })
    if (r) {
      showToast('Ticket renvoyé pour traitement.', 'success')
      setTimeout(() => onClose?.(), 1200)
    }
  }

  const openDoc = async (nomFichier: string) => {
    if (!nomFichier) return
    try {
      const resp = await fetch(
        `${apiBase}/tickets/${idTicket}/form/file?name=${encodeURIComponent(nomFichier)}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!resp.ok) {
        showToast('Document introuvable.', 'error')
        return
      }
      const blob = await resp.blob()
      window.open(URL.createObjectURL(blob), '_blank')
    } catch {
      showToast('Erreur réseau (document).', 'error')
    }
  }

  const supprimerDoc = async (id: string) => {
    if (
      !(await showConfirm({
        message: 'Supprimer ce document de la liste ?',
        confirmLabel: 'Supprimer',
        variant: 'danger',
      }))
    )
      return
    const r = await post({ action: 'delete_document', id_doc: id })
    if (r) {
      setData((d: any) => ({ ...d, documents: r.documents || d.documents }))
      showToast('Document supprimé.', 'success')
    }
  }

  const onPickFile = () => {
    if (!idTypeDoc) {
      showToast('Choisis d\'abord le type de document.', 'error')
      return
    }
    fileInputRef.current?.click()
  }

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    const t = typesDoc.find((x) => x.id === idTypeDoc)
    if (!t) {
      showToast('Type de document invalide.', 'error')
      return
    }
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', f)
      const qs = new URLSearchParams({
        id_type_photo_dpae: t.id,
        lib_type_doc: t.lib,
      }).toString()
      const resp = await fetch(
        `${apiBase}/tickets/${idTicket}/form/upload?${qs}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${getToken()}` },
          body: fd,
        },
      )
      const j = await resp.json().catch(() => null)
      if (!resp.ok || j?.ok === false) {
        showToast(`Erreur : ${j?.error || j?.detail || resp.status}`, 'error')
        return
      }
      setData((d: any) => ({ ...d, documents: j.documents || d.documents }))
      showToast('Document ajouté.', 'success')
    } catch {
      showToast('Erreur réseau (upload).', 'error')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* COLONNE GAUCHE — Identifiants */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-sm">
          <Building2 className="w-4 h-4 text-c-ink-icon" />
          <span className="text-c-ink-soft">Partenaire :</span>
          <span className="text-c-ink font-semibold">
            {data.lib_partenaire || '—'}
          </span>
        </div>

        <label className="block text-sm">
          <span className="text-c-ink-soft">Code Vendeur</span>
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
          />
        </label>

        <p className="text-xs italic text-c-ink-faint">Et / Ou selon les cas</p>

        <label className="block text-sm">
          <span className="text-c-ink-soft">Login</span>
          <input
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
          />
        </label>

        <label className="block text-sm">
          <span className="text-c-ink-soft">Mot de passe</span>
          <input
            value={mdp}
            onChange={(e) => setMdp(e.target.value)}
            className="mt-1 w-full px-2 py-1 border border-c-line-strong rounded-md text-sm"
          />
        </label>

        {/* Bouton conditionnel selon le type */}
        {isDesactivation ? (
          <button
            onClick={desactivation}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-red-600 text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
          >
            <UserX className="w-4 h-4" />
            Désactivation des accès
          </button>
        ) : (
          <button
            onClick={enregistrer}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            Enregistrer
          </button>
        )}

        {/* Lien renvoi traitement */}
        <button
          onClick={renvoyerTraitement}
          disabled={saving}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong text-sm text-c-brand hover:bg-c-brand-soft disabled:opacity-50"
        >
          <Send className="w-4 h-4" />
          Renvoyer le Ticket pour traitement
        </button>
      </div>

      {/* COLONNE DROITE — Documents */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-c-brand-strong uppercase tracking-wide">
          Documents
        </h3>

        <div className="border border-c-line rounded-lg overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-c-surface-soft text-c-ink-soft text-left">
              <tr>
                <th className="px-2 py-2">Nom Fichier</th>
                <th className="px-2 py-2 w-10" />
              </tr>
            </thead>
            <tbody>
              {documents.length === 0 ? (
                <tr>
                  <td
                    colSpan={2}
                    className="px-2 py-3 text-center text-c-ink-faint"
                  >
                    Aucun document.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr
                    key={doc.id}
                    className="border-t border-c-line hover:bg-c-surface-soft"
                  >
                    <td
                      className="px-2 py-1.5 cursor-pointer text-c-brand hover:underline"
                      onClick={() => openDoc(doc.lien_fichier || doc.nom_fichier)}
                      title="Télécharger le fichier"
                    >
                      {doc.nom_fichier || doc.lien_fichier}
                    </td>
                    <td className="px-2 py-1.5">
                      <button
                        onClick={() => supprimerDoc(doc.id)}
                        disabled={saving}
                        className="text-c-ink-faint hover:text-red-600"
                        title="Supprimer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Bouton télécharger (1er doc sélectionné) — proposé par la
            spec ; ici on a déjà le clic sur la ligne. On expose un bouton
            de raccourci sur le dernier doc pour rester fidèle à la maquette. */}
        {documents.length > 0 && (
          <button
            onClick={() =>
              openDoc(
                documents[0].lien_fichier || documents[0].nom_fichier,
              )
            }
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-c-line-strong text-sm hover:bg-c-brand-soft"
          >
            <Download className="w-4 h-4 text-c-brand" />
            Télécharger le 1er document
          </button>
        )}

        {/* Combo type doc + bouton + */}
        <div className="flex items-center gap-2">
          <select
            value={idTypeDoc}
            onChange={(e) => setIdTypeDoc(e.target.value)}
            className="flex-1 px-2 py-1 border border-c-line-strong rounded-md text-sm bg-white"
          >
            <option value="">--- Type Document ---</option>
            {typesDoc.map((t) => (
              <option key={t.id} value={t.id}>
                {t.lib}
              </option>
            ))}
          </select>
          <button
            onClick={onPickFile}
            disabled={uploading || !idTypeDoc}
            className="px-3 py-2 rounded-lg bg-c-brand text-white text-sm font-semibold hover:brightness-110 disabled:opacity-50"
            title="Ajouter un document"
          >
            {uploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={onFileChange}
          />
        </div>
      </div>
    </div>
  )
}
