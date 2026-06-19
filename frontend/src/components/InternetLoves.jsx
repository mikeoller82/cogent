import React from "react";
import { tweets } from "../mock";

const InternetLoves = () => {
  const duplicated = [...tweets, ...tweets];

  return (
    <section className="relative py-24 overflow-hidden">
      <div className="text-center mb-14 px-6">
        <p className="tiny-label">• Social Proof</p>
        <h2 className="mt-5 text-[36px] lg:text-[48px] leading-[1.05] tracking-[-0.03em] font-medium text-[#f5ede0]">
          The internet{" "}
          <span className="font-serif-i text-[#b5a8f5]">loves Cogent.</span>
        </h2>
      </div>

      <div className="relative">
        <div className="flex gap-4 marquee" style={{ width: "max-content" }}>
          {duplicated.map((t, i) => (
            <div
              key={i}
              className="w-[320px] flex-shrink-0 rounded-xl border border-[#f5ede0]/8 p-5"
              style={{
                background: "linear-gradient(180deg, rgba(22, 18, 14, 0.8), rgba(15, 13, 11, 0.6))",
              }}
            >
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-full bg-[#b5a8f5]/20 flex items-center justify-center text-[12px] font-medium text-[#b5a8f5]">
                  {t.name.charAt(0)}
                </div>
                <div>
                  <div className="text-[13px] font-medium text-[#f5ede0]">{t.name}</div>
                  <div className="text-[11px] text-[#8a8278] font-mono">{t.handle}</div>
                </div>
              </div>
              <p className="text-[13px] leading-[1.5] text-[#d8d0c2]">{t.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default InternetLoves;
