import React from "react";
import { ArrowRight, GitBranch, Shield, Cpu } from "lucide-react";

const Hero = () => {
  return (
    <section className="relative pt-[140px] pb-24 top-bg circuit-bg overflow-hidden">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 relative z-10">
        <div className="flex flex-col items-center text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#16120e] border border-[#f5ede0]/10 text-[12px] text-[#d8d0c2] font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-[#22c55e] signal-pulse" />
            Built on Loop Engineering
          </div>

          <h1 className="mt-7 text-[56px] md:text-[88px] leading-[0.92] tracking-[-0.045em] font-medium text-[#f5ede0] max-w-[1000px]">
            The governed{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#b5a8f5] to-[#a78bfa]">
              AI coworker
            </span>
            <br />
            that ships real work.
          </h1>

          <p className="mt-6 max-w-[620px] text-[18px] leading-[1.5] text-[#b8b0a2]">
            Not a chatbot. A colleague governed by Loop Engineering — every action planned,
            executed, verified, and controlled. Cogent uses MCP tools, runs skills, remembers
            context, and refines through a Plan→Execute→Verify→Govern loop.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <a
              href="/app"
              className="group inline-flex items-center gap-2 px-7 py-4 rounded-md btn-cream hover:scale-[1.02] transition-transform"
            >
              Try Cogent Free
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </a>
            <a
              href="#loop"
              className="inline-flex items-center gap-2 px-7 py-4 rounded-md btn-outline hover:scale-[1.02] transition-transform"
            >
              See the loop
            </a>
          </div>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-6 text-[12px] text-[#a8a092] font-mono uppercase tracking-wider">
            <span className="inline-flex items-center gap-2">
              <GitBranch className="w-3.5 h-3.5 text-[#b5a8f5]" /> Plan→Execute→Verify loop
            </span>
            <span className="inline-flex items-center gap-2">
              <Shield className="w-3.5 h-3.5 text-[#22c55e]" /> Governance per iteration
            </span>
            <span className="inline-flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-[#60a5fa]" /> 350+ MCP tools
            </span>
          </div>
        </div>

        <div className="mt-20 max-w-[900px] mx-auto">
          <div className="grid grid-cols-3 gap-px bg-[#f5ede0]/8 rounded-2xl overflow-hidden border border-[#f5ede0]/8">
            {[
              { label: "Plan", desc: "Decompose goal into structured steps with constraints and criteria", color: "from-[#b5a8f5]/20 to-transparent" },
              { label: "Execute", desc: "Run actions through risk-checked boundaries with tool access", color: "from-[#60a5fa]/20 to-transparent" },
              { label: "Verify", desc: "Evaluate outputs against success criteria with 4-signal assessment", color: "from-[#22c55e]/20 to-transparent" },
            ].map((phase) => (
              <div key={phase.label} className={`bg-[#16120e] p-6 lg:p-8 bg-gradient-to-b ${phase.color}`}>
                <div className="flex items-center gap-2 mb-3">
                  <span className="w-2 h-2 rounded-full bg-[#b5a8f5] pulse-soft" />
                  <span className="font-mono text-[11px] tracking-wider text-[#b5a8f5] uppercase">
                    {phase.label}
                  </span>
                </div>
                <p className="text-[14px] leading-[1.5] text-[#a8a092]">{phase.desc}</p>
              </div>
            ))}
          </div>
          <div className="text-center mt-3">
            <span className="font-mono text-[11px] text-[#8a8278] tracking-widest">
              + GOVERN layer across all phases — risk check, evaluate, decide every iteration
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
