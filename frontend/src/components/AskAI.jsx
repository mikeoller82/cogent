import React from "react";
import { ArrowUpRight } from "lucide-react";

const providers = [
  {
    name: "ChatGPT",
    bg: "#10a37f",
    initial: "C",
    href: "https://chatgpt.com/?q=I%27m+evaluating+Cogent%2C+the+AI+coworker+for+Slack+and+Teams.+What+does+it+do%3F",
  },
  {
    name: "Perplexity",
    bg: "#20808d",
    initial: "P",
    href: "https://www.perplexity.ai/search?q=Cogent+AI+coworker+for+Slack",
  },
  {
    name: "Claude",
    bg: "#cc785c",
    initial: "A",
    href: "https://claude.ai/new?q=I%27m+evaluating+Cogent%2C+the+AI+coworker+for+Slack",
  },
];

const AskAI = () => {
  return (
    <section className="relative py-24">
      <div className="max-w-[900px] mx-auto px-6 lg:px-10 text-center">
        <p className="tiny-label">Don’t take our word for it</p>
        <h2 className="mt-5 text-[40px] lg:text-[56px] leading-[1.05] tracking-[-0.03em] font-medium text-[#f5ede0]">
          Ask AI <span className="font-serif-i">about us</span>
        </h2>
        <p className="mt-5 text-[16px] text-[#a8a092] max-w-[480px] mx-auto">
          Pick your favorite AI and ask what it thinks about Cogent.
          <br /> No filter, no spin.
        </p>

        <div className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-3">
          {providers.map((p) => (
            <a
              key={p.name}
              href={p.href}
              target="_blank"
              rel="noreferrer"
              className="group bg-[#1d1813] rounded-xl border border-[#f5ede0]/10 p-5 flex items-center justify-between hover:border-[#b5a8f5]/30 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-9 h-9 rounded-md flex items-center justify-center text-white font-bold"
                  style={{ background: p.bg }}
                >
                  {p.initial}
                </div>
                <span className="text-[14px] font-medium text-[#f5ede0]">Ask {p.name}</span>
              </div>
              <ArrowUpRight className="w-4 h-4 text-[#8a8278] group-hover:text-[#b5a8f5] group-hover:-translate-y-0.5 group-hover:translate-x-0.5 transition-all" />
            </a>
          ))}
        </div>
      </div>
    </section>
  );
};

export default AskAI;
