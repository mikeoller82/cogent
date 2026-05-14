import React from "react";

const Logo = ({ className = "" }) => {
  return (
    <a href="/" className={`flex items-center gap-2 ${className}`}>
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className="flex-shrink-0">
        <path
          d="M12 2L22 12L12 22L2 12L12 2Z"
          stroke="#b5a8f5"
          strokeWidth="1.8"
          fill="none"
        />
        <path
          d="M12 7L17 12L12 17L7 12L12 7Z"
          fill="#b5a8f5"
          fillOpacity="0.35"
        />
      </svg>
      <span className="font-mono text-[15px] tracking-tight text-[#f5ede0]">
        get<span className="text-[#b5a8f5]">viktor</span>.com
      </span>
    </a>
  );
};

export default Logo;
