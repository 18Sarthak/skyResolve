# SkyResolve Agent Hub

SkyResolve — Lovable Frontend Prompt

Build the frontend for SkyResolve — an internal airline customer support agent dashboard used by airline staff (not the customer directly). The interface wraps a real FastAPI backend that resolves flight disruption cases using AI + deterministic policy rules.

Brand Identity

Product name: SkyResolve

Tagline: "Policy-first. Human when it matters."

Audience: Airline support agents and supervisors — this is a professional operations tool, not a consumer app

Tone: Confident, clean, enterprise-grade. Think Stripe, Linear, Vercel dashboard — not a chatbot toy.

Color palette:

Primary: Deep navy #0A1628

Accent: Electric indigo #4F6EF7

Surface: #111827 (cards/panels)

Border: #1F2937

Text primary: #F9FAFB

Text muted: #6B7280

Success green: #10B981

Warning amber: #F59E0B

Escalation red: #EF4444

Typography: Inter (Google Fonts) — 400/500/600/700 weights only

Radius: 8px cards, 6px inputs, 4px badges

No gradients on text. No glassmorphism. No glow effects. No floating blobs. This is a dashboard tool.

Tech Stack

React + Vite (TypeScript)

Vanilla CSS (no Tailwind, no component libraries like MUI or Chakra)

All API calls go to http://localhost:8000 — hardcode this as a constant in an api.ts file

Application Structure

Layout

┌─────────────────────────────────────────────────────────────────┐

│  Sidebar (240px fixed)  │  Main Content Area (flex-grow)        │

│                         │                                        │

│  Logo + "SkyResolve"    │  [Case Header]                        │

│                         │  [Chat Window]                         │

│  ─────────────────      │  [Input Bar]                          │

│  Customer Selector      │                                        │

│  (3 customers)          │                                        │

│                         │                                        │

│  ─────────────────      │                                        │

│  Active Case Info       │                                        │

│  (PNR, flight, status)  │                                        │

│                         │                                        │

│  ─────────────────      │                                        │

│  History toggle         │                                        │

└─────────────────────────────────────────────────────────────────┘

Sidebar — Customer Selector

Show all 3 customers as selectable cards. Each card shows:

Customer name (bold)

PNR badge (monospace, muted)

Tier badge: Silver (gray), Gold (amber #F59E0B), Platinum (indigo #818CF8)

Flight route: e.g. "Delhi → Goa"

Flight status chip: "Cancelled" (red), "Delayed Xh" (amber), "On Time" (green)

Clicking a card loads that customer's case into the main area. Active card has a left accent border in indigo.

Case Header (top of main area)

A thin, fixed bar showing:

Customer name + tier badge

PNR (monospace)

Flight: SK-204 · Delhi → Goa

Status chip (same as sidebar)

If delayed: Scheduled 18:40 → Now 20:00 (+2h)

Right side: ESCALATED badge (red, pulsing dot) OR Active badge (green dot) — driven by API response

Chat Window

Standard chat layout. Two actor types:

Customer message (right-aligned):

White bubble, dark text

Label: "Agent Input" in small muted text above

No avatar

SkyResolve message (left-aligned):

Navy #111827 bubble, light text

Small "SkyResolve" label with a tiny plane icon

Below the bubble, show a collapsible Actions Panel (not inside the bubble):

Row of action chips: ✓ Meal Voucher (₹500) · ✓ Lounge Access · ✓ Free Rebooking

Each chip: small green checkmark, short label, subtle green border

If escalated: a red chip ⚠ Escalated to Supervisor with the escalation reason on hover (tooltip)

Denied actions (if any) shown with an ✗ and muted red styling

Escalation banner: When escalated: true, show a sticky amber/red banner just above the input bar:
⚠ This case has been escalated to a human supervisor. The agent will not take further automated action.

Input Bar (bottom of main area)

Full-width textarea (2 rows, expands to 4 max on content)

Placeholder: "Type the customer's message..."

Right side: Send button (indigo, rounded, with a send icon)

Keyboard shortcut: Cmd/Ctrl + Enter to send

Disabled with a spinner while waiting for API response

Show a subtle typing indicator ("SkyResolve is processing...") while the request is in-flight

History Panel

A toggle button in the sidebar ("View History") slides in a panel over the main area (right-side drawer, 480px wide) showing:

All past turns for the selected PNR

Each turn: timestamp, customer message snippet, actions taken (chips), escalated (badge), token usage (small muted text: ↑ 312 ↓ 89 tokens)

Turns ordered oldest → newest

A "Close" X button

API Contract

Base URL: http://localhost:8000

Send a message

POST /conversation/{pnr}/message

Body: { "message": string }

Response: {

  "response": string,

  "actions_taken": string[],

  "escalated": boolean,

  "escalation_reason": string | null

}

Get history

GET /conversation/{pnr}/history

Response: Array of {

  "id": number,

  "pnr": string,

  "timestamp": string,

  "customer_message": string,

  "agent_response": string,

  "actions_taken_json": string[],

  "escalated": boolean,

  "escalation_reason": string | null,

  "prompt_tokens": number,

  "completion_tokens": number

}

Health check

GET /health

Response: { "status": "ok", "openai_key_configured": true }

Static Customer Data (hardcode in frontend — matches backend)

ts

const CUSTOMERS = [

  {

pnr: "SK4821X",

name: "Priya Nair",

tier: "Gold",

flightNumber: "SK-204",

route: { from: "Delhi", to: "Goa" },

scheduledDt: "2026-09-23T18:40",

status: "Cancelled",

delayHours: 0,

  },

  {

pnr: "TR1190B",

name: "Arvind Kulkarni",

tier: "Silver",

flightNumber: "SK-118",

route: { from: "Mumbai", to: "Bengaluru" },

scheduledDt: "2026-09-23T07:10",

status: "Delayed",

delayHours: 4,

newDepartureDt: "2026-09-23T11:10",

  },

  {

pnr: "WL7742",

name: "Meher Kaur",

tier: "Platinum",

flightNumber: "SK-305",

route: { from: "Delhi", to: "Hyderabad" },

scheduledDt: "2026-09-23T14:00",

status: "Delayed",

delayHours: 6,

newDepartureDt: "2026-09-23T20:00",

  },

];

Action Label Mapping

Map raw actions_taken strings from the API to human-readable labels:

ts

const ACTION_LABELS: Record<string, string> = {

free_rebooking_within_24h: "Free Rebooking (24h)",

full_refund: "Full Refund",

priority_rebooking: "Priority Rebooking",

meal_voucher: "Meal Voucher (₹500)",

lounge_access: "Lounge Access",

hotel_for_delayed_hours_only: "Hotel (Delayed Hours)",

collect_fare_difference: "Fare Difference Collected",

process_refund: "Refund Processed",

};

State Management

Use React useState and useRef only — no Redux, no Zustand, no context providers unless absolutely needed for theme. Keep it simple.

Per-customer state:

messages: { role: 'agent' | 'skyresolve', content: string, actionsTaken?: string[], escalated?: boolean, escalationReason?: string | null }[]

isLoading: boolean

isEscalated: boolean — set to true if any turn returns escalated: true, stays true for session

When switching customers: preserve each customer's message history in-memory (use a Record<string, Message[]> keyed by PNR).

UX Rules — Critical

Never clear the input on error — if the API call fails, show a toast error and keep the message in the textarea

Auto-scroll to bottom after each new message

Disable send while isLoading — no double-submits

Empty state: When no messages yet, show a centered placeholder: "Select a customer and type their message to begin resolution." with a subtle plane icon

Error state: If the API returns a non-200, show a red inline error below the input: "Failed to reach SkyResolve backend. Is the server running?"

No streaming — wait for the full API response, then render it all at once

History drawer fetches fresh from /history endpoint every time it's opened — don't cache it

What this must NOT look like

No bubble gradients, no colorful gradients anywhere

No "Hero" sections or landing page copy

No emoji in the UI chrome (emoji only inside API response text is fine)

No skeleton loaders that are more complex than a simple pulsing line

No "powered by OpenAI" badges or AI branding

No card drop shadows that are too heavy — use borders instead

No Comic Sans, Roboto Slab, or any serif font

No centered full-page layouts — this is a sidebar + content dashboard

No fake data or mock screenshots — all content comes from the live API

Deliverables

Working Vite + React + TypeScript app

All CSS in a single index.css with CSS custom properties (variables) for the color palette

src/api.ts — all fetch calls in one file, typed with the response shapes above

src/App.tsx — root layout

src/components/Sidebar.tsx

src/components/ChatWindow.tsx

src/components/MessageBubble.tsx

src/components/ActionsPanel.tsx

src/components/HistoryDrawer.tsx

src/components/CaseHeader.tsx

src/data/customers.ts — the static CUSTOMERS array



the ui must be black and white contract

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/f4d0fdbb-4c6a-43c1-8563-7aed80890d52).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
