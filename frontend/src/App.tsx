import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import NursePage   from "./pages/NursePage";
import QueuePage   from "./pages/QueuePage";
import ConsultPage from "./pages/ConsultPage";
import EvalPage    from "./pages/EvalPage";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/"        element={<Navigate to="/intake" replace />} />
        <Route path="/intake"  element={<NursePage />} />
        <Route path="/queue"   element={<QueuePage />} />
        <Route path="/consult" element={<ConsultPage />} />
        <Route path="/eval"    element={<EvalPage />} />
      </Routes>
    </Router>
  );
}