import React, { useState } from "react";
import { useCases } from "../mock";
import { ArrowUpRight } from "lucide-react";

const UseCases = () => {
  const [active, setActive] = useState(useCases[0].key);
  const current = useCases.find((u) => u.key === active);

  return (
    <section id="usecases" className="relative py-24">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="text-center mb-12">
          <p className="tiny-label">• Use cases</p>
          <h2 className="mt-5 text-[44px] lg:text-[64px] leading-[1.02] tracking-[-0.035em] font-medium text-[#f5ede0]">
            What Cogent can <span className="font-serif-i">own</span> for your team
          </h2>
        </div>

        <div className="flex flex-wrap justify-center gap-2 mb-10">
          {useCases.map((u) => (
            <button
              key={u.key}
              onClick={() => setActive(u.key)}
              className={`px-5 py-2.5 rounded-full text-[14px] font-medium transition-all ${
                active === u.key
                  ? "bg-[#f5ede0] text-[#15110d]"
                  : "bg-[#1d1813] text-[#d8d0c2] border border-[#f5ede0]/10 hover:border-[#f5ede0]/25"
              }`}
            >
              {u.label}
            </button>
          ))}
        </div>

        <div className="card-grad rounded-3xl border border-[#f5ede0]/8 p-8 lg:p-12">
          <h3 className="text-[28px] lg:text-[36px] leading-[1.2] tracking-[-0.02em] text-[#f5ede0] max-w-[820px]">
            {current.headline}
          </h3>

          <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-4">
            {current.items.map((it) => (
              <div
                key={it.title}
                className="group bg-[#1a1510] rounded-xl border border-[#f5ede0]/8 p-6 hover:border-[#b5a8f5]/25 transition-colors"
              >
                <div className="flex items-start justify-between gap-4 mb-3">
                  <h4 className="text-[18px] font-medium text-[#f5ede0]">{it.title}</h4>
                  <ArrowUpRight className="w-4 h-4 text-[#8a8278] group-hover:text-[#b5a8f5] group-hover:-translate-y-0.5 group-hover:translate-x-0.5 transition-all" />
                </div>
                <p className="text-[14px] leading-[1.6] text-[#a8a092]">{it.desc}</p>
              </div>
            ))}
          </div>

          <div className="mt-10 flex items-center justify-center">
            <a
              href="#cta"
              className="btn-cream px-6 py-3 rounded-md hover:scale-[1.02] transition-transform"
            >
              Start free
            </a>
          </div>
        </div>
      </div>
    </section>
  );
};

export default UseCases;
