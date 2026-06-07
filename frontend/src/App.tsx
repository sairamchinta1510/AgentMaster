import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { TopNav } from "./components/TopNav";
import { PipelinesPage } from "./pages/PipelinesPage";
import { DesignPage } from "./pages/DesignPage";
import { RunPage } from "./pages/RunPage";

function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col h-screen bg-[#0a0e1a] overflow-hidden">
      <TopNav />
      <main className="flex-1 overflow-hidden flex flex-col">
        {children}
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell><PipelinesPage /></AppShell>} />
        <Route path="/design/new" element={<Navigate to="/" replace />} />
        <Route path="/design/:pipelineId" element={<AppShell><DesignPage /></AppShell>} />
        <Route path="/run/:pipelineId" element={<AppShell><RunPage /></AppShell>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
