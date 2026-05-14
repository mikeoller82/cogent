import React, { useState } from "react";
import { ArrowLeft, ArrowRight, Clock, Linkedin } from "lucide-react";
import { testimonials } from "../mock";

const initialsColors = ["#b5a8f5", "#f59e0b", "#22c55e", "#ef4444", "#60a5fa", "#ec4899"];

const Testimonials = () => {
  const [active, setActive] = useState(0);
  const current = testimonials[active];

  const prev = () => setActive((a) => (a - 1 + testimonials.length) % testimonials.length);
  const next = () => setActive((a) => (a + 1) % testimonials.length);

  return (
    <section className="relative py-24">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <h2 className="text-[44px] lg:text-[64px] leading-[1.02] tracking-[-0.035em] font-medium text-[#f5ede0] text-center">
          What our <span className="font-serif-i">customers say</span>
        </h2>

        <div className="mt-14 card-grad rounded-3xl border border-[#f5ede0]/8 p-8 lg:p-12 max-w-[1100px] mx-auto">
          <div className="flex flex-wrap gap-3 mb-10">
            {testimonials.map((t, i) => (
              <button
                key={t.name}
                onClick={() => setActive(i)}
                className={`relative w-14 h-14 rounded-full flex items-center justify-center text-[15px] font-medium text-white transition-all ${
                  i === active
                    ? "ring-2 ring-[#b5a8f5] ring-offset-2 ring-offset-[#1d1813] scale-110"
                    : "opacity-60 hover:opacity-100"
                }`}
                style={{ background: initialsColors[i % initialsColors.length] }}
                aria-label={t.name}
              >
                {t.initials}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-8 items-end">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#1a1510] border border-[#f5ede0]/10 text-[12px] font-mono text-[#b5a8f5]">
                <Clock className="w-3.5 h-3.5" /> Saved: {current.saved}
              </div>
              <p className="mt-6 text-[26px] lg:text-[32px] leading-[1.3] tracking-[-0.02em] text-[#f5ede0] max-w-[800px]">
                “{current.quote}”
              </p>
              <div className="mt-8 flex items-center gap-4">
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center text-white font-medium"
                  style={{ background: initialsColors[active % initialsColors.length] }}
                >
                  {current.initials}
                </div>
                <div>
                  <div className="text-[15px] font-medium text-[#f5ede0]">{current.name}</div>
                  <div className="text-[13px] text-[#a8a092] flex items-center gap-2">
                    {current.title}
                    <Linkedin className="w-3.5 h-3.5 text-[#b5a8f5]" />
                  </div>
                </div>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={prev}
                className="w-12 h-12 rounded-md bg-[#1a1510] border border-[#f5ede0]/10 hover:border-[#f5ede0]/30 transition-colors flex items-center justify-center text-[#d8d0c2]"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
              <button
                onClick={next}
                className="w-12 h-12 rounded-md bg-[#1a1510] border border-[#f5ede0]/10 hover:border-[#f5ede0]/30 transition-colors flex items-center justify-center text-[#d8d0c2]"
              >
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Testimonials;
