import React from "react";

const Logo = ({ className = "" }) => {
  return (
    <a href="/" className={`flex items-center ${className}`}>
      <img
        src="/cogentlogo.png"
        alt="Cogent"
        className="h-[36px] w-auto rounded-md"
      />
    </a>
  );
};

export default Logo;
