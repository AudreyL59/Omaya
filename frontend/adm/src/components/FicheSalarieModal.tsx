import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  User,
  MapPin,
  FileText,
  Loader2,
  FileDown,
  X,
  ExternalLink,
} from 'lucide-react'
import { getToken } from '@/api'

interface Identite {
  id_salarie: number
  civilite: number
  nom: string
  nom_marital: string
  prenom: string
  sexe: string
  nationalite: string
  date_naiss: string
  lieu_naiss: string
  dep_naiss: number
  num_ss: string
  cpam: string
  num_cin: string
  situation_fam: number
  avec_enfant: boolean
  nb_enfants: number
  travailleur_handi: boolean
  photo: string
}

interface Coordonnees {
  adresse1: string
  adresse2: string
  cp: string
  ville: string
  tel_fixe: string
  tel_mob: string
  mail: string
  mail2: string
  urg_nom: string
  urg_lien: string
  urg_tel: string
  iban: string
  bic: string
}

interface FicheData {
  identite: Identite
  coordonnees: Coordonnees
}

interface DocumentItem {
  nom: string
  taille_mo: number
  date: string
  url: string
}

const SITUATION_FAM: Record<number, string> = {
  0: '',
  1: 'Célibataire',
  2: 'Marié(e)',
  3: 'Pacsé(e)',
  4: 'Divorcé(e)',
  5: 'Veuf(ve)',
  6: 'Concubinage',
}

const CIVILITE: Record<number, string> = { 0: '', 1: 'Mr', 2: 'Mme' }

function Field({
  label,
  value,
}: {
  label: string
  value: string | number | boolean
}) {
  const display =
    typeof value === 'boolean'
      ? value
        ? 'Oui'
        : 'Non'
      : String(value || '—')
  return (
    <div>
      <p className="text-xs font-medium text-[#A68D8A]/80 uppercase tracking-wide">
        {label}
      </p>
      <p className="text-sm text-[#4E1D17] mt-0.5">{display}</p>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
        active
          ? 'bg-[#17494E] text-white shadow-sm'
          : 'text-[#A68D8A] hover:bg-[#EFE9E7] hover:text-[#4E1D17]'
      }`}
    >
      {icon}
      {label}
    </button>
  )
}

export default function FicheSalarieModal({
  idSalarie,
  nom,
  prenom,
  onClose,
}: {
  idSalarie: string
  nom: string
  prenom: string
  onClose: () => void
}) {
  const [data, setData] = useState<FicheData | null>(null)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [docsLoading, setDocsLoading] = useState(false)
  const [docsFetched, setDocsFetched] = useState(false)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<
    'identite' | 'coordonnees' | 'documents'
  >('identite')
  const [previewDoc, setPreviewDoc] = useState<DocumentItem | null>(null)

  useEffect(() => {
    fetch(`/api/adm/mon-compte/fiche/${idSalarie}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((res) => res.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [idSalarie])

  useEffect(() => {
    if (activeTab !== 'documents' || docsFetched || docsLoading) return
    setDocsLoading(true)
    fetch(`/api/adm/mon-compte/fiche/${idSalarie}/documents`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((res) => res.json())
      .then((docs: DocumentItem[]) => setDocuments(Array.isArray(docs) ? docs : []))
      .catch(() => {})
      .finally(() => {
        setDocsLoading(false)
        setDocsFetched(true)
      })
  }, [activeTab, docsFetched, docsLoading, idSalarie])

  const id = data?.identite
  const co = data?.coordonnees

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl h-[92vh] flex flex-col overflow-hidden"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5DDDC]">
          <div>
            <h2 className="text-lg font-bold text-[#4E1D17]">
              Fiche Salarié — {nom} {prenom}
            </h2>
            <p className="text-xs text-[#A68D8A]/80 mt-0.5">
              Informations personnelles
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-[#A68D8A]/80 hover:bg-[#EFE9E7] hover:text-[#4E1D17] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 pt-4 pb-3 border-b border-[#E5DDDC] flex gap-2">
          <TabButton
            active={activeTab === 'identite'}
            onClick={() => setActiveTab('identite')}
            icon={<User className="w-4 h-4" />}
            label="Identité"
          />
          <TabButton
            active={activeTab === 'coordonnees'}
            onClick={() => setActiveTab('coordonnees')}
            icon={<MapPin className="w-4 h-4" />}
            label="Coordonnées"
          />
          <TabButton
            active={activeTab === 'documents'}
            onClick={() => setActiveTab('documents')}
            icon={<FileText className="w-4 h-4" />}
            label="Documents"
          />
        </div>

        <div className="flex-1 overflow-auto p-6 bg-white">
          {loading ? (
            <div className="flex items-center justify-center py-24">
              <Loader2 className="w-8 h-8 text-[#E5DDDC] animate-spin" />
            </div>
          ) : !data || !id || !co ? (
            <div className="text-center py-24 text-[#A68D8A]/80 text-sm italic">
              Impossible de charger la fiche
            </div>
          ) : (
            <AnimatePresence mode="wait">
              {activeTab === 'identite' && (
                <motion.div
                  key="identite"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="bg-white rounded-[10px] border border-[#E5DDDC] p-6 flex gap-8">
                    <div className="shrink-0">
                      {id.photo ? (
                        <img
                          src={`data:image/png;base64,${id.photo}`}
                          alt="Photo"
                          className="w-28 h-28 rounded-[10px] object-cover"
                        />
                      ) : (
                        <div className="w-28 h-28 rounded-[10px] bg-[#EFE9E7] flex items-center justify-center">
                          <User className="w-10 h-10 text-[#E5DDDC]" />
                        </div>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-x-12 gap-y-4 flex-1">
                      <Field
                        label="Civilité"
                        value={CIVILITE[id.civilite] || ''}
                      />
                      <Field
                        label="Sexe"
                        value={
                          id.sexe === 'F'
                            ? 'Féminin'
                            : id.sexe === 'M'
                              ? 'Masculin'
                              : id.sexe
                        }
                      />
                      <Field label="Nom" value={id.nom} />
                      <Field label="Nom marital" value={id.nom_marital} />
                      <Field label="Prénom" value={id.prenom} />
                      <Field label="Nationalité" value={id.nationalite} />
                    </div>
                  </div>

                  <div className="bg-white rounded-[10px] border border-[#E5DDDC] p-6 mt-4">
                    <h3 className="text-sm font-semibold text-[#4E1D17] mb-4">
                      Naissance
                    </h3>
                    <div className="grid grid-cols-3 gap-x-12 gap-y-4">
                      <Field label="Date de naissance" value={id.date_naiss} />
                      <Field label="Lieu de naissance" value={id.lieu_naiss} />
                      <Field label="Département" value={id.dep_naiss || ''} />
                    </div>
                  </div>

                  <div className="bg-white rounded-[10px] border border-[#E5DDDC] p-6 mt-4">
                    <h3 className="text-sm font-semibold text-[#4E1D17] mb-4">
                      Informations administratives
                    </h3>
                    <div className="grid grid-cols-3 gap-x-12 gap-y-4">
                      <Field label="N° Sécurité Sociale" value={id.num_ss} />
                      <Field label="CPAM" value={id.cpam} />
                      <Field label="N° CIN" value={id.num_cin} />
                      <Field
                        label="Situation familiale"
                        value={SITUATION_FAM[id.situation_fam] || ''}
                      />
                      <Field label="Avec enfant" value={id.avec_enfant} />
                      <Field label="Nombre d'enfants" value={id.nb_enfants} />
                      <Field
                        label="Travailleur handicapé"
                        value={id.travailleur_handi}
                      />
                    </div>
                  </div>
                </motion.div>
              )}

              {activeTab === 'coordonnees' && (
                <motion.div
                  key="coordonnees"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="bg-white rounded-[10px] border border-[#E5DDDC] p-6">
                    <h3 className="text-sm font-semibold text-[#4E1D17] mb-4">
                      Coordonnées postales et téléphoniques
                    </h3>
                    <div className="grid grid-cols-2 gap-x-12 gap-y-4">
                      <Field label="Adresse" value={co.adresse1} />
                      <Field label="Tél Fixe" value={co.tel_fixe} />
                      <Field label="Complément" value={co.adresse2} />
                      <Field label="Tél Mobile" value={co.tel_mob} />
                      <div className="flex gap-4">
                        <div className="w-24">
                          <Field label="Code Postal" value={co.cp} />
                        </div>
                        <div className="flex-1">
                          <Field label="Ville" value={co.ville} />
                        </div>
                      </div>
                      <Field label="Courriel" value={co.mail} />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mt-4">
                    <div className="bg-white rounded-[10px] border border-[#E5DDDC] p-6">
                      <h3 className="text-sm font-semibold text-[#4E1D17] mb-4">
                        Personne à contacter en cas d'urgence
                      </h3>
                      <div className="space-y-4">
                        <Field label="Nom du contact" value={co.urg_nom} />
                        <Field label="Lien de parenté" value={co.urg_lien} />
                        <Field label="Téléphone" value={co.urg_tel} />
                      </div>
                    </div>

                    <div className="bg-white rounded-[10px] border border-[#E5DDDC] p-6">
                      <h3 className="text-sm font-semibold text-[#4E1D17] mb-4">
                        Coordonnées bancaires
                      </h3>
                      <div className="space-y-4">
                        <Field label="IBAN" value={co.iban} />
                        <Field label="BIC" value={co.bic} />
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {activeTab === 'documents' && (
                <motion.div
                  key="documents"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="bg-white rounded-[10px] border border-[#E5DDDC] p-6">
                    <h3 className="text-sm font-semibold text-[#4E1D17] mb-4">
                      Fiches de salaire
                    </h3>
                    {docsLoading ? (
                      <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-6 h-6 text-[#E5DDDC] animate-spin" />
                      </div>
                    ) : documents.length === 0 ? (
                      <p className="text-[#A68D8A]/80 text-sm py-8 text-center">
                        Aucun document
                      </p>
                    ) : (
                      <>
                        <p className="text-xs text-[#A68D8A]/80 mb-2">
                          {documents.length} document
                          {documents.length > 1 ? 's' : ''}
                        </p>
                        <div className="max-h-[500px] overflow-y-auto border border-[#E5DDDC] rounded-lg">
                          <table className="w-full text-sm">
                            <thead className="sticky top-0 bg-white z-10">
                              <tr className="border-b border-[#E5DDDC]">
                                <th className="text-left py-2 px-3 text-[#A68D8A] font-medium">
                                  Nom
                                </th>
                                <th className="text-right py-2 px-3 text-[#A68D8A] font-medium w-24">
                                  Taille
                                </th>
                                <th className="text-right py-2 px-3 text-[#A68D8A] font-medium w-32">
                                  Date
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {documents.map((doc, i) => (
                                <tr
                                  key={i}
                                  onClick={() => setPreviewDoc(doc)}
                                  className="border-b border-gray-50 last:border-0 hover:bg-blue-50 transition-colors cursor-pointer"
                                >
                                  <td className="py-2.5 px-3">
                                    <div className="flex items-center gap-2">
                                      <FileDown className="w-4 h-4 text-[#E5DDDC] shrink-0" />
                                      <span className="text-[#4E1D17] truncate">
                                        {doc.nom}
                                      </span>
                                    </div>
                                  </td>
                                  <td className="py-2.5 px-3 text-right text-[#A68D8A]">
                                    {doc.taille_mo} Mo
                                  </td>
                                  <td className="py-2.5 px-3 text-right text-[#A68D8A]">
                                    {doc.date}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          )}
        </div>

        <AnimatePresence>
          {previewDoc && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setPreviewDoc(null)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4"
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden"
              >
                <div className="flex items-center justify-between px-5 py-3 border-b border-[#E5DDDC]">
                  <div className="flex items-center gap-3 min-w-0">
                    <FileDown className="w-5 h-5 text-[#A68D8A]/80 shrink-0" />
                    <h3 className="text-sm font-semibold text-[#4E1D17] truncate">
                      {previewDoc.nom}
                    </h3>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <a
                      href={previewDoc.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 rounded-lg text-[#A68D8A] hover:bg-[#EFE9E7] hover:text-[#4E1D17] transition-colors"
                      title="Ouvrir dans un nouvel onglet"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                    <button
                      onClick={() => setPreviewDoc(null)}
                      className="p-2 rounded-lg text-[#A68D8A] hover:bg-[#EFE9E7] hover:text-[#4E1D17] transition-colors"
                      title="Fermer"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="flex-1 bg-white">
                  {/[.](png|jpe?g|gif|webp|bmp|svg)$/i.test(previewDoc.nom) ? (
                    <div className="w-full h-full flex items-center justify-center p-4">
                      <img
                        src={previewDoc.url}
                        alt={previewDoc.nom}
                        className="max-w-full max-h-full object-contain"
                      />
                    </div>
                  ) : (
                    <iframe
                      src={previewDoc.url}
                      title={previewDoc.nom}
                      className="w-full h-full border-0"
                    />
                  )}
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  )
}
