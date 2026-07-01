/**
 * Fen_DistribCttCourtage - Docs Dematerialises pour une societe.
 *
 * Modal ouvert depuis FicheSocieteModal (bouton Docs). Affiche pour
 * un distributeur (id_ste) :
 *   - Header : raison_sociale + nom du gerant
 *   - Tableau haut : Groupes de remuneration (regroupes par Famille)
 *   - Tableau bas : Editions de contrat de courtage
 *
 * Les boutons d'action (Nouveau Groupe, Editer, Dupliquer, Generer
 * le contrat / Nouveau edition, Supprimer, Voir edite, Voir signe...)
 * arriveront dans des commits suivants (le user enverra le code
 * WinDev de chaque bouton).
 */
import { useCallback, useEffect, useState } from 'react'
import {
  X, Loader2, FileText, Building2, Plus, Pencil, Copy, Play,
  Trash2, Eye, RefreshCw,
} from 'lucide-react'
import { getToken } from '@/api'
import { showToast } from '@shared/ui/dialog'
import GroupeRemFicheModal from './GroupeRemFicheModal'
import SocieteDistribPicker from './SocieteDistribPicker'
import GenerationContratModal from './GenerationContratModal'

const API_BASE = '/api/adm'

interface Infos {
  id_ste: string; raison_sociale: string
  id_gerant: number; gerant_display: string
}
interface GroupeRem {
  id_groupe_rem: string; famille: string; famille_id: number
  ss_fam: string; lib_groupe: string
  date_deb: string; date_fin: string; is_actif: boolean
}
interface EditionCtt {
  id_societe_doc_courtage: string; id_salarie: number
  nom_gerant: string; id_groupe_operateur: number
  col_secteur: string; date_edition: string
  recu: boolean; recu_date: string
}

interface Props {
  // string plutot que number : id_ste est un bigint WinDev (timestamp
  // 17 chiffres) qui depasse Number.MAX_SAFE_INTEGER (2^53). parseInt()
  // perd de la precision et charge la mauvaise fiche.
  idSte: string
  onClose: () => void
}

const shortDate = (iso: string): string =>
  !iso || iso.length < 10 ? '' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`

export default function DocsDematerModal({ idSte, onClose }: Props) {
  const [infos, setInfos] = useState<Infos | null>(null)
  const [groupes, setGroupes] = useState<GroupeRem[]>([])
  const [editions, setEditions] = useState<EditionCtt[]>([])
  const [selGroupe, setSelGroupe] = useState<string>('')
  const [selEdition, setSelEdition] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [ficheGroupe, setFicheGroupe] = useState<{ open: boolean; id: string | null }>({ open: false, id: null })
  const [showDistribPicker, setShowDistribPicker] = useState(false)
  const [showGenerate, setShowGenerate] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [i, g, e] = await Promise.all([
        fetch(`${API_BASE}/distrib-courtage/${idSte}/infos`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        }).then(r => r.ok ? r.json() : null),
        fetch(`${API_BASE}/distrib-courtage/${idSte}/groupes-rem`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        }).then(r => r.ok ? r.json() : []),
        fetch(`${API_BASE}/distrib-courtage/${idSte}/editions`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        }).then(r => r.ok ? r.json() : []),
      ])
      setInfos(i); setGroupes(g); setEditions(e)
    } catch (err) {
      showToast(`Erreur : ${(err as Error).message}`, 'error')
    } finally { setLoading(false) }
  }, [idSte])

  useEffect(() => { void load() }, [load])

  // Regroupe visuellement les groupes_rem par famille (comme le
  // tableau WinDev qui a un tri sur Famille et affiche des sections)
  const groupesByFam: Record<string, GroupeRem[]> = {}
  for (const g of groupes) {
    const key = g.famille || '(sans famille)'
    if (!groupesByFam[key]) groupesByFam[key] = []
    groupesByFam[key].push(g)
  }

  const notImpl = (label: string) => () => {
    showToast(`${label} : à venir (code WinDev à envoyer)`, 'info')
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-[60] flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-[1200px] max-w-full max-h-[95vh] flex flex-col"
           onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-c-line">
          <h2 className="text-sm font-bold flex items-center gap-2">
            <FileText className="w-4 h-4 text-c-brand" />
            Contrats de courtage
          </h2>
          <button onClick={onClose}
            className="p-1 hover:bg-c-surface-soft rounded text-c-ink-faint">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Bandeau infos distrib */}
        {infos && (
          <div className="flex items-center gap-4 px-4 py-2 border-b border-c-line-soft bg-c-surface-soft text-sm">
            <div className="flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-c-brand" />
              <span className="font-semibold">{infos.raison_sociale}</span>
            </div>
            {infos.gerant_display && (
              <div className="text-c-ink-soft text-xs">
                Gérant : <span className="text-c-ink">{infos.gerant_display}</span>
              </div>
            )}
          </div>
        )}

        {loading ? (
          <div className="flex-1 flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-c-brand" />
          </div>
        ) : (
          <div className="flex-1 overflow-auto p-4 space-y-4">
            {/* Partie haute : Groupes de rémunération */}
            <section className="border border-c-line rounded-lg overflow-hidden">
              <div className="flex items-center gap-2 px-3 py-2 border-b border-c-line-soft bg-c-surface-soft flex-wrap">
                <h3 className="text-xs font-bold text-c-ink-faint uppercase tracking-wide">
                  Groupes de rémunération
                </h3>
                <div className="flex-1" />
                <button type="button" onClick={() => setFicheGroupe({ open: true, id: null })}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded text-c-brand hover:bg-c-brand/10 text-xs">
                  <Plus className="w-3.5 h-3.5" /> Nouveau Groupe
                </button>
                <button type="button"
                  onClick={() => selGroupe && setFicheGroupe({ open: true, id: selGroupe })}
                  disabled={!selGroupe}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded text-c-brand hover:bg-c-brand/10 disabled:opacity-30 text-xs">
                  <Pencil className="w-3.5 h-3.5" /> Éditer le groupe
                </button>
                <button type="button"
                  onClick={() => selGroupe && setShowDistribPicker(true)}
                  disabled={!selGroupe}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded text-c-brand hover:bg-c-brand/10 disabled:opacity-30 text-xs">
                  <Copy className="w-3.5 h-3.5" /> Dupliquer pour un autre distrib
                </button>
                <button type="button" onClick={() => setShowGenerate(true)}
                  disabled={!infos}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-c-brand text-white hover:opacity-90 disabled:opacity-30 text-xs">
                  <Play className="w-3.5 h-3.5" /> Générer le contrat
                </button>
              </div>
              <div className="max-h-[280px] overflow-auto">
                <table className="w-full text-xs">
                  <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0 z-10">
                    <tr>
                      <th className="px-2 py-2 text-left w-24">Ss Fam</th>
                      <th className="px-2 py-2 text-left">Groupe de REM</th>
                      <th className="px-2 py-2 text-left w-28">Date Deb</th>
                      <th className="px-2 py-2 text-left w-28">Date Fin</th>
                      <th className="px-2 py-2 text-center w-20">Actif</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.keys(groupesByFam).length === 0 ? (
                      <tr><td colSpan={5} className="text-center py-8 text-c-ink-faint-2 italic">
                        Aucun groupe de rémunération.
                      </td></tr>
                    ) : Object.entries(groupesByFam).map(([fam, list]) => (
                      <>
                        <tr key={`h-${fam}`} className="bg-c-brand/5 border-t border-c-line-soft">
                          <td colSpan={5} className="px-3 py-1 text-xs font-bold text-c-brand">
                            — {fam} —
                          </td>
                        </tr>
                        {list.map(g => (
                          <tr key={g.id_groupe_rem}
                            onClick={() => setSelGroupe(g.id_groupe_rem)}
                            onDoubleClick={() => setFicheGroupe({ open: true, id: g.id_groupe_rem })}
                            className={`cursor-pointer border-t border-c-line-soft ${
                              selGroupe === g.id_groupe_rem
                                ? 'bg-c-brand/10' : 'hover:bg-c-surface-soft'
                            }`}>
                            <td className="px-2 py-1.5">{g.ss_fam}</td>
                            <td className="px-2 py-1.5">{g.lib_groupe}</td>
                            <td className="px-2 py-1.5">{shortDate(g.date_deb)}</td>
                            <td className="px-2 py-1.5">{shortDate(g.date_fin)}</td>
                            <td className="px-2 py-1.5 text-center">{g.is_actif ? '✓' : ''}</td>
                          </tr>
                        ))}
                      </>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Partie basse : Éditions de contrat */}
            <section className="border border-c-line rounded-lg overflow-hidden">
              <div className="flex items-center gap-2 px-3 py-2 border-b border-c-line-soft bg-c-surface-soft flex-wrap">
                <h3 className="text-xs font-bold text-c-ink-faint uppercase tracking-wide">
                  Contrats édités
                </h3>
                <div className="flex-1" />
                <button type="button" onClick={notImpl('Nouveau édition')}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded text-c-brand hover:bg-c-brand/10 text-xs">
                  <Plus className="w-3.5 h-3.5" /> Nouveau
                </button>
                <button type="button" onClick={notImpl('Supprimer édition')} disabled={!selEdition}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded text-red-600 hover:bg-red-50 disabled:opacity-30 text-xs">
                  <Trash2 className="w-3.5 h-3.5" /> Supprimer
                </button>
                <button type="button" onClick={notImpl('Voir le ctt édité')} disabled={!selEdition}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded text-c-brand hover:bg-c-brand/10 disabled:opacity-30 text-xs">
                  <Eye className="w-3.5 h-3.5" /> Voir le ctt édité
                </button>
                <button type="button" onClick={notImpl('Voir le ctt signé')} disabled={!selEdition}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded text-c-brand hover:bg-c-brand/10 disabled:opacity-30 text-xs">
                  <Eye className="w-3.5 h-3.5" /> Voir le ctt signé
                </button>
                <button type="button" onClick={() => void load()}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded text-c-ink-soft hover:bg-c-surface-soft text-xs">
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="max-h-[280px] overflow-auto">
                <table className="w-full text-xs">
                  <thead className="bg-c-surface-soft text-c-ink-faint uppercase tracking-wide sticky top-0 z-10">
                    <tr>
                      <th className="px-2 py-2 text-left w-32">Opérateur</th>
                      <th className="px-2 py-2 text-left">Gérant</th>
                      <th className="px-2 py-2 text-left">Secteur</th>
                      <th className="px-2 py-2 text-left w-28">Édité le</th>
                      <th className="px-2 py-2 text-center w-16">Signé</th>
                      <th className="px-2 py-2 text-left w-28">Le</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-c-line-soft">
                    {editions.length === 0 ? (
                      <tr><td colSpan={6} className="text-center py-8 text-c-ink-faint-2 italic">
                        Aucun contrat édité.
                      </td></tr>
                    ) : editions.map(e => (
                      <tr key={e.id_societe_doc_courtage}
                        onClick={() => setSelEdition(e.id_societe_doc_courtage)}
                        className={`cursor-pointer ${
                          selEdition === e.id_societe_doc_courtage
                            ? 'bg-c-brand/10' : 'hover:bg-c-surface-soft'
                        }`}>
                        <td className="px-2 py-1.5 tabular-nums">{e.id_groupe_operateur || ''}</td>
                        <td className="px-2 py-1.5">{e.nom_gerant}</td>
                        <td className="px-2 py-1.5">{e.col_secteur}</td>
                        <td className="px-2 py-1.5">{shortDate(e.date_edition)}</td>
                        <td className="px-2 py-1.5 text-center">{e.recu ? '✓' : ''}</td>
                        <td className="px-2 py-1.5">{shortDate(e.recu_date)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}
      </div>

      {ficheGroupe.open && (
        <GroupeRemFicheModal
          idDistrib={idSte}
          idGroupeRem={ficheGroupe.id}
          onClose={() => setFicheGroupe({ open: false, id: null })}
          onSaved={() => { void load() }} />
      )}
      {showGenerate && infos && (
        <GenerationContratModal
          idDistrib={idSte}
          idGerant={infos.id_gerant}
          onClose={() => setShowGenerate(false)} />
      )}
      {showDistribPicker && selGroupe && (
        <SocieteDistribPicker
          excludeIdSte={idSte}
          onClose={() => setShowDistribPicker(false)}
          onSelect={async (idTargetSte, label) => {
            setShowDistribPicker(false)
            try {
              const r = await fetch(
                `${API_BASE}/distrib-courtage/groupe-rem/${selGroupe}/duplicate-to?id_target_distrib=${idTargetSte}`,
                {
                  method: 'POST',
                  headers: { Authorization: `Bearer ${getToken()}` },
                },
              )
              if (!r.ok) throw new Error(String(r.status))
              showToast(`Groupe dupliqué vers ${label}`, 'success')
            } catch (e) {
              showToast(`Erreur : ${(e as Error).message}`, 'error')
            }
          }} />
      )}
    </div>
  )
}
