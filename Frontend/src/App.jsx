import { Routes, Route } from "react-router-dom";
import HomePage from "./screens/homePage/HomePage";
import Dashboard from "./screens/dashboard/dashboard";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
      <ToastContainer position="top-center" autoClose={3000} />
    </>
  );
}

export default App;
