export const navLinks = [
  {
    label: "Product",
    items: [
      { label: "Loop Engineering", href: "#loop" },
      { label: "Features", href: "#features" },
      { label: "How it works", href: "#how" },
      { label: "Integrations", href: "#" },
    ]
  },
  { label: "Use Cases", href: "#usecases" },
  {
    label: "Resources",
    items: [
      { label: "Docs", href: "#" },
      { label: "The Paper", href: "#paper" },
      { label: "Blog", href: "#" },
      { label: "GitHub", href: "#" },
    ]
  },
  { label: "Pricing", href: "#" },
];

export const loopComponents = [
  {
    id: "goal",
    label: "Goal Representation",
    icon: "🎯",
    desc: "Structured task definition with constraints, success criteria, and stop conditions. The agent has a fixed reference point — not just a prompt.",
    color: "#b5a8f5",
  },
  {
    id: "state",
    label: "State Model",
    icon: "🧠",
    desc: "Five differentiated layers: static (goal), dynamic (outputs), tool (availability), reflective (lessons), governance (budget). Not crammed into one context.",
    color: "#60a5fa",
  },
  {
    id: "action",
    label: "Action Executor",
    icon: "⚡",
    desc: "Controlled boundary around every tool call. Each action passes a risk check before execution — the difference between an agent that can do anything and one that must ask.",
    color: "#22c55e",
  },
  {
    id: "observe",
    label: "Observation Collector",
    icon: "👁️",
    desc: "Captures what actually happened — not what the agent intended. LLMs are famously bad at self-assessment; the collector resolves the gap.",
    color: "#f59e0b",
  },
  {
    id: "evaluate",
    label: "Evaluator",
    icon: "📊",
    desc: "Assesses four signals every iteration: confidence, progress, drift, and risk. Knows when the agent is spinning wheels or veering off course.",
    color: "#ef4444",
  },
  {
    id: "control",
    label: "Controller",
    icon: "🛡️",
    desc: "The decision-maker. Given the evaluation, it decides: continue, revise, rollback, escalate to a human, or stop. Most agents lack this entirely.",
    color: "#a78bfa",
  },
];

export const featureBlocks = [
  {
    title: "MCP Tools",
    subtitle: "350+ integrations, one protocol",
    desc: "Cogent connects to the Model Context Protocol ecosystem — GitHub MCP, Linear, Notion, Stripe, n8n, Playwright, and 350+ servers. Each tool call passes through the governance layer before execution.",
    tags: ["GitHub MCP", "Linear", "Notion", "Stripe", "n8n"],
    visual: "mcp",
  },
  {
    title: "Skill Orchestration",
    subtitle: "Discover, forge, activate",
    desc: "A portable skills system that discovers skills from .cogent/skills/, imports from any GitHub repo, and forges new ones from code analysis. Each skill bundles instructions, scripts, and assets. Activated at runtime via tool call.",
    tags: ["SKILL.md", "Forge", "Import", "Catalog"],
    visual: "skills",
  },
  {
    title: "Persistent Memory",
    subtitle: "Learns once, remembers forever",
    desc: "Cross-session memory with a markdown KV store. Cogent documents what it learns about your business — tone, customers, KPIs, decisions — and carries context across conversations. Every fact is traceable.",
    tags: ["MEMORY.md", "USER.md", "Cross-session", "Context"],
    visual: "memory",
  },
  {
    title: "Governed Execution",
    subtitle: "Plan → Execute → Verify → Govern",
    desc: "Every task runs through an iterative refinement loop with maker/checker split, budget management, circuit-breaker stagnation detection, and risk-checked action boundaries. Governance runs every iteration, not just at exceptions.",
    tags: ["Loop", "Budget", "Circuit Breaker", "Risk"],
    visual: "govern",
  },
];

export const howSteps = [
  {
    n: "/01",
    title: "Install & Connect",
    desc: "Add Cogent to Slack, Teams, or open the web app. Authorize the tools you actually use — CRM, GitHub, Stripe, Notion. The whole thing takes about two minutes."
  },
  {
    n: "/02",
    title: "Describe the Goal",
    desc: "Brief Cogent the same way you'd brief a teammate. Include constraints, success criteria, and what 'done' looks like. The more structure you give, the sharper the result."
  },
  {
    n: "/03",
    title: "Governed Loop",
    desc: "Cogent plans, executes, verifies, and governs — every iteration. The controller evaluates confidence, progress, drift, and risk before each action. No runaway loops, no ungoverned API calls."
  },
  {
    n: "/04",
    title: "Ship the Output",
    desc: "Polished PDFs, deployed web apps, updated CRMs, scheduled reports. Cogent ships finished work — not screenshots and to-dos. It also suggests recurring runs you didn't think to schedule."
  }
];

export const useCases = [
  {
    key: "founders",
    label: "Founders & CEOs",
    headline: "A governed AI coworker that handles the analyst work, the ops work, and the reporting you keep deferring.",
    items: [
      { title: "Live business pulse", desc: "Pulls MRR, churn, CAC, ad spend, and pipeline from Stripe, PostHog, and your CRM. Governed execution — every data pull is risk-checked and logged." },
      { title: "Investor updates on autopilot", desc: "Assembles revenue, runway, pipeline, and headcount into a clean monthly investor deck. The loop verifies accuracy before shipping." },
      { title: "Internal tools in minutes", desc: "Builds dashboards, portals, and approval flows as deployed web apps with database and auth. The controller gates deployment until verification passes." },
      { title: "Metric-driven governance", desc: "Set risk budgets and cost thresholds. Cogent escalates to you before exceeding either — no surprise bills." }
    ]
  },
  {
    key: "marketing",
    label: "Marketing & Growth",
    headline: "Cogent watches your ad accounts, writes your content, builds your pipeline — and governors every action.",
    items: [
      { title: "Full-funnel ad intelligence", desc: "Tracks spend, CAC, CTR, and ROAS across Meta and Google. The evaluator flags underperformers and recommends shifts based on confidence and drift signals." },
      { title: "Governed content engine", desc: "Writes SEO posts, email campaigns, and social drafts. Every output passes the evaluator's quality check before publishing." },
      { title: "Pipeline builder", desc: "Sources matched leads, enriches with firmographic data, syncs to HubSpot. The controller decides when to batch operations to stay within risk budget." },
      { title: "Stakeholder reporting", desc: "Ships performance reports with charts, narrative, and next actions as polished PDFs. Each report is verified against source data." }
    ]
  },
  {
    key: "engineering",
    label: "Engineering",
    headline: "Cogent writes code, opens PRs, triages bugs, and builds tools — with governance on every action.",
    items: [
      { title: "Governed bug triage", desc: "Watches support channels, dedupes reports, cross-references the codebase, and opens scoped tickets. The evaluator assesses reproduction confidence before escalating." },
      { title: "Code contributions with guardrails", desc: "Clones the repo, writes the fix on a branch, opens a PR with context, and drafts the release note. The controller verifies against coding standards before pushing." },
      { title: "Full-stack internal tools", desc: "Builds and deploys dashboards, admin panels, and ops tools as web apps. Each deployment is pre-verified in the loop." },
      { title: "Incident response", desc: "Queries logs and error tracking, summarizes root cause, assigns owners, and writes the postmortem. The loop traces every action for audit." }
    ]
  },
  {
    key: "ops",
    label: "Operations & Finance",
    headline: "Cogent absorbs the spreadsheet wrangling, vendor chasing, and report building — governed so you stay in control.",
    items: [
      { title: "Board pack assembly", desc: "Pulls from Stripe, CRM, Sheets, and headcount tools. Ships the monthly board update with revenue, burn, and KPIs. The controller verifies consistency before delivery." },
      { title: "Document + invoice processing", desc: "Reads invoices and contracts, matches line items against agreements, flags anomalies. High-risk actions queue for human approval via the escalation gate." },
      { title: "Model + forecast refresh", desc: "Updates operating models with live data, highlights where actuals diverge from plan. The evaluator tracks drift from projections." },
      { title: "Cross-team automation", desc: "Tracks missing inputs, nudges owners, syncs data on schedule. The controller manages the task queue within configured risk and iteration budgets." }
    ]
  }
];

export const paperHighlights = [
  {
    quote: "The smarter the model gets, the more damage it can do before you realize something went wrong.",
    author: "Mike Oller",
    context: "Loop Engineering paper"
  },
  {
    quote: "Governance checks must run every iteration rather than only at exception points, because there is no design-time map of which iterations might fail.",
    author: "Mike Oller",
    context: "Loop Engineering paper"
  },
  {
    quote: "A controller that logs a risk classification on every action but never withholds approval is not governing; it is narrating.",
    author: "Mike Oller",
    context: "Loop Engineering paper"
  },
  {
    quote: "Instead of asking 'how do we make the model smarter?' it asks 'how do we build a governance architecture that wraps around the model?'",
    author: "Mike Oller",
    context: "Loop Engineering paper"
  },
  {
    quote: "Most agent systems collapse all of this into a single context window. Loop engineering explicitly separates them so the agent can distinguish between 'what I'm trying to do,' 'what I've done,' and 'what I've learned.'",
    author: "Mike Oller",
    context: "Loop Engineering paper"
  }
];

export const tweets = [
  { name: "Marcus Dean", handle: "@marcusdean", text: "Cogent actually remembers context from two weeks ago. That alone makes it a different category of tool." },
  { name: "Bella K.", handle: "@bellakat", text: "An AI coworker that lives where the work happens. Obvious in hindsight, hard to build, very fun to use." },
  { name: "Mo", handle: "@mobuilds", text: "Asked Cogent to audit our Meta spend. Four minutes later: a PDF with budget recommendations. The governance trace was a nice surprise." },
  { name: "Steven Lee", handle: "@stevenlee", text: "Cogent ships. Polished product, considered onboarding, weirdly delightful that it shows you its evaluation signals." },
  { name: "Rafael S.", handle: "@rafsfeed", text: "Connected Stripe, Notion, and Linear in five minutes. The loop trace is basically an audit log for every decision." },
  { name: "Joel W.", handle: "@joelw", text: "The controller step is what sold me. Finally an agent that knows when to stop and ask for help." },
  { name: "Clintin K.", handle: "@clintink", text: "Quietly excited about Cogent. The loop engineering approach is the form factor agents should have shipped in." },
  { name: "Adrian", handle: "@adrianbuilds", text: "The Cogent UI is so good. And the governance layer means I actually trust it with production access." },
  { name: "Shiva", handle: "@shivapatel", text: "Congrats on Cogent. Best AI launch I've seen in a while. The loop trace alone is worth the onboarding time." }
];

export const faqs = [
  { q: "What is Cogent, exactly?", a: "Cogent is an AI coworker built on Loop Engineering — a governance-first architecture where every action is planned, executed, verified, and governed. It lives in Slack, Teams, and on the web, and completes real tasks end-to-end with traceable decision logs." },
  { q: "What is Loop Engineering?", a: "Loop Engineering is a framework for reliable AI agents. It defines six components — goal representation, state model, action executor, observation collector, evaluator, and controller — that together form a governed execution loop. Every iteration is checked before the next begins." },
  { q: "How is Cogent different from ChatGPT?", a: "ChatGPT talks. Cogent acts — with governance. It has a persistent workspace, connects to your tools through MCP, executes plans through a governed loop, and ships real outputs. You don't copy-paste; Cogent deploys, emails, and updates." },
  { q: "What does 'governed execution' mean?", a: "Every action passes through a controller that evaluates confidence, progress, drift from goal, and risk before proceeding. If an action exceeds risk budget or shows high drift, the controller escalates to you or stops entirely. Governance isn't a one-time review — it runs every iteration." },
  { q: "What can Cogent actually do?", a: "Automate recurring workflows, pull data from multiple tools via MCP, build and deploy web apps, generate reports, write code, open PRs, run web research, draft content, schedule tasks, and activate skills. Anything you can describe as a goal with constraints." },
  { q: "Which tools does it connect to?", a: "350+ MCP servers — GitHub, Linear, Notion, Stripe, n8n, Playwright, Slack, and more. Each integration passes through the action executor's risk check. If your tool isn't in the registry, Cogent can often build a custom integration on the fly." },
  { q: "What is the Skills system?", a: "Skills are portable instruction bundles that teach Cogent specialized capabilities. Each skill has a SKILL.md file with instructions, scripts, and assets. Cogent discovers them automatically, can forge new ones from code analysis, and activates them at runtime." },
  { q: "Is my data secure?", a: "Yes. Each workspace gets an isolated compute environment. The governance layer logs every action in a traceable loop record — you can replay exactly what Cogent did and why. Data is encrypted in transit and at rest. We don't train on your data." },
  { q: "How does memory work?", a: "Cogent maintains a persistent markdown KV store across sessions. It documents facts about your business, team preferences, past decisions, and KPIs. Every memory entry is traceable to the conversation that created it. You can review and clear memory at any time." },
  { q: "Can Cogent make mistakes?", a: "Yes — it's capable, not infallible. That's exactly why the governance layer exists. The evaluator checks confidence and risk before every action. The controller gates high-stakes operations behind human escalation. You stay in control." },
  { q: "How long does setup take?", a: "Minutes. Install Cogent, connect a few MCP servers, and describe your first task. Cogent handles its own onboarding — it'll introduce itself and ask what you need first." }
];

export const footerCols = [
  {
    title: "Product",
    links: ["Features", "Loop Engineering", "MCP Integrations", "Pricing", "Changelog"]
  },
  {
    title: "Use Cases",
    links: ["Founders & CEOs", "Marketing", "Engineering", "Operations", "Enterprise"]
  },
  {
    title: "Resources",
    links: ["Documentation", "The Paper", "Blog", "GitHub", "Community"]
  },
  {
    title: "Company",
    links: ["About", "Careers", "Security", "Privacy", "Terms"]
  }
];
