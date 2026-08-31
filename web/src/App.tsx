import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import AllSectorsDashboard from "./pages/AllSectorsDashboard";
import NiftyBenchmarkPage from "./pages/NiftyBenchmarkPage";
import Questionnaire from "./pages/Questionnaire";
import Recommendations from "./pages/Recommendations";
import SectorDashboard from "./pages/SectorDashboard";
import SectorRankingPage from "./pages/SectorRankingPage";
import StockDetail from "./pages/StockDetail";
import UniversePage from "./pages/UniversePage";

const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 60_000, retry: 1 } },
});

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Questionnaire />} />
            <Route path="universe" element={<UniversePage />} />
            <Route path="recommendations" element={<Recommendations />} />
            <Route path="sectors" element={<AllSectorsDashboard />} />
            <Route path="sectors/:sector" element={<SectorDashboard />} />
            <Route path="sector-ranking" element={<SectorRankingPage />} />
            <Route path="nifty-benchmark" element={<NiftyBenchmarkPage />} />
            <Route path="banking" element={<Navigate to="/sectors/banking" replace />} />
            <Route path="it" element={<Navigate to="/sectors/it" replace />} />
            <Route path="stock/:ticker" element={<StockDetail />} />
            <Route path="*" element={<Navigate to="/universe" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
