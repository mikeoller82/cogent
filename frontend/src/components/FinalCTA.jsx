import React from "react";
import { ArrowRight, Shield } from "lucide-react";

const FinalCTA = () => {
  return (
    <section id="cta" className="relative py-24 circuit-bg">
      <div className="max-w-[900px] mx-auto px-6 lg:px-10 text-center relative z-10">
        <div className="card-grad rounded-3xl border border-[#f5ede0]/8 p-12 lg:p-16">
          <p className="tiny-label">• Get Started</p>
          <h2 className="mt-5 text-[40px] lg:text-[56px] leading-[1.02] tracking-[-0.035em] font-medium text-[#f5ede0]">
            Ready for a{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#b5a8f5] to-[#a78bfa]">
              governed
            </span>{" "}
            AI coworker?
          </h2>
          <p className="mt-5 text-[16px] text-[#a8a092] max-w-[560px] mx-auto">
            Install Cogent in two minutes. Connect your tools, set your risk budget, and
            start shipping real work with governance on every action.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <a
              href="/app"
              className="group inline-flex items-center gap-2 px-8 py-4 rounded-md btn-cream hover:scale-[1.02] transition-transform"
            >
              Try Cogent Free
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </a>
            <a
              href="#paper"
              className="inline-flex items-center gap-2 px-8 py-4 rounded-md btn-outline hover:scale-[1.02] transition-transform"
            >
              Read the paper
            </a>
          </div>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-6 text-[12px] text-[#8a8278] font-mono">
            <span className="flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-[#22c55e]" /> Governed execution
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#b5a8f5]" /> 350+ MCP tools
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#60a5fa]" /> Persistent memory
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default FinalCTA;
