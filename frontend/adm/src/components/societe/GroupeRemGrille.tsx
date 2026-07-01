/**
 * Grille NxM editable des montants pour un groupe REM.
 * Partie 2 (grille + Ajouter col/ligne) + Partie 3 (edit cellule +
 * dialogue Modifier/Supprimer/Deplacer col+ligne).
 *
 * Cf FI_GroupeREM WinDev :
 *   - En-tete colonnes (X) : bouton Bouton4 avec le libelle,
 *     clic ouvre dialogue 'Gestion de la colonne'.
 *   - En-tete lignes (Y) : premiere colonne, clic ouvre dialogue
 *     'Gestion de la ligne'.
 *   - Cellules : montant, clic ouvre saisie numerique.
 */
import { useCallback, useEffect, useState } from 'react'
import { Plus, Loader2, Pencil, Trash2, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, X, Save } from 'lucide-react'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'

const API_BASE = '/api/adm'

interface XItem { id_groupe_rem_x: string; lib: string; code_interne: string; ordre: number }
interface YItem { id_groupe_rem_y: string; lib: string; code_interne: string; ordre: number }
interface Cellule { id_groupe_rem_tab: string; id_groupe_rem_x: string; id_groupe_rem_y: string; montant: number }
interface Grille {
  id_groupe_rem: string
  colonnes: XItem[]; lignes: YItem[]; cellules: Cellule[]
}

interface Props {
  idGroupeRem: string
  reloadTrigger?: number   // incrementer pour forcer reload
}

export default function GroupeRemGrille({ idGroupeRem, reloadTrigger }: Props) {
  const [grille, setGrille] = useState<Grille | null>(null)
  const [loading, setLoading] = useState(true)

  // Actions overlays
  const [editX, setEditX] = useState<XItem | null>(null)
  const [editY, setEditY] = useState<YItem | null>(null)
  const [gestionX, setGestionX] = useState<XItem | null>(null)
  const [gestionY, setGestionY] = useState<YItem | null>(null)
  const [editCell, setEditCell] = useState<{ x: XItem; y: YItem; cellule: Cellule | null } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(
        `${API_BASE}/distrib-courtage/groupe-rem/${idGroupeRem}/grille`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      )
      if (!r.ok) throw new Error(String(r.status))
      setGrille(await r.json())
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [idGroupeRem])

  useEffect(() => { void load() }, [load, reloadTrigger])

  const doPost = async (url: string) => {
    const r = await fetch(url, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!r.ok) throw new Error(String(r.status))
  }
  const doDelete = async (url: string) => {
    const r = await fetch(url, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!r.ok) throw new Error(String(r.status))
  }

  const addColonne = async () => {
    try {
      await doPost(`${API_BASE}/distrib-courtage/groupe-rem/${idGroupeRem}/colonne`)
      await load()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }
  const addLigne = async () => {
    try {
      await doPost(`${API_BASE}/distrib-courtage/groupe-rem/${idGroupeRem}/ligne`)
      await load()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }

  const suppXCol = async (id_x: string) => {
    const ok = await showConfirm({
      title: 'Supprimer cette colonne',
      message: 'Voulez-vous vraiment supprimer cette colonne ?',
    })
    if (!ok) return
    try {
      await doDelete(`${API_BASE}/distrib-courtage/groupe-rem-x/${id_x}?id_groupe_rem=${idGroupeRem}`)
      await load()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }
  const suppYLigne = async (id_y: string) => {
    const ok = await showConfirm({
      title: 'Supprimer cette ligne',
      message: 'Voulez-vous vraiment supprimer cette ligne ?',
    })
    if (!ok) return
    try {
      await doDelete(`${API_BASE}/distrib-courtage/groupe-rem-y/${id_y}?id_groupe_rem=${idGroupeRem}`)
      await load()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }
  const moveX = async (id_x: string, direction: 'left' | 'right') => {
    try {
      await doPost(`${API_BASE}/distrib-courtage/groupe-rem-x/${id_x}/move?id_groupe_rem=${idGroupeRem}&direction=${direction}`)
      await load()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }
  const moveY = async (id_y: string, direction: 'up' | 'down') => {
    try {
      await doPost(`${API_BASE}/distrib-courtage/groupe-rem-y/${id_y}/move?id_groupe_rem=${idGroupeRem}&direction=${direction}`)
      await load()
    } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
  }

  const cellMap = new Map<string, Cellule>()
  if (grille) {
    for (const c of grille.cellules) {
      cellMap.set(`${c.id_groupe_rem_x}|${c.id_groupe_rem_y}`, c)
    }
  }

  return (
    <div className="border border-c-line rounded-lg overflow-hidden">
      <div className="px-3 py-2 border-b border-c-line-soft bg-c-surface-soft flex items-center gap-2">
        <h3 className="text-xs font-bold text-c-ink-faint uppercase tracking-wide flex-1">
          Grille de rémunération
        </h3>
        <button type="button" onClick={addColonne}
          className="flex items-center gap-1 px-2 py-0.5 rounded text-c-brand hover:bg-c-brand/10 text-xs">
          <Plus className="w-3.5 h-3.5" /> Colonne
        </button>
        <button type="button" onClick={addLigne}
          className="flex items-center gap-1 px-2 py-0.5 rounded text-c-brand hover:bg-c-brand/10 text-xs">
          <Plus className="w-3.5 h-3.5" /> Ligne
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-c-brand" />
        </div>
      ) : !grille || (grille.colonnes.length === 0 && grille.lignes.length === 0) ? (
        <div className="text-center py-8 text-c-ink-faint-2 italic text-xs">
          Aucune colonne ni ligne. Cliquez sur + Colonne ou + Ligne pour en ajouter.
        </div>
      ) : (
        <div className="overflow-auto max-h-[400px]">
          <table className="w-full text-xs">
            <thead>
              <tr>
                <th className="bg-[#17494E] text-white px-2 py-1 text-left w-40 sticky left-0 z-10"></th>
                {grille.colonnes.map(x => (
                  <th key={x.id_groupe_rem_x}
                    className="bg-[#17494E] text-white px-2 py-1 text-center min-w-[120px] cursor-pointer hover:bg-[#0F353A]"
                    onClick={() => setGestionX(x)}
                    title="Clic : Gérer la colonne">
                    {x.lib}
                    {x.code_interne && (
                      <div className="text-[9px] font-normal opacity-70">{x.code_interne}</div>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {grille.lignes.length === 0 ? (
                <tr>
                  <td colSpan={grille.colonnes.length + 1}
                    className="text-center py-6 text-c-ink-faint-2 italic">
                    Aucune ligne. Ajouter une ligne pour créer les cellules.
                  </td>
                </tr>
              ) : grille.lignes.map(y => (
                <tr key={y.id_groupe_rem_y} className="hover:bg-c-surface-soft">
                  <td className="bg-[#17494E] text-white px-2 py-1 sticky left-0 z-10 cursor-pointer hover:bg-[#0F353A]"
                    onClick={() => setGestionY(y)}
                    title="Clic : Gérer la ligne">
                    <div>{y.lib}</div>
                    {y.code_interne && (
                      <div className="text-[9px] opacity-70">{y.code_interne}</div>
                    )}
                  </td>
                  {grille.colonnes.map(x => {
                    const c = cellMap.get(`${x.id_groupe_rem_x}|${y.id_groupe_rem_y}`) ?? null
                    return (
                      <td key={x.id_groupe_rem_x}
                        onClick={() => setEditCell({ x, y, cellule: c })}
                        className="px-2 py-1 text-right tabular-nums cursor-pointer border border-c-line-soft hover:bg-c-brand/5">
                        {c ? c.montant.toFixed(2).replace('.', ',') : '—'}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Dialogues et editeurs */}
      {gestionX && (
        <GestionAxeDialog
          type="colonne"
          item={{ lib: gestionX.lib }}
          onClose={() => setGestionX(null)}
          onModifier={() => { setEditX(gestionX); setGestionX(null) }}
          onSupprimer={async () => { await suppXCol(gestionX.id_groupe_rem_x); setGestionX(null) }}
          onLeft={async () => { await moveX(gestionX.id_groupe_rem_x, 'left'); setGestionX(null) }}
          onRight={async () => { await moveX(gestionX.id_groupe_rem_x, 'right'); setGestionX(null) }}
        />
      )}
      {gestionY && (
        <GestionAxeDialog
          type="ligne"
          item={{ lib: gestionY.lib }}
          onClose={() => setGestionY(null)}
          onModifier={() => { setEditY(gestionY); setGestionY(null) }}
          onSupprimer={async () => { await suppYLigne(gestionY.id_groupe_rem_y); setGestionY(null) }}
          onLeft={async () => { await moveY(gestionY.id_groupe_rem_y, 'up'); setGestionY(null) }}
          onRight={async () => { await moveY(gestionY.id_groupe_rem_y, 'down'); setGestionY(null) }}
        />
      )}
      {editX && (
        <EditAxeModal
          type="colonne"
          initLib={editX.lib} initCode={editX.code_interne}
          onClose={() => setEditX(null)}
          onSave={async (lib, code) => {
            try {
              const r = await fetch(`${API_BASE}/distrib-courtage/groupe-rem-x/${editX.id_groupe_rem_x}`, {
                method: 'PUT',
                headers: {
                  Authorization: `Bearer ${getToken()}`,
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({ lib, code_interne: code }),
              })
              if (!r.ok) throw new Error(String(r.status))
              setEditX(null)
              await load()
            } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
          }}
        />
      )}
      {editY && (
        <EditAxeModal
          type="ligne"
          initLib={editY.lib} initCode={editY.code_interne}
          onClose={() => setEditY(null)}
          onSave={async (lib, code) => {
            try {
              const r = await fetch(`${API_BASE}/distrib-courtage/groupe-rem-y/${editY.id_groupe_rem_y}`, {
                method: 'PUT',
                headers: {
                  Authorization: `Bearer ${getToken()}`,
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({ lib, code_interne: code }),
              })
              if (!r.ok) throw new Error(String(r.status))
              setEditY(null)
              await load()
            } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
          }}
        />
      )}
      {editCell && (
        <EditCelluleModal
          x={editCell.x} y={editCell.y}
          initMontant={editCell.cellule?.montant ?? 0}
          onClose={() => setEditCell(null)}
          onSave={async (montant) => {
            try {
              const r = await fetch(
                `${API_BASE}/distrib-courtage/groupe-rem-tab/${editCell.x.id_groupe_rem_x}/${editCell.y.id_groupe_rem_y}`,
                {
                  method: 'PUT',
                  headers: {
                    Authorization: `Bearer ${getToken()}`,
                    'Content-Type': 'application/json',
                  },
                  body: JSON.stringify({ montant }),
                },
              )
              if (!r.ok) throw new Error(String(r.status))
              setEditCell(null)
              await load()
            } catch (e) { showToast(`Erreur : ${(e as Error).message}`, 'error') }
          }}
        />
      )}
    </div>
  )
}

// -- Dialogue Gestion d'un axe (colonne ou ligne) ------------------

function GestionAxeDialog({
  type, item, onClose, onModifier, onSupprimer, onLeft, onRight,
}: {
  type: 'colonne' | 'ligne'
  item: { lib: string }
  onClose: () => void
  onModifier: () => void
  onSupprimer: () => void
  onLeft: () => void
  onRight: () => void
}) {
  const label = type === 'colonne' ? 'colonne' : 'ligne'
  return (
    <div className="fixed inset-0 bg-black/40 z-[80] flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-[400px] max-w-full"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-c-line">
          <h3 className="text-sm font-bold">
            Gestion de la {label} : « {item.lib} »
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-c-surface-soft rounded">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-3 text-xs text-c-ink-soft">
          Quelle opération souhaitez-vous faire ?
        </div>
        <div className="grid grid-cols-2 gap-2 px-3 pb-3">
          <button type="button" onClick={onModifier}
            className="flex items-center gap-2 px-3 py-2 rounded border border-c-line hover:bg-c-brand/10 text-xs">
            <Pencil className="w-3.5 h-3.5 text-c-brand" /> Modifier
          </button>
          <button type="button" onClick={onSupprimer}
            className="flex items-center gap-2 px-3 py-2 rounded border border-c-line hover:bg-red-50 text-xs text-red-600">
            <Trash2 className="w-3.5 h-3.5" /> Supprimer
          </button>
          <button type="button" onClick={onLeft}
            className="flex items-center gap-2 px-3 py-2 rounded border border-c-line hover:bg-c-brand/10 text-xs">
            {type === 'colonne'
              ? <><ArrowLeft className="w-3.5 h-3.5" /> Déplacer à gauche</>
              : <><ArrowUp className="w-3.5 h-3.5" /> Déplacer vers le haut</>}
          </button>
          <button type="button" onClick={onRight}
            className="flex items-center gap-2 px-3 py-2 rounded border border-c-line hover:bg-c-brand/10 text-xs">
            {type === 'colonne'
              ? <><ArrowRight className="w-3.5 h-3.5" /> Déplacer à droite</>
              : <><ArrowDown className="w-3.5 h-3.5" /> Déplacer vers le bas</>}
          </button>
        </div>
      </div>
    </div>
  )
}

// -- Editeur Colonne/Ligne (lib + code_interne) -------------------

function EditAxeModal({
  type, initLib, initCode, onClose, onSave,
}: {
  type: 'colonne' | 'ligne'
  initLib: string; initCode: string
  onClose: () => void
  onSave: (lib: string, code: string) => void
}) {
  const [lib, setLib] = useState(initLib)
  const [code, setCode] = useState(initCode)
  return (
    <div className="fixed inset-0 bg-black/40 z-[80] flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-[450px] max-w-full"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-c-line">
          <h3 className="text-sm font-bold">
            Éditer la {type === 'colonne' ? 'colonne' : 'ligne'}
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-c-surface-soft rounded">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-4 space-y-3 text-xs">
          <div>
            <label className="text-[10px] text-c-ink-faint block">Libellé</label>
            <input type="text" value={lib} onChange={e => setLib(e.target.value)}
              className="w-full px-2 py-1 border border-c-line rounded text-xs h-7" />
          </div>
          <div>
            <label className="text-[10px] text-c-ink-faint block">Code interne (optionnel)</label>
            <input type="text" value={code} onChange={e => setCode(e.target.value)}
              className="w-full px-2 py-1 border border-c-line rounded text-xs h-7" />
          </div>
        </div>
        <div className="flex justify-end gap-2 px-4 py-3 border-t border-c-line">
          <button type="button" onClick={onClose}
            className="px-3 py-1.5 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
            Annuler
          </button>
          <button type="button" onClick={() => onSave(lib, code)}
            className="flex items-center gap-2 px-4 py-1.5 rounded bg-c-brand text-white text-xs font-medium hover:opacity-90">
            <Save className="w-3.5 h-3.5" /> Enregistrer
          </button>
        </div>
      </div>
    </div>
  )
}

// -- Editeur d'une cellule (montant) -----------------------------

function EditCelluleModal({
  x, y, initMontant, onClose, onSave,
}: {
  x: XItem; y: YItem; initMontant: number
  onClose: () => void
  onSave: (montant: number) => void
}) {
  const [montant, setMontant] = useState(initMontant)
  return (
    <div className="fixed inset-0 bg-black/40 z-[80] flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-[400px] max-w-full"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-c-line">
          <h3 className="text-sm font-bold">Saisir le montant</h3>
          <button onClick={onClose} className="p-1 hover:bg-c-surface-soft rounded">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-4 space-y-3 text-xs">
          <div className="text-c-ink-soft">
            <div><b>Colonne :</b> {x.lib}</div>
            <div><b>Ligne :</b> {y.lib}</div>
          </div>
          <div>
            <label className="text-[10px] text-c-ink-faint block">Montant</label>
            <input type="number" step="0.01" value={montant || ''}
              autoFocus
              onChange={e => setMontant(parseFloat(e.target.value) || 0)}
              className="w-full px-2 py-1 border border-c-line rounded text-xs h-7 text-right tabular-nums" />
          </div>
        </div>
        <div className="flex justify-end gap-2 px-4 py-3 border-t border-c-line">
          <button type="button" onClick={onClose}
            className="px-3 py-1.5 rounded border border-c-line text-xs text-c-ink-soft hover:bg-c-surface-soft">
            Annuler
          </button>
          <button type="button" onClick={() => onSave(montant)}
            className="flex items-center gap-2 px-4 py-1.5 rounded bg-c-brand text-white text-xs font-medium hover:opacity-90">
            <Save className="w-3.5 h-3.5" /> Valider
          </button>
        </div>
      </div>
    </div>
  )
}
