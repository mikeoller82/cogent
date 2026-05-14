import React, { useState, useEffect } from "react";
import { ChevronDown, Menu, X } from "lucide-react";
import { navLinks } from "../mock";
import Logo from "./Logo";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "./ui/dropdown-menu";
import { Sheet, SheetContent, SheetTrigger } from "./ui/sheet";

const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-[#15110d]/85 backdrop-blur-md border-b border-[#f5ede0]/10"
          : "bg-transparent"
      }`}
    >
      <nav className="max-w-[1280px] mx-auto px-6 lg:px-10 h-[68px] flex items-center justify-between">
        <Logo />

        <div className="hidden lg:flex items-center gap-1">
          {navLinks.map((link) =>
            link.items ? (
              <DropdownMenu key={link.label}>
                <DropdownMenuTrigger className="group flex items-center gap-1.5 px-4 py-2 text-[14px] text-[#d8d0c2] hover:text-[#f5ede0] transition-colors outline-none">
                  {link.label}
                  <ChevronDown className="w-3.5 h-3.5 opacity-60 group-data-[state=open]:rotate-180 transition-transform" />
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  className="bg-[#1d1813] border-[#f5ede0]/10 text-[#f5ede0] mt-2 min-w-[220px]"
                  align="start"
                >
                  {link.items.map((it) => (
                    <DropdownMenuItem
                      key={it.label}
                      className="text-[13px] text-[#d8d0c2] focus:bg-[#f5ede0]/5 focus:text-[#f5ede0] cursor-pointer py-2"
                      onClick={() => {
                        const el = document.querySelector(it.href);
                        if (el) el.scrollIntoView({ behavior: "smooth" });
                      }}
                    >
                      {it.label}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <a
                key={link.label}
                href={link.href}
                className="px-4 py-2 text-[14px] text-[#d8d0c2] hover:text-[#f5ede0] transition-colors"
              >
                {link.label}
              </a>
            )
          )}
        </div>

        <div className="flex items-center gap-3">
          <a
            href="/app"
            className="hidden md:inline-flex btn-cream px-5 py-2.5 rounded-md hover:scale-[1.02] transition-transform"
          >
            Get Started For Free
          </a>

          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger className="lg:hidden p-2 text-[#f5ede0]">
              <Menu className="w-5 h-5" />
            </SheetTrigger>
            <SheetContent
              side="right"
              className="bg-[#1a1410] border-[#f5ede0]/10 text-[#f5ede0] w-[300px]"
            >
              <div className="flex flex-col gap-1 mt-8">
                {navLinks.map((link) => (
                  <div key={link.label} className="py-2 border-b border-[#f5ede0]/5">
                    <div className="text-[14px] font-medium">{link.label}</div>
                    {link.items && (
                      <div className="mt-2 flex flex-col gap-2 pl-2">
                        {link.items.map((it) => (
                          <a
                            key={it.label}
                            href={it.href}
                            className="text-[13px] text-[#a8a092]"
                            onClick={() => setOpen(false)}
                          >
                            {it.label}
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
                <a href="#cta" className="btn-cream mt-6 px-4 py-3 rounded-md text-center">
                  Get Started
                </a>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </nav>
    </header>
  );
};

export default Navbar;
