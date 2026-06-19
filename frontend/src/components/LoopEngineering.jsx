import React from "react";
import { loopComponents } from "../mock";

const icons = {
  goal: "🎯",
  state: "🧠",
  action: "⚡",
  observe: "👁️",
  evaluate: "📊",
  control: "🛡️",
};

const LoopEngineering = () => {
  return (
    <section id="loop" className="relative py-24 circuit-bg">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 relative z-10">
        <div className="text-center mb-16">
          <p className="tiny-label">• The Architecture</p>
          <h2 className="mt-5 text-[44px] lg:text-[64px] leading-[1.02] tracking-[-0.035em] font-medium text-[#f5ede0] max-w-[900px] mx-auto">
            Six components.{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#b5a8f5] to-[#a78bfa]">
              One governed loop.
            </span>
          </h2>
          <p className="mt-5 text-[16px] text-[#a8a092] max-w-[640px] mx-auto">
            Loop Engineering defines six components that every reliable AI agent needs.
            Cogent implements all of them — governance runs every iteration, not just at exceptions.
          </p>
        </div>

        <div className="relative">
          {/* Central hub */}
          <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-24 h-24 rounded-full bg-[#16120e] border-2 border-[#b5a8f5]/30 items-center justify-center z-10">
            <div className="text-center">
              <div className="text-[11px] font-mono text-[#b5a8f5] tracking-wider">LOOP</div>
              <div className="text-[10px] font-mono text-[#8a8278]">ENGINE</div>
            </div>
          </div>

          {/* Connection lines from center to nodes */}
          <div className="hidden lg:block absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[520px] h-[520px] rounded-full border border-[#f5ede0]/5" />
          <div className="hidden lg:block absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] rounded-full border border-[#f5ede0]/3" />

          {/* Simple: 3x2 grid on mobile, radial on desktop */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {loopComponents.map((comp, i) => (
              <div
                key={comp.id}
                className="group card-grad rounded-2xl border border-[#f5ede0]/8 p-6 hover:border-[#b5a8f5]/25 transition-all duration-300 hover:-translate-y-1"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
                    style={{ background: `${comp.color}15`, color: comp.color }}
                  >
                    {icons[comp.id]}
                  </div>
                  <div>
                    <div className="text-[13px] font-mono text-[#8a8278]">
                      {String(i + 1).padStart(2, "0")}
                    </div>
                    <h3 className="text-[16px] font-medium text-[#f5ede0]">{comp.label}</h3>
                  </div>
                </div>
                <p className="text-[14px] leading-[1.6] text-[#a8a092]">{comp.desc}</p>
                <div
                  className="mt-4 h-px w-0 group-hover:w-full transition-all duration-500"
                  style={{ background: `linear-gradient(90deg, ${comp.color}, transparent)` }}
                />
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 text-center">
          <div className="inline-flex flex-wrap items-center justify-center gap-4 text-[13px] text-[#8a8278] font-mono">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#b5a8f5]" /> Goal → State → Act
            </span>
            <span className="text-[#f5ede0]/20">/</span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#f59e0b]" /> Observe → Evaluate
            </span>
            <span className="text-[#f5ede0]/20">/</span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#a78bfa]" /> Control
            </span>
            <span className="text-[#f5ede0]/20">/</span>
            <span className="text-[#b5a8f5]">Govern every iteration</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default LoopEngineering;
