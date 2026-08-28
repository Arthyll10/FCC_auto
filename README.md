# freeCodeCamp Automation Engine

A Playwright-powered Python engine designed to automate FreeCodeCamp responsive web design coursework. Uses a dual-page architecture to fetch solutions and sync multi-file Monaco editors reliably while handling donation timers, tab states, and React state triggers.

## Architecture & Core Mechanics

- **Scout vs. Worker Pattern:** Operates two concurrent pages within a persistent browser context. `Scout` loads Step $N+1$ to extract solution code, while `Worker` applies code and submits Step $N$.
- **Tab Isolation & Multi-File Support:** Identifies active file tabs (`index.html`, `styles.css`) and dynamically manages `aria-expanded` states to prevent unwanted split-editor layouts.
- **Redundancy & Diff Checking:** Reads code from both Scout and Worker prior to pasting. If code is identical, write cycles are skipped to eliminate redundant React re-renders.
- **React State-Safe Input:** Uses native OS hotkey events (`Control+A`, `Control+C`, `Control+V`) so FreeCodeCamp's React `onChange` listeners capture model changes correctly.
- **Donation Modal Defense:** Detects delay-based donation popups, waits for the timer to finish (~25–30s), clicks "Ask me later", and re-copies solution code if the clipboard buffer expired during the wait.

## Prerequisites

- Python 3.8+
- Playwright Chromium browser binary

## Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Arthyll10/fcc-automation.git](https://github.com/Arthyll10/fcc-automation.git)
   cd fcc-automation