import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Hero from "./components/Hero";
import Features from "./components/Features";
import Shift from "./components/Shift";
import Testimonials from "./components/Testimonials";
import Solution from "./components/Solution";
import HowItWorks from "./components/HowItWorks";
import UseCases from "./components/UseCases";
import InternetLoves from "./components/InternetLoves";
import AskAI from "./components/AskAI";
import FAQ from "./components/FAQ";
import FinalCTA from "./components/FinalCTA";
import Footer from "./components/Footer";
import { Toaster } from "./components/ui/sonner";

function Landing() {
  return (
    <div className="App">
      <Navbar />
      <Hero />
      <Features />
      <Shift />
      <Testimonials />
      <Solution />
      <HowItWorks />
      <UseCases />
      <InternetLoves />
      <AskAI />
      <FAQ />
      <FinalCTA />
      <Footer />
      <Toaster theme="dark" />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
