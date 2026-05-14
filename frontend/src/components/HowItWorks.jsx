import React from "react";
import { Plug, MessageSquare, Sparkles } from "lucide-react";
import { howSteps } from "../mock";

const icons = [Plug, MessageSquare, Sparkles];

const HowItWorks = () => {
  return (
    <section id="how" className="relative py-24">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="text-center mb-16">
          <p className="tiny-label">• How It Works</p>
          <h2 className="mt-5 text-[44px] lg:text-[64px] leading-[1.02] tracking-[-0.035em] font-medium text-[#f5ede0] max-w-[900px] mx-auto">
            Onboarding new hires has never been{" "}
            <span className="font-serif-i text-[#b5a8f5]">this easy.</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {howSteps.map((s, i) => {
            const Icon = icons[i];
            return (
              <div
                key={s.n}
                className="card-grad rounded-2xl border border-[#f5ede0]/8 p-7 group hover:border-[#b5a8f5]/25 transition-colors"
              >
                <div className="flex items-center justify-between mb-8">
                  <span className="text-[13px] font-mono text-[#8a8278]">{s.n}</span>
                  <div className="w-11 h-11 rounded-xl bg-[#1a1510] border border-[#f5ede0]/10 flex items-center justify-center group-hover:border-[#b5a8f5]/30 transition-colors">
                    <Icon className="w-5 h-5 text-[#b5a8f5]" />
                  </div>
                </div>
                <h3 className="text-[28px] tracking-[-0.02em] font-medium text-[#f5ede0]">
                  {s.title}
                </h3>
                <p className="mt-4 text-[15px] leading-[1.55] text-[#a8a092]">{s.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
