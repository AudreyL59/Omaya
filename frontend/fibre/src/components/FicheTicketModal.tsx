/**
 * Popup fiche d'un ticket Call Fibre (transposition PAGE_TicketFicheFibre).
 *
 * Phase 1 = lecture seule. Affichage en 3 colonnes :
 *  - Gauche : infos client + bloc vendeur en bas
 *  - Centre : panier d'offres + boutons d'action (grises en phase 1)
 *  - Droite : detail de l'offre selectionnee (portabilite + statut + type
 *    vente + options + test d'eligibilite) + bloc vente
 *
 * Mobile masque "0612345xx" tant que l'ope n'a pas pose le verrou (champ
 * is_my_call cote backend).
 */

import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Loader2,
  ArrowLeft,
  Phone,
  ExternalLink,
  CreditCard,
  CheckCircle2,
  Circle,
  FileText,
} from 'lucide-react'
import { getToken } from '@/api'
import DocumentViewerModal from '@/components/DocumentViewerModal'

interface FicheClient {
  civilite: number
  nom: string
  nom_marital: string
  prenom: string
  nom_format: string
  date_naiss: string
  dep_naiss: number
  type_logement: number
  adresse1: string
  adresse2: string
  cp: string
  ville: string
  email: string
  mobile1: string
  mobile2: string
  opt_rappel: boolean
  opt_partenaire: boolean
  client_pro: boolean
  client_rs: string
  client_siret: string
}

interface FicheVendeur {
  id_salarie: number
  nom: string
  prenom: string
  gsm: string
  lib_affectation: string
}

interface FicheVente {
  ref_appel: string
  intervention_vendeur: boolean
  mobile_propose_vendeur: boolean
  info_vente: string
}

interface FicheAnomalie {
  active: boolean
  id_type: number
  info_cplt: string
}

interface FicheOffre {
  id: string
  id_offre: string
  lib_offre: string
  type: string
  opt_tv: boolean
  portabilite: boolean
  type_vente: number
  statut_prod: number
  motif_annulation: string
  num_portabilite: string
  num_rio: string
  num_prise_optique: string
  opt_choisies: string
}

interface StatutVenteOption {
  id: number
  label: string
}

interface DocRef {
  url: string
  kind: 'pdf' | 'image' | ''
}

interface FicheData {
  id_ticket: string
  id_call_sfr: string
  id_tk_statut: number
  is_cloture: boolean
  is_statut_34: boolean
  is_my_call: boolean
  client: FicheClient
  vendeur: FicheVendeur
  vente: FicheVente
  anomalie: FicheAnomalie
  panier: FicheOffre[]
  nb_prod_total: number
  nb_prod_valide: number
  nb_prod_annule: number
  btn_valider_actif: boolean
  btn_annuler_actif: boolean
  statuts_vente: StatutVenteOption[]
}

const API_BASE = '/api/call/fibre'

interface Props {
  idTicket: string | null
  onClose: () => void
}

export default function FicheTicketModal({ idTicket, onClose }: Props) {
  const [data, setData] = useState<FicheData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [selectedPanierId, setSelectedPanierId] = useState<string>('')
  const [testEligImg, setTestEligImg] = useState<string>('')
  // Etat du viewer doc (CIN / KBIS / Lettre resil) + URLs detectees
  const [docCin, setDocCin] = useState<DocRef>({ url: '', kind: '' })
  const [docKbis, setDocKbis] = useState<DocRef>({ url: '', kind: '' })
  const [docLettre, setDocLettre] = useState<DocRef>({ url: '', kind: '' })
  const [viewerOpen, setViewerOpen] = useState<null | 'cin' | 'kbis' | 'lettre'>(null)

  // Fetch fiche
  useEffect(() => {
    if (!idTicket) return
    setLoading(true)
    setError('')
    setData(null)
    setSelectedPanierId('')
    setTestEligImg('')
    setDocCin({ url: '', kind: '' })
    setDocKbis({ url: '', kind: '' })
    setDocLettre({ url: '', kind: '' })
    ;(async () => {
      try {
        const r = await fetch(`${API_BASE}/tickets/${idTicket}/fiche`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        if (!r.ok) {
          let detail = ''
          try {
            const j = await r.json()
            detail = j?.detail ? `: ${j.detail}` : ''
          } catch {
            /* ignore */
          }
          setError(`Chargement échoué (${r.status})${detail}`)
          return
        }
        const d = (await r.json()) as FicheData
        setData(d)
        // Pré-sélection : 1re ligne FIBRE si présente, sinon 1re ligne
        const firstFibre = d.panier.find((p) => p.type === 'FIBRE')
        if (firstFibre) setSelectedPanierId(firstFibre.id)
        else if (d.panier.length > 0) setSelectedPanierId(d.panier[0].id)
        // Detecte les documents en arriere-plan (CIN + KBIS si Pro)
        fetch(`${API_BASE}/tickets/${idTicket}/documents?client_pro=${d.client.client_pro ? 1 : 0}`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
          .then((r2) => (r2.ok ? r2.json() : null))
          .then((docs) => {
            if (docs?.cin) setDocCin(docs.cin)
            if (docs?.kbis) setDocKbis(docs.kbis)
          })
          .catch(() => {
            /* silencieux */
          })
      } catch (e) {
        setError('Erreur réseau')
      } finally {
        setLoading(false)
      }
    })()
  }, [idTicket])

  // Lazy load TestEligibilite quand on sélectionne une ligne FIBRE
  const selectedOffre = useMemo(
    () => data?.panier.find((p) => p.id === selectedPanierId) || null,
    [data, selectedPanierId],
  )
  useEffect(() => {
    if (!selectedOffre || selectedOffre.type !== 'FIBRE') {
      setTestEligImg('')
      setDocLettre({ url: '', kind: '' })
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const r = await fetch(`${API_BASE}/tickets/panier/${selectedOffre.id}/test-eligibilite`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        })
        if (!r.ok) return
        const d = await r.json()
        if (!cancelled) setTestEligImg(d.test_eligibilite || '')
      } catch {
        /* ignore */
      }
    })()
    // Lettre de resil : visible uniquement si FIBRE + pas portabilite
    if (!selectedOffre.portabilite && idTicket) {
      fetch(`${API_BASE}/tickets/${idTicket}/panier/${selectedOffre.id}/lettre-resil`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => {
          if (!cancelled && d) setDocLettre(d)
        })
        .catch(() => {
          /* silencieux */
        })
    } else {
      setDocLettre({ url: '', kind: '' })
    }
    return () => {
      cancelled = true
    }
  }, [selectedOffre, idTicket])

  // Esc ferme la modal
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!idTicket) return null

  // Document actif dans le viewer
  const viewerDoc: DocRef =
    viewerOpen === 'cin' ? docCin : viewerOpen === 'kbis' ? docKbis : viewerOpen === 'lettre' ? docLettre : { url: '', kind: '' }
  const viewerTitle =
    viewerOpen === 'cin' ? "Carte d'identité" : viewerOpen === 'kbis' ? 'KBIS' : viewerOpen === 'lettre' ? 'Lettre de résiliation' : ''

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-3"
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.97 }}
          className="bg-white rounded-xl shadow-2xl w-full max-w-[1500px] h-[95vh] flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-3 border-b border-c-line">
            <div className="flex items-center gap-3">
              <button
                onClick={onClose}
                className="p-1.5 rounded text-c-ink-soft hover:bg-c-brand-soft hover:text-c-ink transition-colors"
                title="Retour"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <h2 className="text-base font-bold text-c-ink">
                Fiche Ticket Call SFR
                {data ? ` — ${data.client.nom_format}` : ''}
              </h2>
              {data?.is_statut_34 && (
                <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                  Vente mobile en différé
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              <a
                href="https://ezy-distrib.distrib.sfr.fr/home/frontoffice/dfo/dist/index.html#/portail"
                target="_blank"
                rel="noreferrer"
                className="text-xs text-c-brand hover:underline flex items-center gap-1"
              >
                Portail de saisie EZY - SFR
                <ExternalLink className="w-3 h-3" />
              </a>
              <button
                onClick={onClose}
                className="p-1.5 rounded text-c-ink-soft hover:bg-c-brand-soft hover:text-c-ink transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Corps */}
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-c-brand animate-spin" />
            </div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center text-red-600 text-sm">
              {error}
            </div>
          ) : !data ? (
            <div className="flex-1 flex items-center justify-center text-c-ink-faint text-sm italic">
              Aucune donnée
            </div>
          ) : (
            <div className="flex-1 grid grid-cols-12 gap-4 p-4 overflow-auto bg-gray-50">
              <ColonneGauche
                data={data}
                cinAvailable={!!docCin.url}
                kbisAvailable={!!docKbis.url}
                onOpenCin={() => setViewerOpen('cin')}
                onOpenKbis={() => setViewerOpen('kbis')}
              />
              <ColonneCentre data={data} selectedId={selectedPanierId} onSelect={setSelectedPanierId} />
              <ColonneDroite
                data={data}
                offre={selectedOffre}
                testEligImg={testEligImg}
                lettreAvailable={!!docLettre.url}
                onOpenLettre={() => setViewerOpen('lettre')}
              />
            </div>
          )}
        </motion.div>

        {/* Viewer documents (CIN / KBIS / Lettre resil) */}
        <DocumentViewerModal
          open={viewerOpen !== null}
          title={viewerTitle}
          url={viewerDoc.url}
          kind={viewerDoc.kind}
          onClose={() => setViewerOpen(null)}
        />
      </motion.div>
    </AnimatePresence>
  )
}

// --- Colonne gauche : Client + Vendeur -----------------------------------

function ColonneGauche({
  data,
  cinAvailable,
  kbisAvailable,
  onOpenCin,
  onOpenKbis,
}: {
  data: FicheData
  cinAvailable: boolean
  kbisAvailable: boolean
  onOpenCin: () => void
  onOpenKbis: () => void
}) {
  const c = data.client
  const v = data.vendeur
  return (
    <div className="col-span-4 flex flex-col gap-4">
      {/* Bloc client */}
      <div className="bg-white rounded-lg border border-c-line p-4">
        <h3 className="text-sm font-bold text-c-ink mb-3">Information contrat et client</h3>

        <div className="space-y-2.5 text-xs">
          <Radios
            label="Civilité"
            value={c.civilite}
            options={[
              { v: 1, l: 'M.' },
              { v: 2, l: 'Mme' },
              { v: 3, l: 'Mlle' },
            ]}
          />
          <Field label="Nom" value={c.nom} />
          <Field label="Nom Marital" value={c.nom_marital} />
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <Field label="Prénom" value={c.prenom} />
            </div>
            <button
              onClick={onOpenCin}
              disabled={!cinAvailable}
              className="shrink-0 w-12 h-9 rounded border border-c-line hover:bg-c-brand-soft flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed"
              title={cinAvailable ? 'Voir la CIN' : 'Aucune CIN disponible'}
            >
              <CreditCard className="w-5 h-5 text-c-ink-soft" />
            </button>
          </div>
          <div className="text-[10px] text-c-ink-faint text-right -mt-1.5">
            {cinAvailable ? (
              <button onClick={onOpenCin} className="hover:underline">
                Voir la CIN SOS
              </button>
            ) : (
              <span className="italic">Pas de CIN trouvée</span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Né(e) le" value={c.date_naiss} />
            <Field label="Dép" value={c.dep_naiss ? String(c.dep_naiss).padStart(2, '0') : ''} />
          </div>
          <Radios
            label="Logement"
            value={c.type_logement}
            options={[
              { v: 1, l: 'Maison' },
              { v: 2, l: 'Appartement' },
            ]}
          />
          <Field label="Adresse" value={c.adresse1} />
          <Field label="Cplt" value={c.adresse2} />
          <div className="grid grid-cols-3 gap-3">
            <Field label="CP" value={c.cp} />
            <div className="col-span-2">
              <Field label="Ville" value={c.ville} />
            </div>
          </div>
          <Field label="Email" value={c.email} />
          <div className="grid grid-cols-2 gap-3">
            <Field label="Mobile 1" value={c.mobile1} muted={!data.is_my_call} />
            <Field label="Mobile 2 / Fixe" value={c.mobile2} muted={!data.is_my_call} />
          </div>

          {/* Consentements (toggles affichage seul en phase 1) */}
          <div className="pt-2 space-y-2">
            <Toggle
              label="Le client est d'accord pour être rappelé immédiatement par le Call"
              value={c.opt_rappel}
            />
            <Toggle
              label="Le client accepte que ses coordonnées soient transmises aux partenaires"
              value={c.opt_partenaire}
            />
          </div>

          {/* Bouton Part / Pro */}
          <div className="pt-2 flex bg-gray-900 text-white rounded-md p-0.5">
            <ProTab active={!c.client_pro} label="Client Part" />
            <ProTab active={c.client_pro} label="Client Pro" />
          </div>

          {/* Si client Pro : Raison Sociale + SIRET + bouton KBIS */}
          {c.client_pro && (
            <div className="pt-2 space-y-2.5">
              <Field label="Raison Sociale" value={c.client_rs} />
              <div className="flex items-end gap-3">
                <div className="flex-1">
                  <Field label="n° SIRET" value={c.client_siret} />
                </div>
                <button
                  onClick={onOpenKbis}
                  disabled={!kbisAvailable}
                  className="shrink-0 flex items-center gap-1.5 px-3 h-9 rounded border border-c-line hover:bg-c-brand-soft text-xs disabled:opacity-40 disabled:cursor-not-allowed"
                  title={kbisAvailable ? 'Voir le KBIS' : 'Aucun KBIS disponible'}
                >
                  <FileText className="w-3.5 h-3.5 text-c-ink-soft" />
                  KBIS
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bloc vendeur */}
      <div className="bg-white rounded-lg border border-c-line p-4">
        <h3 className="text-sm font-bold text-c-ink mb-3">Information Vendeur</h3>
        <div className="space-y-2.5 text-xs">
          <Field label="Nom" value={v.nom} />
          <Field label="Prénom" value={v.prenom} />
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <Field label="Mobile" value={v.gsm} muted={!data.is_my_call} />
            </div>
            <button
              disabled
              className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded border border-c-line text-xs text-c-ink-soft cursor-not-allowed"
              title="À venir (phase 3)"
            >
              <Phone className="w-3.5 h-3.5 text-green-600" />
              Démarrer l'appel
            </button>
          </div>
          {v.lib_affectation && (
            <div className="text-[10px] text-c-ink-faint mt-1">{v.lib_affectation}</div>
          )}
        </div>
      </div>
    </div>
  )
}

// --- Colonne centre : Panier ---------------------------------------------

function ColonneCentre({
  data,
  selectedId,
  onSelect,
}: {
  data: FicheData
  selectedId: string
  onSelect: (id: string) => void
}) {
  return (
    <div className="col-span-4 flex flex-col gap-3">
      <div className="bg-white rounded-lg border border-c-line overflow-hidden flex-1 flex flex-col">
        <div className="bg-gray-50 border-b border-c-line text-xs font-semibold text-c-ink-soft grid grid-cols-[80px_1fr_60px_70px]">
          <div className="px-2 py-2">Type</div>
          <div className="px-2 py-2">Lib Offre</div>
          <div className="px-2 py-2 text-center">Opt TV / PS5</div>
          <div className="px-2 py-2 text-center">Portabilité</div>
        </div>
        <div className="overflow-y-auto flex-1">
          {data.panier.length === 0 ? (
            <div className="p-4 text-center text-c-ink-faint italic text-xs">
              Aucune offre au panier
            </div>
          ) : (
            data.panier.map((p) => {
              const isSel = p.id === selectedId
              return (
                <div
                  key={p.id}
                  onClick={() => onSelect(p.id)}
                  className={`grid grid-cols-[80px_1fr_60px_70px] text-xs border-b border-c-line-soft cursor-pointer transition-colors ${
                    isSel ? 'bg-c-brand-soft' : 'hover:bg-gray-50'
                  }`}
                >
                  <div className="px-2 py-2 font-semibold">{p.type}</div>
                  <div className="px-2 py-2">{p.lib_offre}</div>
                  <div className="px-2 py-2 text-center">
                    {p.opt_tv ? <CheckCircle2 className="w-4 h-4 inline text-c-brand" /> : <Circle className="w-4 h-4 inline text-c-ink-faint/50" />}
                  </div>
                  <div className="px-2 py-2 text-center">
                    {p.portabilite ? <CheckCircle2 className="w-4 h-4 inline text-c-brand" /> : <Circle className="w-4 h-4 inline text-c-ink-faint/50" />}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Compteurs */}
      <div className="bg-white rounded-lg border border-c-line p-3 text-xs space-y-2">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <span className="text-c-ink-soft">nb Prod validé(s) : </span>
            <span className="font-bold text-c-ink">{data.nb_prod_valide}</span>
          </div>
          <div>
            <span className="text-c-ink-soft">nb Prod annulé(s) : </span>
            <span className="font-bold text-c-ink">{data.nb_prod_annule}</span>
          </div>
        </div>
        <div className="grid grid-cols-[80px_1fr] gap-2 items-center">
          <label className="text-c-ink-soft">Réf Appel :</label>
          <input
            type="text"
            value={data.vente.ref_appel}
            readOnly
            className="px-2 py-1 border border-c-line rounded text-xs bg-gray-50"
          />
        </div>
      </div>

      {/* Boutons d'action (grisés en phase 1) */}
      <div className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <ActionButton
            label="Valider le panier"
            disabled={!data.btn_valider_actif}
            variant="dark"
          />
          <ActionButton
            label="Annuler toute la vente"
            disabled={!data.btn_annuler_actif}
            variant="dark"
          />
        </div>
        <ActionButton label="Renvoyer le panier pour complément" disabled variant="orange" full />
      </div>
    </div>
  )
}

// --- Colonne droite : Détail offre + Vente -------------------------------

function ColonneDroite({
  data,
  offre,
  testEligImg,
  lettreAvailable,
  onOpenLettre,
}: {
  data: FicheData
  offre: FicheOffre | null
  testEligImg: string
  lettreAvailable: boolean
  onOpenLettre: () => void
}) {
  return (
    <div className="col-span-4 flex flex-col gap-4">
      {/* Détail offre sélectionnée */}
      <div className="bg-white rounded-lg border border-c-line p-4">
        {offre ? (
          <>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <input type="radio" checked={offre.portabilite} readOnly className="accent-c-brand" />
                <span className="text-sm font-semibold text-c-ink">Portabilité</span>
              </div>
              {offre.type === 'FIBRE' && !offre.portabilite && (
                <button
                  onClick={onOpenLettre}
                  disabled={!lettreAvailable}
                  className="px-3 py-1.5 rounded bg-orange-500 text-white text-xs font-semibold hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed"
                  title={lettreAvailable ? 'Ouvrir la Lettre de résiliation' : 'Aucune Lettre de résiliation trouvée'}
                >
                  Lettre de résil
                </button>
              )}
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Num à conserver" value={offre.num_portabilite} />
                <Field label="Code RIO" value={offre.num_rio} />
              </div>
              {offre.type === 'FIBRE' && (
                <Field label="Prise Optique" value={offre.num_prise_optique} />
              )}
              <div className="grid grid-cols-2 gap-3">
                <SelectField
                  label="Statut Vente"
                  value={offre.statut_prod}
                  options={data.statuts_vente.map((s) => ({ v: s.id, l: s.label }))}
                />
                <SelectField
                  label="Type Vente"
                  value={offre.type_vente}
                  options={[
                    { v: 0, l: 'Non défini' },
                    { v: 1, l: 'Conquête' },
                    { v: 2, l: 'Mig Mobile / Mig ADSL' },
                  ]}
                />
              </div>
              <Field label="Options Choisies" value={offre.opt_choisies} multi />
            </div>

            {/* Test d'éligibilité (FIBRE only) */}
            {offre.type === 'FIBRE' && (
              <div className="mt-3 pt-3 border-t border-c-line-soft">
                <div className="text-[11px] font-semibold text-c-ink-soft">
                  Test d'éligibilité réalisé par le vendeur
                </div>
                <div className="text-[10px] text-c-ink-faint italic mb-2">
                  Cliquez sur l'image pour agrandir
                </div>
                {testEligImg ? (
                  <img
                    src={testEligImg}
                    alt="Test d'éligibilité"
                    className="w-full max-h-[180px] object-contain rounded border border-c-line bg-gray-50 cursor-zoom-in"
                    title="Cliquer pour agrandir (à venir)"
                  />
                ) : (
                  <div className="w-full h-24 bg-gray-100 rounded border border-c-line flex items-center justify-center text-[10px] text-c-ink-faint italic">
                    Aucune image d'éligibilité
                  </div>
                )}
              </div>
            )}

            <button
              disabled
              className="mt-3 w-full py-2 rounded bg-gray-900 text-white text-xs font-semibold opacity-60 cursor-not-allowed"
              title="À venir (phase 2)"
            >
              Enregistrer les modifs Offre
            </button>
          </>
        ) : (
          <div className="text-xs text-c-ink-faint italic py-8 text-center">
            Sélectionne une offre du panier pour voir son détail
          </div>
        )}
      </div>

      {/* Bloc vente : Intervention vendeur / Mobile proposé / Info vente */}
      <div className="bg-white rounded-lg border border-c-line p-4">
        <div className="grid grid-cols-2 gap-3 mb-3 text-xs">
          <div>
            <div className="font-semibold text-c-ink mb-1">Intervention du vendeur :</div>
            <div className="flex gap-3">
              <Radio active={data.vente.intervention_vendeur} label="Oui" />
              <Radio active={!data.vente.intervention_vendeur} label="Non" />
            </div>
          </div>
          <div>
            <div className="font-semibold text-c-ink mb-1">Le vendeur a proposé un mobile :</div>
            <div className="flex gap-3">
              <Radio active={data.vente.mobile_propose_vendeur} label="Oui" />
              <Radio active={!data.vente.mobile_propose_vendeur} label="Non" />
            </div>
          </div>
        </div>

        <div className="space-y-1 text-xs">
          <label className="font-semibold text-c-ink">Info Vente</label>
          <textarea
            value={data.vente.info_vente}
            readOnly
            rows={3}
            className="w-full px-2 py-1.5 border border-c-line rounded text-xs bg-gray-50 resize-none"
          />
        </div>

        <button
          disabled
          className="mt-3 w-full py-2 rounded bg-gray-900 text-white text-xs font-semibold opacity-60 cursor-not-allowed"
          title="À venir (phase 2)"
        >
          Enregistrer les infos client et vente
        </button>
      </div>

      {/* Bloc anomalie mobile (si AnomalieMobile=1) */}
      {data.anomalie.active && (
        <div className="bg-blue-50 rounded-lg border border-blue-200 p-4">
          <h3 className="text-sm font-bold text-blue-700 mb-2">Vente mobile en différé</h3>
          <div className="space-y-2 text-xs">
            <Field label="Motif" value={String(data.anomalie.id_type || '')} />
            <Field label="Si Autre, Précisions" value={data.anomalie.info_cplt} multi />
            <div className="font-semibold text-blue-700 mt-2">Demande de dégroupage Panier</div>
          </div>
        </div>
      )}
    </div>
  )
}

// --- Helpers UI ----------------------------------------------------------

function Field({
  label,
  value,
  multi,
  muted,
}: {
  label: string
  value: string | number
  multi?: boolean
  muted?: boolean
}) {
  return (
    <div className="space-y-0.5">
      <label className="block text-c-ink-soft">{label}</label>
      {multi ? (
        <textarea
          value={String(value || '')}
          readOnly
          rows={2}
          className={`w-full px-2 py-1 border border-c-line rounded text-xs bg-gray-50 resize-none ${muted ? 'text-c-ink-faint italic' : ''}`}
        />
      ) : (
        <input
          type="text"
          value={String(value || '')}
          readOnly
          className={`w-full px-2 py-1 border border-c-line rounded text-xs bg-gray-50 ${muted ? 'text-c-ink-faint italic' : ''}`}
        />
      )}
    </div>
  )
}

function Radios({
  label,
  value,
  options,
}: {
  label: string
  value: number
  options: { v: number; l: string }[]
}) {
  return (
    <div className="flex items-center gap-4">
      <span className="text-c-ink-soft w-20">{label} :</span>
      {options.map((opt) => (
        <label key={opt.v} className="flex items-center gap-1 cursor-default">
          <input
            type="radio"
            checked={value === opt.v}
            readOnly
            className="accent-c-brand"
          />
          <span className="text-c-ink">{opt.l}</span>
        </label>
      ))}
    </div>
  )
}

function Toggle({ label, value }: { label: string; value: boolean }) {
  return (
    <div className="flex items-center gap-2 text-c-ink">
      <div
        className={`w-10 h-5 rounded-full p-0.5 flex items-center transition-colors ${
          value ? 'bg-green-500 justify-end' : 'bg-gray-300 justify-start'
        }`}
      >
        <div className="w-4 h-4 bg-white rounded-full shadow" />
      </div>
      <span className="flex-1">{label}</span>
    </div>
  )
}

function ProTab({ active, label }: { active: boolean; label: string }) {
  return (
    <div
      className={`flex-1 text-center text-xs font-semibold py-1.5 rounded ${
        active ? 'bg-white text-gray-900' : 'text-gray-300'
      }`}
    >
      {label}
    </div>
  )
}

function SelectField({
  label,
  value,
  options,
}: {
  label: string
  value: number
  options: { v: number; l: string }[]
}) {
  return (
    <div className="space-y-0.5">
      <label className="block text-c-ink-soft">{label}</label>
      <select
        value={value}
        disabled
        className="w-full px-2 py-1 border border-c-line rounded text-xs bg-gray-50 cursor-not-allowed"
      >
        {options.map((opt) => (
          <option key={opt.v} value={opt.v}>
            {opt.l}
          </option>
        ))}
      </select>
    </div>
  )
}

function ActionButton({
  label,
  disabled,
  variant,
  full,
}: {
  label: string
  disabled?: boolean
  variant: 'dark' | 'orange'
  full?: boolean
}) {
  const cls =
    variant === 'orange'
      ? 'bg-orange-500 text-white'
      : 'bg-gray-900 text-white'
  return (
    <button
      disabled={disabled}
      className={`${cls} ${full ? 'w-full' : ''} py-2 px-3 rounded text-xs font-semibold transition-opacity ${
        disabled ? 'opacity-50 cursor-not-allowed' : 'hover:brightness-110'
      }`}
      title={disabled ? 'Indisponible en lecture seule (phase 1)' : ''}
    >
      {label}
    </button>
  )
}

function Radio({ active, label }: { active: boolean; label: string }) {
  return (
    <label className="flex items-center gap-1 cursor-default">
      <input type="radio" checked={active} readOnly className="accent-c-brand" />
      <span>{label}</span>
    </label>
  )
}
