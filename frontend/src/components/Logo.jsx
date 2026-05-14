import React from "react";

const Logo = ({ className = "" }) => {
  return (
    <a href="/" className={`flex items-center gap-2.5 ${className}`}>
      {/* Two intersecting arcs forming a lens — the "co-" + "agent" intersection */}
      <svg width="24" height="24" viewBox="0 0 32 32" fill="none" className="flex-shrink-0">
        <path
          d="M4 16 Q 16 4, 28 16"
          stroke="#b5a8f5"
          strokeWidth="2.2"
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M4 16 Q 16 28, 28 16"
          stroke="#b5a8f5"
          strokeWidth="2.2"
          strokeLinecap="round"
          fill="none"
        />
        <circle cx="16" cy="16" r="2.4" fill="#b5a8f5" />
      </svg>
      <span className="font-mono text-[15px] tracking-tight text-[#f5ede0] lowercase">
        co<span className="text-[#b5a8f5]">gent</span>
      </span>
    </a>
  );
};

export default Logo;
