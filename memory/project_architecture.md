---
name: Project architecture
description: Key architectural decisions and file organization
type: project
originSessionId: e06d26ba-2f33-4d5f-a526-e6c68b6f2b3b
---
**Stack:** Electron 31 + React 18 + Vite 5 + TypeScript + Zustand (with immer) + nanoid.

**Layout:** The app uses absolute-positioned overlay panels in "canvas view". TopBar, view-tabs, and StatusBar are `position: absolute` when hidden so they don't push the canvas down. Side panels (NodeLibrary, PropertyPanel) float over the canvas with CSS transforms.

**Panel auto-hide (latching):** Mouse proximity zones (36px edge threshold) + per-panel hover tracking (via `hoveredRef` + `handlePanelEnter`/`handlePanelLeave`). Once triggered, panels stay visible until manually dismissed via the status bar's "收起所有面板" button (calls `hideAllPanels` which resets proximity + forcedVisible flags). Top bar only triggers from center area (between 260px left inset and 320px right inset) to avoid overlapping side panels. Uses `pointer-events: none` on `.top-wrapper` in canvas view with `pointer-events: auto` on its children so mouse events pass through to side panels underneath.

**Canvas panning:** Middle-mouse drag is throttled via `requestAnimationFrame` in FlowCanvas.tsx to avoid jank.

**Script template:** Initial script is loaded from `createTemplateScript('desktop-monitor')`. `fitToScreen()` is called after `loadTemplate`, `loadScript`, `newScript`, and on initial mount to center the flowchart.

**Native menu:** Defined in `src/main/main.ts` via `buildAppMenu()`. All Chinese labels. Standard edit actions use `role` for native web contents integration. File operations (new/open/save) use IPC `menu-action` channel bridged through preload.

**AI Assistant:** Changed from full-page view to floating dialog (AIAssistantDialog.tsx). Clicking the AI button toggles a centered floating dialog instead of switching viewMode.
