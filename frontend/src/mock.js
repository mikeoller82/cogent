// Mock data for Viktor.com clone

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
      { label: "Viktor vs ChatGPT", href: "#" },
      { label: "Viktor vs Copilot", href: "#" },
      { label: "Viktor vs Zapier", href: "#" }
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
    title: "Real output, not just text.",
    desc: "Viktor doesn't brainstorm. It ships. PDFs your board can read. Dashboards your team actually uses. Web apps you'd think a developer built.",
    tags: ["PDF", "Excel", "PowerPoint", "Web App"]
  },
  {
    title: "One message, all your tools.",
    desc: "Stripe, Meta Ads, Notion, GitHub. Viktor queries them all in a single run. No tab-switching, no CSV exports.",
    tags: ["Stripe", "Notion", "GitHub", "Meta", "Slack"]
  },
  {
    title: "Never repeat yourself.",
    desc: "Every conversation makes Viktor smarter about your business. It remembers what worked, what didn't, and how you like things done.",
    tags: ["Memory", "Context", "Learning"]
  }
];

export const shiftComparisons = [
  {
    label: "AD SPEND AUDIT",
    other: { name: "ChatGPT", text: "Tells you how to audit your ad spend." },
    viktor: { text: "Audits it.", emphasis: "Hands you the PDF." }
  },
  {
    label: "MEETING FOLLOW-UPS",
    other: { name: "Copilot", text: "Summarizes your meetings." },
    viktor: { text: "Creates the tasks,", emphasis: "sends the follow-ups, updates the CRM." }
  },
  {
    label: "WORKFLOW AUTOMATION",
    other: { name: "Zapier", text: "Follows rules you write." },
    viktor: { text: "Figures out what needs", emphasis: "automating and does it." }
  },
  {
    label: "BUILDING TOOLS",
    other: { name: "Claude Code", text: "Writes the code. You figure out the rest." },
    viktor: { text: "Builds it, ships it,", emphasis: "sends you the link." }
  }
];

export const testimonials = [
  {
    saved: "1-3 hours/week",
    quote: "Viktor is like Claude, but you can interact with him like with a colleague, not an LLM. He can run projects and scheduled tasks in the cloud, and everybody on the team can interact with it.",
    name: "Tobias Giesen",
    title: "CEO, Growably",
    initials: "TG"
  },
  {
    saved: "10+ hours/week",
    quote: "Mindblowing all-in-one AI which does everything in a single solution.",
    name: "Antonín \u0160tětina",
    title: "CEO, KULINA Group",
    initials: "AS"
  },
  {
    saved: "10+ hours/week",
    quote: "Viktor is like the most capable all-round colleague you can imagine.",
    name: "Sam Kopelman",
    title: "CEO, Givr",
    initials: "SK"
  },
  {
    saved: "10+ hours/week",
    quote: "Viktor is an incredible tool - it was almost instantly adopted by the bulk of my team.",
    name: "Boris Wexler",
    title: "CEO, Space Dinosaurs",
    initials: "BW"
  },
  {
    saved: "10+ hours/week",
    quote: "It's kind of blown my mind seeing what Viktor can actually do. I'm having real conversations with my business partner about investing in an AI tool — something we used to only think about when it came to hiring actual people.",
    name: "Robert Tyrrell",
    title: "Owner, TalentBright",
    initials: "RT"
  },
  {
    saved: "10+ hours/week",
    quote: "Viktor is our eyes, ears, and hands. It's made us realize that we might really never have to hire someone.",
    name: "Jordan Dikoum",
    title: "Co-Founder, UniTru Inc.",
    initials: "JD"
  }
];

export const howSteps = [
  {
    n: "/01",
    title: "Connect",
    desc: "Install Viktor from the Slack App Directory or Microsoft Teams. Connect your tools: Stripe, Notion, Google Ads, whatever you use. Takes 2 minutes."
  },
  {
    n: "/02",
    title: "Ask",
    desc: "Talk to Viktor like a colleague. \"Pull our Meta Ads data and compare vs. last month.\" \"Create a Linear issue for the pricing update.\" \"Build me a revenue dashboard.\""
  },
  {
    n: "/03",
    title: "Viktor delivers",
    desc: "Viktor queries your tools, analyzes data, and delivers real outputs: PDFs, spreadsheets, web apps, code. It also schedules recurring tasks and proposes automations you didn't think to ask for."
  }
];

export const useCases = [
  {
    key: "founders",
    label: "Founders & CEOs",
    headline: "One AI coworker that does the analyst work, the marketing work, and the ops work you keep putting off.",
    items: [
      { title: "Live business pulse", desc: "Pulls MRR, churn, CAC, ad spend, and pipeline from Stripe, PostHog, Google Ads, Meta Ads, and your CRM. Delivered to Slack every morning \u2014 no dashboard login needed." },
      { title: "Investor updates on autopilot", desc: "Assembles revenue, burn rate, pipeline, and headcount into a polished board deck or investor email. Monthly. You just hit send." },
      { title: "Outbound that runs itself", desc: "Builds ICP lead lists from Apollo, enriches contacts, launches email sequences via Instantly, and reports what's converting. Repeats weekly." },
      { title: "Internal tools in minutes", desc: "Builds revenue dashboards, client portals, and approval workflows as deployed web apps with database and auth. No engineering tickets. No sprint planning." }
    ]
  },
  {
    key: "marketing",
    label: "Marketing & Growth",
    headline: "Viktor manages your ad accounts, writes your content, builds your pipeline, and reports on all of it. Every day.",
    items: [
      { title: "Full-funnel ad intelligence", desc: "Pulls spend, CAC, CTR, and ROAS across Meta Ads and Google Ads. Flags underperformers, recommends budget shifts, and drafts new ad copy based on what's winning." },
      { title: "Content engine", desc: "Writes SEO blog posts, launch copy, email campaigns, ad scripts, and social drafts. Publishes directly to your CMS or GitHub. Repeats on any schedule." },
      { title: "Pipeline builder", desc: "Sources ICP-matched leads from Apollo, enriches with firmographic data, pushes to HubSpot or Attio, and activates outbound sequences through Instantly. Hands-free." },
      { title: "Stakeholder reporting", desc: "Builds performance reports with charts, narrative, and clear next actions as polished PDFs \u2014 not raw spreadsheet exports. Weekly or on-demand." }
    ]
  },
  {
    key: "engineering",
    label: "Engineering",
    headline: "Viktor writes code, opens PRs, triages bugs, and builds internal tools. Your engineers only work on what matters.",
    items: [
      { title: "Intelligent bug triage", desc: "Monitors support channels, groups duplicate reports, cross-references the codebase, and opens scoped tickets in Linear or Jira with reproduction steps and context." },
      { title: "Code contributions", desc: "Clones your repo, writes fixes on a feature branch, opens pull requests with full context, and drafts release notes. Real commits, real PRs, shipped." },
      { title: "Full-stack internal tools", desc: "Builds and deploys dashboards, admin panels, and ops tools as web apps with database, auth, and hosting. Zero backlog added to the core team." },
      { title: "Incident + error response", desc: "Queries error tracking and logs, summarizes root cause, assigns owners, creates the postmortem checklist, and follows up until every action item closes." }
    ]
  },
  {
    key: "ops",
    label: "Operations & Finance",
    headline: "Viktor eliminates the spreadsheet wrangling, vendor chasing, and report building that eats your ops team alive.",
    items: [
      { title: "Board pack assembly", desc: "Pulls from Stripe, your CRM, Google Sheets, and headcount tools. Delivers a polished investor update with revenue, burn, pipeline, and KPIs \u2014 every month, zero manual assembly." },
      { title: "Document + invoice processing", desc: "Reads invoices and contracts as PDFs, matches line items against agreements, flags anomalies, and queues everything for review. Handles the paperwork." },
      { title: "Forecast + model refresh", desc: "Updates operating models with live data from your tools, highlights where actuals diverge from plan, and surfaces the variances that actually matter." },
      { title: "Cross-team automation", desc: "Tracks missing inputs, nudges owners in Slack, syncs data between tools on schedule, and closes reporting loops \u2014 without you being the bottleneck." }
    ]
  }
];

export const tweets = [
  { name: "Marko Dinic", handle: "@markodinic", text: "Viktor's persistent memory is wild. It actually remembers what I told it three weeks ago about our pricing strategy." },
  { name: "Bilal Bakr", handle: "@bilalbakr", text: "A very smart idea. AI coworker living in Slack is exactly the right form factor." },
  { name: "modi", handle: "@modibuilds", text: "Asked Viktor to audit my Meta Ads. Got a PDF back in 4 minutes with budget recommendations. Insane." },
  { name: "Steven Tey", handle: "@steventey", text: "Congrats on the launch! The product is beautifully crafted." },
  { name: "Raphael Spannocchi", handle: "@rspannocchi", text: "Worked out of the box. Connected Stripe, Notion, and Linear in under 5 minutes." },
  { name: "Joel Willans", handle: "@joelwillans", text: "Loving the updated Viktor. The new model is noticeably sharper." },
  { name: "Clintin Kruger", handle: "@clintinkruger", text: "So excited about Viktor. This is the future of work, no question." },
  { name: "Jowanza Joseph", handle: "@jowanza", text: "The Viktor design is so good. Every detail considered." },
  { name: "Adrian", handle: "@adrianbuilds", text: "Installed Viktor and was immediately impressed. Output quality is on another level." },
  { name: "Mike Chambers", handle: "@mikejc", text: "We are Viktor pilled. Whole team is using it daily." },
  { name: "Shiva", handle: "@shivapatel", text: "Congratulations on Viktor! Best AI launch of the year IMO." }
];

export const faqs = [
  { q: "What is Viktor, exactly?", a: "Viktor is an AI coworker that lives in Slack. It has its own computer in the cloud where it writes and runs code to complete tasks. It's not a chatbot \u2014 it's a colleague that does real work." },
  { q: "How is Viktor different from ChatGPT or other AI assistants?", a: "Most AI tools generate text. Viktor executes. It has a persistent workspace, connects to your actual tools, and performs actions \u2014 sending emails, updating CRMs, building apps, generating reports. You don't copy-paste outputs. Viktor does the work end-to-end." },
  { q: "What can Viktor actually do?", a: "Automate recurring workflows. Pull data from multiple tools. Build and deploy web apps. Create and edit documents. Browse the web. Research competitors. Generate reports. Anything you can describe, Viktor can probably code and execute." },
  { q: "What tools does Viktor connect to?", a: "Over 3,000 \u2014 including Salesforce, HubSpot, Linear, Notion, Jira, Stripe, GitHub, Google Drive, Slack, and more. If your tool isn't supported, Viktor can build a custom integration." },
  { q: "Is my data secure?", a: "Yes. Each user gets an isolated compute environment. Viktor only accesses tools you explicitly connect. Data is encrypted in transit and at rest. We don't train on your data." },
  { q: "Does Viktor have access to all my Slack messages?", a: "Viktor only sees channels it's invited to. You control where Viktor can read and respond. It remembers context to be helpful, but you can remove it from any channel at any time." },
  { q: "How does Viktor learn about my team?", a: "Viktor reads conversations in channels it joins, observes workflows, and builds a knowledge base over time. It documents what it learns in 'skills' \u2014 internal notes it references to work more effectively with your team." },
  { q: "Can Viktor make mistakes?", a: "Yes. Viktor is capable, not infallible. It double-checks its work and asks for confirmation before high-stakes actions like sending emails or deploying to production. You stay in control." },
  { q: "How long does setup take?", a: "Minutes. Install Viktor in Slack, connect the tools you want, and start working. Viktor handles onboarding itself \u2014 it'll introduce itself and ask what you need help with." },
  { q: "Can multiple people on my team use Viktor?", a: "Yes. Viktor works across your Slack workspace. Anyone can mention @Viktor. It maintains context about the whole team while respecting individual preferences." }
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
