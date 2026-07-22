// Page principale du module Process (bibliothèque de procédures/tutos).
// Partagée entre Vendeur (canEdit=false) et ADM (canEdit=true).
//
// Layout 2 colonnes :
// - gauche : liste + recherche mots-clés + bouton "Nouveau" (ADM)
// - droite : détail du process sélectionné (titre + service + mots-clés,
//            liste des PJ, gestion des droits d'accès)

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Download, FileText, Lock, Network, Pencil, Plus, Save, Search,
  ShieldCheck, Tag, Trash2, Upload, X,
} from 'lucide-react'

import { showConfirm, showToast } from '../ui/dialog'
import {
  deleteDiagramme, deleteDroit, deleteFichier, deleteProcess, fetchList,
  fetchOne, fetchProfils, fetchServices, fetchSocietes, fichierUrl,
  saveDroit, saveProcess, uploadFichier,
} from './api'
import DiagrammeEditor from './DiagrammeEditor'
import SalarieAutocomplete from './SalarieAutocomplete'
import type {
  Process, ProcessDroit, ProcessFichierMeta,
  ProcessListItem, ProcessPageProps, ProfilItem, SocieteItem,
} from './types'

const fmtSize = (n: number): string => {
  if (!n) return ''
  if (n < 1024) return `${n} o`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} Ko`
  return `${(n / (1024 * 1024)).toFixed(1)} Mo`
}

const fmtDateFR = (raw: string): string => {
  if (!raw) return ''
  const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})/)
  return m ? `${m[3]}/${m[2]}/${m[1]}` : raw
}

// Ligne meta compacte : "Créé par X le date · Modifié par Y le date".
// Si le modificateur est identique au createur, on omet 'par Y'.
// Si la date de modif = date de crea (ou vide), on omet toute la 2e partie.
const metaLine = (meta: {
  DateCrea?: string; DerniereModif?: string
  NomOpeCrea?: string; NomOpeModif?: string
}): string => {
  const parts: string[] = []
  if (meta.NomOpeCrea || meta.DateCrea) {
    let s = 'Créé'
    if (meta.NomOpeCrea) s += ` par ${meta.NomOpeCrea}`
    if (meta.DateCrea) s += ` le ${fmtDateFR(meta.DateCrea)}`
    parts.push(s)
  }
  const hasModif = meta.DerniereModif
    && meta.DerniereModif.slice(0, 10) !== (meta.DateCrea || '').slice(0, 10)
  if (hasModif) {
    let s = 'Modifié'
    if (meta.NomOpeModif && meta.NomOpeModif !== meta.NomOpeCrea) {
      s += ` par ${meta.NomOpeModif}`
    }
    s += ` le ${fmtDateFR(meta.DerniereModif!)}`
    parts.push(s)
  }
  return parts.join(' · ')
}

// Format storage : mots séparés par RC (\n) — convention WinDev. Tolérance
// en parsing pour virgule et point-virgule (saisie legacy). Dedupe case
// insensitive, ordre préservé.
const parseMotsCles = (raw: string): string[] => {
  if (!raw) return []
  const seen = new Set<string>()
  const out: string[] = []
  for (const t of raw.split(/[\n,;]+/)) {
    const s = t.trim()
    if (!s) continue
    const k = s.toLowerCase()
    if (seen.has(k)) continue
    seen.add(k); out.push(s)
  }
  return out
}
const joinMotsCles = (tags: string[]): string => tags.join('\n')

// ---------------------------------------------------------------------------

export default function ProcessPage(props: ProcessPageProps) {
  const { apiBase, getToken, canEdit } = props
  const ctx = useMemo(() => ({ apiBase, getToken }), [apiBase, getToken])

  const [list, setList] = useState<ProcessListItem[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Process | null>(null)
  const [selectedId, setSelectedId] = useState<string>('')
  const [editing, setEditing] = useState(false)
  const [showDroits, setShowDroits] = useState(false)
  // Diagramme ouvert : null = fermé, {id:'0', titre:'...'} = nouveau,
  // sinon meta existante.
  const [diagOpen, setDiagOpen] = useState<null | {
    id: string; titre: string
  }>(null)

  // Form fields
  const [titre, setTitre] = useState('')
  const [service, setService] = useState('')
  const [motsCles, setMotsCles] = useState('')
  const [services, setServices] = useState<string[]>([])

  const chargerListe = useCallback(async () => {
    setLoading(true)
    const r = await fetchList(ctx, search)
    setList(Array.isArray(r) ? r : [])
    setLoading(false)
  }, [ctx, search])

  useEffect(() => {
    // Debounce recherche 250 ms
    const iv = setTimeout(() => { void chargerListe() }, 250)
    return () => clearTimeout(iv)
  }, [chargerListe])

  useEffect(() => {
    void fetchServices(ctx).then(r => { if (Array.isArray(r)) setServices(r) })
  }, [ctx])

  const ouvrir = async (item: ProcessListItem) => {
    setSelectedId(item.IDProcess)
    setEditing(false)
    const p = await fetchOne(ctx, item.IDProcess)
    if (p) {
      setSelected(p)
      setTitre(p.Titre); setService(p.Service); setMotsCles(p.MotsCles)
    }
  }

  const nouveau = () => {
    setSelected(null); setSelectedId('')
    setTitre(''); setService(''); setMotsCles('')
    setEditing(true)
  }

  const sauvegarder = async () => {
    if (!titre.trim()) {
      showToast('Titre obligatoire', 'error'); return
    }
    const r = await saveProcess(ctx, {
      IDProcess: selected?.IDProcess || '0',
      Titre: titre.trim(),
      Service: service.trim().toUpperCase(),
      MotsCles: motsCles.trim(),
    })
    if (!r?.IDProcess) { showToast('Échec sauvegarde', 'error'); return }
    showToast('Enregistré', 'success')
    await chargerListe()
    // Recharger le detail
    const p = await fetchOne(ctx, r.IDProcess)
    if (p) { setSelected(p); setSelectedId(p.IDProcess) }
    setEditing(false)
  }

  const supprimer = async () => {
    if (!selected) return
    const ok = await showConfirm({
      title: 'Supprimer ce process ?',
      message: `« ${selected.Titre} »\nCette action est irréversible.`,
      confirmLabel: 'Supprimer', variant: 'danger',
    })
    if (!ok) return
    const r = await deleteProcess(ctx, selected.IDProcess)
    if (!r?.ok) { showToast('Échec', 'error'); return }
    setSelected(null); setSelectedId(''); setEditing(false)
    await chargerListe()
    showToast('Supprimé', 'success')
  }

  const uploadPJ = async (file: File) => {
    if (!selected) return
    const r = await uploadFichier(ctx, selected.IDProcess, file)
    if (!r?.IDProcessFichier) { showToast('Échec upload', 'error'); return }
    const p = await fetchOne(ctx, selected.IDProcess)
    if (p) setSelected(p)
    await chargerListe()
  }

  const supprimerPJ = async (f: ProcessFichierMeta) => {
    const ok = await showConfirm({
      title: 'Supprimer ce fichier ?',
      message: `« ${f.Titre}${f.Extension} »`,
      confirmLabel: 'Supprimer', variant: 'danger',
    })
    if (!ok) return
    const r = await deleteFichier(ctx, f.IDProcessFichier)
    if (!r?.ok) { showToast('Échec', 'error'); return }
    if (selected) {
      const p = await fetchOne(ctx, selected.IDProcess); if (p) setSelected(p)
    }
    await chargerListe()
  }

  return (
    <div className="flex h-full min-h-0 gap-3 p-3">
      {/* Colonne gauche : liste */}
      <aside className="w-96 flex flex-col bg-white border border-c-line-soft rounded overflow-hidden">
        <div className="p-3 border-b border-c-line-soft space-y-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-2 top-2.5 text-c-ink-soft" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Rechercher mots-clés, titre…"
              className="w-full pl-8 pr-2 py-1.5 text-sm border border-c-line rounded bg-white" />
          </div>
          {canEdit && (
            <button onClick={nouveau}
              className="w-full flex items-center justify-center gap-1 px-3 py-2 rounded bg-gray-900 text-white text-sm font-semibold hover:brightness-110">
              <Plus className="w-4 h-4" /> Nouveau process
            </button>
          )}
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="p-4 text-sm text-c-ink-soft text-center">Chargement…</div>
          )}
          {!loading && list.length === 0 && (
            <div className="p-4 text-sm text-c-ink-faint text-center italic">
              Aucun process
            </div>
          )}
          {list.map(it => (
            <button key={it.IDProcess} onClick={() => ouvrir(it)}
              className={`w-full text-left px-3 py-2 border-b border-c-line-soft hover:bg-c-brand-soft ${
                selectedId === it.IDProcess ? 'bg-c-brand-soft' : ''}`}>
              <div className="text-sm font-medium truncate">{it.Titre}</div>
              <div className="text-xs text-c-ink-soft truncate">
                {it.Service && <span className="font-semibold">{it.Service}</span>}
                {it.MotsCles && ` · ${it.MotsCles}`}
              </div>
              <div className="text-[10px] text-c-ink-faint mt-0.5">
                {it.NomOpeCrea} · {fmtDateFR(it.DateCrea)}
                {it.NbFichiers > 0 && ` · ${it.NbFichiers} fichier(s)`}
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* Colonne droite : détail / édition */}
      <main className="flex-1 flex flex-col bg-white border border-c-line-soft rounded overflow-hidden">
        {!selected && !editing && (
          <div className="flex-1 flex items-center justify-center text-c-ink-faint italic">
            Sélectionne un process à gauche{canEdit && ' ou crée-en un nouveau'}
          </div>
        )}

        {(selected || editing) && (
          <>
            <header className="p-3 border-b border-c-line-soft flex items-center gap-2">
              <div className="flex-1 min-w-0">
                {editing ? (
                  <input value={titre} onChange={e => setTitre(e.target.value)}
                    placeholder="Titre du process *"
                    className="w-full text-base font-semibold border border-c-line rounded px-2 py-1 bg-white" />
                ) : (
                  <h2 className="text-base font-semibold truncate">
                    {selected!.Titre}
                  </h2>
                )}
                {!editing && (
                  <div className="text-xs text-c-ink-soft mt-0.5">
                    Créé par {selected!.NomOpeCrea} · Modifié le{' '}
                    {fmtDateFR(selected!.DerniereModif || selected!.DateCrea)}
                  </div>
                )}
              </div>
              {canEdit && !editing && selected && (
                <>
                  <button onClick={() => setEditing(true)}
                    className="p-2 rounded hover:bg-gray-100 text-c-ink-soft"
                    title="Modifier">
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button onClick={() => setShowDroits(true)}
                    className="p-2 rounded hover:bg-gray-100 text-c-ink-soft"
                    title="Droits d'accès">
                    <ShieldCheck className="w-4 h-4" />
                  </button>
                  <button onClick={supprimer}
                    className="p-2 rounded hover:bg-red-50 text-red-600"
                    title="Supprimer">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </>
              )}
              {editing && (
                <>
                  <button onClick={sauvegarder}
                    className="flex items-center gap-1 px-3 py-1.5 rounded bg-c-brand text-white text-sm font-semibold hover:brightness-110">
                    <Save className="w-4 h-4" /> Enregistrer
                  </button>
                  <button onClick={() => {
                    if (selected) {
                      setTitre(selected.Titre); setService(selected.Service)
                      setMotsCles(selected.MotsCles)
                    }
                    setEditing(false)
                  }} className="p-2 rounded hover:bg-gray-100">
                    <X className="w-4 h-4" />
                  </button>
                </>
              )}
            </header>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Métadonnées */}
              <div className="grid grid-cols-2 gap-4">
                <label className="block">
                  <span className="block text-xs text-c-ink-soft mb-0.5">Service</span>
                  {editing ? (
                    <input value={service} onChange={e => setService(e.target.value)}
                      list="services-list"
                      placeholder="IT, RH, COMM…"
                      className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white uppercase" />
                  ) : (
                    <div className="text-sm py-1.5">{selected!.Service || '—'}</div>
                  )}
                  <datalist id="services-list">
                    {services.map(s => <option key={s} value={s} />)}
                  </datalist>
                </label>
                <div className="block">
                  <span className="block text-xs text-c-ink-soft mb-0.5">Mots-clés</span>
                  <MotsClesChips
                    value={editing ? motsCles : (selected?.MotsCles || '')}
                    editable={editing}
                    onChange={setMotsCles} />
                </div>
              </div>

              {/* Fichiers */}
              {selected && !editing && (
                <FichiersList selected={selected} ctx={ctx}
                  canEdit={canEdit}
                  onUpload={uploadPJ} onDelete={supprimerPJ} />
              )}

              {/* Diagrammes (N par process) */}
              {selected && !editing && (
                <DiagrammesList selected={selected} canEdit={canEdit}
                  onOpen={(id, titre) => setDiagOpen({ id, titre })}
                  onNouveau={() => setDiagOpen({
                    id: '0', titre: `Diagramme ${(selected.Diagrammes?.length || 0) + 1}`,
                  })}
                  onDelete={async (id) => {
                    const ok = await showConfirm({
                      title: 'Supprimer ce diagramme ?',
                      message: 'Action irréversible.',
                      confirmLabel: 'Supprimer', variant: 'danger',
                    })
                    if (!ok) return
                    const r = await deleteDiagramme(ctx, id)
                    if (r?.ok) {
                      const p = await fetchOne(ctx, selected.IDProcess)
                      if (p) setSelected(p)
                      showToast('Diagramme supprimé', 'success')
                    }
                  }} />
              )}
            </div>
          </>
        )}
      </main>

      {/* Modal droits */}
      {showDroits && selected && (
        <DroitsModal selected={selected} ctx={ctx}
          onClose={() => setShowDroits(false)}
          onChanged={async () => {
            const p = await fetchOne(ctx, selected.IDProcess)
            if (p) setSelected(p)
          }} />
      )}

      {/* Editeur/viewer de diagramme */}
      {diagOpen && selected && (
        <DiagrammeEditor ctx={ctx}
          idProcess={selected.IDProcess}
          idDiagramme={diagOpen.id}
          initialTitre={diagOpen.titre}
          readonly={!canEdit}
          onSaved={async () => {
            const p = await fetchOne(ctx, selected.IDProcess)
            if (p) setSelected(p)
          }}
          onClose={async () => {
            setDiagOpen(null)
            const p = await fetchOne(ctx, selected.IDProcess)
            if (p) setSelected(p)
          }} />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
//  Champ mots-clés en jetons (chips)
// ---------------------------------------------------------------------------

function MotsClesChips({ value, editable, onChange }: {
  value: string
  editable: boolean
  onChange: (v: string) => void
}) {
  const tags = useMemo(() => parseMotsCles(value), [value])
  const [input, setInput] = useState('')

  const add = (raw: string) => {
    const bits = parseMotsCles(raw)
    if (!bits.length) return
    const set = new Set(tags.map(t => t.toLowerCase()))
    const merged = [...tags]
    for (const b of bits) {
      if (!set.has(b.toLowerCase())) { merged.push(b); set.add(b.toLowerCase()) }
    }
    onChange(joinMotsCles(merged))
    setInput('')
  }
  const remove = (i: number) => {
    const next = tags.filter((_, k) => k !== i)
    onChange(joinMotsCles(next))
  }

  if (!editable) {
    return tags.length === 0 ? (
      <div className="text-sm py-1.5 text-c-ink-faint">—</div>
    ) : (
      <div className="flex flex-wrap gap-1 py-1">
        {tags.map((t, i) => (
          <span key={i}
            className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-c-brand-soft text-c-brand rounded">
            <Tag className="w-3 h-3" />{t}
          </span>
        ))}
      </div>
    )
  }
  return (
    <div className="min-h-[38px] w-full border border-c-line rounded px-2 py-1 bg-white
                    flex flex-wrap items-center gap-1 focus-within:border-c-brand
                    focus-within:ring-1 focus-within:ring-c-brand">
      {tags.map((t, i) => (
        <span key={i}
          className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-c-brand-soft text-c-brand rounded">
          {t}
          <button type="button" onClick={() => remove(i)}
            className="hover:text-red-600" aria-label={`Retirer ${t}`}>×</button>
        </span>
      ))}
      <input value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter' || e.key === ',' || e.key === ';') {
            e.preventDefault(); add(input)
          } else if (e.key === 'Backspace' && !input && tags.length) {
            e.preventDefault(); remove(tags.length - 1)
          }
        }}
        onPaste={e => {
          const txt = e.clipboardData.getData('text')
          if (/[\n,;]/.test(txt)) {
            e.preventDefault(); add(input + ' ' + txt); return
          }
        }}
        onBlur={() => { if (input) add(input) }}
        placeholder={tags.length === 0 ? 'Ajoute un mot-clé (Entrée pour valider)…' : ''}
        className="flex-1 min-w-[120px] text-sm border-0 bg-transparent outline-none py-0.5" />
    </div>
  )
}

// ---------------------------------------------------------------------------
//  Liste des PJ
// ---------------------------------------------------------------------------

function FichiersList({ selected, ctx, canEdit, onUpload, onDelete }: {
  selected: Process
  ctx: { apiBase: string; getToken: () => string | null }
  canEdit: boolean
  onUpload: (f: File) => void
  onDelete: (f: ProcessFichierMeta) => void
}) {
  const fileRef = useState<HTMLInputElement | null>(null)
  return (
    <section>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold">
          Fichiers ({selected.Fichiers?.length || 0})
        </h3>
        {canEdit && (
          <label className="flex items-center gap-1 px-2 py-1 rounded bg-gray-900 text-white text-xs font-semibold cursor-pointer hover:brightness-110">
            <Upload className="w-3.5 h-3.5" /> Ajouter
            <input type="file" hidden
              onChange={e => {
                const f = e.target.files?.[0]; if (f) onUpload(f)
                if (e.target) e.target.value = ''
              }} />
          </label>
        )}
      </div>
      {(!selected.Fichiers || selected.Fichiers.length === 0) && (
        <div className="text-xs italic text-c-ink-faint py-2">
          Aucun fichier attaché
        </div>
      )}
      <div className="space-y-1">
        {selected.Fichiers?.map(f => (
          <div key={f.IDProcessFichier}
            className="flex items-center gap-2 px-2 py-1.5 border border-c-line-soft rounded bg-white">
            <FileText className="w-4 h-4 text-c-ink-soft shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-sm truncate">{f.Titre}{f.Extension}</div>
              <div className="text-[10px] text-c-ink-faint">
                {fmtSize(f.TailleFic)}
                {metaLine(f) && ` · ${metaLine(f)}`}
              </div>
            </div>
            <a href={fichierUrl(ctx, f.IDProcessFichier) + `?token=${encodeURIComponent(ctx.getToken() || '')}`}
              target="_blank" rel="noreferrer"
              onClick={async e => {
                // fetch authentifié + blob URL pour supporter Bearer
                e.preventDefault()
                const r = await fetch(fichierUrl(ctx, f.IDProcessFichier), {
                  headers: { Authorization: `Bearer ${ctx.getToken()}` },
                })
                if (!r.ok) return
                const blob = await r.blob()
                const url = URL.createObjectURL(blob)
                window.open(url, '_blank')
                setTimeout(() => URL.revokeObjectURL(url), 60_000)
              }}
              className="p-1 rounded hover:bg-gray-100 text-c-ink-soft"
              title="Ouvrir">
              <Download className="w-4 h-4" />
            </a>
            {canEdit && (
              <button onClick={() => onDelete(f)}
                className="p-1 rounded hover:bg-red-50 text-red-600"
                title="Supprimer">
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>
      {/* satisfait TS pour fileRef non utilisé */}
      <input ref={r => fileRef[1](r)} hidden />
    </section>
  )
}

// ---------------------------------------------------------------------------
//  Liste des diagrammes du process
// ---------------------------------------------------------------------------

function DiagrammesList({ selected, canEdit, onOpen, onNouveau, onDelete }: {
  selected: Process
  canEdit: boolean
  onOpen: (id: string, titre: string) => void
  onNouveau: () => void
  onDelete: (id: string) => void
}) {
  const items = selected.Diagrammes || []
  return (
    <section>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold">
          Diagrammes ({items.length})
        </h3>
        {canEdit && (
          <button onClick={onNouveau}
            className="flex items-center gap-1 px-2 py-1 rounded bg-gray-900 text-white text-xs font-semibold hover:brightness-110">
            <Network className="w-3.5 h-3.5" /> Nouveau diagramme
          </button>
        )}
      </div>
      {items.length === 0 && (
        <div className="text-xs italic text-c-ink-faint py-2">
          Aucun diagramme{canEdit && ' — clique sur "Nouveau diagramme" pour en créer un'}
        </div>
      )}
      <div className="space-y-1">
        {items.map(d => (
          <div key={d.IDProcessDiagramme}
            className="flex items-center gap-2 px-2 py-1.5 border border-c-line-soft rounded bg-white">
            <Network className="w-4 h-4 text-c-brand shrink-0" />
            <button onClick={() => onOpen(d.IDProcessDiagramme, d.Titre)}
              className="flex-1 min-w-0 text-left hover:underline">
              <div className="text-sm truncate">{d.Titre || '(sans titre)'}</div>
              <div className="text-[10px] text-c-ink-faint">
                {metaLine(d)}
              </div>
            </button>
            {canEdit && (
              <button onClick={() => onDelete(d.IDProcessDiagramme)}
                className="p-1 rounded hover:bg-red-50 text-red-600"
                title="Supprimer">
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
//  Modal droits d'accès
// ---------------------------------------------------------------------------

function DroitsModal({ selected, ctx, onClose, onChanged }: {
  selected: Process
  ctx: { apiBase: string; getToken: () => string | null }
  onClose: () => void; onChanged: () => Promise<void>
}) {
  const [profils, setProfils] = useState<ProfilItem[]>([])
  const [societes, setSocietes] = useState<SocieteItem[]>([])
  const [newSalarie, setNewSalarie] = useState('')  // id_salarie ou vide
  const [newSalarieLib, setNewSalarieLib] = useState('')
  const [newProfil, setNewProfil] = useState('')
  const [newSte, setNewSte] = useState('')  // '' = toutes

  useEffect(() => {
    void fetchProfils(ctx).then(r => { if (Array.isArray(r)) setProfils(r) })
    void fetchSocietes(ctx).then(r => { if (Array.isArray(r)) setSocietes(r) })
  }, [ctx])

  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onEsc)
    return () => window.removeEventListener('keydown', onEsc)
  }, [onClose])

  const ajouter = async () => {
    const idSal = (newSalarie || '').trim()
    const profil = (newProfil || '').trim()
    if (!idSal && !profil) {
      showToast('Choisis un salarié OU un profil', 'error'); return
    }
    const r = await saveDroit(ctx, {
      IDProcessDroit: '0',
      IDProcess: selected.IDProcess,
      IDSalarie: idSal || '0',
      TypeProfil: idSal ? '' : profil,
      IdSte: newSte || '0',
      DroitActif: true,
    })
    if (!r?.IDProcessDroit) { showToast('Échec', 'error'); return }
    setNewSalarie(''); setNewSalarieLib('')
    setNewProfil(''); setNewSte('')
    await onChanged()
  }

  const supprimer = async (d: ProcessDroit) => {
    const r = await deleteDroit(ctx, d.IDProcessDroit)
    if (!r?.ok) { showToast('Échec', 'error'); return }
    await onChanged()
  }

  return (
    <div className="fixed inset-0 z-[90] bg-black/50 flex items-center justify-center p-4"
      onClick={onClose}>
      <div onClick={e => e.stopPropagation()}
        className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        <header className="flex items-center justify-between px-4 py-3 border-b border-c-line-soft">
          <h3 className="text-base font-semibold flex items-center gap-2">
            <Lock className="w-4 h-4" /> Droits d'accès
          </h3>
          <button onClick={onClose}
            className="p-1 rounded hover:bg-gray-100">
            <X className="w-4 h-4" />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {/* Formulaire ajout */}
          <div className="border border-c-line-soft rounded p-3 bg-c-surface-soft space-y-2">
            <div className="text-xs text-c-ink-soft">
              Ajoute un droit par <b>profil</b> (niveau mini hiérarchique) OU par <b>salarié nommé</b>.
              Combine avec une <b>société</b> (ou "Toutes").
            </div>
            <div className="grid grid-cols-3 gap-2">
              <label className="block">
                <span className="block text-xs text-c-ink-soft mb-0.5">Profil</span>
                <select value={newProfil} onChange={e => {
                  setNewProfil(e.target.value); if (e.target.value) setNewSalarie('')
                }}
                  className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white">
                  <option value="">— Choisir —</option>
                  {profils.map(p => (
                    <option key={p.Code} value={p.Code}>{p.Lib}</option>
                  ))}
                </select>
              </label>
              <div className="block">
                <span className="block text-xs text-c-ink-soft mb-0.5">Salarié</span>
                <SalarieAutocomplete ctx={ctx}
                  value={newSalarie} valueLib={newSalarieLib}
                  onChange={(id, lib) => {
                    setNewSalarie(id); setNewSalarieLib(lib)
                    if (id) setNewProfil('')
                  }} />
              </div>
              <label className="block">
                <span className="block text-xs text-c-ink-soft mb-0.5">Société</span>
                <select value={newSte} onChange={e => setNewSte(e.target.value)}
                  className="w-full border border-c-line rounded px-2 py-1.5 text-sm bg-white">
                  <option value="">Toutes</option>
                  {societes.map(s => (
                    <option key={s.IdSte} value={s.IdSte}>{s.Lib}</option>
                  ))}
                </select>
              </label>
            </div>
            <button onClick={ajouter}
              className="px-3 py-1.5 rounded bg-c-brand text-white text-sm font-semibold hover:brightness-110">
              Ajouter
            </button>
          </div>

          {/* Liste existante */}
          <div>
            <h4 className="text-xs font-semibold text-c-ink-soft mb-1">
              Droits configurés ({selected.Droits?.length || 0})
            </h4>
            {(!selected.Droits || selected.Droits.length === 0) && (
              <div className="text-xs italic text-c-ink-faint py-2">
                Aucun droit d'accès. Seul le créateur peut voir ce process.
              </div>
            )}
            <div className="space-y-1">
              {selected.Droits?.map(d => (
                <div key={d.IDProcessDroit}
                  className="flex items-center gap-2 px-2 py-1.5 border border-c-line-soft rounded bg-white">
                  <div className="flex-1 text-sm">
                    {d.IDSalarie ? (
                      <><b>{d.NomSalarie || `#${d.IDSalarie}`}</b> (nominatif)</>
                    ) : (
                      <><b>{d.TypeProfil}</b> et au-dessus</>
                    )}
                    <span className="text-c-ink-soft"> ·  </span>
                    {d.IdSte ? d.LibSte : <span className="italic">Toutes sociétés</span>}
                  </div>
                  <button onClick={() => supprimer(d)}
                    className="p-1 rounded hover:bg-red-50 text-red-600">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
