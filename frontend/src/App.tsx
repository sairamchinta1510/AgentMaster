import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { NewPipelinePage } from "./pages/NewPipelinePage";
import { DesignPage } from "./pages/DesignPage";
import { RunPage } from "./pages/RunPage";

function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-950 overflow-hidden">
      <Sidebar />
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
        <Route
          path="/"
          element={
            <AppShell>
              <NewPipelinePage />
            </AppShell>
          }
        />
        <Route
          path="/design/new"
          element={<Navigate to="/" replace />}
        />
        <Route
          path="/design/:pipelineId"
          element={
            <AppShell>
              <DesignPage />
            </AppShell>
          }
        />
        <Route
          path="/run/:pipelineId"
          element={
            <AppShell>
              <RunPage />
            </AppShell>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
