import React from "react";
import { featureBlocks } from "../mock";
import { Box, Puzzle, Brain, Shield } from "lucide-react";

const FeatureVisual = ({ visual }) => {
  if (visual === "mcp")
    return (
      <div className="relative w-full h-[240px] flex items-center justify-center">
        <div className="flex flex-wrap items-center justify-center gap-2 max-w-[300px]">
          {["GitHub", "Linear", "Stripe", "n8n", "Notion", "Slack"].map((name, i) => (
            <div
              key={name}
              className="px-3 py-1.5 rounded-lg bg-[#16120e] border border-[#f5ede0]/10 text-[11px] font-mono text-[#d8d0c2] hover:border-[#b5a8f5]/30 transition-colors"
              style={{ animationDelay: `${i * 100}ms` }}
            >
              {name}
            </div>
          ))}
          <div className="w-full text-center mt-3">
            <span className="text-[11px] font-mono text-[#b5a8f5] tracking-wider">
              MCP Protocol
            </span>
          </div>
        </div>
      </div>
    );
  if (visual === "skills")
    return (
      <div className="relative w-full h-[240px] flex items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          {["Discover", "Forge", "Activate"].map((step, i) => (
            <div key={step} className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-[#16120e] border border-[#f5ede0]/10 flex items-center justify-center text-[11px] font-mono text-[#b5a8f5]">
                {i + 1}
              </div>
              <span className="text-[13px] font-mono text-[#d8d0c2]">{step}</span>
              {i < 2 && (
                <div className="w-px h-4 bg-[#f5ede0]/10 ml-4" />
              )}
            </div>
          ))}
        </div>
      </div>
    );
  if (visual === "memory")
    return (
      <div className="relative w-full h-[240px] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          {["Tone preferences", "Q3 goals", "Stripe: prod", "Team contacts"].map((fact, i) => (
            <div
              key={fact}
              className="px-4 py-2 rounded-lg bg-[#16120e] border border-[#f5ede0]/8 text-[12px] font-mono text-[#d8d0c2] flex items-center gap-2"
              style={{ transform: `translateX(${(i - 1.5) * 12}px)` }}
            >
              <Brain className="w-3 h-3 text-[#b5a8f5]" />
              {fact}
            </div>
          ))}
        </div>
      </div>
    );
  return (
    <div className="relative w-full h-[240px] flex items-center justify-center">
      <div className="flex items-center gap-3">
        {["Plan", "Execute", "Verify", "Govern"].map((phase, i) => (
          <div key={phase} className="flex items-center">
            <div className="w-14 h-14 rounded-xl bg-[#16120e] border border-[#f5ede0]/10 flex items-center justify-center text-[10px] font-mono text-[#b5a8f5] tracking-wider">
              {phase}
            </div>
            {i < 3 && <div className="w-4 h-px bg-[#f5ede0]/10" />}
          </div>
        ))}
      </div>
    </div>
  );
};

const Features = () => {
  return (
    <section id="features" className="relative py-24">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="text-center mb-16">
          <p className="tiny-label">• Capabilities</p>
          <h2 className="mt-5 text-[44px] lg:text-[64px] leading-[1.02] tracking-[-0.035em] font-medium text-[#f5ede0]">
            Everything an{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#b5a8f5] to-[#a78bfa]">
              AI coworker
            </span>{" "}
            needs.
          </h2>
        </div>

        <div className="space-y-5">
          {featureBlocks.map((b, i) => {
            const reverse = i % 2 === 1;
            return (
              <div
                key={b.title}
                className={`card-grad rounded-3xl border border-[#f5ede0]/8 p-8 lg:p-12 grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center ${
                  reverse ? "lg:[&>div:first-child]:order-2" : ""
                }`}
              >
                <div>
                  <span className="font-mono text-[11px] text-[#8a8278] tracking-wider uppercase">
                    {b.subtitle}
                  </span>
                  <h3 className="mt-2 text-[32px] lg:text-[40px] leading-[1.05] tracking-[-0.025em] font-medium text-[#f5ede0]">
                    {b.title}
                  </h3>
                  <p className="mt-4 text-[16px] leading-[1.6] text-[#a8a092] max-w-[500px]">
                    {b.desc}
                  </p>
                  <div className="mt-6 flex flex-wrap gap-2">
                    {b.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-3 py-1 rounded-full bg-[#16120e] border border-[#f5ede0]/8 text-[11px] font-mono text-[#d8d0c2]"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="relative">
                  <FeatureVisual visual={b.visual} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Features;
