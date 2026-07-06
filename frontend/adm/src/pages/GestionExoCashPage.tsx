/**
 * Fen_GestionExoCash - Gestion Exo Cash (3 onglets).
 *
 * Onglet 1 : Lots (pgt_exo_cash_lot) - CRUD complet + Fen_LotFiche modal
 * Onglet 2 : Famille Prod (pgt_exo_cash_famille_lot) - CRUD [a coder]
 * Onglet 3 : Suivi des livrets (pgt_salarie_livret AGG) - lecture [a coder]
 *
 * Cf. WinDev Fen_GestionExoCash + Fen_LotFiche.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ArrowLeft, Banknote, Loader2, Plus, Pencil, Copy, Trash2, Check, X,
  Save, Upload, Image as ImageIcon,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getToken } from '@/api'
import { showToast, showConfirm } from '@shared/ui/dialog'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import {
  useTableSortFilter, SortableTh, FilterInput,
} from '@shared/production/_tableHelpers'
import FI_LotFicheModal from '@/components/exocash/FI_LotFicheModal'

const API_BASE = '/api/adm'

interface Lot {
  id_exo_cash_lot: string
  id_exo_cash_famille_lot: string
  lib_famille_lot: string
  marque: string
  lib_lot: string
  categorie: number
  montant: number
  stock: number
  sur_commande: boolean
  en_solde: boolean
  montant_solde: number
  solde_deb: string
  solde_fin: string
  is_actif: boolean
  description: string
  modif_date: string
  modif_op: string
  modif_op_nom: string
  has_photo1: boolean
  has_photo2: boolean
  has_photo3: boolean
}

interface Famille {
  id_exo_cash_famille_lot: string
  lib_famille_lot: string
  has_icone: boolean
}

interface Livret {
  id_salarie: string
  nom_prenom: string
  somme_debit: number
  somme_credit: number
  solde_livret: number
}

type Tab = 'lots' | 'famille' | 'suivi'

const money = (n: number): string =>
  `${n.toFixed(2).replace('.', ',')} €`

export default function GestionExoCashPage() {
  useDocumentTitle('Gestion Exo Cash')
  const [tab, setTab] = useState<Tab>('lots')
  const [lots, setLots] = useState<Lot[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<string>('')
  const [ficheOpen, setFicheOpen] = useState<{ id: string | null } | null>(null)

  // Famille (onglet 2)
  const [familles, setFamilles] = useState<Famille[]>([])
  const [selectedFam, setSelectedFam] = useState<string>('')
  const [famEdit, setFamEdit] = useState<{
    id: string
    lib: string
    dirty: boolean
  } | null>(null)
  const famIconeInput = useRef<HTMLInputElement>(null)

  // Suivi Livrets (onglet 3)
  const [livrets, setLivrets] = useState<Livret[]>([])

  const loadLots = useCallback(async () => {
    setLoading(true)
    setSelected('')
    try {
      const r = await fetch(`${API_BASE}/gestion-exo-cash/lots`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setLots(d.items || [])
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadFamilles = useCallback(async () => {
    setLoading(true)
    setSelectedFam('')
    setFamEdit(null)
    try {
      const r = await fetch(`${API_BASE}/gestion-exo-cash/familles`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setFamilles(d.items || [])
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadLivrets = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/gestion-exo-cash/suivi-livrets`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      const d = await r.json()
      setLivrets(d.items || [])
    } catch (e) {
      showToast(`Erreur : ${(e as Error).message}`, 'error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (tab === 'lots') void loadLots()
    else if (tab === 'famille') void loadFamilles()
    else if (tab === 'suivi') void loadLivrets()
  }, [tab, loadLots, loadFamilles, loadLivrets])

  // ============ FAMILLE handlers ============
  const selFam = familles.find((f) => f.id_exo_cash_famille_lot === selectedFam) || null

  const famNew = () => {
    setSelectedFam('')
    setFamEdit({ id: '0', lib: '', dirty: false })
  }
  const famEdit_open = () => {
    if (!selFam) return
    setFamEdit({
      id: selFam.id_exo_cash_famille_lot,
      lib: selFam.lib_famille_lot,
      dirty: false,
    })
  }
  const famSave = async () => {
    if (!famEdit || !famEdit.lib.trim()) return
    const r = await fetch(`${API_BASE}/gestion-exo-cash/familles`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id_exo_cash_famille_lot: Number(famEdit.id),
        lib_famille_lot: famEdit.lib,
      }),
    })
    const d = await r.json()
    if (d.ok) {
      showToast('Famille enregistrée', 'success')
      setFamEdit({ id: d.id_exo_cash_famille_lot, lib: famEdit.lib, dirty: false })
      setSelectedFam(d.id_exo_cash_famille_lot)
      void loadFamilles()
    } else {
      showToast(d.error || 'Erreur', 'error')
    }
  }
  const famDelete = async () => {
    if (!selFam) return
    const ok = await showConfirm({
      title: 'Supprimer cette famille',
      message: 'Vous êtes sur le point de supprimer ce type d\'opération. Voulez-vous continuer ?',
      variant: 'danger',
    })
    if (!ok) return
    const r = await fetch(
      `${API_BASE}/gestion-exo-cash/familles/${selFam.id_exo_cash_famille_lot}`,
      { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    const d = await r.json()
    if (d.ok) {
      showToast('Famille supprimée', 'success')
      void loadFamilles()
    } else {
      showToast(d.error || 'Erreur', 'error')
    }
  }
  const famUploadIcone = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !famEdit || famEdit.id === '0') {
      showToast('Enregistre d\'abord la famille avant de charger une icône.', 'info')
      return
    }
    const fd = new FormData()
    fd.append('fichier', file)
    const r = await fetch(
      `${API_BASE}/gestion-exo-cash/familles/${famEdit.id}/icone`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      },
    )
    const d = await r.json()
    if (d.ok) {
      showToast('Icône chargée', 'success')
      void loadFamilles()
    } else {
      showToast(d.error || 'Erreur', 'error')
    }
  }

  const tsfFam = useTableSortFilter(
    familles as unknown as Array<Record<string, unknown>>,
    { key: 'lib_famille_lot', dir: 'asc' },
    (r) => String(r.lib_famille_lot || ''),
  )
  const visibleFam = tsfFam.rows as unknown as Famille[]

  // ============ LIVRET tsf ============
  const tsfLiv = useTableSortFilter(
    livrets as unknown as Array<Record<string, unknown>>,
    { key: 'solde_livret', dir: 'desc' },
    (r) => String(r.nom_prenom || ''),
  )
  const visibleLiv = tsfLiv.rows as unknown as Livret[]
  const totalDebit = visibleLiv.reduce((s, l) => s + l.somme_debit, 0)
  const totalCredit = visibleLiv.reduce((s, l) => s + l.somme_credit, 0)
  const totalSolde = totalCredit - totalDebit

  const tsf = useTableSortFilter(
    lots as unknown as Array<Record<string, unknown>>,
    { key: 'lib_famille_lot', dir: 'asc' },
    (r) => [r.lib_famille_lot, r.marque, r.lib_lot].join(' '),
  )
  const visible = tsf.rows as unknown as Lot[]
  const sel = visible.find((l) => l.id_exo_cash_lot === selected) || null

  const onCreate = () => setFicheOpen({ id: null })
  const onEdit = () => sel && setFicheOpen({ id: sel.id_exo_cash_lot })
  const onDuplicate = async () => {
    if (!sel) return
    const r = await fetch(
      `${API_BASE}/gestion-exo-cash/lots/${sel.id_exo_cash_lot}/duplicate`,
      { method: 'POST', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    const d = await r.json()
    if (d.ok) {
      showToast('Lot dupliqué', 'success')
      void loadLots()
    } else {
      showToast(d.error || 'Erreur', 'error')
    }
  }
  const onDelete = async () => {
    if (!sel) return
    const ok = await showConfirm({
      title: 'Supprimer ce lot',
      message: 'Vous êtes sur le point de supprimer ce lot. Voulez-vous continuer ?',
      variant: 'danger',
    })
    if (!ok) return
    const r = await fetch(
      `${API_BASE}/gestion-exo-cash/lots/${sel.id_exo_cash_lot}`,
      { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } },
    )
    const d = await r.json()
    if (d.ok) {
      showToast('Lot supprimé', 'success')
      void loadLots()
    } else {
      showToast(d.error || 'Erreur', 'error')
    }
  }

  return (
    <div className="min-h-screen bg-[#F5F5F0] p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <Link
            to="/"
            className="p-2 rounded hover:bg-white/50"
            title="Retour"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <Banknote className="w-6 h-6 text-[#8B7355]" />
          <h1 className="text-2xl font-semibold text-[#8B7355]">
            Gestion Exo Cash
          </h1>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-[#E5E0D5] mb-4">
          {(
            [
              { key: 'lots', label: 'Lots' },
              { key: 'famille', label: 'Famille Prod' },
              { key: 'suivi', label: 'Suivi des livrets' },
            ] as { key: Tab; label: string }[]
          ).map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                tab === t.key
                  ? 'border-[#8B7355] text-[#8B7355]'
                  : 'border-transparent text-gray-500 hover:text-[#8B7355]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'lots' && (
          <div className="bg-white rounded-lg shadow p-4">
            {/* Actions top */}
            <div className="flex items-center gap-2 mb-4">
              <button
                onClick={onCreate}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#8B7355] text-white hover:bg-[#725e46]"
              >
                <Plus className="w-4 h-4" />
                Nouveau lot
              </button>
              <button
                onClick={onEdit}
                disabled={!sel}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] disabled:opacity-40 hover:bg-[#ECF1F2]"
              >
                <Pencil className="w-4 h-4" />
                Éditer
              </button>
              <button
                onClick={onDuplicate}
                disabled={!sel}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] disabled:opacity-40 hover:bg-[#ECF1F2]"
              >
                <Copy className="w-4 h-4" />
                Dupliquer
              </button>
              <button
                onClick={onDelete}
                disabled={!sel}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-red-500 text-red-500 disabled:opacity-40 hover:bg-red-50"
              >
                <Trash2 className="w-4 h-4" />
                Supprimer
              </button>
              <div className="ml-auto">
                <FilterInput
                  value={tsf.filter}
                  onChange={tsf.setFilter}
                  placeholder="Rechercher..."
                />
              </div>
            </div>

            {loading ? (
              <div className="flex items-center justify-center p-8">
                <Loader2 className="w-6 h-6 animate-spin text-[#8B7355]" />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[#8B7355] border-b border-[#E5E0D5]">
                      <SortableTh label="Famille" sortKey="lib_famille_lot"
                        sort={tsf.sort} onSort={tsf.toggleSort} />
                      <SortableTh label="Marque" sortKey="marque"
                        sort={tsf.sort} onSort={tsf.toggleSort} />
                      <SortableTh label="Nom" sortKey="lib_lot"
                        sort={tsf.sort} onSort={tsf.toggleSort} />
                      <SortableTh label="Stock" sortKey="stock" align="right"
                        sort={tsf.sort} onSort={tsf.toggleSort} />
                      <SortableTh label="Montant" sortKey="montant" align="right"
                        sort={tsf.sort} onSort={tsf.toggleSort} />
                      <SortableTh label="En Solde" sortKey="en_solde" align="center"
                        sort={tsf.sort} onSort={tsf.toggleSort} />
                      <SortableTh label="Soldé" sortKey="montant_solde" align="right"
                        sort={tsf.sort} onSort={tsf.toggleSort} />
                      <SortableTh label="Actif" sortKey="is_actif" align="center"
                        sort={tsf.sort} onSort={tsf.toggleSort} />
                    </tr>
                  </thead>
                  <tbody>
                    {visible.map((l) => {
                      const isSelected = l.id_exo_cash_lot === selected
                      return (
                        <tr
                          key={l.id_exo_cash_lot}
                          onClick={() => setSelected(l.id_exo_cash_lot)}
                          onDoubleClick={() =>
                            setFicheOpen({ id: l.id_exo_cash_lot })
                          }
                          className={`cursor-pointer border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${
                            isSelected ? 'bg-[#ECF1F2] ring-1 ring-[#8B7355]' : ''
                          } ${!l.is_actif ? 'opacity-60' : ''}`}
                        >
                          <td className="py-2 px-2">{l.lib_famille_lot}</td>
                          <td className="py-2 px-2">{l.marque}</td>
                          <td className="py-2 px-2">{l.lib_lot}</td>
                          <td className="py-2 px-2 text-right tabular-nums">
                            {l.stock}
                            {l.sur_commande && (
                              <span
                                className="ml-1 text-[10px] text-blue-600"
                                title="Sur commande"
                              >
                                ⚙
                              </span>
                            )}
                          </td>
                          <td className="py-2 px-2 text-right tabular-nums">
                            {money(l.montant)}
                          </td>
                          <td className="py-2 px-2 text-center">
                            {l.en_solde ? (
                              <Check className="w-4 h-4 text-green-600 inline" />
                            ) : (
                              <span className="text-gray-300">—</span>
                            )}
                          </td>
                          <td className="py-2 px-2 text-right tabular-nums">
                            {l.en_solde ? money(l.montant_solde) : ''}
                          </td>
                          <td className="py-2 px-2 text-center">
                            {l.is_actif ? (
                              <Check className="w-4 h-4 text-green-600 inline" />
                            ) : (
                              <X className="w-4 h-4 text-red-500 inline" />
                            )}
                          </td>
                        </tr>
                      )
                    })}
                    {visible.length === 0 && (
                      <tr>
                        <td colSpan={8} className="py-6 text-center text-gray-400">
                          Aucun lot.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            <div className="mt-3 text-xs text-gray-500">
              {visible.length} lot{visible.length > 1 ? 's' : ''}
              &nbsp;— double-clic pour éditer
            </div>
          </div>
        )}

        {tab === 'famille' && (
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
            <div className="bg-white rounded-lg shadow p-4">
              {/* Actions top */}
              <div className="flex items-center gap-2 mb-4">
                <button
                  onClick={famNew}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#8B7355] text-white hover:bg-[#725e46]"
                >
                  <Plus className="w-4 h-4" />
                  Nouvelle famille
                </button>
                <button
                  onClick={famEdit_open}
                  disabled={!selFam}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#8B7355] text-[#8B7355] disabled:opacity-40 hover:bg-[#ECF1F2]"
                >
                  <Pencil className="w-4 h-4" />
                  Éditer
                </button>
                <button
                  onClick={famDelete}
                  disabled={!selFam}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-red-500 text-red-500 disabled:opacity-40 hover:bg-red-50"
                >
                  <Trash2 className="w-4 h-4" />
                  Supprimer
                </button>
                <div className="ml-auto">
                  <FilterInput
                    value={tsfFam.filter}
                    onChange={tsfFam.setFilter}
                    placeholder="Rechercher..."
                  />
                </div>
              </div>

              {loading ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="w-6 h-6 animate-spin text-[#8B7355]" />
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[#8B7355] border-b border-[#E5E0D5]">
                      <th className="py-1.5 px-2 w-14 text-center">Icône</th>
                      <SortableTh label="Libellé" sortKey="lib_famille_lot"
                        sort={tsfFam.sort} onSort={tsfFam.toggleSort} />
                    </tr>
                  </thead>
                  <tbody>
                    {visibleFam.map((f) => {
                      const isSel = f.id_exo_cash_famille_lot === selectedFam
                      return (
                        <tr
                          key={f.id_exo_cash_famille_lot}
                          onClick={() => setSelectedFam(f.id_exo_cash_famille_lot)}
                          className={`cursor-pointer border-b border-[#F0EDE5] hover:bg-[#ECF1F2] ${
                            isSel ? 'bg-[#ECF1F2] ring-1 ring-[#8B7355]' : ''
                          }`}
                        >
                          <td className="py-1.5 px-2 text-center">
                            {f.has_icone ? (
                              <img
                                src={`${API_BASE}/gestion-exo-cash/familles/${f.id_exo_cash_famille_lot}/icone`}
                                alt=""
                                className="w-8 h-8 object-cover rounded inline-block"
                              />
                            ) : (
                              <ImageIcon className="w-6 h-6 text-gray-300 inline-block" />
                            )}
                          </td>
                          <td className="py-1.5 px-2">{f.lib_famille_lot}</td>
                        </tr>
                      )
                    })}
                    {visibleFam.length === 0 && (
                      <tr>
                        <td colSpan={2} className="py-6 text-center text-gray-400">
                          Aucune famille.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>

            {/* Panneau édition à droite */}
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="text-sm font-semibold text-[#8B7355] mb-3">
                {famEdit
                  ? famEdit.id === '0'
                    ? 'Nouvelle famille'
                    : 'Édition famille'
                  : 'Sélectionnez ou créez une famille'}
              </h3>
              {famEdit ? (
                <div className="space-y-3">
                  <label className="flex flex-col text-sm gap-1">
                    <span className="text-[#8B7355] font-medium">
                      Libellé (max 50)
                    </span>
                    <input
                      value={famEdit.lib}
                      onChange={(e) =>
                        setFamEdit({ ...famEdit, lib: e.target.value, dirty: true })
                      }
                      maxLength={50}
                      className="px-2 py-1.5 border border-[#E5E0D5] rounded"
                      autoFocus
                    />
                  </label>
                  <div className="flex justify-end">
                    <button
                      onClick={famSave}
                      disabled={!famEdit.lib.trim()}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#059669] text-white disabled:opacity-40 hover:bg-[#047857]"
                    >
                      <Save className="w-4 h-4" />
                      Enregistrer
                    </button>
                  </div>

                  {/* Icône */}
                  <div className="border-t border-[#E5E0D5] pt-3 mt-3">
                    <p className="text-xs text-[#8B7355] font-medium mb-2">
                      Icône
                    </p>
                    <div className="flex items-center gap-3">
                      {famEdit.id !== '0' &&
                      familles.find((f) => f.id_exo_cash_famille_lot === famEdit.id)?.has_icone ? (
                        <img
                          src={`${API_BASE}/gestion-exo-cash/familles/${famEdit.id}/icone?_=${Date.now()}`}
                          alt=""
                          className="w-16 h-16 object-cover rounded border border-[#E5E0D5]"
                        />
                      ) : (
                        <div className="w-16 h-16 rounded border border-[#E5E0D5] bg-[#F5F5F0] flex items-center justify-center">
                          <ImageIcon className="w-8 h-8 text-gray-300" />
                        </div>
                      )}
                      <button
                        onClick={() => famIconeInput.current?.click()}
                        disabled={famEdit.id === '0'}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#8B7355] text-white disabled:opacity-40 hover:bg-[#725e46]"
                      >
                        <Upload className="w-4 h-4" />
                        Télécharger
                      </button>
                      <input
                        ref={famIconeInput}
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={famUploadIcone}
                      />
                    </div>
                    {famEdit.id === '0' && (
                      <p className="text-xs text-gray-500 italic mt-2">
                        Enregistre d'abord pour charger une icône.
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-gray-400 italic">
                  Utilisez les boutons ci-contre pour créer ou éditer une famille.
                </p>
              )}
            </div>
          </div>
        )}

        {tab === 'suivi' && (
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2 mb-4">
              <FilterInput
                value={tsfLiv.filter}
                onChange={tsfLiv.setFilter}
                placeholder="Rechercher un salarié..."
              />
              <div className="ml-auto text-xs text-gray-600 tabular-nums">
                Solde total :{' '}
                <span
                  className={`font-semibold ${
                    totalSolde >= 0 ? 'text-green-700' : 'text-red-700'
                  }`}
                >
                  {money(totalSolde)}
                </span>
              </div>
            </div>
            {loading ? (
              <div className="flex items-center justify-center p-8">
                <Loader2 className="w-6 h-6 animate-spin text-[#8B7355]" />
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[#8B7355] border-b border-[#E5E0D5]">
                    <SortableTh label="Salarié" sortKey="nom_prenom"
                      sort={tsfLiv.sort} onSort={tsfLiv.toggleSort} />
                    <SortableTh label="Débit" sortKey="somme_debit" align="right"
                      sort={tsfLiv.sort} onSort={tsfLiv.toggleSort} />
                    <SortableTh label="Crédit" sortKey="somme_credit" align="right"
                      sort={tsfLiv.sort} onSort={tsfLiv.toggleSort} />
                    <SortableTh label="Solde" sortKey="solde_livret" align="right"
                      sort={tsfLiv.sort} onSort={tsfLiv.toggleSort} />
                  </tr>
                </thead>
                <tbody>
                  {visibleLiv.map((l) => (
                    <tr
                      key={l.id_salarie}
                      className="border-b border-[#F0EDE5] hover:bg-[#ECF1F2]"
                    >
                      <td className="py-2 px-2">{l.nom_prenom}</td>
                      <td className="py-2 px-2 text-right tabular-nums">
                        {l.somme_debit > 0 ? money(l.somme_debit) : ''}
                      </td>
                      <td className="py-2 px-2 text-right tabular-nums">
                        {l.somme_credit > 0 ? money(l.somme_credit) : ''}
                      </td>
                      <td
                        className={`py-2 px-2 text-right tabular-nums font-semibold ${
                          l.solde_livret >= 0 ? 'text-green-700' : 'text-red-700'
                        }`}
                      >
                        {money(l.solde_livret)}
                      </td>
                    </tr>
                  ))}
                  {visibleLiv.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-6 text-center text-gray-400">
                        Aucun livret.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
            <div className="mt-3 text-xs text-gray-500">
              {visibleLiv.length} salarié{visibleLiv.length > 1 ? 's' : ''} —
              trié par solde décroissant
            </div>
          </div>
        )}
      </div>

      {ficheOpen && (
        <FI_LotFicheModal
          idLot={ficheOpen.id}
          onClose={(reload) => {
            setFicheOpen(null)
            if (reload) void loadLots()
          }}
        />
      )}
    </div>
  )
}
