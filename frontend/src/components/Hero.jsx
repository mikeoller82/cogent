import React from "react";
import { FileText, CreditCard, Shield } from "lucide-react";
import { builtByLogos, backedByLogos } from "../mock";

const Hero = () => {
  return (
    <section className="relative pt-[140px] pb-20 topo-bg overflow-hidden">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="flex flex-col items-center text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#1d1813] border border-[#f5ede0]/10 text-[12px] text-[#d8d0c2] font-mono">
            <span>🇺🇸</span>
            Cogent speaks English
          </div>

          <h1 className="mt-7 text-[64px] md:text-[96px] leading-[0.95] tracking-[-0.04em] font-medium text-[#f5ede0]">
            Hire the agent. <span className="font-serif-i text-[#f5ede0]">Keep the work.</span>
          </h1>

          <p className="mt-7 max-w-[620px] text-[18px] leading-[1.5] text-[#b8b0a2]">
            Cogent is an AI coworker that lives where your team does. It plugs into your stack, runs real tasks end-to-end, and ships the output — reports, dashboards, code, campaigns.
          </p>

          <a
            href="/app"
            className="mt-10 group btn-cream inline-flex items-center gap-3 px-7 py-4 rounded-md hover:scale-[1.02] transition-transform"
          >
            Try Cogent Now
            <svg width="18" height="18" viewBox="0 0 32 32" fill="none">
              <path d="M4 16 Q 16 4, 28 16" stroke="#15110d" strokeWidth="2.4" strokeLinecap="round" fill="none" />
              <path d="M4 16 Q 16 28, 28 16" stroke="#15110d" strokeWidth="2.4" strokeLinecap="round" fill="none" />
              <circle cx="16" cy="16" r="2.4" fill="#15110d" />
            </svg>
          </a>

          <div className="mt-7 flex flex-wrap items-center justify-center gap-6 text-[12px] text-[#a8a092] font-mono uppercase tracking-wider">
            <span className="inline-flex items-center gap-2">
              <CreditCard className="w-3.5 h-3.5" /> $100 in free credits
            </span>
            <span className="inline-flex items-center gap-2">
              <FileText className="w-3.5 h-3.5" /> No credit card required
            </span>
            <span className="inline-flex items-center gap-2">
              <Shield className="w-3.5 h-3.5" /> SOC2 Compliant
            </span>
          </div>
        </div>

        <div className="mt-24 grid grid-cols-1 lg:grid-cols-[1fr_auto_1fr] gap-10 items-center">
          <div>
            <p className="tiny-label mb-5">Built by engineers from:</p>
            <div className="grid grid-cols-5 gap-3">
              {builtByLogos.map((l) => (
                <div
                  key={l.name}
                  className="h-14 rounded-md border border-[#f5ede0]/10 flex items-center justify-center text-[#d8d0c2] text-[14px] font-medium hover:border-[#f5ede0]/25 transition-colors"
                >
                  {l.text}
                </div>
              ))}
            </div>
          </div>

          <div className="hidden lg:block w-px h-16 bg-[#f5ede0]/10" />

          <div>
            <p className="tiny-label mb-5">Backed by:</p>
            <div className="grid grid-cols-2 gap-3 max-w-[280px]">
              {backedByLogos.map((l) => (
                <div
                  key={l.name}
                  className="h-14 rounded-md border border-[#f5ede0]/10 flex items-center justify-center text-[#d8d0c2] text-[14px] font-medium hover:border-[#f5ede0]/25 transition-colors"
                >
                  {l.text}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
