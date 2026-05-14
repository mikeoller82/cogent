import React from "react";
import { Heart } from "lucide-react";
import { tweets } from "../mock";

const colors = ["#b5a8f5", "#f59e0b", "#22c55e", "#ef4444", "#60a5fa", "#ec4899", "#14b8a6"];

const TweetCard = ({ t, i }) => (
  <div className="w-[320px] flex-shrink-0 bg-[#1d1813] rounded-2xl border border-[#f5ede0]/8 p-5 hover:border-[#b5a8f5]/20 transition-colors">
    <div className="flex items-center gap-3 mb-3">
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center text-white font-medium text-[14px]"
        style={{ background: colors[i % colors.length] }}
      >
        {t.name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
      </div>
      <div>
        <div className="text-[13px] font-medium text-[#f5ede0] leading-tight">{t.name}</div>
        <div className="text-[12px] text-[#8a8278]">{t.handle}</div>
      </div>
    </div>
    <p className="text-[14px] leading-[1.5] text-[#d8d0c2]">{t.text}</p>
  </div>
);

const InternetLoves = () => {
  const row1 = tweets.slice(0, 6);
  const row2 = tweets.slice(6);
  return (
    <section className="relative py-24 overflow-hidden">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="text-center mb-12">
          <h2 className="text-[44px] lg:text-[64px] leading-[1.02] tracking-[-0.035em] font-medium text-[#f5ede0] inline-flex flex-wrap items-center justify-center gap-3">
            The internet <span className="font-serif-i">loves</span> Cogent
            <svg width="60" height="60" viewBox="0 0 32 32" fill="none" className="inline-block">
              <path d="M4 16 Q 16 4, 28 16" stroke="#b5a8f5" strokeWidth="1.5" strokeLinecap="round" fill="none" /><path d="M4 16 Q 16 28, 28 16" stroke="#b5a8f5" strokeWidth="1.5" strokeLinecap="round" fill="none" /><circle cx="16" cy="16" r="2.4" fill="#b5a8f5" />
            </svg>
            <Heart className="w-10 h-10 text-[#ef4444] fill-[#ef4444]" />
            <Heart className="w-7 h-7 text-[#ec4899] fill-[#ec4899]" />
          </h2>
          <a
            href="#cta"
            className="inline-flex mt-8 btn-cream px-6 py-3 rounded-md hover:scale-[1.02] transition-transform"
          >
            Get Started for Free
          </a>
        </div>
      </div>

      <div className="space-y-4">
        <div className="relative w-full overflow-hidden">
          <div className="flex gap-4 marquee w-max">
            {[...row1, ...row1].map((t, i) => (
              <TweetCard t={t} i={i} key={`r1-${i}`} />
            ))}
          </div>
        </div>
        <div className="relative w-full overflow-hidden">
          <div className="flex gap-4 marquee w-max" style={{ animationDirection: "reverse" }}>
            {[...row2, ...row2, ...row2].map((t, i) => (
              <TweetCard t={t} i={i + 3} key={`r2-${i}`} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default InternetLoves;
