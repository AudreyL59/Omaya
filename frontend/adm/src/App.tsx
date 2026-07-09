import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import PlaceholderPage from '@/pages/PlaceholderPage'
import StatRHPage from '@/pages/StatRHPage'
import StatRHRdvPage from '@/pages/StatRHRdvPage'
import StatRHEntreeSortiePage from '@/pages/StatRHEntreeSortiePage'
import StatRHSaisieCvPage from '@/pages/StatRHSaisieCvPage'
import StatRHAnnonceursPage from '@/pages/StatRHAnnonceursPage'
import AgendaRecrutementPage from '@/pages/AgendaRecrutementPage'
import OrganigrammePage from '@/pages/OrganigrammePage'
import RecherchePage from '@/pages/RecherchePage'
import RegistreRHPage from '@/pages/RegistreRHPage'
import DpaeRecherchePage from '@/pages/DpaeRecherchePage'
import DpaeNouvellePage from '@/pages/DpaeNouvellePage'
import CttTravailPage from '@/pages/CttTravailPage'
import ParcAutoPage from '@/pages/ParcAutoPage'
import DocUleasePage from '@/pages/DocUleasePage'
import RechercheUleasePage from '@/pages/RechercheUleasePage'
import FormationsIAGPage from '@/pages/FormationsIAGPage'
import SuiviMutuellePage from '@/pages/SuiviMutuellePage'
import ParametresRHPage from '@/pages/ParametresRHPage'
import RechercheCVPageAdm from '@/pages/RechercheCVPage'
import RechercheCvMotsClesPageAdm from '@/pages/RechercheCvMotsClesPage'
import LieuxRDVPageAdm from '@/pages/LieuxRDVPage'
import SaisieCVPage from '@/pages/SaisieCVPage'
import PrevRecPageAdm from '@/pages/PrevRecPage'
import CvPresaisisPageAdm from '@/pages/CvPresaisisPage'
import VillesFavoritesPageAdm from '@/pages/VillesFavoritesPage'
import RechercheVillePage from '@/pages/RechercheVillePage'
import ListeSocietePage from '@/pages/ListeSocietePage'
import ListeDocCourtagePage from '@/pages/ListeDocCourtagePage'
import SuiviDistribPage from '@/pages/SuiviDistribPage'
import SuiviDistribRappelPage from '@/pages/SuiviDistribRappelPage'
import GestionExoCashPage from '@/pages/GestionExoCashPage'
import ModulePaiesPage from '@/pages/ModulePaiesPage'
import FichesSalairePage from '@/pages/FichesSalairePage'
import ExportTRPage from '@/pages/ExportTRPage'
import TableauxDiversPage from '@/pages/TableauxDiversPage'
import GestionPodiumPage from '@/pages/GestionPodiumPage'
import CalculPointsPage from '@/pages/CalculPointsPage'
import TableauSalariePage from '@/pages/TableauSalariePage'
import SmsPerfPage from '@/pages/SmsPerfPage'
import ScoolFormationsPage from '@/pages/ScoolFormationsPage'
import ScoolFormationFichePage from '@/pages/ScoolFormationFichePage'
import ScoolPlanningPage from '@/pages/ScoolPlanningPage'
import ScoolFormModelesPage from '@/pages/ScoolFormModelesPage'
import ScoolBulletinPage from '@/pages/ScoolBulletinPage'
import GestionRecruteursPageAdm from '@/pages/GestionRecruteursPage'
import ParametresCVPage from '@/pages/ParametresCVPage'
import ImportsHubPage from '@/pages/ImportsHubPage'
import ImportEniPage from '@/pages/ImportEniPage'
import ImportIagPage from '@/pages/ImportIagPage'
import ImportOenPage from '@/pages/ImportOenPage'
import ImportProPage from '@/pages/ImportProPage'
import ImportSfrPage from '@/pages/ImportSfrPage'
import ImportStrPage from '@/pages/ImportStrPage'
import ImportValPage from '@/pages/ImportValPage'
import ImportMassePage from '@/pages/ImportMassePage'
import ImportAjoutColonnePage from '@/pages/ImportAjoutColonnePage'
import ImportNotationPage from '@/pages/ImportNotationPage'
import SuiviFacturesPage from '@/pages/SuiviFacturesPage'
import SuiviSfrPage from '@/pages/SuiviSfrPage'
import SuiviEnergiePage from '@/pages/SuiviEnergiePage'
import EnergieExtractionPage from '@/pages/EnergieExtractionPage'
import EnergieTicketCallPage from '@/pages/EnergieTicketCallPage'
import SfrCttsARaccorderPage from '@/pages/SfrCttsARaccorderPage'
import SfrRemunerationsPage from '@/pages/SfrRemunerationsPage'
import SfrTicketCallPage from '@/pages/SfrTicketCallPage'
import SfrExtractionPage from '@/pages/SfrExtractionPage'
import SfrParcoursChainesPage from '@/pages/SfrParcoursChainesPage'
import SfrClusterPage from '@/pages/SfrClusterPage'
import SfrOffresEzyPage from '@/pages/SfrOffresEzyPage'
import SfrRdvTechPage from '@/pages/SfrRdvTechPage'
import SfrExtractionEtpPage from '@/pages/SfrExtractionEtpPage'
import ProductionPage from '@shared/production/ProductionPage'
import ProductionDetailPage from '@shared/production/ProductionDetailPage'
import AdmTicketsPage from '@/pages/AdmTicketsPage'
import Layout from '@/components/Layout'
import ProtectedRoute from '@/components/ProtectedRoute'
import { DialogHost } from '@shared/ui/dialog'

const BASENAME = import.meta.env.BASE_URL.replace(/\/$/, '')
const ADM_API = '/api/adm'

function App() {
  return (
    <BrowserRouter basename={BASENAME}>
      <DialogHost />
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="agenda-recrutement" element={<AgendaRecrutementPage />} />
          <Route path="envois-sms" element={<PlaceholderPage />} />
          <Route path="factures" element={<SuiviFacturesPage />} />
          <Route path="suivi-sfr" element={<SuiviSfrPage />} />
          <Route path="suivi-energie" element={<SuiviEnergiePage />} />
          <Route path="suivi-energie/extraction" element={<EnergieExtractionPage />} />
          <Route path="suivi-energie/ticket-call" element={<EnergieTicketCallPage />} />
          <Route path="suivi-sfr/ctts-a-raccorder" element={<SfrCttsARaccorderPage />} />
          <Route path="suivi-sfr/remunerations" element={<SfrRemunerationsPage />} />
          <Route path="suivi-sfr/ticket-call" element={<SfrTicketCallPage />} />
          <Route path="suivi-sfr/extraction" element={<SfrExtractionPage />} />
          <Route path="suivi-sfr/parcours-chaines" element={<SfrParcoursChainesPage />} />
          <Route path="suivi-sfr/cluster" element={<SfrClusterPage />} />
          <Route path="suivi-sfr/offres-ezy" element={<SfrOffresEzyPage />} />
          <Route path="suivi-sfr/rdv-tech" element={<SfrRdvTechPage />} />
          <Route path="suivi-sfr/extraction-etp" element={<SfrExtractionEtpPage />} />
          <Route path="recherche-rh" element={<PlaceholderPage />} />
          <Route path="stat-rh" element={<StatRHPage />} />
          <Route path="stat-rh/saisie-cv" element={<StatRHSaisieCvPage />} />
          <Route path="stat-rh/rdv" element={<StatRHRdvPage />} />
          <Route path="stat-rh/dpae-sortie" element={<StatRHEntreeSortiePage />} />
          <Route path="stat-rh/annonceurs" element={<StatRHAnnonceursPage />} />
          <Route path="stat-adv" element={<PlaceholderPage />} />
          <Route path="organigramme" element={<OrganigrammePage />} />
          <Route path="recherche" element={<RecherchePage />} />
          <Route path="salaries/registre" element={<RegistreRHPage />} />
          <Route path="salaries/dpae" element={<DpaeRecherchePage />} />
          <Route path="salaries/dpae/nouvelle" element={<DpaeNouvellePage />} />
          <Route path="salaries/contrats" element={<CttTravailPage />} />
          <Route path="ulease/parc-auto" element={<ParcAutoPage />} />
          <Route path="ulease/documents" element={<DocUleasePage />} />
          <Route path="ulease/recherche" element={<RechercheUleasePage />} />
          <Route path="salaries/formations-iag" element={<FormationsIAGPage />} />
          <Route path="salaries/mutuelle" element={<SuiviMutuellePage />} />
          <Route path="salaries/parametres" element={<ParametresRHPage />} />
          <Route path="recrutement/recherche-cv" element={<RechercheCVPageAdm />} />
          <Route path="recrutement/recherche-cv-kw" element={<RechercheCvMotsClesPageAdm />} />
          <Route path="recrutement/lieu-rdv" element={<LieuxRDVPageAdm />} />
          <Route path="recrutement/saisie-cv" element={<SaisieCVPage />} />
          <Route path="recrutement/prevision" element={<PrevRecPageAdm />} />
          <Route path="recrutement/cv-presaisis" element={<CvPresaisisPageAdm />} />
          <Route path="recrutement/villes" element={<VillesFavoritesPageAdm />} />
          <Route path="villes" element={<RechercheVillePage />} />
          <Route path="societes" element={<ListeSocietePage />} />
          <Route path="contrats-courtage" element={<ListeDocCourtagePage />} />
          <Route path="distributeurs" element={<SuiviDistribPage />} />
          <Route path="distributeurs/documents" element={<SuiviDistribRappelPage />} />
          <Route path="comm/exo-cash" element={<GestionExoCashPage />} />
          <Route path="paies" element={<ModulePaiesPage />} />
          <Route path="paies/fiches" element={<FichesSalairePage />} />
          <Route path="paies/export-tr" element={<ExportTRPage />} />
          <Route path="paies/tableaux-divers" element={<TableauxDiversPage />} />
          <Route path="comm/podium" element={<GestionPodiumPage />} />
          <Route path="paies/points" element={<CalculPointsPage />} />
          <Route path="paies/tableau-salarie" element={<TableauSalariePage />} />
          <Route path="comm/sms-perf" element={<SmsPerfPage />} />
          <Route path="scool/formations" element={<ScoolFormationsPage />} />
          <Route path="scool/formations/:id" element={<ScoolFormationFichePage />} />
          <Route path="scool/planning" element={<ScoolPlanningPage />} />
          <Route path="scool/modeles" element={<ScoolFormModelesPage />} />
          <Route path="scool/formations/:id_formation/bulletin/:id_bulletin"
                 element={<ScoolBulletinPage />} />
          <Route path="scool/formations/:id_formation/bulletin/nouveau"
                 element={<ScoolBulletinPage />} />
          <Route path="recrutement/recruteurs" element={<GestionRecruteursPageAdm />} />
          <Route path="recrutement/parametres" element={<ParametresCVPage />} />
          <Route path="imports/contrats" element={<ImportsHubPage />} />
          <Route path="imports/eni" element={<ImportEniPage />} />
          <Route path="imports/iag" element={<ImportIagPage />} />
          <Route path="imports/oen" element={<ImportOenPage />} />
          <Route path="imports/pro" element={<ImportProPage />} />
          <Route path="imports/sfr" element={<ImportSfrPage />} />
          <Route path="imports/str" element={<ImportStrPage />} />
          <Route path="imports/val" element={<ImportValPage />} />
          <Route path="imports/masse" element={<ImportMassePage />} />
          <Route path="imports/colonnes" element={<ImportAjoutColonnePage />} />
          <Route path="imports/notations" element={<ImportNotationPage />} />
          <Route path="production" element={<ProductionPage apiBase={ADM_API} />} />
          <Route path="production/jobs/:id" element={<ProductionDetailPage apiBase={ADM_API} />} />
          <Route path="tickets" element={<AdmTicketsPage />} />
          {/* Fallback : toute route inconnue dans le shell auth → Placeholder */}
          <Route path="*" element={<PlaceholderPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
