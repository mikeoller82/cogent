// Mock data for Cogent landing page (original copy under the Cogent brand)

export const navLinks = [
  {
    label: "Product",
    items: [
      { label: "How it works", href: "#how" },
      { label: "Integrations", href: "#" },
      { label: "Security", href: "#" },
      { label: "Changelog", href: "#" }
    ]
  },
  { label: "Enterprise", href: "#" },
  {
    label: "Resources",
    items: [
      { label: "Blog", href: "#" },
      { label: "Docs", href: "#" },
      { label: "Customer stories", href: "#" },
      { label: "Help center", href: "#" }
    ]
  },
  {
    label: "Compare",
    items: [
      { label: "Cogent vs ChatGPT", href: "#" },
      { label: "Cogent vs Copilot", href: "#" },
      { label: "Cogent vs Zapier", href: "#" }
    ]
  },
  {
    label: "Solutions",
    items: [
      { label: "Founders & CEOs", href: "#usecases" },
      { label: "Marketing & Growth", href: "#usecases" },
      { label: "Engineering", href: "#usecases" },
      { label: "Operations & Finance", href: "#usecases" }
    ]
  }
];

export const builtByLogos = [
  { name: "Meta AI", text: "Meta AI" },
  { name: "Oxford", text: "OXFORD" },
  { name: "Google", text: "Google" },
  { name: "Tesla", text: "TESLA" },
  { name: "Amazon", text: "amazon" }
];

export const backedByLogos = [
  { name: "NFDG", text: "NFDG" },
  { name: "BEK", text: "bek" }
];

export const featureBlocks = [
  {
    title: "Outputs, not opinions.",
    desc: "Cogent ships finished work. Polished PDFs you can email. Dashboards your team actually opens. Tiny web apps deployed to a real URL — not screenshots and to-dos.",
    tags: ["PDF", "Excel", "PowerPoint", "Web App"]
  },
  {
    title: "One ask, every system.",
    desc: "Stripe, Notion, GitHub, Meta Ads, your CRM. Cogent reaches into all of them in a single turn. No tab juggling, no exports, no glue scripts.",
    tags: ["Stripe", "Notion", "GitHub", "Meta", "Slack"]
  },
  {
    title: "Learns once. Remembers forever.",
    desc: "Every conversation makes Cogent sharper about your business. Tone, customers, KPIs, what shipped, what flopped — it keeps the context so you don't repeat yourself.",
    tags: ["Memory", "Context", "Learning"]
  }
];

export const shiftComparisons = [
  {
    label: "AD SPEND AUDIT",
    other: { name: "ChatGPT", text: "Explains how to audit your ad spend." },
    cogent: { text: "Does the audit.", emphasis: "Hands you the PDF." }
  },
  {
    label: "MEETING FOLLOW-UPS",
    other: { name: "Copilot", text: "Summarizes the meeting." },
    cogent: { text: "Creates the tasks,", emphasis: "sends the follow-ups, updates the CRM." }
  },
  {
    label: "WORKFLOW AUTOMATION",
    other: { name: "Zapier", text: "Runs the rules you wrote." },
    cogent: { text: "Spots what needs automating", emphasis: "and wires it up itself." }
  },
  {
    label: "BUILDING TOOLS",
    other: { name: "Claude Code", text: "Writes the code. You run it." },
    cogent: { text: "Builds it, deploys it,", emphasis: "sends you the live link." }
  }
];

export const testimonials = [
  {
    saved: "1-3 hours/week",
    quote: "It feels like hiring a junior analyst who never sleeps. I send a message in Slack and a polished report shows up before standup.",
    name: "Mariana Ortiz",
    title: "Head of Ops, Lumen Health",
    initials: "MO"
  },
  {
    saved: "10+ hours/week",
    quote: "Cogent took over our weekly ad readout. The team gets a fresh PDF every Monday with notes and recommendations. We haven't built a slide in months.",
    name: "Kenji Park",
    title: "Growth Lead, Forge Labs",
    initials: "KP"
  },
  {
    saved: "10+ hours/week",
    quote: "The closest thing to a generalist hire I've used. It writes, it researches, it ships small tools — and it remembers what we already decided.",
    name: "Priya Anand",
    title: "Founder, Stackline",
    initials: "PA"
  },
  {
    saved: "10+ hours/week",
    quote: "Adoption was almost suspiciously fast. Two days in and half the team was tagging Cogent for anything that smelled like busy work.",
    name: "Daniel Owusu",
    title: "COO, Northbeam Studio",
    initials: "DO"
  },
  {
    saved: "10+ hours/week",
    quote: "I keep catching myself reaching for it before I reach for a person. That's either delightful or terrifying. Probably both.",
    name: "Hana Brennan",
    title: "Operator, TalentBright",
    initials: "HB"
  },
  {
    saved: "10+ hours/week",
    quote: "For a two-person team, this is roughly the difference between drowning and floating. Cogent handles the work we'd otherwise punt on.",
    name: "Eli Vargas",
    title: "Co-Founder, UniTru",
    initials: "EV"
  }
];

export const howSteps = [
  {
    n: "/01",
    title: "Connect",
    desc: "Install Cogent in Slack or Teams. Authorize the tools you actually use — Stripe, Notion, GitHub, your CRM. The whole thing takes about two minutes."
  },
  {
    n: "/02",
    title: "Ask",
    desc: "Talk to Cogent the same way you'd brief a teammate. \"Pull our Q3 numbers and draft the investor update.\" \"Open a ticket and assign it to Alex.\" \"Build me a tiny revenue dashboard.\""
  },
  {
    n: "/03",
    title: "Cogent delivers",
    desc: "It queries your systems, does the work, and ships outputs you can use immediately — PDFs, spreadsheets, web apps, code. It also suggests recurring runs you didn't think to schedule."
  }
];

export const useCases = [
  {
    key: "founders",
    label: "Founders & CEOs",
    headline: "One coworker that handles the analyst work, the marketing work, and the ops work you keep deferring.",
    items: [
      { title: "Live business pulse", desc: "Pulls MRR, churn, CAC, ad spend, and pipeline from Stripe, PostHog, and your CRM. Lands in your inbox or Slack every morning." },
      { title: "Investor updates on autopilot", desc: "Assembles revenue, runway, pipeline, and headcount into a clean monthly investor email or deck. You read it and hit send." },
      { title: "Outbound that maintains itself", desc: "Builds ICP lead lists, enriches contacts, launches sequences, and reports what's converting. Restarts itself every week." },
      { title: "Internal tools in minutes", desc: "Builds dashboards, portals, and approval flows as deployed web apps with database and auth. No backlog, no sprint planning." }
    ]
  },
  {
    key: "marketing",
    label: "Marketing & Growth",
    headline: "Cogent watches your ad accounts, writes your content, builds your pipeline, and reports on all of it. Daily.",
    items: [
      { title: "Full-funnel ad intelligence", desc: "Tracks spend, CAC, CTR, and ROAS across Meta and Google. Flags underperformers, recommends shifts, drafts new creative based on winners." },
      { title: "Content engine", desc: "Writes SEO posts, launch copy, email campaigns, and social drafts. Publishes to your CMS or GitHub on whatever cadence you set." },
      { title: "Pipeline builder", desc: "Sources matched leads, enriches with firmographic data, syncs to HubSpot or Attio, and triggers outbound. Hands-free." },
      { title: "Stakeholder reporting", desc: "Ships performance reports with charts, narrative, and next actions as polished PDFs — not raw exports." }
    ]
  },
  {
    key: "engineering",
    label: "Engineering",
    headline: "Cogent writes code, opens PRs, triages bugs, and builds internal tools so your engineers stay on the real roadmap.",
    items: [
      { title: "Bug triage that thinks", desc: "Watches support channels, dedupes reports, cross-references the codebase, and opens scoped tickets with repro steps." },
      { title: "Real code contributions", desc: "Clones the repo, writes the fix on a branch, opens a PR with context, and drafts the release note. Real commits, shipped." },
      { title: "Full-stack internal tools", desc: "Builds and deploys dashboards, admin panels, and ops tools as web apps with database, auth, and hosting included." },
      { title: "Incident response", desc: "Queries logs and error tracking, summarizes root cause, assigns owners, and writes the postmortem checklist." }
    ]
  },
  {
    key: "ops",
    label: "Operations & Finance",
    headline: "Cogent absorbs the spreadsheet wrangling, vendor chasing, and report building that eats your team's day.",
    items: [
      { title: "Board pack assembly", desc: "Pulls from Stripe, your CRM, Sheets, and headcount tools. Ships the monthly board update with revenue, burn, and KPIs — zero manual assembly." },
      { title: "Document + invoice processing", desc: "Reads invoices and contracts, matches line items against agreements, flags anomalies, and queues them for review." },
      { title: "Model + forecast refresh", desc: "Updates operating models with live data, highlights where actuals diverge from plan, and surfaces the variances that matter." },
      { title: "Cross-team automation", desc: "Tracks missing inputs, nudges owners, syncs data on schedule, and closes reporting loops so you're not the bottleneck." }
    ]
  }
];

export const tweets = [
  { name: "Marcus Dean", handle: "@marcusdean", text: "Cogent actually remembers context from two weeks ago. That alone makes it a different category of tool." },
  { name: "Bella K.", handle: "@bellakat", text: "An AI coworker that lives where the work happens. Obvious in hindsight, hard to build, very fun to use." },
  { name: "Mo", handle: "@mobuilds", text: "Asked Cogent to audit our Meta spend. Four minutes later: a PDF with budget recommendations. Wild." },
  { name: "Steven Lee", handle: "@stevenlee", text: "Cogent shipped. Polished product, considered onboarding, weirdly delightful empty states." },
  { name: "Rafael S.", handle: "@rafsfeed", text: "Worked out of the box. Connected Stripe, Notion, and Linear in under five minutes." },
  { name: "Joel W.", handle: "@joelw", text: "Loving the new release. The latest model is noticeably sharper at multi-step tasks." },
  { name: "Clintin K.", handle: "@clintink", text: "Quietly excited about Cogent. This is the form factor agents should have shipped in." },
  { name: "Jo Allen", handle: "@joallen", text: "The Cogent UI is so good. Every micro-interaction is considered." },
  { name: "Adrian", handle: "@adrianbuilds", text: "Installed Cogent and immediately impressed. Output quality is on another level." },
  { name: "Mike Chambers", handle: "@mikejc", text: "Whole team is Cogent-pilled. We use it daily for things we used to schedule meetings about." },
  { name: "Shiva", handle: "@shivapatel", text: "Congrats on Cogent. Best AI launch I've seen in a while." }
];

export const faqs = [
  { q: "What is Cogent, exactly?", a: "Cogent is an AI coworker. It lives in Slack (and on the web), runs on its own cloud workspace where it can read, write, and run code, and completes real tasks end-to-end — not just generates text about them." },
  { q: "How is Cogent different from ChatGPT?", a: "ChatGPT talks. Cogent acts. It has a persistent workspace, connects to your tools, and performs real actions — building PDFs, deploying apps, updating CRMs, sending emails. You don't copy-paste outputs; Cogent ships them." },
  { q: "What can Cogent actually do?", a: "Automate recurring workflows, pull data from multiple tools, build and deploy small web apps, generate reports and documents, run web research, draft content, schedule itself. Anything you can describe in a sentence, Cogent can usually code and execute." },
  { q: "Which tools does it connect to?", a: "3,000+ integrations — Salesforce, HubSpot, Linear, Notion, Jira, Stripe, GitHub, Google Drive, Slack, and more. If your tool isn't supported, Cogent can usually build a custom integration on the fly." },
  { q: "Is my data secure?", a: "Yes. Each workspace gets an isolated compute environment. Cogent only touches tools you explicitly connect. Data is encrypted in transit and at rest. We don't train on your data." },
  { q: "Does Cogent read all my Slack messages?", a: "Only channels it's invited to. You decide where it has access. It remembers context to be useful, but you can remove it from any channel at any time." },
  { q: "How does it learn about my team?", a: "By reading the channels it joins, observing your workflows, and building a private knowledge base over time. It documents what it learns so it gets sharper with use." },
  { q: "Can Cogent make mistakes?", a: "Yes. It's capable, not infallible. It double-checks its work and asks for confirmation before high-stakes actions like sending emails or deploying. You stay in control." },
  { q: "How long does setup take?", a: "Minutes. Install Cogent, connect a few tools, and start working. It handles its own onboarding — it'll introduce itself and ask what you need first." },
  { q: "Can my whole team use it?", a: "Yes. Cogent works across your workspace. Anyone can tag it. It keeps context about the team while respecting individual preferences." }
];

export const footerCols = [
  {
    title: "Product",
    links: ["How it works", "Integrations", "Pricing", "Changelog", "Roadmap"]
  },
  {
    title: "Solutions",
    links: ["Founders & CEOs", "Marketing", "Engineering", "Operations", "Enterprise"]
  },
  {
    title: "Resources",
    links: ["Blog", "Docs", "Help center", "Customer stories", "Community"]
  },
  {
    title: "Company",
    links: ["About", "Careers", "Security", "Privacy", "Terms"]
  }
];
