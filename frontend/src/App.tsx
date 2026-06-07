import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Home } from "./pages/Home";
import { Session } from "./pages/Session";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/session/:sessionId" element={<Session />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
