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
    <section id="faq" className="relative py-24">
      <div className="max-w-[800px] mx-auto px-6 lg:px-10">
        <div className="text-center mb-14">
          <p className="tiny-label">• FAQ</p>
          <h2 className="mt-5 text-[36px] lg:text-[48px] leading-[1.05] tracking-[-0.03em] font-medium text-[#f5ede0]">
            Questions you'll{" "}
            <span className="font-serif-i text-[#b5a8f5]">actually ask.</span>
          </h2>
        </div>

        <Accordion type="single" collapsible className="w-full space-y-3">
          {faqs.map((faq, i) => (
            <AccordionItem
              key={i}
              value={`faq-${i}`}
              className="card-grad border border-[#f5ede0]/8 rounded-xl px-6 data-[state=open]:border-[#b5a8f5]/20 transition-colors"
            >
              <AccordionTrigger className="text-[15px] font-medium text-[#f5ede0] py-5 hover:no-underline text-left">
                {faq.q}
              </AccordionTrigger>
              <AccordionContent className="text-[14px] leading-[1.7] text-[#a8a092] pb-5">
                {faq.a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
};

export default FAQ;
