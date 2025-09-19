import { Routes, Route } from "react-router-dom";
import HomePage from "./screens/homePage/HomePage";
import Dashboard from "./screens/dashboard/dashboard";

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/dashboard" element={<Dashboard />} />
    </Routes>
  );
}

export default App;
