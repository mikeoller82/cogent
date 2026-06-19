import React from "react";
import { footerCols } from "../mock";
import Logo from "./Logo";

const Footer = () => {
  return (
    <footer className="relative py-16 border-t border-[#f5ede0]/8">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8">
          <div className="col-span-2 md:col-span-1">
            <Logo />
            <p className="mt-4 text-[13px] leading-[1.6] text-[#8a8278] max-w-[200px]">
              The governed AI coworker that ships real work.
            </p>
            <div className="mt-4 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#22c55e] signal-pulse" />
              <span className="text-[11px] font-mono text-[#8a8278]">All systems governed</span>
            </div>
          </div>

          {footerCols.map((col) => (
            <div key={col.title}>
              <h4 className="text-[12px] font-mono tracking-wider uppercase text-[#8a8278] mb-4">
                {col.title}
              </h4>
              <ul className="space-y-2.5">
                {col.links.map((link) => (
                  <li key={link}>
                    <a
                      href="#"
                      className="text-[13px] text-[#d8d0c2] hover:text-[#f5ede0] transition-colors"
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 pt-6 border-t border-[#f5ede0]/8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-[12px] text-[#8a8278] font-mono">
            &copy; {new Date().getFullYear()} Cogent. Governed execution for AI agents.
          </p>
          <div className="flex items-center gap-4 text-[12px] text-[#8a8278] font-mono">
            <span>v2.0</span>
            <span className="text-[#f5ede0]/20">/</span>
            <span>Loop Engineering</span>
            <span className="text-[#f5ede0]/20">/</span>
            <span>MCP Registry</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
