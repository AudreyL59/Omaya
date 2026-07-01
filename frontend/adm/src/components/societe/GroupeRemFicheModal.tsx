/**
 * Fen_GroupeRemFiche - Nouveau / Editer un groupe de remuneration
 * pour un distributeur.
 *
 * Partie 1 (ce commit) : formulaire + combos filtrees + crea/edit.
 *   - Champs : LibGroupe, GroupeDoc (combo), Famille (combo, filtree
 *     selon Groupe Doc), Ss Fam (combo, filtree selon Famille),
 *     nbCol/nbLigne (uniquement a la creation), DateDeb/DateFin, IsActif.
 *   - Cascade WinDev : GroupeDoc -> Famille -> Ss Fam.
 *   - A la creation : cree groupe + nb_col x pgt_groupe_rem_x
 *     + nb_ligne x pgt_groupe_rem_y + (nb_col * nb_ligne) cellules Tab.
 *
 * Partie 2 (a venir) : grille NxM editable des montants +
 * boutons Ajouter colonne / Ajouter ligne + edition cellule
 * (Modifier, Supprimer, deplacer).
 */
import { useCallback, useEffect, useState } from 'react'
import { X, Save, Loader2, Layers } from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import GroupeRemGrille from './GroupeRemGrille'

const API_BASE = '/api/adm'

interface GroupeOpItem { id_groupe_operateur: number; lib_groupe: string }
interface PartenaireItem { id_partenaire: number; lib_partenaire: string }
interface GroupeRem {
  id_groupe_rem: string; id_distrib: string
  id_groupe_operateur: number; lib_groupe: string
  famille: number; ss_fam: string
  nb_col: number; nb_ligne: number
  date_deb: string; date_fin: string; is_actif: boolean
}

interface Props {
  idDistrib: string
  idGroupeRem: string | null    // null = Nouveau, sinon id existant
  onClose: () => void
  onSaved?: () => void
}

const EMPTY: GroupeRem = {
  id_groupe_rem: '0', id_distrib: '',
  id_groupe_operateur: 0, lib_groupe: '',
  famille: 0, ss_fam: '',
  nb_col: 0, nb_ligne: 0,
  date_deb: '', date_fin: '', is_actif: true,
}

export default function GroupeRemFicheModal({
  idDistrib, idGroupeRem, onClose, onSaved,
}: Props) {
  const isNew = idGroupeRem == null
  const [d, setD] = useState<GroupeRem>({ ...EMPTY, id_distrib: idDistrib })
  const [groupesOp, setGroupesOp] = useState<GroupeOpItem[]>([])
  const [familles, setFamilles] = useState<PartenaireItem[]>([])
  const [ssFams, setSsFams] = useState<string[]>([])
  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving] = useState(false)

  // Combo 'Groupe Doc' (chargee 1x)
  useEffect(() => {
    fetch(`${API_BASE}/distrib-courtage/combos/groupes-operateur`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then((g: GroupeOpItem[]) => setGroupesOp(Array.isArray(g) ? g : []))
  }, [])

  // Chargement du groupe existant (si edit)
  useEffect(() => {
    if (isNew) { setD({ ...EMPTY, id_distrib: idDistrib }); return }
    setLoading(true)
    fetch(`${API_BASE}/distrib-courtage/groupe-rem/${idGroupeRem}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(async r => {
        if (!r.ok) throw new Error(String(r.status))
        return r.json() as Promise<GroupeRem>
      })
      .then(setD)
      .catch(e => showToast(`Erreur : ${(e as Error).message}`, 'error'))
      .finally(() => setLoading(false))
  }, [idGroupeRem, isNew, idDistrib])

  // Combo Famille : filtree selon id_groupe_operateur
  const loadFamilles = useCallback((idOp: number) => {
    if (!idOp) { setFamilles([]); return }
    fetch(`${API_BASE}/distrib-courtage/combos/familles?id_groupe_operateur=${idOp}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then((f: PartenaireItem[]) => setFamilles(Array.isArray(f) ? f : []))
  }, [])
  useEffect(() => { loadFamilles(d.id_groupe_operateur) }, [d.id_groupe_operateur, loadFamilles])

  // Combo Ss Fam : filtree selon famille
  const loadSsFams = useCallback((idPart: number) => {
    if (!idPart) { setSsFams([]); return }
    fetch(`${API_BASE}/distrib-courtage/combos/ss-fam?famille=${idPart}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then((s: string[]) => setSsFams(Array.isArray(s) ? s : []))
  }, [])
  useEffect(() => { loadSsFams(d.famille) }, [d.famille, loadSsFams])

  const update = (patch: Partial<GroupeRem>) => setD(p => ({ ...p, ...patch }))

  const enregistrer = async () => {
    if (!d.lib_groupe.trim()) {
      showToast('Le libellé est obligatoire.', 'error'); return
    }
    setSaving(true)
    try {
      // id_distrib passe en query string (string) pour eviter la perte
      // de precision JS sur les bigint 17 chiffres. Le reste du payload
      // en JSON classique.
      const url = isNew
        ? `${API_BASE}/distrib-courtage/groupe-rem?id_distrib=${idDistrib}`
        : `${API_BASE}/distrib-courtage/groupe-rem/${idGroupeRem}?id_distrib=${idDistrib}`
      const method = isNew ? 'POST' : 'PUT'
      const payload = {
        id_distrib: 0,   // ignore backend, remplace par query
        id_groupe_operateur: d.id_groupe_operateur,
        lib_groupe: d.lib_groupe, famille: d.famille, ss_fam: d.ss_fam,
        nb_col: d.nb_col, nb_ligne: d.nb_ligne,
        date_deb: d.date_deb || null, date_fin: d.date_fin || null,
        is_actif: d.is_actif,
      }
      const r = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })
      if (!r.ok) throw new Error(String(r.status))
      showToast(isNew ? 'Groupe créé' : 'Groupe enregistré', 'success')
      onSaved?.()
      onClose()
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-[70] flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-[900px] max-w-full max-h-[95vh] flex flex-col"
           onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-c-line">
          <h2 className="text-sm font-bold flex items-center gap-2">
            <Layers className="w-4 h-4 text-c-brand" />
            {isNew ? 'Nouveau Groupe REM' : 'Éditer le groupe REM'}
          </h2>
          <button onClick={onClose}
            className="p-1 hover:bg-c-surface-soft rounded text-c-ink-faint">
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-c-brand" />
          </div>
        ) : (
          <div className="flex-1 overflow-auto p-4">
            <div className="grid grid-cols-4 gap-3 text-xs">
              {/* Ligne 1 : LibGroupe (col 4) */}
              <Field label="Lib Groupe *" cols={4}>
                <Input value={d.lib_groupe}
                  onChange={v => update({ lib_groupe: v })}
                  placeholder="Nom du groupe de rémunération" />
              </Field>
              {/* Ligne 2 : Groupe Doc */}
              <Field label="Groupe Doc" cols={2}>
                <select value={d.id_groupe_operateur}
                  onChange={e => update({
                    id_groupe_operateur: parseInt(e.target.value, 10) || 0,
                    famille: 0, ss_fam: '',
                  })}
                  className="w-full px-2 py-1 border border-c-line rounded text-xs h-7">
                  <option value={0}>—</option>
                  {groupesOp.map(g => (
                    <option key={g.id_groupe_operateur} value={g.id_groupe_operateur}>
                      {g.lib_groupe}
                    </option>
                  ))}
                </select>
              </Field>
              {/* Ligne 2 suite : Famille */}
              <Field label="Famille" cols={1}>
                <select value={d.famille}
                  onChange={e => update({
                    famille: parseInt(e.target.value, 10) || 0,
                    ss_fam: '',
                  })}
                  disabled={!d.id_groupe_operateur}
                  className="w-full px-2 py-1 border border-c-line rounded text-xs h-7 disabled:opacity-50">
                  <option value={0}>—</option>
                  {familles.map(f => (
                    <option key={f.id_partenaire} value={f.id_partenaire}>
                      {f.lib_partenaire}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Ss Fam" cols={1}>
                <select value={d.ss_fam}
                  onChange={e => update({ ss_fam: e.target.value })}
                  disabled={!d.famille}
                  className="w-full px-2 py-1 border border-c-line rounded text-xs h-7 disabled:opacity-50">
                  <option value="">—</option>
                  {ssFams.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </Field>
              {/* Ligne 3 : nbCol / nbLigne (uniquement en creation) */}
              {isNew && (
                <>
                  <Field label="nb Colonnes">
                    <input type="number" min={0} value={d.nb_col || ''}
                      onChange={e => update({ nb_col: parseInt(e.target.value, 10) || 0 })}
                      className="w-full px-2 py-1 border border-c-line rounded text-xs h-7 text-right tabular-nums" />
                  </Field>
                  <Field label="nb Lignes">
                    <input type="number" min={0} value={d.nb_ligne || ''}
                      onChange={e => update({ nb_ligne: parseInt(e.target.value, 10) || 0 })}
                      className="w-full px-2 py-1 border border-c-line rounded text-xs h-7 text-right tabular-nums" />
                  </Field>
                  <div className="col-span-2 text-[10px] text-c-ink-faint italic self-end">
                    La grille sera créée à l'enregistrement. Les cellules pourront être éditées ensuite.
                  </div>
                </>
              )}
              {/* Ligne 4 : Du / Au / Actif */}
              <Field label="Du">
                <input type="date" value={d.date_deb ? d.date_deb.slice(0, 10) : ''}
                  onChange={e => update({ date_deb: e.target.value })}
                  className="w-full px-2 py-1 border border-c-line rounded text-xs h-7" />
              </Field>
              <Field label="Au">
                <input type="date" value={d.date_fin ? d.date_fin.slice(0, 10) : ''}
                  onChange={e => update({ date_fin: e.target.value })}
                  className="w-full px-2 py-1 border border-c-line rounded text-xs h-7" />
              </Field>
              <div className="col-span-2 flex items-center gap-2 self-end pb-1">
                <input type="checkbox" checked={d.is_actif}
                  onChange={e => update({ is_actif: e.target.checked })}
                  id="is_actif" />
                <label htmlFor="is_actif">Actif</label>
              </div>
            </div>

            {!isNew && idGroupeRem && (
              <div className="mt-4">
                <GroupeRemGrille idGroupeRem={idGroupeRem} />
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end gap-2 px-4 py-3 border-t border-c-line">
          <button type="button" onClick={onClose}
            className="px-3 py-1.5 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
            Annuler
          </button>
          <button type="button" onClick={enregistrer} disabled={saving || loading}
            className="flex items-center gap-2 px-4 py-1.5 rounded bg-c-brand text-white text-xs font-medium hover:opacity-90 disabled:opacity-50">
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                     : <Save className="w-3.5 h-3.5" />}
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children, cols = 1 }: {
  label: string; children: React.ReactNode; cols?: number
}) {
  return (
    <div className={cols === 4 ? 'col-span-4' : cols === 3 ? 'col-span-3' : cols === 2 ? 'col-span-2' : ''}>
      <label className="text-[10px] text-c-ink-faint block">{label}</label>
      {children}
    </div>
  )
}

function Input({
  value, onChange, placeholder,
}: {
  value: string; onChange: (v: string) => void; placeholder?: string
}) {
  return (
    <input type="text" value={value ?? ''}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full px-2 py-1 border border-c-line rounded text-xs h-7" />
  )
}
