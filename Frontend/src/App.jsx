import { Routes, Route, useLocation } from "react-router-dom";
import HomePage from "./screens/homePage/HomePage";
import Dashboard from "./screens/dashboard/dashboard";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import ComingSoon from "./screens/comingSoon";
import Navbar from "./components/navbar/navbar";
import ContactUsPage from "./screens/homePage/contactUsPage";
import LoginPage from "./screens/login/loginPage";
import SignupPage from "./screens/login/signupPage";
import SignupSuccess from "./screens/login/signupSuccessScreen";

function App() {
  const location = useLocation();
  const hideNavbarRoutes = ["/login", "/signup", "/signup-success"];
  const shouldShowNavbar = !hideNavbarRoutes.includes(location.pathname);

  return (
    <>
      {shouldShowNavbar && <Navbar />}
      <div style={{ marginTop: shouldShowNavbar ? "80px" : "0" }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/signup-success" element={<SignupSuccess />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/contact" element={<ContactUsPage />} />
          <Route path="/comingSoon" element={<ComingSoon />} />
        </Routes>
      </div>
      <ToastContainer position="top-center" autoClose={3000} />
    </>
  );
}

export default App;
