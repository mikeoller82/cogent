import React, { useState } from "react";
import { Play, Pause } from "lucide-react";

const Solution = () => {
  const [playing, setPlaying] = useState(false);

  return (
    <section className="relative py-24">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10 text-center">
        <p className="tiny-label">• The Solution</p>
        <h2 className="mt-5 text-[48px] lg:text-[80px] leading-[1.02] tracking-[-0.04em] font-medium text-[#f5ede0]">
          Just{" "}
          <span className="inline-block px-3 py-1 rounded-lg bg-[#b5a8f5]/15 text-[#b5a8f5] mx-1">
            @Viktor.
          </span>{" "}
          <span className="font-serif-i">It’s handled.</span>
        </h2>

        <div className="mt-14 relative max-w-[1080px] mx-auto rounded-3xl overflow-hidden border border-[#f5ede0]/10 aspect-[16/9] bg-gradient-to-br from-[#1d1813] via-[#221b15] to-[#181410]">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="absolute inset-0 opacity-50">
              <div className="absolute top-1/4 left-1/4 w-64 h-64 rounded-full bg-[#b5a8f5]/20 blur-3xl" />
              <div className="absolute bottom-1/4 right-1/4 w-64 h-64 rounded-full bg-[#b5a8f5]/10 blur-3xl" />
            </div>

            <div className="relative z-10 w-full max-w-[640px] px-8">
              <div className="bg-[#15110d]/80 backdrop-blur-md rounded-2xl border border-[#f5ede0]/10 p-6 text-left">
                <div className="flex items-start gap-3 mb-4">
                  <div className="w-9 h-9 rounded bg-[#b5a8f5]/20 flex items-center justify-center">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                      <path d="M12 2L22 12L12 22L2 12L12 2Z" stroke="#b5a8f5" strokeWidth="2" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-baseline gap-2">
                      <span className="text-[14px] font-medium text-[#f5ede0]">Viktor</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#b5a8f5]/20 text-[#b5a8f5] font-mono">APP</span>
                      <span className="text-[11px] text-[#8a8278]">2:43 PM</span>
                    </div>
                    <p className="mt-2 text-[14px] text-[#d8d0c2] leading-relaxed">
                      I’ve pulled your Stripe MRR, churn, and Meta Ads spend for Q3. Drafting the
                      board update PDF now — will share in 2 minutes.
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <span className="text-[11px] px-2 py-1 rounded bg-[#f5ede0]/5 text-[#a8a092] font-mono">📊 dashboard.pdf</span>
                  <span className="text-[11px] px-2 py-1 rounded bg-[#f5ede0]/5 text-[#a8a092] font-mono">📈 metrics.xlsx</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => setPlaying((p) => !p)}
              className="absolute bottom-6 right-6 w-14 h-14 rounded-full bg-[#f5ede0] text-[#15110d] flex items-center justify-center hover:scale-105 transition-transform"
              aria-label="play demo"
            >
              {playing ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Solution;
