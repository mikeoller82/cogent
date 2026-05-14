import React from "react";
import { ArrowRight } from "lucide-react";
import { shiftComparisons } from "../mock";

const OtherIcon = ({ name }) => {
  const map = {
    ChatGPT: { bg: "#10a37f", letter: "C" },
    Copilot: { bg: "#0078d4", letter: "M" },
    Zapier: { bg: "#ff4f00", letter: "Z" },
    "Claude Code": { bg: "#cc785c", letter: "A" },
  };
  const m = map[name] || { bg: "#555", letter: name[0] };
  return (
    <div
      className="w-7 h-7 rounded-md flex items-center justify-center text-white text-[12px] font-bold"
      style={{ background: m.bg }}
    >
      {m.letter}
    </div>
  );
};

const CogentIcon = () => (
  <div className="w-7 h-7 rounded-md bg-[#1d1813] border border-[#b5a8f5]/40 flex items-center justify-center">
    <svg width="14" height="14" viewBox="0 0 32 32" fill="none">
      <path d="M4 16 Q 16 4, 28 16" stroke="#b5a8f5" strokeWidth="2" strokeLinecap="round" fill="none" /><path d="M4 16 Q 16 28, 28 16" stroke="#b5a8f5" strokeWidth="2" strokeLinecap="round" fill="none" /><circle cx="16" cy="16" r="2" fill="#b5a8f5" />
    </svg>
  </div>
);

const Shift = () => {
  return (
    <section className="relative py-24">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="text-center">
          <p className="tiny-label">• The Shift</p>
          <h2 className="mt-5 text-[44px] lg:text-[64px] leading-[1.02] tracking-[-0.035em] font-medium text-[#f5ede0] max-w-[900px] mx-auto">
            You’ve tried the AI tools.
            <br />
            <span className="font-serif-i">The work is still there.</span>
          </h2>
          <p className="mt-6 text-[17px] text-[#a8a092] max-w-[640px] mx-auto">
            ChatGPT. Claude. Zapier. Notion AI. You’re already using AI. You’re also still doing the work.
          </p>
        </div>

        <div className="mt-16 space-y-3">
          {shiftComparisons.map((c) => (
            <div
              key={c.label}
              className="card-grad rounded-2xl border border-[#f5ede0]/8 p-6 lg:p-8"
            >
              <p className="tiny-label mb-5">{c.label}</p>
              <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-5 items-center">
                <div className="bg-[#1a1510] rounded-xl border border-[#f5ede0]/8 p-5">
                  <div className="flex items-center gap-2.5 mb-3">
                    <OtherIcon name={c.other.name} />
                    <span className="text-[13px] font-medium text-[#d8d0c2]">{c.other.name}</span>
                  </div>
                  <p className="text-[20px] leading-[1.3] tracking-[-0.01em] text-[#d8d0c2]">
                    {c.other.text}
                  </p>
                </div>
                <div className="flex items-center justify-center gap-0.5 text-[#b5a8f5]/60">
                  <ArrowRight className="w-4 h-4" />
                  <ArrowRight className="w-4 h-4 -ml-2" />
                  <ArrowRight className="w-4 h-4 -ml-2 text-[#b5a8f5]" />
                </div>
                <div className="bg-[#1d1813] rounded-xl border border-[#b5a8f5]/15 p-5">
                  <div className="flex items-center gap-2.5 mb-3">
                    <CogentIcon />
                    <span className="text-[13px] font-medium text-[#f5ede0]">Cogent</span>
                  </div>
                  <p className="text-[20px] leading-[1.3] tracking-[-0.01em] text-[#f5ede0]">
                    <span className="text-[#b5a8f5]">{c.cogent.text}</span> {c.cogent.emphasis}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Shift;
