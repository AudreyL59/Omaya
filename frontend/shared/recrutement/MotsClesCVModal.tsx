/**
 * Fen_CVEditMotsCles (WinDev) - Edition simple des mots cles d'un CV.
 *
 * Ouverte depuis Fen_CVFiche via le bouton loupe (ScanSearch).
 * Charge cvtheque.mots_cles, permet l'edition, save = UPDATE.
 */

import { useEffect, useState } from 'react'
import { ArrowLeft, FileText, Loader2, Save, X } from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '../ui/dialog'

const COL_BRUN = '#4E1D17'
const COL_PRIMARY = '#17494E'
const COL_BORDER = '#E5DDDC'
const COL_BG_SOFT = '#F8F5F4'

interface MotsClesCVModalProps {
  apiBase: string
  idCv: string
  candidatNom?: string
  candidatPrenom?: string
  onClose: () => void
}

export default function MotsClesCVModal({
  apiBase, idCv, candidatNom = '', candidatPrenom = '', onClose,
}: MotsClesCVModalProps) {
  const [motsCles, setMotsCles] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetch(`${apiBase}/recrutement/cv/${idCv}/mots-cles`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : { mots_cles: '' })
      .then(d => setMotsCles(d.mots_cles || ''))
      .finally(() => setLoading(false))
  }, [apiBase, idCv])

  const enregistrer = async () => {
    setSaving(true)
    try {
      const r = await fetch(`${apiBase}/recrutement/cv/${idCv}/mots-cles`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ mots_cles: motsCles }),
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast('Mots-clés enregistrés.', 'success')
      onClose()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col"
           onClick={e => e.stopPropagation()}
           style={{ border: `1px solid ${COL_BORDER}` }}>
        {/* HEADER */}
        <div className="px-4 py-3 border-b flex items-center gap-2"
             style={{ borderColor: COL_BORDER }}>
          <FileText className="w-5 h-5" style={{ color: COL_PRIMARY }} />
          <h2 className="text-lg font-bold flex-1" style={{ color: COL_BRUN }}>
            Édition des mots-clés
            {(candidatNom || candidatPrenom) && (
              <span className="text-sm font-normal ml-2" style={{ color: COL_PRIMARY }}>
                — {candidatNom} {candidatPrenom}
              </span>
            )}
          </h2>
          <button type="button" onClick={onClose}
                  className="p-1.5 rounded hover:bg-gray-100">
            <X className="w-5 h-5" style={{ color: COL_BRUN }} />
          </button>
        </div>

        {/* BODY */}
        {loading ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin" style={{ color: COL_PRIMARY }} />
          </div>
        ) : (
          <div className="flex-1 p-4 flex flex-col">
            <label className="text-xs font-semibold mb-2" style={{ color: COL_BRUN }}>
              Mots Clés
            </label>
            <textarea value={motsCles}
                      onChange={e => setMotsCles(e.target.value)}
                      placeholder="Ajoute ici les mots-clés du CV (un par ligne ou séparés par des virgules)..."
                      className="flex-1 px-3 py-2 rounded border text-sm font-mono resize-none"
                      style={{ borderColor: COL_BORDER, minHeight: 300 }} />
            <p className="text-xs mt-2 italic" style={{ color: '#A68D8A' }}>
              {motsCles.length} caractères
            </p>
          </div>
        )}

        {/* FOOTER */}
        {!loading && (
          <div className="px-4 py-3 border-t flex items-center gap-2"
               style={{ borderColor: COL_BORDER, backgroundColor: COL_BG_SOFT }}>
            <button type="button" onClick={onClose}
                    className="flex items-center gap-1 px-3 py-1.5 rounded border text-sm"
                    style={{ borderColor: COL_BORDER, color: COL_BRUN, backgroundColor: 'white' }}>
              <ArrowLeft className="w-3.5 h-3.5" />
              Retour Fiche CV
            </button>
            <div className="flex-1" />
            <button type="button" onClick={enregistrer} disabled={saving}
                    className="flex items-center gap-2 px-4 py-2 rounded text-white text-sm disabled:opacity-50"
                    style={{ backgroundColor: COL_PRIMARY }}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin" />
                      : <Save className="w-4 h-4" />}
              Enregistrer
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
