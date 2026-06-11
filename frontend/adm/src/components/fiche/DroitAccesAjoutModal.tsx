/**
 * Popup ajout de droits d'acces (transposition WinDev) :
 *   - variant='intranet' -> Fen_SalarieDroitAjout (ADM=0, FDV=1 +
 *     combo Profil + 'Choisir ce profil').
 *   - variant='software' -> Fen_ChoixDroitPerso (ADM=1, FDV=0,
 *     restreint aux droits de l'operateur connecte).
 *
 * Selection multiple via checkbox + Tout cocher. A la validation,
 * le backend gere INSERT (nouveau) vs UPDATE (deja attribue).
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Check, Loader2, X } from 'lucide-react'

import { getToken } from '@/api'
import { showConfirm, showToast } from '@shared/ui/dialog'
import { COLOR_BG_SOFT, COLOR_BRUN, COLOR_PRIMARY } from '@shared/fiche/EmbaucheTab'

interface Droit {
  id_type_droit_acces: number
  lib_droit: string
  code_interne: string
  description: string
  categorie: string
  deja_attribue: boolean
  droit_actif: boolean
}

interface Props {
  idSalarie: string
  variant: 'intranet' | 'software'
  onClose: () => void
  onSaved: () => void
}

export default function DroitAccesAjoutModal({
  idSalarie,
  variant,
  onClose,
  onSaved,
}: Props) {
  const [rows, setRows] = useState<Droit[]>([])
  const [profils, setProfils] = useState<string[]>([])
  const [profilChoix, setProfilChoix] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [saving, setSaving] = useState(false)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/droit-acces/disponibles?type=${variant}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      const j = (await r.json()) as { items: Droit[] }
      setRows(j.items || [])
    } catch (e) {
      showToast(`Échec chargement : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [idSalarie, variant])

  useEffect(() => {
    void reload()
  }, [reload])

  // Combo profils : uniquement pour 'intranet'
  useEffect(() => {
    if (variant !== 'intranet') return
    fetch('/api/adm/fiche-salarie/droit-acces/profils', {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((j) => setProfils((j as { items: string[] }).items || []))
      .catch(() => {})
  }, [variant])

  const groups = useMemo(() => {
    const map = new Map<string, Droit[]>()
    for (const it of rows) {
      const k = it.categorie || '(sans catégorie)'
      const arr = map.get(k) || []
      arr.push(it)
      map.set(k, arr)
    }
    return Array.from(map.entries()).map(([key, items]) => ({ key, items }))
  }, [rows])

  const toggle = (id: number) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelected(next)
  }

  const handleValider = async () => {
    if (selected.size === 0) {
      showToast('Sélectionner au moins une ligne.', 'info')
      return
    }
    // Pour les deja attribues, demander Activer/Desactiver
    const ids = Array.from(selected)
    const alreadyAttributed = ids.filter(
      (id) => rows.find((r) => r.id_type_droit_acces === id)?.deja_attribue,
    )
    let droitActif = true
    if (alreadyAttributed.length > 0) {
      const choice = await showConfirm({
        title: 'Droit déjà attribué',
        message:
          `${alreadyAttributed.length} droit(s) sélectionné(s) sont déjà attribués. ` +
          `Choisir Activer (Oui) ou Désactiver (Non).`,
        confirmLabel: 'Activer',
        cancelLabel: 'Désactiver',
      })
      droitActif = choice
    }
    setSaving(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/droit-acces/attribuer`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({ id_types: ids, droit_actif: droitActif }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const j = (await r.json()) as { nb_inserted: number; nb_updated: number }
      showToast(
        `${j.nb_inserted} ajouté(s), ${j.nb_updated} mis à jour.`,
        'success',
      )
      onSaved()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleChoisirProfil = async () => {
    if (!profilChoix) {
      showToast('Sélectionner un profil.', 'info')
      return
    }
    const ok = await showConfirm({
      title: 'Attribuer ce profil ?',
      message: `Vous êtes sur le point d'attribuer le profil "${profilChoix}". Voulez-vous continuer ?`,
      confirmLabel: 'Attribuer',
    })
    if (!ok) return
    setSaving(true)
    try {
      const r = await fetch(
        `/api/adm/fiche-salarie/${idSalarie}/droit-acces/profil`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({ categorie: profilChoix }),
        },
      )
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error((j as { detail?: string })?.detail || String(r.status))
      }
      const j = (await r.json()) as { nb_inserted: number; nb_updated: number }
      showToast(
        `Profil appliqué : ${j.nb_inserted} ajouté(s), ${j.nb_updated} mis à jour.`,
        'success',
      )
      onSaved()
    } catch (e) {
      showToast(`Échec : ${(e as Error).message}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const title =
    variant === 'intranet'
      ? "Ajouter un droit d'accès (Intranet / Appli)"
      : 'Choisir parmi ces droits (Omaya Software)'
  const subtitle =
    variant === 'intranet'
      ? "Liste des droits pour l'intranet et appli, pour les droits spécifiques sur Omaya Software, contactez l'administrateur."
      : 'Seuls les droits que vous possédez vous-même sont proposés (délégation).'

  const template = '36px 70px 1fr 1.5fr 100px'

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white rounded-2xl shadow-2xl w-[1100px] max-w-[97vw] max-h-[88vh] flex flex-col overflow-hidden"
        >
          <div
            className="flex items-center justify-between px-5 py-3 border-b"
            style={{ borderColor: COLOR_BG_SOFT }}
          >
            <h2 className="text-base font-semibold" style={{ color: COLOR_BRUN }}>
              {title}
            </h2>
            <button
              onClick={onClose}
              className="p-1 rounded hover:bg-[#EFE9E7]"
              style={{ color: COLOR_BRUN }}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Bandeau actions */}
          <div
            className="flex items-center gap-3 px-5 py-3 border-b"
            style={{ borderColor: COLOR_BG_SOFT, backgroundColor: '#FBF9F8' }}
          >
            <button
              type="button"
              onClick={handleValider}
              disabled={saving || selected.size === 0}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded text-white disabled:opacity-40"
              style={{ backgroundColor: COLOR_PRIMARY }}
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Valider ce(s) droit(s)
            </button>
            {variant === 'intranet' && (
              <div className="flex items-center gap-2 ml-auto">
                <span className="text-sm" style={{ color: COLOR_BRUN }}>
                  Profil :
                </span>
                <select
                  value={profilChoix}
                  onChange={(e) => setProfilChoix(e.target.value)}
                  className="px-2 py-1 border rounded text-sm bg-white"
                  style={{ borderColor: COLOR_BG_SOFT, color: COLOR_BRUN, minWidth: 160 }}
                >
                  <option value="">—</option>
                  {profils.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleChoisirProfil}
                  disabled={saving || !profilChoix}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded border disabled:opacity-40"
                  style={{ borderColor: COLOR_PRIMARY, color: COLOR_PRIMARY }}
                >
                  <Check className="w-4 h-4" /> Choisir ce profil
                </button>
              </div>
            )}
          </div>

          <p className="px-5 py-2 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.7 }}>
            {subtitle}
          </p>

          {/* Tableau */}
          <div className="flex-1 overflow-hidden flex flex-col px-5 pb-5">
            <div
              className="grid items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
              style={{
                gridTemplateColumns: template,
                color: COLOR_BRUN,
                backgroundColor: COLOR_BG_SOFT,
                borderColor: COLOR_BG_SOFT,
              }}
            >
              <div className="flex justify-center">
                <input
                  type="checkbox"
                  checked={rows.length > 0 && selected.size === rows.length}
                  onChange={() =>
                    setSelected(
                      selected.size === rows.length
                        ? new Set()
                        : new Set(rows.map((r) => r.id_type_droit_acces)),
                    )
                  }
                />
              </div>
              <div>ID</div>
              <div>Libellé</div>
              <div>Description</div>
              <div className="text-center">Code int.</div>
            </div>
            <div className="flex-1 overflow-y-auto border-l border-r border-b rounded-b" style={{ borderColor: COLOR_BG_SOFT }}>
              {loading && (
                <div className="p-3 flex items-center gap-2 text-xs" style={{ color: COLOR_BRUN }}>
                  <Loader2 className="w-4 h-4 animate-spin" /> Chargement…
                </div>
              )}
              {!loading && rows.length === 0 && (
                <div className="p-3 text-xs italic" style={{ color: COLOR_BRUN, opacity: 0.6 }}>
                  Aucun droit à proposer.
                </div>
              )}
              {groups.map((g) => (
                <div key={g.key}>
                  <div
                    className="px-3 py-1 text-xs font-bold"
                    style={{ backgroundColor: '#F7EEEB', color: COLOR_BRUN }}
                  >
                    {g.key}
                  </div>
                  {g.items.map((it) => {
                    const sel = selected.has(it.id_type_droit_acces)
                    return (
                      <div
                        key={it.id_type_droit_acces}
                        onClick={() => toggle(it.id_type_droit_acces)}
                        className="grid items-center gap-2 px-3 py-1.5 text-xs border-b cursor-pointer"
                        style={{
                          gridTemplateColumns: template,
                          backgroundColor: sel
                            ? COLOR_BG_SOFT
                            : it.deja_attribue
                              ? '#FBF9F8'
                              : 'white',
                          borderColor: COLOR_BG_SOFT,
                          color: COLOR_BRUN,
                        }}
                      >
                        <div className="flex justify-center">
                          <input
                            type="checkbox"
                            checked={sel}
                            onChange={() => toggle(it.id_type_droit_acces)}
                          />
                        </div>
                        <div className="font-mono">{it.id_type_droit_acces}</div>
                        <div className="truncate" title={it.lib_droit}>
                          {it.lib_droit}
                          {it.deja_attribue && (
                            <span className="ml-2 text-[10px] italic" style={{ opacity: 0.7 }}>
                              (déjà attribué{it.droit_actif ? ', actif' : ', inactif'})
                            </span>
                          )}
                        </div>
                        <div className="truncate" title={it.description}>
                          {it.description}
                        </div>
                        <div className="text-center font-mono">{it.code_interne}</div>
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
