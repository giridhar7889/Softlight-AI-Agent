#  Agent B: Autonomous UI State Capture

> A production-ready AI agent that navigates live web applications, reasoning about non-URL states (modals, popovers, dynamic grids) .

##  Problem Statement
Modern web apps (Linear, AG Grid, Airbnb) rely heavily on client-side state. A unique URL often doesn't exist for:
- A specific filter configuration in a data grid.
- An open dropdown menu or modal.
- A multi-step form halfway filled.

**Agent B** solves this by autonomously navigating these states using Vision-Language Models (VLMs) and Playwright, capturing a structured "ground truth" dataset of visual state + metadata.

---

##  Key Capabilities
- **Real-Time Reasoning:** Uses GPT-4o/Claude to "see" the page and decide the next action.
- **Non-URL State Capture:** Snapshots transient UI elements like floating menus and popovers.
- **Set-of-Marks (SoM):** Injects numbered labels for precise, hallucination-free clicking.
- **Loop Prevention:** `ActionValidator` module prevents repetitive clicking or getting stuck.
- **Modular Architecture:** Works across any app (Airbnb, SauceDemo, AG Grid) without hardcoded scripts.

---

##  System Architecture

The system follows an **Observe-Orient-Decide-Act (OODA)** loop:

```
┌─────────────────────────────────────────────────────────────┐
│                        User / CLI                           │
│                    (main.py entry point)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Workflow Orchestrator                      │
│  • Coordinates all components                               │
│  • Manages workflow lifecycle                               │
│  • Controls execution loop                                  │
└────┬──────────────┬──────────────┬──────────────┬───────────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
┌─────────┐    ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Browser │    │   LLM    │   │    UI    │   │  State   │
│ Control │    │  Agent   │   │ Detector │   │ Manager  │
│         │    │          │   │          │   │          │
└────┬────┘    └────┬─────┘   └────┬─────┘   └────┬─────┘
     │              │              │              │
     │              │              │              │
     └──────────────┴──────────────┴──────────────┘
                    │
                    ▼
          ┌──────────────────┐
          │   App Adapters   │
          │  (Linear, etc)   │
          └──────────────────┘
```

1.  **Workflow Orchestrator:** The central "brain" that manages the lifecycle. It decides when to observe, when to act, and when to stop based on goal completion.
2.  **Browser Controller:** The "hands" of the system. Wraps Playwright to handle resilient clicking, typing, scrolling, and **Set-of-Marks (SoM)** injection.
3.  **LLM Agent:** The "intelligence." Receives labeled screenshots and prompts from the Orchestrator to reason about the next step.
4.  **UI Detector:** Monitors the visual state to confirm if actions succeeded (e.g., "Did the modal open?").
5.  **State Manager:** The "memory." Captures clean screenshots and logs metadata (URL, reasoning, timestamps) into the structured `dataset/` format.
6.  **App Adapters:** Optional plugins to handle app-specific login flows or quirks, keeping the core system generic.

---

##  Setup & Usage

### 1. Installation
```bash
# Clone repo
git clone https://github.com/yourusername/agent-b.git
cd agent-b

# Install dependencies
pip install -r requirements.txt
playwright install
```

### 2. Configuration
Create a `.env` file with your API keys:
```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
HEADLESS=true
```

### 3. Running a Workflow
You can run ad-hoc tasks via the CLI:
```bash
# Example: Capture AG Grid audit workflow
python src/main.py --task "Filter Language to French and sort Balance" --start-url "https://www.ag-grid.com/example/"
```

Or run the pre-packaged validation scripts:
```bash
# Run the Airbnb "Paris Map" workflow
python scripts/capture_airbnb_paris_map.py
```

---

##  Dataset Structure (Deliverable)

All captures are stored in `dataset/` organized by App and Task.

**Example: AG Grid Audit**
`dataset/Linear/ag_grid_audit_view_french_20251125_205717/`
- `step_01_navigate.png`: Initial grid load.
- `step_02_filter.png`: "French" typed in filter (rows updated).
- `step_03_pin.png`: Language column pinned left (visual verification).
- `step_04_sort.png`: Bank Balance sorted descending.
- `metadata.json`: Full log of URLs, timestamps, and AI reasoning.
- `README.md`: Auto-generated narrative of the session.

---

##  Demo Video
(Link to Loom video goes here)

---

##  Tested Workflows
We have successfully captured complex, multi-step workflows on:
1.  **AG Grid:** Filtering, sorting, pinning, and grouping data.
2.  **Airbnb:** Map exploration, listing deep-dives, and experiences.
3.  **SauceDemo:** E-commerce cart management and checkout wizard.

See `dataset/` for the full artifacts.
