import { Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import PlanPage from "./pages/PlanPage";
import HistoryPage from "./pages/HistoryPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/history" element={<HistoryPage />} />
      <Route path="/plan" element={<PlanPage />} />
      <Route path="/plan/:planId" element={<PlanPage />} />
    </Routes>
  );
}
