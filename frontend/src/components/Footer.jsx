import React from "react";
import Logo from "./Logo";
import { footerCols } from "../mock";
import { Twitter, Linkedin, Github } from "lucide-react";

const Footer = () => {
  return (
    <footer className="relative pt-20 pb-10 border-t border-[#f5ede0]/8">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-10">
          <div className="col-span-2">
            <Logo />
            <p className="mt-5 text-[14px] text-[#a8a092] max-w-[280px] leading-[1.55]">
              The AI coworker that lives in Slack, connects to 3,000+ tools, and does the work.
            </p>
            <div className="mt-6 flex items-center gap-3">
              {[Twitter, Linkedin, Github].map((Icon, i) => (
                <a
                  key={i}
                  href="#"
                  className="w-9 h-9 rounded-md border border-[#f5ede0]/10 flex items-center justify-center text-[#a8a092] hover:text-[#f5ede0] hover:border-[#f5ede0]/25 transition-colors"
                >
                  <Icon className="w-4 h-4" />
                </a>
              ))}
            </div>
          </div>

          {footerCols.map((c) => (
            <div key={c.title}>
              <h4 className="text-[13px] font-mono uppercase tracking-wider text-[#8a8278] mb-4">
                {c.title}
              </h4>
              <ul className="space-y-3">
                {c.links.map((l) => (
                  <li key={l}>
                    <a
                      href="#"
                      className="text-[14px] text-[#d8d0c2] hover:text-[#f5ede0] transition-colors"
                    >
                      {l}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-16 pt-6 border-t border-[#f5ede0]/8 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-[12px] font-mono text-[#8a8278]">
            © 2025 Viktor. All rights reserved.
          </p>
          <div className="flex items-center gap-6 text-[12px] font-mono text-[#8a8278]">
            <a href="#" className="hover:text-[#f5ede0] transition-colors">Privacy</a>
            <a href="#" className="hover:text-[#f5ede0] transition-colors">Terms</a>
            <a href="#" className="hover:text-[#f5ede0] transition-colors">Security</a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
