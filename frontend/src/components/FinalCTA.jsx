import React from "react";
import { Check } from "lucide-react";

const FinalCTA = () => {
  const items = [
    "3,000+ integrations",
    "Slack and Teams",
    "Reports, dashboards, apps",
    "Code and PR reviews",
    "SOC 2 compliant",
  ];

  return (
    <section id="cta" className="relative py-24">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="relative card-grad rounded-3xl border border-[#f5ede0]/10 p-10 lg:p-16 overflow-hidden">
          <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-[#b5a8f5]/10 blur-3xl pointer-events-none" />

          <div className="relative text-center">
            <h2 className="text-[48px] lg:text-[72px] leading-[1.02] tracking-[-0.035em] font-medium text-[#f5ede0]">
              Start free.
              <br />
              <span className="font-serif-i">Pay only when you’re ready.</span>
            </h2>
            <p className="mt-7 text-[17px] text-[#a8a092] max-w-[640px] mx-auto leading-[1.55]">
              Every feature. Every integration.{" "}
              <span className="text-[#f5ede0] font-medium">$100</span> in credits on the
              house. No credit card, no sales call, no catch. When you need more, it starts
              $50/month.
            </p>

            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
              <a
                href="#"
                className="btn-cream px-7 py-4 rounded-md hover:scale-[1.02] transition-transform"
              >
                Get Started For Free
              </a>
              <a
                href="#"
                className="px-7 py-4 rounded-md border border-[#f5ede0]/15 text-[#f5ede0] text-[12px] font-mono uppercase tracking-wider hover:border-[#f5ede0]/30 transition-colors"
              >
                See all plans
              </a>
            </div>

            <div className="mt-12 flex flex-wrap items-center justify-center gap-x-7 gap-y-3 text-[13px] font-mono text-[#a8a092]">
              {items.map((it) => (
                <span key={it} className="inline-flex items-center gap-2">
                  <Check className="w-3.5 h-3.5 text-[#b5a8f5]" /> {it}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default FinalCTA;
