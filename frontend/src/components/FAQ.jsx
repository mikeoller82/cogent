import React from "react";
import { faqs } from "../mock";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "./ui/accordion";

const FAQ = () => {
  return (
    <section className="relative py-24">
      <div className="max-w-[920px] mx-auto px-6 lg:px-10">
        <h2 className="text-[44px] lg:text-[64px] leading-[1.02] tracking-[-0.035em] font-medium text-[#f5ede0] text-center">
          F<span className="font-serif-i">A</span>Q
        </h2>

        <Accordion type="single" collapsible className="mt-12 w-full">
          {faqs.map((f, i) => (
            <AccordionItem
              key={i}
              value={`item-${i}`}
              className="border-b border-[#f5ede0]/10"
            >
              <AccordionTrigger className="text-left text-[17px] lg:text-[19px] font-medium text-[#f5ede0] hover:text-[#b5a8f5] py-5 hover:no-underline">
                {f.q}
              </AccordionTrigger>
              <AccordionContent className="text-[15px] leading-[1.65] text-[#a8a092] pb-6 pr-8">
                {f.a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>

        <div className="mt-8 text-center">
          <button className="text-[14px] font-mono text-[#b5a8f5] hover:text-[#f5ede0] transition-colors">
            Show all (19) Questions
          </button>
        </div>
      </div>
    </section>
  );
};

export default FAQ;
