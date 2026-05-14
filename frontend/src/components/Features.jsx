import React from "react";
import { FileText, Table, Presentation, Globe, Database, GitBranch, Brain, Zap } from "lucide-react";
import { featureBlocks } from "../mock";

const Illus1 = () => (
  <div className="relative w-full h-[260px] flex items-center justify-center gap-3">
    {[
      { Icon: FileText, label: "PDF", color: "#ef4444" },
      { Icon: Table, label: "Excel", color: "#22c55e" },
      { Icon: Presentation, label: "PPT", color: "#f59e0b" },
      { Icon: Globe, label: "Web App", color: "#b5a8f5" },
    ].map(({ Icon, label, color }, i) => (
      <div
        key={label}
        className="w-[100px] h-[130px] rounded-xl bg-[#252018] border border-[#f5ede0]/10 flex flex-col items-center justify-center gap-3 hover:-translate-y-2 transition-transform duration-300"
        style={{ transform: `rotate(${(i - 1.5) * 4}deg)` }}
      >
        <Icon className="w-9 h-9" style={{ color }} />
        <span className="text-[11px] font-mono text-[#d8d0c2]">{label}</span>
      </div>
    ))}
  </div>
);

const Illus2 = () => (
  <div className="relative w-full h-[260px] flex items-center justify-center">
    <div className="relative w-[240px] h-[240px]">
      {[
        { Icon: Database, color: "#635bff", angle: -75 },
        { Icon: GitBranch, color: "#f5ede0", angle: -25 },
        { Icon: Brain, color: "#b5a8f5", angle: 25 },
        { Icon: Zap, color: "#f59e0b", angle: 75 },
      ].map(({ Icon, color, angle }, i) => (
        <div
          key={i}
          className="absolute w-[64px] h-[64px] rounded-2xl bg-[#252018] border border-[#f5ede0]/10 flex items-center justify-center"
          style={{
            left: "50%",
            top: "50%",
            transform: `translate(-50%, -50%) rotate(${angle}deg) translateY(-100px) rotate(${-angle}deg)`,
          }}
        >
          <Icon className="w-7 h-7" style={{ color }} />
        </div>
      ))}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-20 h-20 rounded-full bg-[#b5a8f5]/20 blur-2xl" />
      </div>
    </div>
  </div>
);

const Illus3 = () => (
  <div className="relative w-full h-[260px] flex items-center justify-center">
    <div className="relative">
      <div className="w-[120px] h-[120px] rounded-full bg-gradient-to-br from-[#b5a8f5]/30 to-[#b5a8f5]/5 border border-[#b5a8f5]/30 flex items-center justify-center">
        <Brain className="w-14 h-14 text-[#b5a8f5]" />
      </div>
      {["Likes pdfs", "Q3 goals", "Tone: concise", "Stripe: prod"].map((t, i) => (
        <div
          key={t}
          className="absolute px-3 py-1.5 rounded-full bg-[#252018] border border-[#f5ede0]/10 text-[11px] font-mono text-[#d8d0c2] whitespace-nowrap"
          style={{
            left: `${[-140, 110, -130, 100][i]}px`,
            top: `${[20, 0, 80, 80][i]}px`,
          }}
        >
          {t}
        </div>
      ))}
    </div>
  </div>
);

const illus = [Illus1, Illus2, Illus3];

const Features = () => {
  return (
    <section className="relative py-24">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 space-y-6">
        {featureBlocks.map((b, i) => {
          const Il = illus[i];
          const reverse = i % 2 === 1;
          return (
            <div
              key={b.title}
              className={`card-grad rounded-3xl border border-[#f5ede0]/8 p-10 lg:p-14 grid grid-cols-1 lg:grid-cols-2 gap-10 items-center ${
                reverse ? "lg:[&>div:first-child]:order-2" : ""
              }`}
            >
              <div>
                <h3 className="text-[36px] lg:text-[44px] leading-[1.05] tracking-[-0.025em] font-medium text-[#f5ede0]">
                  {b.title}
                </h3>
                <p className="mt-5 text-[17px] leading-[1.55] text-[#a8a092] max-w-[480px]">
                  {b.desc}
                </p>
              </div>
              <div className="relative">
                <Il />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default Features;
