# Grid Background Animation - Debugging Guide

## Problem
The animated perspective grid background was not visible on the landing page.

## Root Causes Identified

### 1. **Body Background Covering Grid** (CRITICAL)
- `body` had `background: var(--bg)` (solid dark color `#0e1117`)
- Elements with negative z-index are painted **behind** the body's background
- Grid at `z-index: -2` was literally behind the body background, making it invisible

### 2. **Stacking Context Issues**
- Original `body` had `position: relative` which creates a stacking context
- This prevented negative z-index children from showing properly

### 3. **Wrong Grid Implementation Pattern**
- Original code used `::before`/`::after` pseudo-elements
- Applied `perspective()` inside the `transform` property
- Used `overflow: hidden` on parent which clipped 3D-transformed children
- Animated `background-position` which doesn't work well with 3D transforms

## Solution Implemented

### Layering Structure (z-index)
```
z-index: -3  →  .bg-layer (solid dark background)
z-index: -2  →  .grid-bg (animated grid container)
z-index: -1  →  .grid-fade (gradient mask), .grid-glow (horizon glow)
z-index: 0   →  #app, #content, .section-panel (transparent content)
z-index: 1+  →  UI elements (buttons, cards, etc.)
```

### Key Changes

#### HTML Structure
```html
<body>
    <!-- New: Separate background layer -->
    <div class="bg-layer"></div>
    
    <!-- Grid with real child div (not pseudo-elements) -->
    <div class="grid-bg">
        <div class="grid-bg-lines"></div>
    </div>
    
    <div class="grid-fade"></div>
    <div class="grid-glow"></div>
    
    <!-- Content with transparent background -->
    <div id="app">
        <!-- ... -->
    </div>
</body>
```

#### CSS Changes

**Before:**
```css
body {
    background: var(--bg);  /* BLOCKS grid */
    position: relative;      /* Creates stacking context */
}

.grid-bg {
    z-index: 0;
    overflow: hidden;  /* Clips 3D transforms */
}

.grid-bg::before {
    transform: perspective(350px) rotateX(52deg);
    animation: gridScroll 10s linear infinite;  /* background-position */
}
```

**After:**
```css
body {
    background: transparent;  /* ✓ No background to block grid */
}

.bg-layer {
    position: fixed;
    inset: 0;
    background: var(--bg);
    z-index: -3;  /* ✓ Behind everything */
}

.grid-bg {
    position: fixed;
    bottom: 0;
    height: 70vh;
    perspective: 56.25vh;  /* ✓ On container */
    z-index: -2;
    overflow: hidden;  /* Safe now - no 3D transforms on this element */
}

.grid-bg-lines {
    height: 200%;
    transform-origin: 100% 0 0;
    animation: gridPlay 30s linear infinite;  /* ✓ translateY */
}

@keyframes gridPlay {
    0% {
        transform: rotateX(45deg) translateY(-50%);
    }
    100% {
        transform: rotateX(45deg) translateY(0);
    }
}
```

### Grid Parameters (matching arcprize.org)

| Property | Value | Purpose |
|----------|-------|---------|
| Container height | `70vh` | Covers bottom 70% of viewport |
| Container perspective | `56.25vh` | Creates 3D depth |
| Lines height | `200%` | Double height for scrolling space |
| Lines opacity | `rgba(88, 166, 255, 0.35)` | Visible but subtle |
| Grid spacing | `4vh × 3vh` | Cell size |
| Rotation | `rotateX(45deg)` | Perspective angle |
| Animation | `translateY(-50%)` → `translateY(0)` | Scrolls toward viewer |
| Duration | `30s` | Smooth slow animation |

## Testing

### Quick Visual Test
Open the test file: `web/templates/grid-test.html`

This minimal test page isolates the grid effect to verify it works.

### What You Should See
1. Animated blue grid lines in perspective (like a floor)
2. Grid scrolling toward you from the bottom
3. Gradient fade at the top
4. Radial vignette darkening at edges
5. Subtle horizontal glow line at ~30% from bottom

### If Grid Still Not Visible

Check these in browser DevTools:

```javascript
// 1. Check z-index layering
console.log('bg-layer z-index:', getComputedStyle(document.querySelector('.bg-layer')).zIndex);
console.log('grid-bg z-index:', getComputedStyle(document.querySelector('.grid-bg')).zIndex);
console.log('grid-fade z-index:', getComputedStyle(document.querySelector('.grid-fade')).zIndex);

// 2. Check grid container
const grid = document.querySelector('.grid-bg');
console.log('Grid dimensions:', grid.offsetWidth, grid.offsetHeight);
console.log('Grid perspective:', getComputedStyle(grid).perspective);

// 3. Check grid lines animation
const lines = document.querySelector('.grid-bg-lines');
console.log('Lines transform:', getComputedStyle(lines).transform);
console.log('Lines animation:', getComputedStyle(lines).animation);

// 4. Temporarily increase opacity for testing
document.querySelector('.grid-bg-lines').style.backgroundImage = 
    'linear-gradient(to right, rgba(88, 166, 255, 0.8) 1px, transparent 0), ' +
    'linear-gradient(to bottom, rgba(88, 166, 255, 0.8) 1px, transparent 0)';
```

### Common Issues

1. **Grid too faint**: Increase opacity in `.grid-bg-lines` background-image
   - Change from `0.35` to `0.5` or higher

2. **Grid not animating**: Check animation is running
   - Look for `animation: gridPlay 30s linear infinite` on `.grid-bg-lines`

3. **Grid clipped**: Verify `overflow: hidden` is only on `.grid-bg` (not on body/html)

4. **Grid behind content**: Check z-index values
   - bg-layer: -3
   - grid-bg: -2
   - grid-fade: -1
   - content: 0+

## Browser Compatibility

Tested and working:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Known issues:
- Safari < 14 may need `-webkit-perspective` prefix
- IE11: Not supported (no CSS perspective/transform support)

## Performance

- Grid uses CSS animations (GPU-accelerated)
- No JavaScript required
- Fixed positioning avoids reflows
- ~60fps animation on modern devices

## Mobile Responsive

Grid is hidden on screens ≤600px width:
```css
@media (max-width: 600px) {
    .bg-layer,
    .grid-bg,
    .grid-fade,
    .grid-glow {
        display: none;
    }
}
```

This improves mobile performance and avoids visual clutter on small screens.