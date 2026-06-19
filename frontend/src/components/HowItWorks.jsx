import React from "react";
import { Plug, Target, GitBranch, Ship } from "lucide-react";
import { howSteps } from "../mock";

const icons = [Plug, Target, GitBranch, Ship];

const HowItWorks = () => {
  return (
    <section id="how" className="relative py-24 circuit-bg">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 relative z-10">
        <div className="text-center mb-16">
          <p className="tiny-label">• How It Works</p>
          <h2 className="mt-5 text-[44px] lg:text-[64px] leading-[1.02] tracking-[-0.035em] font-medium text-[#f5ede0] max-w-[900px] mx-auto">
            From connect to{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#b5a8f5] to-[#a78bfa]">
              governed delivery.
            </span>
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {howSteps.map((s, i) => {
            const Icon = icons[i];
            return (
              <div
                key={s.n}
                className="card-grad rounded-2xl border border-[#f5ede0]/8 p-6 group hover:border-[#b5a8f5]/25 transition-all duration-300 hover:-translate-y-1"
              >
                <div className="flex items-center justify-between mb-6">
                  <span className="text-[12px] font-mono text-[#8a8278]">{s.n}</span>
                  <div className="w-10 h-10 rounded-xl bg-[#16120e] border border-[#f5ede0]/10 flex items-center justify-center group-hover:border-[#b5a8f5]/30 transition-colors">
                    <Icon className="w-5 h-5 text-[#b5a8f5]" />
                  </div>
                </div>
                <h3 className="text-[22px] tracking-[-0.02em] font-medium text-[#f5ede0]">
                  {s.title}
                </h3>
                <p className="mt-3 text-[14px] leading-[1.6] text-[#a8a092]">{s.desc}</p>
                {i < howSteps.length - 1 && (
                  <div className="mt-4 h-px bg-gradient-to-r from-[#b5a8f5]/20 to-transparent" />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
