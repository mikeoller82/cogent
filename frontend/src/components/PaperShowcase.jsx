import React from "react";
import { paperHighlights } from "../mock";
import { BookOpen, ExternalLink } from "lucide-react";

const PaperShowcase = () => {
  return (
    <section id="paper" className="relative py-24">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="text-center mb-16">
          <p className="tiny-label">• The Research</p>
          <h2 className="mt-5 text-[44px] lg:text-[64px] leading-[1.02] tracking-[-0.035em] font-medium text-[#f5ede0] max-w-[900px] mx-auto">
            Built on{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#b5a8f5] to-[#a78bfa]">
              Loop Engineering.
            </span>
          </h2>
          <p className="mt-5 text-[16px] text-[#a8a092] max-w-[640px] mx-auto">
            Cogent is the production implementation of the Loop Engineering framework —
            the missing governance layer for reliable AI agents.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {paperHighlights.map((h, i) => (
            <div
              key={i}
              className="card-grad rounded-2xl border border-[#f5ede0]/8 p-6 lg:p-8 group hover:border-[#b5a8f5]/20 transition-colors"
            >
              <div className="flex items-start gap-3">
                <span className="text-[#b5a8f5] text-lg mt-0.5">"</span>
                <div>
                  <p className="text-[15px] leading-[1.6] text-[#d8d0c2] font-medium">
                    {h.quote}
                  </p>
                  <div className="mt-4 flex items-center gap-2 text-[12px] text-[#8a8278] font-mono">
                    <span>— {h.author}</span>
                    <span className="text-[#f5ede0]/20">/</span>
                    <span>{h.context}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-10 text-center">
          <a
            href="#"
            className="inline-flex items-center gap-2 btn-outline px-6 py-3 rounded-md hover:scale-[1.02] transition-transform"
          >
            <BookOpen className="w-4 h-4" />
            Read the full paper
            <ExternalLink className="w-3 h-3 opacity-60" />
          </a>
        </div>
      </div>
    </section>
  );
};

export default PaperShowcase;
