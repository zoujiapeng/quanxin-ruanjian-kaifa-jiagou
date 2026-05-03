---
name: UI feedback guidance
description: Lessons learned from UI customization feedback
type: feedback
originSessionId: e06d26ba-2f33-4d5f-a526-e6c68b6f2b3b
---
Panels shown via edge proximity should stay visible while the mouse hovers over the panel content, not just while within the narrow edge zone. **How to apply:** Use `onMouseEnter`/`onMouseLeave` + ref-based hover tracking that feeds into the proximity zone calculation (not separate CSS classes).

Hidden panel elements must not take layout space. `transform: translateY(-100%)` hides visually but the element still occupies space in the flex layout — use `position: absolute` to remove them from the flow. **Why:** The canvas needs to fill 100vh, and hidden topbar/view-tabs were leaving ~90px of blank space. **How to apply:** In canvas view, make the wrapping containers absolute, and set `app-body` to `height: 100vh`.

fitToScreen offsets must match actual layout. When panels become overlays, recalculate the `W`/`H` constants. **Why:** The `-580` offset in fitToScreen was for side panels that were later changed to absolute overlays, causing left-shifted centering. **How to apply:** Use only padding (e.g., `innerWidth - 120`) rather than subtracting fixed panel widths.

Auto-hide timer must be removed — panels should latch visible once triggered and only hide manually. **Why:** User said "顶部侧栏显示了就要在底部栏手动隐藏,关闭自动隐藏功能". The 3s setTimeout in `handleMouseMove` was deleted. Proximity now only transitions false→true; never true→false from mouse events. **How to apply:** StatusBar has a `Minimize2` icon button "收起所有面板" that resets `proximity` state + `hoveredRef` + `forcedVisible` flags. Top bar center-area restriction (260px/320px insets) is still maintained.
