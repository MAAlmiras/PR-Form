# Concept board: Internal Purchase Request system

Working document for the concept stage. It collects what we have **decided**, what is **assumed** and still needs a yes or no, and what is **open**. Nothing here is the PRD yet. Once every item marked *Before PRD* is closed, this board becomes the input for the PRD.

IDs stay stable so we can refer to them in chat ("Q-14: yes").

---

## 1. How we work

| Stage | Output | Who reviews | Gate to move on |
|---|---|---|---|
| 1. Concept (now) | This board, process maps (BPMN 2.0, HTML) | Mohamed | Every *Before PRD* question closed |
| 2. PRD | `docs/PRD.md` | Product/project manager agent, senior full-stack engineer agent, then Mohamed | Mohamed approves the PRD |
| 3. UI/UX | Screens, user journeys, clickable prototype | UI/UX reviewer agent | All UI/UX comments closed |
| 4. Implementation plan | Phases with dependencies, added to the PRD | Senior full-stack engineer agent, cybersecurity auditor agent | Mohamed approves the plan |
| 5. Build, phase by phase | Code, tests, release notes | Senior full-stack engineer agent each phase; other auditors when Mohamed calls them | Phase passes review with no regressions |

Reviewers are only called at the stages above or when Mohamed asks.

## 2. The team

| Agent | Role | Called at |
|---|---|---|
| Claude (this session) | Orchestrator and programmer. Drafts documents, writes code, runs reviews, reports back. | Always |
| Product / project manager | Leads scope and priorities. Challenges the PRD for gaps, conflicts, unclear acceptance criteria and scope creep. | PRD, phase planning |
| UI/UX reviewer and auditor | Usability, mobile-first, accessibility (WCAG 2.2 AA), Arabic/RTL, brand compliance, journey friction. | UI/UX stage, then on request |
| Senior full-stack engineer | Implements and reviews code. Reviews PRD and plan for feasibility, architecture, data model, testing, regressions. | PRD, plan, every build phase |
| Cybersecurity auditor | Auth, OTP, signatures, sealing, secrets, OWASP ASVS / Top 10, Microsoft 365 permissions, audit trail, privacy (PDPL). | Plan, before go-live, on request |

The agents will be defined as Claude Code subagents in `.claude/agents/`, each told to read this board, the PRD and the process maps first so they share full context.

## 3. Vision and roadmap

The purchase request system is the first module of a larger internal operations platform for the group:

1. **Internal purchase requests** (this project): request, stock check, procurement approval, signed PDF.
2. **Store and inventory management**: stock levels per store, receipts, issues to projects. Will fill "available in store" automatically.
3. **Procurement**: supplier list, quotations, purchase orders, invoices, checked against internal standards.

What this means for design now:

- Build a shared core that later modules reuse: companies, users and roles, projects and cost centres, item and unit master data, approval and signing, PDF and sealing, notifications, audit trail.
- Keep the PR module self-contained on top of that core.
- Hosting starts on Railway and may move to AWS, pay per use. Use only portable building blocks (containers, PostgreSQL, S3-compatible file storage, standard SMTP or Graph for email) so the move is a deployment change, not a rewrite.

## 4. Decided

| ID | Decision | Source |
|---|---|---|
| D-01 | Signatures are built into the app (option A): Microsoft 365 sign-in, email code at signing, content fingerprint, PAdES seal with trusted timestamp, audit trail. No external signature provider. | Chat, signature research |
| D-02 | Each company adopts an internal e-signature policy naming this system as the agreed signing method. | Chat |
| D-03 | Signing check: a 6-digit code emailed to the signer. No fresh Microsoft sign-in at signing. | Chat |
| D-04 | No Microsoft Authenticator. Our own server sends the codes. | Chat |
| D-05 | Login with Microsoft 365 accounts. Every signer has one. | Chat |
| D-06 | Each user draws or uploads a signature image once, in their settings. It appears on every PDF they sign. | Chat |
| D-07 | Signing order: requester, then store manager, then procurement. The PR reaches procurement for a PO only after all three have signed. | Chat |
| D-08 | Rejection at any step sends the PR back to the requester. After editing, the whole cycle starts again and earlier signatures are voided. | Chat |
| D-09 | Emails go out from a shared mailbox for the app. | Chat |
| D-10 | A PDF can be exported at any stage, built from one standard template that matches the company's current paper form. | Chat, form shared |
| D-11 | Multiple companies. The super admin creates companies; each company's settings (logo, CR number, colours, details) drive its PDFs. | Chat |
| D-12 | The technical admin is a super admin who can see and control everything. | Chat |
| D-13 | Other departments (HR, accounts and so on) can raise requests with a role like the project manager's. | Chat |
| D-14 | Mobile-first. Creating a PR and doing the store check must take as few steps as possible. | Chat |
| D-15 | Hosting on Railway first; possible move to AWS later. No data-residency requirement. | Chat |
| D-16 | The app uses Almiras branding. | Chat |
| D-17 | UI built with shadcn/ui components. Theme ("skin") still to be confirmed (Q-02). | Chat |
| D-18 | Process maps in BPMN 2.0, viewable in HTML. | Chat |
| D-19 | Private repository; brand fonts are kept in it. | Chat |

## 5. Assumptions to confirm

| ID | Assumption | If wrong |
|---|---|---|
| A-01 | All companies are in **one** Microsoft 365 tenant (one group tenant). | We need multi-tenant sign-in and per-company mailboxes. |
| A-02 | One shared mailbox for the whole group sends all emails (for example `pr@almiras.sa`). | Per-company sender addresses. |
| A-03 | A person can belong to more than one company, with a different role in each. | Simpler user model. |
| A-04 | Each company has its own store manager(s) and procurement team; they are not shared across the group. | Shared group procurement changes routing. |
| A-05 | The email code is also required at **login** on a new device, then the device is trusted for 30 days. Every signature always needs a fresh code. | Codes only at signing. |
| A-06 | One signer per step. Any user holding the role in that company can act on the step (first come, first served). | Named signers per project, or several signers per step. |
| A-07 | "Qty" on the form means the total needed; procurement buys Qty minus Available in store. | Qty already means "to buy". |
| A-08 | Interface in English and Arabic (with right-to-left layout); the PDF stays bilingual as in the sample. | English only for now. |
| A-09 | PR numbers follow `<company code>-PR-<year>-<4-digit sequence>`, restarting each year. | Different numbering. |
| A-10 | Records are kept at least 10 years (Saudi commercial record keeping) and never deleted, only cancelled. | Shorter retention. |
| A-11 | BPMN diagrams are drawn as real BPMN 2.0 XML and shown in HTML with bpmn-js, so they also open in standard BPMN tools. | Hand-drawn HTML diagrams. |

## 6. Open questions

Priority: **Now** = shapes the process maps; **Before PRD** = must be answered before writing the PRD; **Later** = can wait until UI or build.

### Organisation, users and roles

| ID | Question | Priority |
|---|---|---|
| Q-01 | Do you mean a **product** manager (owns what we build) or a **project** manager (owns plan and timeline)? You used both. | Now |
| Q-02 | Which shadcn/ui skill and which skin? (Not installed yet; send the command or link.) | Before PRD |
| Q-03 | Besides super admin, do we need a **company admin** who manages users, projects and settings for one company only? | Now |
| Q-04 | Who creates projects and assigns requesters to them? Can a requester raise PRs on any project of the company, or only assigned ones? | Now |
| Q-05 | For HR, accounts and other departments, is the "project" field replaced by a **department / cost centre**? | Now |
| Q-06 | Delegation: when a store manager or procurement person is on leave, who signs? (Deputy, or the super admin reassigns.) | Before PRD |
| Q-07 | Do we need a read-only role (for example finance, management, internal audit)? | Before PRD |

### The PR process

| ID | Question | Priority |
|---|---|---|
| Q-08 | If the store has **everything** in stock, does the PR stop at the store (fulfilled from stock), or still go to procurement? | Now |
| Q-09 | Does the store manager **issue** stock to the project at this point, or only report what is available? | Now |
| Q-10 | Can the store manager or procurement **edit** lines (for example cut a quantity), or only approve or return? | Now |
| Q-11 | Can a reviewer return or reject **single lines**, or always the whole PR? | Now |
| Q-12 | Is there a difference between **return for correction** (goes back to requester) and **reject / cancel** (PR is closed for good)? | Now |
| Q-13 | Can the requester withdraw or cancel a PR after submitting it? | Now |
| Q-14 | Is there a value or urgency rule that adds an extra approver (for example a GM above a limit)? Do PRs carry estimated prices at all? | Now |
| Q-15 | After approval, what happens in this system: does procurement record the PO number, attach the PO, and mark the PR as ordered, delivered, closed? | Now |
| Q-16 | Urgent requests: do we need an "urgent" flag with faster reminders? | Before PRD |
| Q-17 | Reminders and escalation: after how long without action do we remind, and do we escalate to someone? | Before PRD |

### Items and the form

| ID | Question | Priority |
|---|---|---|
| Q-18 | Free-text item descriptions, or pick from an item list that grows over time? (An item list now makes the inventory module much easier later.) | Before PRD |
| Q-19 | Fixed list of units managed by the admin, or free text? | Before PRD |
| Q-20 | Attachments on a PR or line (site photos, drawings, specs)? Shown on the PDF? | Before PRD |
| Q-21 | Extra header fields beyond the paper form: required-by date, deliver-to location, notes? (The sample added them.) | Before PRD |
| Q-22 | Maximum lines per PR? The paper form fits about 25; the PDF can run to more pages. | Later |
| Q-23 | Do we add a "Qty to purchase" column to the PDF, or keep exactly the six columns of the paper form? | Later |

### Signing, login and security

| ID | Question | Priority |
|---|---|---|
| Q-24 | Code rules: proposed 6 digits, valid 10 minutes, 5 wrong tries then a 15-minute lock. OK? | Before PRD |
| Q-25 | If a user has not saved a signature image, block signing, or print their typed name in a signature style? | Before PRD |
| Q-26 | Seal certificate: start with an Almiras self-issued certificate, or buy a document-signing certificate from a licensed Saudi provider from day one? | Before PRD |
| Q-27 | Should the QR verification page be public (anyone with the PDF), or require login? Public shows only PR number, status and signer names. | Before PRD |
| Q-28 | Who drafts the internal e-signature policy text: we draft it for legal review, or legal provides it? | Later |

### Notifications and reporting

| ID | Question | Priority |
|---|---|---|
| Q-29 | Email only, or Microsoft Teams messages too? | Before PRD |
| Q-30 | Which reports and lists matter on day one (my requests, waiting for me, all PRs per project, overdue PRs, export to Excel)? | Before PRD |

### Platform and integrations

| ID | Question | Priority |
|---|---|---|
| Q-31 | Does the group use an accounting or ERP system today (for example Odoo, SAP Business One, Zoho, Qoyod) that later modules must connect to? | Before PRD |
| Q-32 | Expected scale: number of companies, users, PRs per month? | Before PRD |
| Q-33 | Work from site with weak signal: is saving a draft offline needed, or is online-only acceptable? | Before PRD |
| Q-34 | Domain for the app (for example `pr.almiras.sa`)? | Later |

## 7. Parking lot (future modules)

- Inventory: stores per company or project, stock levels, receipts against POs, issues to projects, transfers.
- Procurement: supplier register, RFQs and quotation comparison, PO creation and approval, invoices, three-way match (PO, receipt, invoice), internal standards checks.
- Group dashboards across companies.
