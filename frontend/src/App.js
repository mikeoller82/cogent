import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Hero from "./components/Hero";
import LoopEngineering from "./components/LoopEngineering";
import Features from "./components/Features";
import HowItWorks from "./components/HowItWorks";
import UseCases from "./components/UseCases";
import PaperShowcase from "./components/PaperShowcase";
import InternetLoves from "./components/InternetLoves";
import FAQ from "./components/FAQ";
import FinalCTA from "./components/FinalCTA";
import Footer from "./components/Footer";
import ChatApp from "./chat/ChatApp";
import { Toaster } from "./components/ui/sonner";

function Landing() {
  return (
    <div className="App scanline">
      <Navbar />
      <Hero />
      <LoopEngineering />
      <Features />
      <HowItWorks />
      <UseCases />
      <PaperShowcase />
      <InternetLoves />
      <FAQ />
      <FinalCTA />
      <Footer />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app/*" element={<ChatApp />} />
      </Routes>
      <Toaster theme="dark" />
    </BrowserRouter>
  );
}

export default App;
