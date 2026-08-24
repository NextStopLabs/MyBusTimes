/* ==========================================================================
   Livery Creator
   ========================================================================== */

/* ==========================================================================
   Shape presets

   "user_colour" is replaced by the selected colour.
   ========================================================================== */

const SHAPES = [
    [
        "Flick",
        "radial-gradient(165% 155% at 0% 38%,transparent 50%,user_colour 50%)",
        "radial-gradient(165% 155% at 100% 38%,transparent 50%,user_colour 50%)"
    ],
    [
        "Front Block",
        "linear-gradient(90deg,user_colour 25%,transparent 25%)",
        "linear-gradient(270deg,user_colour 25%,transparent 25%)"
    ],
    [
        "Front Circle",
        "radial-gradient(75% 100% at 0% 50%,user_colour 50%,transparent 50%)",
        "radial-gradient(75% 100% at 100% 50%,user_colour 50%,transparent 50%)"
    ],
    [
        "Front Stripe",
        "linear-gradient(120deg,user_colour 30%,transparent 30%)",
        "linear-gradient(-120deg,user_colour 30%,transparent 30%)"
    ],
    [
        "Lower Stripe",
        "linear-gradient(0deg,user_colour 5%,transparent 5%)",
        "linear-gradient(0deg,user_colour 5%,transparent 5%)"
    ],
    [
        "Lower Swoop",
        "radial-gradient(145% 85% at 100% 110%,user_colour 50%,transparent 50%)",
        "radial-gradient(145% 85% at 0% 110%,user_colour 50%,transparent 50%)"
    ],
    [
        "Rear Stripe",
        "linear-gradient(-60deg,user_colour 30%,transparent 30%)",
        "linear-gradient(60deg,user_colour 30%,transparent 30%)"
    ],
    [
        "Side Stripe",
        "linear-gradient(-60deg,transparent 25%, user_colour 25% 35%,transparent 35%)",
        "linear-gradient(60deg,transparent 25%, user_colour 25% 35%,transparent 35%)"
    ],
    [
        "Side Swoop",
        "radial-gradient(70% 100% at 0% 0%,transparent 35%,user_colour 35% 50%,transparent 50%)",
        "radial-gradient(70% 100% at 100% 0%,transparent 35%,user_colour 35% 50%,transparent 50%)"
    ],
    [
        "Stripe (1)",
        "linear-gradient(0deg,user_colour 10%,transparent 10%)",
        "linear-gradient(0deg,user_colour 10%,transparent 10%)"
    ],
    [
        "Stripe (2)",
        "linear-gradient(0deg,user_colour 20%,transparent 20%)",
        "linear-gradient(0deg,user_colour 20%,transparent 20%)"
    ],
    [
        "Stripe (3)",
        "linear-gradient(0deg,user_colour 30%,transparent 30%)",
        "linear-gradient(0deg,user_colour 30%,transparent 30%)"
    ],
    [
        "Stripe Swoop",
        "radial-gradient(70% 100% at 100% 0%,transparent 50%,user_colour 50% 55%,transparent 55%)",
        "radial-gradient(70% 100% at 0% 0%,transparent 50%,user_colour 50% 55%,transparent 55%)"
    ],
    [
        "Swoop",
        "radial-gradient(100% 100% at 60% 120%,user_colour 50%,transparent 50%),radial-gradient(120% 195% at 25% 14%,transparent 50%,user_colour 50%)",
        "radial-gradient(100% 100% at 60% 120%,user_colour 50%,transparent 50%),radial-gradient(120% 195% at 25% 14%,transparent 50%,user_colour 50%)"
    ],
    [
        "Upper band",
        "linear-gradient(0deg,transparent 65%, user_colour 65% 75%,transparent 75%)",
        "linear-gradient(0deg,transparent 65%, user_colour 65% 75%,transparent 75%)",
    ],
    [
        "Upper Swoop",
        "radial-gradient(70% 100% at 0% 0%,user_colour 50%,transparent 50%)",
        "radial-gradient(70% 100% at 100% 0%,user_colour 50%,transparent 50%)"
    ],
    [
        "Verbose Swoop",
        "radial-gradient(60% 100% at 0% 100%,user_colour 50%,transparent 50%),linear-gradient(0deg,user_colour 20%,transparent 20%)",
        "radial-gradient(60% 100% at 100% 100%,user_colour 50%,transparent 50%),linear-gradient(0deg,user_colour 20%,transparent 20%)"
    ]
];

/* ==========================================================================
   DOM references
   ========================================================================== */

const leftCell =
    document.getElementById("left");

const leftZoomedCell =
    document.getElementById("left-zoomed");

const leftMidZoomedCell =
    document.getElementById("left-mid-zoomed");

const rightCell =
    document.getElementById("right");

const rightZoomedCell =
    document.getElementById("right-zoomed");

const rightMidZoomedCell =
    document.getElementById("right-mid-zoomed");

const simpleCell =
    document.getElementById("simpleCell");

const cssLeftField =
    document.getElementById("livery-css-left");

const cssRightField =
    document.getElementById("livery-css-right");

const textColourField =
    document.getElementById("text-colour");

const textStrokeColourField =
    document.getElementById("text-stroke-colour");

const liveryColourField =
    document.getElementById("livery-colour");


/* ==========================================================================
   Utility
   ========================================================================== */

function normaliseCss(value) {
    return (value || "").trim() || "#111";
}


function setCssFields(leftCss, rightCss) {
    cssLeftField.value = normaliseCss(leftCss);
    cssRightField.value = normaliseCss(rightCss);

    applyCssToCells();
}


function getPreviewCells() {
    return [
        leftCell,
        leftZoomedCell,
        leftMidZoomedCell,
        rightCell,
        rightZoomedCell,
        rightMidZoomedCell,
        document.getElementById("preview-left"),
        document.getElementById("preview-right")
    ].filter(Boolean);
}


/* ==========================================================================
   Autosave (localStorage)
   ========================================================================== */

const AUTOSAVE_KEY =
    "livery_creator_autosave_v2";

let autosaveTimeout =
    null;

function scheduleAutosave() {
    if (autosaveTimeout) {
        clearTimeout(autosaveTimeout);
    }

    autosaveTimeout =
        setTimeout(
            saveAutosave,
            300
        );
}

function saveAutosave() {
    try {
        const data = {
            blockColours:
                typeof blockColours !==
                "undefined"
                    ? blockColours
                    : null,
            horizontal:
                horizontalCheckbox
                    ? horizontalCheckbox.checked
                    : false,
            shapeLayers:
                typeof shapeLayers !==
                "undefined"
                    ? shapeLayers
                    : [],
            shapeBackground:
                shapeBackgroundInput
                    ? shapeBackgroundInput.value
                    : "#ffffff",
            selectedShapeIndex:
                typeof selectedShapeIndex !==
                "undefined"
                    ? selectedShapeIndex
                    : 0,
            cssLeft:
                cssLeftField
                    ? cssLeftField.value
                    : "",
            cssRight:
                cssRightField
                    ? cssRightField.value
                    : "",
            textColour:
                textColourField
                    ? textColourField.value
                    : "",
            strokeColour:
                textStrokeColourField
                    ? textStrokeColourField.value
                    : "",
            liveryColour:
                liveryColourField
                    ? liveryColourField.value
                    : "",
            liveryName:
                document.getElementById(
                    "livery-name"
                )
                    ? document.getElementById(
                          "livery-name"
                      ).value
                    : "",
            mbtBaseLeftCss:
                typeof mbtBaseLeftCss !==
                "undefined"
                    ? mbtBaseLeftCss
                    : "",
            mbtBaseRightCss:
                typeof mbtBaseRightCss !==
                "undefined"
                    ? mbtBaseRightCss
                    : "",
            recolourColours:
                typeof recolourColours !==
                "undefined"
                    ? recolourColours
                    : [],
            activeTopTab:
                document.querySelector(
                    ".livery-creator-tab.active-tab"
                )?.dataset.tab || "quick",
            activeQuickSub:
                document.querySelector(
                    ".livery-creator-quick .livery-sub-tab.active-sub-tab"
                )?.dataset.sub || "simple",
            activeImportSub:
                document.querySelector(
                    ".livery-creator-import .livery-sub-tab.active-sub-tab"
                )?.dataset.sub || "liverylab"
        };

        localStorage.setItem(
            AUTOSAVE_KEY,
            JSON.stringify(data)
        );
    } catch (e) {}
}

function clearAutosave() {
    try {
        localStorage.removeItem(
            AUTOSAVE_KEY
        );
    } catch (e) {}
}

function loadAutosave() {
    try {
        const raw =
            localStorage.getItem(
                AUTOSAVE_KEY
            );

        if (!raw) {
            return false;
        }

        const data =
            JSON.parse(raw);

        if (!data) {
            return false;
        }

        if (
            Array.isArray(data.blockColours) &&
            data.blockColours.length
        ) {
            blockColours = data.blockColours;
        }

        if (
            typeof data.horizontal ===
            "boolean" &&
            horizontalCheckbox
        ) {
            horizontalCheckbox.checked =
                data.horizontal;
        }

        if (
            Array.isArray(data.shapeLayers)
        ) {
            shapeLayers = data.shapeLayers;
        }

        if (
            typeof data.selectedShapeIndex ===
            "number"
        ) {
            selectedShapeIndex =
                data.selectedShapeIndex;
        }

        if (
            data.shapeBackground &&
            shapeBackgroundInput
        ) {
            shapeBackgroundInput.value =
                data.shapeBackground;
            shapeBackgroundInput.style.background =
                data.shapeBackground;
        }

        if (
            typeof data.cssLeft ===
            "string"
        ) {
            cssLeftField.value =
                data.cssLeft;
        }

        if (
            typeof data.cssRight ===
            "string"
        ) {
            cssRightField.value =
                data.cssRight;
        }

        if (
            typeof data.textColour ===
            "string"
        ) {
            textColourField.value =
                data.textColour;
        }

        if (
            typeof data.strokeColour ===
            "string"
        ) {
            textStrokeColourField.value =
                data.strokeColour;
        }

        if (
            typeof data.liveryColour ===
            "string"
        ) {
            liveryColourField.value =
                data.liveryColour;
        }

        if (
            typeof data.liveryName ===
            "string"
        ) {
            const nameField =
                document.getElementById(
                    "livery-name"
                );
            if (nameField) {
                nameField.value =
                    data.liveryName;
            }
        }

        if (
            typeof data.mbtBaseLeftCss ===
            "string"
        ) {
            mbtBaseLeftCss =
                data.mbtBaseLeftCss;
            if (data.mbtBaseLeftCss) {
                cssLeftField.dataset.base =
                    data.mbtBaseLeftCss;
            }
        }

        if (
            typeof data.mbtBaseRightCss ===
            "string"
        ) {
            mbtBaseRightCss =
                data.mbtBaseRightCss;
            if (data.mbtBaseRightCss) {
                cssRightField.dataset.base =
                    data.mbtBaseRightCss;
            }
        }

        if (
            Array.isArray(data.recolourColours)
        ) {
            recolourColours =
                data.recolourColours;
        }

        // Restore tabs after DOM is ready
        if (data.activeTopTab) {
            activateTopTab(
                data.activeTopTab
            );
        }

        const quickSubTab =
            document.querySelector(
                `.livery-creator-quick .livery-sub-tab[data-sub="${data.activeQuickSub}"]`
            );
        if (quickSubTab) {
            quickSubTab.click();
        }

        const importSubTab =
            document.querySelector(
                `.livery-creator-import .livery-sub-tab[data-sub="${data.activeImportSub}"]`
            );
        if (importSubTab) {
            importSubTab.click();
        }

        // Re-render
        if (
            typeof renderBlockSwatches ===
            "function"
        ) {
            renderBlockSwatches();
        }

        if (
            typeof renderShapeGrid ===
            "function"
        ) {
            renderShapeGrid();
        }

        if (
            typeof renderShapeLayers ===
            "function"
        ) {
            renderShapeLayers();
        }

        if (
            typeof renderRecolourColours ===
            "function"
        ) {
            renderRecolourColours();
        }

        applyCssToCells();
        updateRecolourVisibility();

        return true;
    } catch (e) {
        return false;
    }
}


/* ==========================================================================
   Colour helpers (similar/dark)
   ========================================================================== */

function hexToRgb(hex) {
    if (!hex) return null;
    let h = hex.trim().toLowerCase();
    if (h === "none" || h === "transparent") return null;
    if (h.length === 4) {
        h = "#" + h[1] + h[1] + h[2] + h[2] + h[3] + h[3];
    }
    const m = /^#([0-9a-f]{6})$/.exec(h);
    if (!m) return null;
    return {
        r: parseInt(m[1].slice(0, 2), 16),
        g: parseInt(m[1].slice(2, 4), 16),
        b: parseInt(m[1].slice(4, 6), 16)
    };
}

function colourDistance(hex1, hex2) {
    const a = hexToRgb(hex1);
    const b = hexToRgb(hex2);
    if (!a || !b) return Infinity;
    const dr = a.r - b.r;
    const dg = a.g - b.g;
    const db = a.b - b.b;
    return Math.sqrt(dr * dr + dg * dg + db * db);
}

function isSimilarColour(hex1, hex2, threshold) {
    if (!hex1 || !hex2) return false;
    const t = threshold != null ? threshold : 100;
    // Exact match
    if (hex1.toLowerCase() === hex2.toLowerCase()) return true;
    return colourDistance(hex1, hex2) < t;
}

function isDarkColour(hex) {
    const rgb = hexToRgb(hex);
    if (!rgb) return false;
    const lum = (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
    // Very dark always flagged (blacks, very dark greys/blues)
    if (lum < 0.32) return true;
    // Moderately dark (0.32-0.4) only flagged if not vivid/saturated
    // e.g. #0268ee rgb(2,104,238) lum 0.348 but vivid blue should NOT be flagged
    if (lum < 0.4) {
        const max = Math.max(rgb.r, rgb.g, rgb.b) / 255;
        const min = Math.min(rgb.r, rgb.g, rgb.b) / 255;
        const delta = max - min;
        const sat = max === 0 ? 0 : delta / max;
        // Highly saturated bright colours are fine on map
        if (sat > 0.6) return false;
        return true;
    }
    return false;
}

function isTransparentHex(hex) {
    if (!hex) return true;
    const h = hex.trim().toLowerCase();
    if (h === "transparent" || h === "#0000" || h === "#00000000") return true;
    // 4-digit #RGBA where A is 0
    if (/^#[0-9a-f]{4}$/.test(h) && h[4] === "0") return true;
    if (/^#[0-9a-f]{8}$/.test(h) && h.slice(-2) === "00") return true;
    return false;
}

function splitCssLayers(css) {
    if (!css) return [];
    const layers = [];
    let depth = 0;
    let start = 0;
    for (let i = 0; i < css.length; i++) {
        const ch = css[i];
        if (ch === "(") depth++;
        else if (ch === ")") depth = Math.max(0, depth - 1);
        else if (ch === "," && depth === 0) {
            layers.push(css.slice(start, i).trim());
            start = i + 1;
        }
    }
    layers.push(css.slice(start).trim());
    return layers.filter((s) => s.length);
}

function estimateMajorityColour(leftCss, rightCss) {
    const combined = [leftCss || "", rightCss || ""].join(",");
    const layers = splitCssLayers(combined);
    const coverage = {};

    for (const layer of layers) {
        const trimmed = layer.trim();
        if (!trimmed) continue;
        // Solid colour without gradient
        if (!trimmed.includes("gradient")) {
            const m = trimmed.match(/#([0-9A-Fa-f]{3,8})\b/);
            if (m) {
                const hex = m[0].toLowerCase();
                if (!isTransparentHex(hex)) {
                    const norm = hex.length === 4 ? "#" + hex[1] + hex[1] + hex[2] + hex[2] + hex[3] + hex[3] : hex.length === 5 ? hex.slice(0, 4).toLowerCase() : hex;
                    // Normalize 3-digit to 6
                    let normHex = hex.toLowerCase();
                    if (normHex.length === 4) {
                        normHex = "#" + normHex[1] + normHex[1] + normHex[2] + normHex[2] + normHex[3] + normHex[3];
                    }
                    coverage[normHex] = (coverage[normHex] || 0) + 100;
                }
            }
            continue;
        }

        const isConic = trimmed.toLowerCase().includes("conic-gradient");
        const total = isConic ? 360 : 100;

        // Find all hexes in order
        const hexRe = /#([0-9A-Fa-f]{3,8})\b/g;
        const stops = [];
        let match;
        while ((match = hexRe.exec(trimmed)) !== null) {
            const hex = match[0];
            const hexIdx = match.index;
            const nextIdx = (() => {
                hexRe.lastIndex = match.index + hex.length;
                const next = hexRe.exec(trimmed);
                hexRe.lastIndex = match.index + hex.length;
                // Actually need to find next hex index manually
                return next ? next.index : -1;
            })();
            // Extract substring after this hex up to next hex or layer end
            let endSearch = trimmed.length;
            // Find next hex position
            const nextHexPos = (() => {
                const sub = trimmed.slice(hexIdx + hex.length);
                const nextM = sub.match(/#([0-9A-Fa-f]{3,8})\b/);
                if (nextM && nextM.index !== undefined) {
                    return hexIdx + hex.length + nextM.index;
                }
                return trimmed.length;
            })();
            const after = trimmed.slice(hexIdx + hex.length, nextHexPos);
            // Find up to two numbers with % or deg
            const nums = [];
            const numRe = /(\d+(?:\.\d+)?)\s*(%|deg)?/gi;
            let numMatch;
            while ((numMatch = numRe.exec(after)) !== null) {
                // Only take numbers that look like stops (before next hex)
                // Limit to 2 per hex
                if (nums.length >= 2) break;
                const val = parseFloat(numMatch[1]);
                const unit = numMatch[2] || (isConic ? "deg" : "%");
                // Normalize deg to 0-360, % to 0-100
                nums.push({ val, unit: unit.toLowerCase() });
                if (nums.length >= 2) break;
            }
            // Also handle case where hex has no number but is at start: implicit 0
            stops.push({ hex, nums });
        }

        if (!stops.length) continue;

        // Compute coverage per stop
        for (let i = 0; i < stops.length; i++) {
            const cur = stops[i];
            if (isTransparentHex(cur.hex)) continue;
            let normHex = cur.hex.toLowerCase();
            if (normHex.length === 4) {
                normHex = "#" + normHex[1] + normHex[1] + normHex[2] + normHex[2] + normHex[3] + normHex[3];
            }
            // Coverage based on positions
            let cov = 0;
            if (cur.nums.length === 2) {
                // Explicit range 85% 90% or 60deg 120deg
                const a = cur.nums[0].val;
                const b = cur.nums[1].val;
                cov = Math.abs(b - a);
                // For conic, still deg diff, for linear % diff
                // Normalize to total
                if (isConic) cov = (cov / 360) * 100; // convert to % for weighting, but keep relative
            } else if (cur.nums.length === 1) {
                const pos = cur.nums[0].val;
                // First stop single pos: from 0 to pos
                if (i === 0) {
                    cov = pos;
                } else {
                    const nextPos =
                        i + 1 < stops.length && stops[i + 1].nums.length
                            ? stops[i + 1].nums[0].val
                            : total;
                    // If next has two positions, its first is start
                    cov = Math.abs(nextPos - pos);
                }
            } else {
                // No position: distribute evenly? Assume equal share
                cov = total / stops.length;
            }

            // For radial, area is proportional to radius squared, not linear
            const isRadial = trimmed.toLowerCase().includes("radial-gradient");
            if (isRadial && !isConic) {
                // Approximate area: if cov is linear radial %, area ~ (r2^2 - r1^2)
                // For single pos case where cov is from start to pos, need actual radii
                // Simplified: if cov computed as linear, convert to area
                // For double pos 85-90, area = (0.9^2 - 0.85^2)=0.0875 vs linear 5, ratio ~1.75x
                // For first stop 0-85, area = 0.85^2=0.7225 vs linear 85, ratio 0.85
                // This weighting will make outer rings larger.
                // Rough: use squared for radial
                if (cur.nums.length === 2) {
                    const r1 = cur.nums[0].val / 100;
                    const r2 = cur.nums[1].val / 100;
                    cov = Math.abs(r2 * r2 - r1 * r1) * 100;
                } else if (cur.nums.length === 1 && i === 0) {
                    const r = cur.nums[0].val / 100;
                    cov = r * r * 100;
                } else if (cur.nums.length === 1) {
                    const r1 = cur.nums[0].val / 100;
                    const nextR =
                        i + 1 < stops.length && stops[i + 1].nums.length
                            ? stops[i + 1].nums[0].val / 100
                            : 1;
                    cov = Math.abs(nextR * nextR - r1 * r1) * 100;
                }
            }

            // Clamp and accumulate
            if (cov < 0) cov = 0;
            if (cov > 100) cov = 100;
            coverage[normHex] = (coverage[normHex] || 0) + cov;
        }
    }

    let best = null;
    let bestCov = -1;
    for (const [hex, cov] of Object.entries(coverage)) {
        if (cov > bestCov) {
            bestCov = cov;
            best = hex;
        }
    }
    return best;
}

async function estimateMajorityViaCanvas(leftCss, rightCss) {
    try {
        const css = (leftCss && leftCss.trim()) || (rightCss && rightCss.trim()) || "";
        if (!css) return null;
        const width = 160;
        const height = 80;
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        if (!ctx) return null;
        const safeCss = css.replace(/"/g, "'").replace(/\n/g, " ");
        const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><foreignObject width="100%" height="100%"><div xmlns="http://www.w3.org/1999/xhtml" style="width:${width}px;height:${height}px;background:${safeCss};"></div></foreignObject></svg>`;
        const dataUrl = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
        const img = new Image();
        const result = await new Promise((resolve) => {
            let done = false;
            const timer = setTimeout(() => {
                if (!done) {
                    done = true;
                    resolve(null);
                }
            }, 1200);
            img.onload = () => {
                if (done) return;
                done = true;
                clearTimeout(timer);
                try {
                    ctx.clearRect(0, 0, width, height);
                    ctx.drawImage(img, 0, 0);
                    const data = ctx.getImageData(0, 0, width, height).data;
                    const counts = {};
                    for (let i = 0; i < data.length; i += 4) {
                        const a = data[i + 3];
                        if (a < 20) continue;
                        const r = data[i];
                        const g = data[i + 1];
                        const b = data[i + 2];
                        // Ignore near-black transparent leftover? Keep
                        const hex = "#" + [r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("");
                        // Ignore pure white background of page if livery is transparent? But canvas has no background, transparent pixels already skipped
                        counts[hex] = (counts[hex] || 0) + 1;
                    }
                    let best = null;
                    let bestCnt = -1;
                    for (const [hex, cnt] of Object.entries(counts)) {
                        if (cnt > bestCnt) {
                            bestCnt = cnt;
                            best = hex;
                        }
                    }
                    resolve(best);
                } catch (e) {
                    resolve(null);
                }
            };
            img.onerror = () => {
                if (!done) {
                    done = true;
                    clearTimeout(timer);
                    resolve(null);
                }
            };
            img.src = dataUrl;
        });
        return result;
    } catch (e) {
        return null;
    }
}

function getReadableTextColour(bgHex) {
    const rgb = hexToRgb(bgHex);
    if (!rgb) return "#ffffff";
    const lum = (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
    return lum < 0.5 ? "#ffffff" : "#000000";
}

async function updateDefaultStrokeAndText() {
    try {
        const left = cssLeftField ? cssLeftField.value : "";
        const right = cssRightField ? cssRightField.value : "";
        if (!left && !right) return;
        let majority = null;
        try {
            majority = await estimateMajorityViaCanvas(left, right);
        } catch (e) {}
        if (!majority) {
            majority = estimateMajorityColour(left, right);
        }
        if (!majority || isTransparentHex(majority)) return;
        const norm = majority.toLowerCase();
        if (!/^#[0-9a-f]{6}$/.test(norm)) return;
        const readable = getReadableTextColour(norm);
        let changed = false;
        if (textStrokeColourField && textStrokeColourField.value.toLowerCase() !== norm) {
            textStrokeColourField.value = norm;
            changed = true;
        }
        if (textColourField && textColourField.value.toLowerCase() !== readable) {
            textColourField.value = readable;
            changed = true;
        }
        if (liveryColourField && liveryColourField.value.toLowerCase() !== norm) {
            liveryColourField.value = norm;
            changed = true;
        }
        if (changed) {
            applyTextStyling();
            scheduleAutosave();
        }
    } catch (e) {}
}

function updateStrokeSimilarWarning() {
    const warnEl = document.getElementById("stroke-similar-warning");
    if (!warnEl) return;
    const text = textColourField ? textColourField.value.trim() : "";
    const stroke = textStrokeColourField ? textStrokeColourField.value.trim() : "";
    if (!text || !stroke || stroke.toLowerCase() === "none") {
        warnEl.style.display = "none";
        warnEl.textContent = "";
        return;
    }
    if (isSimilarColour(text, stroke, 100)) {
        warnEl.textContent =
            "⚠️ Text and stroke colours are too similar (" +
            text +
            " / " +
            stroke +
            ") and will be hard to read.";
        warnEl.style.display = "block";
    } else {
        warnEl.style.display = "none";
        warnEl.textContent = "";
    }
}

function updateBlobDarkWarning() {
    const warnEl = document.getElementById("blob-dark-warning");
    if (!warnEl) return;
    const blob = liveryColourField ? liveryColourField.value.trim() : "";
    if (!blob) {
        warnEl.style.display = "none";
        warnEl.textContent = "";
        return;
    }
    if (isDarkColour(blob)) {
        warnEl.textContent =
            "⚠️ Dark map blob colours can be hard to see on the map (currently " +
            blob +
            "). This is just a warning.";
        warnEl.style.display = "block";
    } else {
        warnEl.style.display = "none";
        warnEl.textContent = "";
    }
}

function showSimilarPopup(textHex, strokeHex) {
    const modal = document.getElementById("similar-colour-modal");
    if (!modal) return;
    const textPrev = document.getElementById("similar-text-preview");
    const strokePrev = document.getElementById("similar-stroke-preview");
    const textHexEl = document.getElementById("similar-text-hex");
    const strokeHexEl = document.getElementById("similar-stroke-hex");
    if (textPrev) textPrev.style.background = textHex;
    if (strokePrev) strokePrev.style.background = strokeHex;
    if (textHexEl) textHexEl.textContent = textHex;
    if (strokeHexEl) strokeHexEl.textContent = strokeHex;
    modal.classList.add("open");
}

function hideSimilarPopup() {
    const modal = document.getElementById("similar-colour-modal");
    if (modal) modal.classList.remove("open");
}


/* ==========================================================================
   Preview
   ========================================================================== */

function applyCssToCells() {
    // Auto-set stroke to majority and text to readable contrast
    try {
        updateDefaultStrokeAndText();
    } catch (e) {}

    const leftCss =
        normaliseCss(cssLeftField.value);

    const rightCss =
        normaliseCss(cssRightField.value);

    [
        leftCell,
        leftZoomedCell,
        leftMidZoomedCell
    ].forEach((cell) => {
        if (cell) {
            cell.style.background = leftCss;
        }
    });

    [
        rightCell,
        rightZoomedCell,
        rightMidZoomedCell
    ].forEach((cell) => {
        if (cell) {
            cell.style.background = rightCss;
        }
    });

    const previewLeft =
        document.getElementById("preview-left");

    const previewRight =
        document.getElementById("preview-right");

    if (previewLeft) {
        previewLeft.style.background = leftCss;
    }

    if (previewRight) {
        previewRight.style.background = rightCss;
    }

    applyTextStyling();
    rebuildPaletteChoices();
}


/* ==========================================================================
   Text styling
   ========================================================================== */

function applyTextStyling() {
    const textColor =
        textColourField.value.trim();

    const strokeColor =
        textStrokeColourField.value.trim();

    const cells =
        getPreviewCells();

    cells.forEach((cell) => {
        const span =
            cell.querySelector("span");

        if (!span) {
            return;
        }

        if (textColor) {
            span.style.color = textColor;
        }

        if (
            strokeColor &&
            strokeColor !== "none"
        ) {
            span.style.webkitTextStroke =
                `2px ${strokeColor}`;

            span.style.textStroke =
                `2px ${strokeColor}`;
        } else {
            span.style.webkitTextStroke =
                "0px transparent";

            span.style.textStroke =
                "0px transparent";
        }
    });

    const blob =
        liveryColourField.value.trim();

    if (blob && simpleCell) {
        simpleCell.style.background = blob;

        const previewBlob =
            document.getElementById("preview-blob");

        if (previewBlob) {
            previewBlob.style.background = blob;
        }
    }

    updateStrokeSimilarWarning();
    updateBlobDarkWarning();
}


/* ==========================================================================
   Top level tabs
   ========================================================================== */

const topTabs =
    document.querySelectorAll(
        ".livery-creator-tab"
    );

const topPanels =
    document.querySelectorAll(
        ".livery-creator-container > [data-panel]"
    );


function activateTopTab(tabName) {
    topTabs.forEach((tab) => {
        tab.classList.toggle(
            "active-tab",
            tab.dataset.tab === tabName
        );
    });

    topPanels.forEach((panel) => {
        panel.classList.toggle(
            "active-content",
            panel.dataset.panel === tabName
        );
    });

    const detailsTab =
        document.querySelector(
            '.livery-creator-tab[data-tab="details"]'
        );

    if (
        detailsTab &&
        tabName === "details"
    ) {
        detailsTab.classList.remove(
            "disabled-tab"
        );
    }

    updateRecolourVisibility();
}


topTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
        if (
            tab.classList.contains("disabled-tab")
        ) {
            return;
        }

        activateTopTab(tab.dataset.tab);
    });
});


document
    .querySelectorAll(".next-to-details")
    .forEach((button) => {
        button.addEventListener("click", () => {
            const detailsTab =
                document.querySelector(
                    '.livery-creator-tab[data-tab="details"]'
                );

            if (detailsTab) {
                detailsTab.classList.remove(
                    "disabled-tab"
                );
            }

            activateTopTab("details");
        });
    });


/* ==========================================================================
   Sub tabs
   ========================================================================== */

function wireSubTabs(scopeSelector) {
    const scope =
        document.querySelector(scopeSelector);

    if (!scope) {
        return;
    }

    const subTabs =
        scope.querySelectorAll(
            ".livery-sub-tab"
        );

    const subPanels =
        scope.querySelectorAll(
            ".livery-sub-panel"
        );

    subTabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            subTabs.forEach((item) => {
                item.classList.remove(
                    "active-sub-tab"
                );
            });

            subPanels.forEach((panel) => {
                panel.classList.remove(
                    "active-sub-content"
                );
            });

            tab.classList.add(
                "active-sub-tab"
            );

            const panel =
                scope.querySelector(
                    `[data-sub-panel="${tab.dataset.sub}"]`
                );

            if (panel) {
                panel.classList.add(
                    "active-sub-content"
                );
            }

            updateRecolourVisibility();
        });
    });
}


wireSubTabs(".livery-creator-quick");
wireSubTabs(".livery-creator-import");


function updateRecolourVisibility() {
    const wrapper =
        document.getElementById(
            "recolour-wrapper"
        );

    if (!wrapper) {
        return;
    }

    const importTab =
        document.querySelector(
            '.livery-creator-tab[data-tab="import"]'
        );

    const importPanel =
        importTab &&
        importTab.classList.contains(
            "active-tab"
        );

    const mbtTab =
        document.querySelector(
            '.livery-creator-import .livery-sub-tab[data-sub="mbt"]'
        );

    const mbtActive =
        mbtTab &&
        mbtTab.classList.contains(
            "active-sub-tab"
        );

    const bustimesTab =
        document.querySelector(
            '.livery-creator-import .livery-sub-tab[data-sub="bustimes"]'
        );

    const bustimesActive =
        bustimesTab &&
        bustimesTab.classList.contains(
            "active-sub-tab"
        );

    wrapper.style.display =
        importPanel && (mbtActive || bustimesActive)
            ? "block"
            : "none";
}


/* ==========================================================================
   QUICK > SIMPLE
   ========================================================================== */

const blockSwatchRow =
    document.getElementById(
        "blockSwatchRow"
    );

const addBlockColourBtn =
    document.getElementById(
        "addBlockColour"
    );

const horizontalCheckbox =
    document.getElementById(
        "horizontal"
    );


let blockColours = [
    "#c8102e",
    "#ffffff"
];

let draggedColourIndex = null;


function moveArrayItem(array, from, to) {
    if (
        from < 0 ||
        to < 0 ||
        from >= array.length ||
        to >= array.length
    ) {
        return;
    }

    const item =
        array.splice(from, 1)[0];

    array.splice(to, 0, item);
}


function renderBlockSwatches() {
    if (!blockSwatchRow) {
        return;
    }

    blockSwatchRow.innerHTML = "";

    blockColours.forEach(
        (colour, index) => {
            const swatch =
                document.createElement("div");

            swatch.className =
                "block-swatch";

            swatch.draggable = true;

            swatch.dataset.index =
                String(index);


            swatch.addEventListener(
                "dragstart",
                () => {
                    draggedColourIndex =
                        index;

                    swatch.classList.add(
                        "dragging"
                    );
                }
            );


            swatch.addEventListener(
                "dragend",
                () => {
                    draggedColourIndex =
                        null;

                    swatch.classList.remove(
                        "dragging"
                    );
                }
            );


            swatch.addEventListener(
                "dragover",
                (event) => {
                    event.preventDefault();
                }
            );


            swatch.addEventListener(
                "drop",
                (event) => {
                    event.preventDefault();

                    if (
                        draggedColourIndex === null ||
                        draggedColourIndex === index
                    ) {
                        return;
                    }

                    moveArrayItem(
                        blockColours,
                        draggedColourIndex,
                        index
                    );

                    renderBlockSwatches();
                    updateSimpleBlocks();
                }
            );


            const input =
                document.createElement("input");

            input.type = "text";
            input.setAttribute("data-coloris", "");
            input.value = colour;
            input.style.background = colour;


            input.addEventListener(
                "input",
                (event) => {
                    blockColours[index] =
                        event.target.value;
                    event.target.style.background =
                        event.target.value;

                    updateSimpleBlocks();
                }
            );


            const footer =
                document.createElement("div");

            footer.className =
                "block-swatch-footer";


            const label =
                document.createElement("span");

            label.textContent =
                `Colour ${index + 1}`;


            const controls =
                document.createElement("div");

            controls.className =
                "reorder-buttons";


            if (index > 0) {
                const up =
                    document.createElement("button");

                up.type = "button";
                up.textContent = "←";
                up.title =
                    "Move colour left/up";

                up.addEventListener(
                    "click",
                    () => {
                        moveArrayItem(
                            blockColours,
                            index,
                            index - 1
                        );

                        renderBlockSwatches();
                        updateSimpleBlocks();
                    }
                );

                controls.appendChild(up);
            }


            if (
                index <
                blockColours.length - 1
            ) {
                const down =
                    document.createElement("button");

                down.type = "button";
                down.textContent = "→";
                down.title =
                    "Move colour right/down";


                down.addEventListener(
                    "click",
                    () => {
                        moveArrayItem(
                            blockColours,
                            index,
                            index + 1
                        );

                        renderBlockSwatches();
                        updateSimpleBlocks();
                    }
                );

                controls.appendChild(down);
            }


            if (blockColours.length > 1) {
                const removeBtn =
                    document.createElement(
                        "button"
                    );

                removeBtn.type = "button";
                removeBtn.className =
                    "remove-block";

                removeBtn.textContent = "×";
                removeBtn.title =
                    "Remove colour";


                removeBtn.addEventListener(
                    "click",
                    () => {
                        blockColours.splice(
                            index,
                            1
                        );

                        renderBlockSwatches();
                        updateSimpleBlocks();
                    }
                );

                controls.appendChild(
                    removeBtn
                );
            }


            footer.appendChild(label);
            footer.appendChild(controls);

            swatch.appendChild(input);
            swatch.appendChild(footer);

            blockSwatchRow.appendChild(
                swatch
            );
        }
    );

    if (typeof Coloris !== "undefined") {
        try {
            Coloris({ el: "[data-coloris]" });
        } catch (e) {}
    }
}


function updateSimpleBlocks() {
    const colourField =
        document.getElementById("colour");

    if (colourField) {
        colourField.value =
            blockColours.join(",");
    }

    if (blockColours.length === 0) {
        setCssFields(
            "#111",
            "#111"
        );

        return;
    }


    if (blockColours.length === 1) {
        setCssFields(
            blockColours[0],
            blockColours[0]
        );

        return;
    }


    const step =
        100 / blockColours.length;


    const stops =
        blockColours
            .map((colour, index) => {
                const start =
                    (index * step).toFixed(2);

                const end =
                    ((index + 1) * step)
                        .toFixed(2);

                return `${colour} ${start}% ${end}%`;
            })
            .join(", ");


    const isHorizontal =
        horizontalCheckbox
            ? horizontalCheckbox.checked
            : false;


    const leftDirection =
        isHorizontal
            ? "to bottom"
            : "to right";


    const rightDirection =
        isHorizontal
            ? "to bottom"
            : "to left";


    const leftCss =
        `linear-gradient(${leftDirection}, ${stops})`;


    const rightCss =
        `linear-gradient(${rightDirection}, ${stops})`;


    setCssFields(
        leftCss,
        rightCss
    );
}


if (addBlockColourBtn) {
    addBlockColourBtn.addEventListener(
        "click",
        () => {
            blockColours.push(
                "#000000"
            );

            renderBlockSwatches();
            updateSimpleBlocks();
        }
    );
}


if (horizontalCheckbox) {
    horizontalCheckbox.addEventListener(
        "change",
        updateSimpleBlocks
    );
}


/* ==========================================================================
   QUICK > SHAPE
   ========================================================================== */

const shapeGrid =
    document.getElementById(
        "shapeGrid"
    );

const shapeColourInput =
    document.getElementById(
        "shapeColour"
    );

const addShapeLayerButton =
    document.getElementById(
        "addShapeLayer"
    );

const shapeLayersContainer =
    document.getElementById(
        "shapeLayers"
    );

const shapeBackgroundInput =
    document.getElementById(
        "shapeBackgroundColour"
    );


let selectedShapeIndex = 0;


/*
 * The first entry is the top CSS layer.
 *
 * layers[0]
 *     ↓
 * top/background layer
 *
 * layers[last]
 *     ↓
 * bottom/background layer
 */

let shapeLayers = [];

let draggedShapeIndex = null;


function renderShapeGrid() {
    if (!shapeGrid) {
        return;
    }

    shapeGrid.innerHTML = "";

    SHAPES.forEach(
        (entry, index) => {
            const name = entry[0];
            const leftCss = entry[1];

            const option =
                document.createElement("div");

            option.className =
                "shape-option";

            option.dataset.index =
                String(index);


            const preview =
                document.createElement("div");

            preview.className =
                "shape-preview";

            preview.style.background =
                leftCss.replace(
                    /user_colour/g,
                    shapeColourInput
                        ? shapeColourInput.value
                        : "#000000"
                );


            const label =
                document.createElement("small");

            label.textContent =
                name;


            option.appendChild(preview);
            option.appendChild(label);


            option.addEventListener(
                "click",
                () => {
                    selectedShapeIndex =
                        index;

                    renderShapeGrid();
                }
            );


            if (
                index ===
                selectedShapeIndex
            ) {
                option.classList.add(
                    "selected-shape"
                );
            }


            shapeGrid.appendChild(
                option
            );
        }
    );
}


function createShapeLayer() {
    const entry =
        SHAPES[selectedShapeIndex];
    const name =
        entry[0];
    const leftTemplate =
        entry[1];
    const rightTemplate =
        entry[2] || entry[1];

    const colour =
        shapeColourInput
            ? shapeColourInput.value
            : "#000000";

    return {
        id:
            `${Date.now()}-${Math.random()}`,

        name,

        colour,

        leftTemplate,
        rightTemplate,

        css:
            leftTemplate.replace(
                /user_colour/g,
                colour
            ),

        cssLeft:
            leftTemplate.replace(
                /user_colour/g,
                colour
            ),

        cssRight:
            rightTemplate.replace(
                /user_colour/g,
                colour
            )
    };
}


function renderShapeLayers() {
    if (!shapeLayersContainer) {
        return;
    }

    shapeLayersContainer.innerHTML = "";

    shapeLayers.forEach(
        (layer, index) => {
            const row =
                document.createElement("div");

            row.className =
                "shape-layer";

            row.draggable = true;

            row.dataset.index =
                String(index);


            row.addEventListener(
                "dragstart",
                () => {
                    draggedShapeIndex =
                        index;

                    row.classList.add(
                        "dragging"
                    );
                }
            );


            row.addEventListener(
                "dragend",
                () => {
                    draggedShapeIndex =
                        null;

                    row.classList.remove(
                        "dragging"
                    );
                }
            );


            row.addEventListener(
                "dragover",
                (event) => {
                    event.preventDefault();
                }
            );


            row.addEventListener(
                "drop",
                (event) => {
                    event.preventDefault();

                    if (
                        draggedShapeIndex === null ||
                        draggedShapeIndex === index
                    ) {
                        return;
                    }

                    moveArrayItem(
                        shapeLayers,
                        draggedShapeIndex,
                        index
                    );

                    renderShapeLayers();
                    updateShapeCss();
                }
            );


            const preview =
                document.createElement("div");

            preview.className =
                "shape-layer-preview";

            preview.style.background =
                layer.cssLeft || layer.css;
            preview.style.position =
                "relative";
            preview.style.overflow =
                "hidden";
            preview.style.cursor =
                "pointer";
            preview.title =
                "Click to recolour";

            const picker =
                document.createElement(
                    "input"
                );

            picker.type =
                "text";
            picker.setAttribute(
                "data-coloris",
                ""
            );
            picker.value =
                layer.colour;
            picker.style.position =
                "absolute";
            picker.style.inset =
                "0";
            picker.style.opacity =
                "0";
            picker.style.cursor =
                "pointer";
            picker.style.width =
                "100%";
            picker.style.height =
                "100%";

            picker.addEventListener(
                "input",
                (event) => {
                    const newColour =
                        event.target.value;

                    if (
                        !/^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/i.test(
                            newColour
                        )
                    ) {
                        return;
                    }

                    layer.colour =
                        newColour;

                    const template =
                        SHAPES.find(
                            ([n]) =>
                                n ===
                                layer.name
                        );

                    if (template) {
                        const leftTpl = template[1];
                        const rightTpl =
                            template[2] || template[1];
                        layer.leftTemplate = leftTpl;
                        layer.rightTemplate = rightTpl;
                        layer.cssLeft =
                            leftTpl.replace(
                                /user_colour/g,
                                newColour
                            );
                        layer.cssRight =
                            rightTpl.replace(
                                /user_colour/g,
                                newColour
                            );
                        layer.css = layer.cssLeft;
                    } else {
                        layer.cssLeft = (
                            layer.cssLeft || layer.css
                        ).replace(
                            /#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})/i,
                            newColour
                        );
                        layer.cssRight = (
                            layer.cssRight || layer.css
                        ).replace(
                            /#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})/i,
                            newColour
                        );
                        layer.css = layer.cssLeft;
                    }

                    colour.textContent =
                        newColour;
                    preview.style.background =
                        layer.cssLeft || layer.css;

                    updateShapeCss();
                }
            );

            preview.appendChild(
                picker
            );


            const info =
                document.createElement("div");

            info.className =
                "shape-layer-info";


            const title =
                document.createElement("strong");

            title.textContent =
                layer.name;


            const colour =
                document.createElement("small");

            colour.textContent =
                layer.colour;


            info.appendChild(title);
            info.appendChild(colour);


            const controls =
                document.createElement("div");

            controls.className =
                "shape-layer-controls";


            if (index > 0) {
                const up =
                    document.createElement(
                        "button"
                    );

                up.type = "button";
                up.textContent = "↑";


                up.addEventListener(
                    "click",
                    () => {
                        moveArrayItem(
                            shapeLayers,
                            index,
                            index - 1
                        );

                        renderShapeLayers();
                        updateShapeCss();
                    }
                );

                controls.appendChild(up);
            }


            if (
                index <
                shapeLayers.length - 1
            ) {
                const down =
                    document.createElement(
                        "button"
                    );

                down.type = "button";
                down.textContent = "↓";


                down.addEventListener(
                    "click",
                    () => {
                        moveArrayItem(
                            shapeLayers,
                            index,
                            index + 1
                        );

                        renderShapeLayers();
                        updateShapeCss();
                    }
                );

                controls.appendChild(down);
            }


            const remove =
                document.createElement(
                    "button"
                );

            remove.type = "button";
            remove.textContent =
                "Remove";


            remove.addEventListener(
                "click",
                () => {
                    shapeLayers.splice(
                        index,
                        1
                    );

                    renderShapeLayers();
                    updateShapeCss();
                }
            );


            controls.appendChild(remove);


            row.appendChild(preview);
            row.appendChild(info);
            row.appendChild(controls);

            shapeLayersContainer.appendChild(
                row
            );
        }
    );

    if (typeof Coloris !== "undefined") {
        try {
            Coloris({ el: "[data-coloris]" });
        } catch (e) {}
    }
}


function updateShapeCss() {
    const backgroundCss =
        shapeBackgroundInput
            ? shapeBackgroundInput.value.trim() || "#ffffff"
            : "#ffffff";

    const layersLeftCss =
        shapeLayers
            .map((layer) => layer.cssLeft || layer.css)
            .join(", ");

    const layersRightCss =
        shapeLayers
            .map((layer) => layer.cssRight || layer.css)
            .join(", ");

    const leftCss =
        layersLeftCss
            ? `${layersLeftCss}, ${backgroundCss}`
            : backgroundCss;

    const rightCss =
        layersRightCss
            ? `${layersRightCss}, ${backgroundCss}`
            : backgroundCss;


    const shapeCssField =
        document.getElementById(
            "shape-css"
        );

    const shapeNameField =
        document.getElementById(
            "shape-name"
        );


    if (shapeCssField) {
        shapeCssField.value = leftCss;
    }


    if (shapeNameField) {
        shapeNameField.value =
            shapeLayers
                .map((layer) => layer.name)
                .join(", ");
    }


    setCssFields(
        leftCss || "#111",
        rightCss || "#111"
    );
}


if (addShapeLayerButton) {
    addShapeLayerButton.addEventListener(
        "click",
        () => {
            shapeLayers.unshift(
                createShapeLayer()
            );

            renderShapeLayers();
            updateShapeCss();
        }
    );
}


if (shapeColourInput) {
    shapeColourInput.style.background =
        shapeColourInput.value;
    shapeColourInput.addEventListener(
        "input",
        (event) => {
            event.target.style.background =
                event.target.value;
            renderShapeGrid();
        }
    );
}

if (shapeBackgroundInput) {
    shapeBackgroundInput.style.background =
        shapeBackgroundInput.value;
    shapeBackgroundInput.addEventListener(
        "input",
        (event) => {
            event.target.style.background =
                event.target.value;
            updateShapeCss();
        }
    );
}


renderShapeGrid();
renderShapeLayers();
updateShapeCss();


/* ==========================================================================
   LiveryLab import
   ========================================================================== */

const liveryLabDecodeButton =
    document.getElementById(
        "liverylab-decode"
    );


if (liveryLabDecodeButton) {
    liveryLabDecodeButton.addEventListener(
        "click",
        async () => {
            const statusEl =
                document.getElementById(
                    "liverylab-status"
                );

            const codeField =
                document.getElementById(
                    "liverylab-code"
                ) ||
                document.getElementById(
                    "liverylab-url"
                );

            let code =
                codeField
                    ? codeField.value.trim()
                    : "";

            // Allow pasting full URL and extract code
            const urlMatch = code.match(
                /(\d{6})/
            );
            if (urlMatch) {
                code = urlMatch[1];
                if (codeField) {
                    codeField.value = code;
                }
            }

            if (!code) {
                if (statusEl) {
                    statusEl.textContent =
                        "Enter the 6 digit code first.";

                    statusEl.className =
                        "import-status error";
                }

                return;
            }

            if (!/^\d{6}$/.test(code)) {
                if (statusEl) {
                    statusEl.textContent =
                        "Code must be 6 digits.";

                    statusEl.className =
                        "import-status error";
                }

                return;
            }


            if (statusEl) {
                statusEl.textContent =
                    "Importing…";

                statusEl.className =
                    "import-status";
            }


            try {
                const response =
                    await fetch(
                        `/api/liverylab/${code}/`,
                        {
                            method: "GET",
                            credentials: "same-origin"
                        }
                    );


                let data = {};

                try {
                    data =
                        await response.json();
                } catch (jsonError) {
                    data = {};
                }


                if (!response.ok) {
                    throw new Error(
                        data.error ||
                        data.message ||
                        "Import failed."
                    );
                }


                const leftCss =
                    data.left ||
                    data.leftCss ||
                    data.left_css ||
                    data.css ||
                    "";


                const rightCss =
                    data.right ||
                    data.rightCss ||
                    data.right_css ||
                    data.css ||
                    "";


                if (!leftCss && !rightCss) {
                    throw new Error(
                        "The API returned no CSS."
                    );
                }


                cssLeftField.value =
                    leftCss || "#111";

                cssRightField.value =
                    rightCss || "#111";


                if (data.name) {
                    const nameField =
                        document.getElementById(
                            "livery-name"
                        );

                    if (nameField) {
                        nameField.value =
                            data.name;
                    }
                }


                const textVal =
                    data.text ||
                    data.textColour ||
                    data.text_colour ||
                    data.textColor;

                if (textVal) {
                    textColourField.value =
                        textVal;
                }


                const strokeVal =
                    data.stroke ||
                    data.strokeColour ||
                    data.stroke_colour ||
                    data.strokeColor;

                if (strokeVal) {
                    textStrokeColourField.value =
                        strokeVal;
                }


                // Derive blob colour if not provided
                const blobVal =
                    data.livery_colour ||
                    data.liveryColor ||
                    data.blob ||
                    "";

                if (blobVal) {
                    liveryColourField.value =
                        blobVal;
                } else {
                    const hexes =
                        extractHexColors(
                            leftCss || rightCss
                        );
                    if (hexes.length) {
                        liveryColourField.value =
                            hexes[0];
                    }
                }


                delete cssLeftField.dataset.base;
                delete cssRightField.dataset.base;

                applyCssToCells();


                if (statusEl) {
                    statusEl.textContent =
                        "Imported successfully.";

                    statusEl.className =
                        "import-status success";
                }

                // Take straight to details
                const detailsTab =
                    document.querySelector(
                        '.livery-creator-tab[data-tab="details"]'
                    );

                if (detailsTab) {
                    detailsTab.classList.remove(
                        "disabled-tab"
                    );
                }

                activateTopTab("details");
            } catch (error) {
                console.error(
                    "LiveryLab import failed:",
                    error
                );


                if (statusEl) {
                    statusEl.textContent =
                        error.message ||
                        "Something went wrong importing that code.";

                    statusEl.className =
                        "import-status error";
                }
            }
        }
    );
}


/* ==========================================================================
   LiveryLab 6-box OTP handling (Cloudflare-style)
   ========================================================================== */

(function setupLiverylabOtp() {
    const boxes =
        document.querySelectorAll(
            ".liverylab-code-box"
        );
    const hidden =
        document.getElementById(
            "liverylab-code"
        );

    if (!boxes.length || !hidden) {
        return;
    }

    const getCode = () =>
        Array.from(boxes)
            .map((b) => b.value)
            .join("");

    const updateHidden = () => {
        hidden.value = getCode();
    };

    boxes.forEach((box, idx) => {
        box.addEventListener("input", (e) => {
            let val = e.target.value.replace(
                /\D/g,
                ""
            );
            if (val.length > 1) {
                val = val.slice(-1);
            }
            e.target.value = val;
            updateHidden();
            if (
                val &&
                idx < boxes.length - 1
            ) {
                boxes[idx + 1].focus();
            }
        });

        box.addEventListener("keydown", (e) => {
            if (
                e.key === "Backspace" &&
                !e.target.value &&
                idx > 0
            ) {
                boxes[idx - 1].focus();
                boxes[idx - 1].value = "";
                updateHidden();
                e.preventDefault();
            } else if (
                e.key === "ArrowLeft" &&
                idx > 0
            ) {
                boxes[idx - 1].focus();
            } else if (
                e.key === "ArrowRight" &&
                idx < boxes.length - 1
            ) {
                boxes[idx + 1].focus();
            }
        });

        box.addEventListener("paste", (e) => {
            e.preventDefault();
            const paste = (
                e.clipboardData ||
                window.clipboardData
            ).getData("text");
            const digits = paste
                .replace(/\D/g, "")
                .slice(0, 6);
            if (!digits) {
                return;
            }
            digits
                .split("")
                .forEach((d, i) => {
                    if (boxes[i]) {
                        boxes[i].value = d;
                    }
                });
            updateHidden();
            const next = Math.min(
                digits.length,
                boxes.length - 1
            );
            boxes[next].focus();
        });

        box.addEventListener("focus", (e) =>
            e.target.select()
        );
    });

    hidden.addEventListener("input", () => {
        const v = hidden.value
            .replace(/\D/g, "")
            .slice(0, 6);
        v.split("").forEach((d, i) => {
            if (boxes[i]) {
                boxes[i].value = d;
            }
        });
        // Clear remaining
        for (
            let i = v.length;
            i < boxes.length;
            i++
        ) {
            boxes[i].value = "";
        }
        hidden.value = v;
    });
})();


/* ==========================================================================
   CSS colour extraction
   ========================================================================== */

function extractHexColors(css) {
    const pattern =
        /#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b/g;


    const expandHex =
        (hex) => {
            if (hex.length === 4) {
                return (
                    "#" +
                    hex[1] + hex[1] +
                    hex[2] + hex[2] +
                    hex[3] + hex[3]
                );
            }

            return hex;
        };


    return (
        css.match(pattern) || []
    ).map(expandHex);
}


/* ==========================================================================
   MBT Recolour
   ========================================================================== */

function replaceColoursInCss(
    css,
    replacements
) {
    if (!css) {
        return css;
    }


    const pattern =
        /#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b/g;


    return css.replace(
        pattern,
        (matched) => {
            const expanded =
                matched.length === 4
                    ? (
                        "#" +
                        matched[1] +
                        matched[1] +
                        matched[2] +
                        matched[2] +
                        matched[3] +
                        matched[3]
                    )
                    : matched;


            const key =
                expanded.toLowerCase();


            return (
                replacements[key] ||
                matched
            );
        }
    );
}


let mbtBaseLeftCss = "";
let mbtBaseRightCss = "";

let recolourColours = [];

let draggedRecolourIndex = null;


function buildRecolourPalette(
    leftCss,
    rightCss
) {
    const combined = [
        ...extractHexColors(leftCss),
        ...extractHexColors(rightCss)
    ];


    const unique =
        [
            ...new Set(
                combined.map(
                    (colour) =>
                        colour.toLowerCase()
                )
            )
        ];


    recolourColours =
        unique.map(
            (colour) => ({
                original: colour,
                colour
            })
        );


    renderRecolourColours();
}


function renderRecolourColours() {
    const container =
        document.getElementById(
            "colorPickersBoth"
        );


    if (!container) {
        return;
    }


    container.innerHTML = "";


    recolourColours.forEach(
        (item, index) => {
            const row =
                document.createElement("div");

            row.className =
                "recolour-colour-row";

            row.draggable = true;


            row.addEventListener(
                "dragstart",
                () => {
                    draggedRecolourIndex =
                        index;

                    row.classList.add(
                        "dragging"
                    );
                }
            );


            row.addEventListener(
                "dragend",
                () => {
                    draggedRecolourIndex =
                        null;

                    row.classList.remove(
                        "dragging"
                    );
                }
            );


            row.addEventListener(
                "dragover",
                (event) => {
                    event.preventDefault();
                }
            );


            row.addEventListener(
                "drop",
                (event) => {
                    event.preventDefault();

                    if (
                        draggedRecolourIndex === null ||
                        draggedRecolourIndex === index
                    ) {
                        return;
                    }


                    moveArrayItem(
                        recolourColours,
                        draggedRecolourIndex,
                        index
                    );


                    renderRecolourColours();
                }
            );


            const handle =
                document.createElement(
                    "span"
                );

            handle.className =
                "drag-handle";

            handle.textContent =
                "☰";


            const input =
                document.createElement(
                    "input"
                );

            input.type = "text";
            input.setAttribute("data-coloris", "");

            input.value =
                item.colour;
            input.style.background =
                item.colour;


            input.addEventListener(
                "input",
                (event) => {
                    item.colour =
                        event.target.value;
                    event.target.style.background =
                        event.target.value;

                    updateCombinedRecolour();
                }
            );


            const label =
                document.createElement(
                    "span"
                );

            label.className =
                "colour-label";

            label.textContent =
                `${item.original} → ${item.colour}`;


            const up =
                document.createElement(
                    "button"
                );

            up.type =
                "button";

            up.textContent =
                "↑";


            up.addEventListener(
                "click",
                () => {
                    if (index === 0) {
                        return;
                    }


                    moveArrayItem(
                        recolourColours,
                        index,
                        index - 1
                    );


                    renderRecolourColours();
                }
            );


            const down =
                document.createElement(
                    "button"
                );

            down.type =
                "button";

            down.textContent =
                "↓";


            down.addEventListener(
                "click",
                () => {
                    if (
                        index ===
                        recolourColours.length - 1
                    ) {
                        return;
                    }


                    moveArrayItem(
                        recolourColours,
                        index,
                        index + 1
                    );


                    renderRecolourColours();
                }
            );


            row.appendChild(handle);
            row.appendChild(input);
            row.appendChild(label);
            row.appendChild(up);
            row.appendChild(down);

            container.appendChild(row);
        }
    );

    if (typeof Coloris !== "undefined") {
        try {
            Coloris({ el: "[data-coloris]" });
        } catch (e) {}
    }

    updateCombinedRecolour();
}


function updateCombinedRecolour() {
    if (
        !mbtBaseLeftCss &&
        !mbtBaseRightCss
    ) {
        return;
    }


    const replacements = {};


    recolourColours.forEach(
        (item) => {
            replacements[
                item.original.toLowerCase()
            ] =
                item.colour;
        }
    );


    const newLeftCss =
        replaceColoursInCss(
            mbtBaseLeftCss,
            replacements
        );


    const newRightCss =
        replaceColoursInCss(
            mbtBaseRightCss,
            replacements
        );


    cssLeftField.value =
        newLeftCss;

    cssRightField.value =
        newRightCss;


    applyCssToCells();
}


/* ==========================================================================
   MBT Livery API

   This is the MBT source for the
   BusTimes/Recolour mode.
   ========================================================================== */

if (
    typeof $ !== "undefined"
) {
    $(document).ready(function () {

        function formatLivery(livery) {
            if (!livery.id) {
                return livery.text;
            }


            const option =
                $("#bustimes-livery").find(
                    `option[value="${livery.id}"]`
                );


            const leftCss =
                livery.left_css ||
                option.data("left_css") ||
                "#ccc";


            return $(
                `
                <div style="display:flex;align-items:center;gap:8px;">
                    <div
                        style="
                            width:45px;
                            height:25px;
                            border:1px solid var(--border-color);
                            border-radius:3px;
                            background:${leftCss};
                        ">
                    </div>

                    <span>${livery.text}</span>
                </div>
                `
            );
        }


        const bustimesLivery =
            $("#bustimes-livery");


        if (
            bustimesLivery.length &&
            typeof bustimesLivery.select2 === "function"
        ) {
            bustimesLivery.select2({
                placeholder:
                    "Select a livery",

                allowClear:
                    true,

                width:
                    "100%",

                templateResult:
                    formatLivery,

                templateSelection:
                    formatLivery,

                ajax: {
                    url:
                        "https://bustimes.org/api/liveries/",

                    dataType:
                        "json",

                    delay:
                        250,

                    data:
                        (params) => ({
                            limit:
                                100,

                            offset:
                                params.page
                                    ? params.page * 100
                                    : 0,

                            name__icontains:
                                params.term || ""
                        }),

                    processResults:
                        (data) => ({
                            results:
                                data.results.map(
                                    (livery) => ({
                                        id:
                                            livery.id,

                                        text:
                                            livery.name,

                                        left_css:
                                            livery.left_css,

                                        right_css:
                                            livery.right_css
                                    })
                                ),

                            pagination: {
                                more:
                                    data.next !== null
                            }
                        }),

                    cache:
                        true
                },

                minimumInputLength:
                    0
            });


            bustimesLivery.on(
                "select2:select",
                function (event) {
                    const selected =
                        event.params.data;


                    const leftCss =
                        selected.left_css ||
                        "";

                    const rightCss =
                        selected.right_css ||
                        "";


                    const nameField =
                        document.getElementById(
                            "livery-name"
                        );


                    if (nameField) {
                        nameField.value =
                            selected.text || "";
                    }

                    mbtBaseLeftCss = leftCss;
                    mbtBaseRightCss = rightCss;

                    cssLeftField.dataset.base = leftCss;
                    cssRightField.dataset.base = rightCss;

                    buildRecolourPalette(leftCss, rightCss);

                    applyCssToCells();
                    updateRecolourVisibility();
                }
            );


            bustimesLivery.on(
                "select2:clear",
                function () {
                    const statusEl =
                        document.getElementById(
                            "bustimes-status"
                        );

                    if (statusEl) {
                        statusEl.textContent = "";
                        statusEl.className =
                            "import-status";
                    }

                    mbtBaseLeftCss = "";
                    mbtBaseRightCss = "";
                    recolourColours = [];

                    const recolourContainer =
                        document.getElementById(
                            "colorPickersBoth"
                        );

                    if (recolourContainer) {
                        recolourContainer.innerHTML = "";
                    }

                    delete cssLeftField.dataset.base;
                    delete cssRightField.dataset.base;

                    applyCssToCells();
                }
            );
        }


        /*
         * Legacy own-livery select.
         */

        const ownLivery =
            $("#livery");


        if (
            ownLivery.length &&
            typeof ownLivery.select2 === "function"
        ) {
            ownLivery.select2({
                placeholder:
                    "Select a livery",

                allowClear:
                    true,

                width:
                    "100%",

                ajax: {
                    url:
                        "/api/liveries/",

                    dataType:
                        "json",

                    delay:
                        250,

                    data:
                        (params) => ({
                            limit:
                                100,

                            offset:
                                params.page
                                    ? params.page * 100
                                    : 0,

                            name__icontains:
                                params.term || ""
                        }),

                    processResults:
                        (data) => ({
                            results:
                                data.results.map(
                                    (livery) => ({
                                        id:
                                            livery.id,

                                        text:
                                            livery.name,

                                        left_css:
                                            livery.left_css,

                                        right_css:
                                            livery.right_css
                                    })
                                ),

                            pagination: {
                                more:
                                    data.next !== null
                            }
                        }),

                    cache:
                        true
                },

                minimumInputLength:
                    0
            });

            ownLivery.on(
                "select2:select",
                function (event) {
                    const selected =
                        event.params.data;

                    const leftCss =
                        selected.left_css || "";

                    const rightCss =
                        selected.right_css || "";

                    const nameField =
                        document.getElementById(
                            "livery-name"
                        );

                    if (nameField) {
                        nameField.value =
                            selected.text || "";
                    }

                    mbtBaseLeftCss =
                        leftCss;

                    mbtBaseRightCss =
                        rightCss;

                    cssLeftField.dataset.base =
                        leftCss;

                    cssRightField.dataset.base =
                        rightCss;

                    buildRecolourPalette(
                        leftCss,
                        rightCss
                    );

                    applyCssToCells();
                    updateRecolourVisibility();
                }
            );

            ownLivery.on(
                "select2:clear",
                function () {
                    mbtBaseLeftCss = "";
                    mbtBaseRightCss = "";
                    recolourColours = [];

                    const recolourContainer =
                        document.getElementById(
                            "colorPickersBoth"
                        );

                    if (recolourContainer) {
                        recolourContainer.innerHTML =
                            "";
                    }

                    delete cssLeftField.dataset.base;
                    delete cssRightField.dataset.base;

                    applyCssToCells();
                }
            );
        }
    });
}


/* ==========================================================================
   Manual CSS
   ========================================================================== */

if (cssLeftField) {
    cssLeftField.addEventListener(
        "input",
        () => {
            delete cssLeftField.dataset.base;

            applyCssToCells();
        }
    );
}


if (cssRightField) {
    cssRightField.addEventListener(
        "input",
        () => {
            delete cssRightField.dataset.base;

            applyCssToCells();
        }
    );
}


/* ==========================================================================
   Details palette
   ========================================================================== */

function currentPalette() {
    const combined = [
        ...extractHexColors(
            cssLeftField.value
        ),

        ...extractHexColors(
            cssRightField.value
        )
    ];


    return [
        ...new Set(
            combined.map(
                (colour) =>
                    colour.toLowerCase()
            )
        )
    ];
}


function rebuildPaletteChoices() {
    buildStrokeChoices();
    buildBlobChoices();
}


/* ==========================================================================
   Text colour
   ========================================================================== */

const textColourChoicesRow =
    document.getElementById(
        "textColourChoices"
    );

const textColourCustomTrigger =
    document.getElementById(
        "textColourCustomTrigger"
    );

const textColourCustomPicker =
    document.getElementById(
        "textColourCustomPicker"
    );


function selectTextColour(
    colour,
    element
) {
    const currentStroke = textStrokeColourField
        ? textStrokeColourField.value.trim()
        : "";
    if (
        currentStroke &&
        currentStroke.toLowerCase() !== "none" &&
        isSimilarColour(colour, currentStroke, 100)
    ) {
        showSimilarPopup(colour, currentStroke);
        return;
    }

    textColourField.value =
        colour;


    if (textColourChoicesRow) {
        textColourChoicesRow
            .querySelectorAll(
                ".swatch-choice"
            )
            .forEach((swatch) => {
                swatch.classList.remove(
                    "selected-swatch"
                );
            });
    }


    if (element) {
        element.classList.add(
            "selected-swatch"
        );
    }


    applyTextStyling();
    scheduleAutosave();
}


if (textColourChoicesRow) {
    textColourChoicesRow
        .querySelectorAll(
            ".swatch-choice[data-fixed-colour]"
        )
        .forEach((element) => {
            element.addEventListener(
                "click",
                () => {
                    selectTextColour(
                        element.dataset.fixedColour,
                        element
                    );
                }
            );
        });
}





/* ==========================================================================
   Stroke choices
   ========================================================================== */

function buildStrokeChoices() {
    const row =
        document.getElementById(
            "strokeColourChoices"
        );


    if (!row) {
        return;
    }


    const basePalette =
        currentPalette();

    const palette = [
        "#ffffff",
        "#000000",
        ...basePalette.filter(
            (c) =>
                c.toLowerCase() !== "#ffffff" &&
                c.toLowerCase() !== "#000000"
        )
    ];

    row.innerHTML = "";


    palette.forEach(
        (colour) => {
            const swatch =
                document.createElement(
                    "div"
                );

            swatch.className =
                "swatch-choice";

            swatch.style.background =
                colour;

            swatch.title =
                colour;


            if (
                colour ===
                textStrokeColourField.value
                    .toLowerCase()
            ) {
                swatch.classList.add(
                    "selected-swatch"
                );
            }


            swatch.addEventListener(
                "click",
                () => {
                    const currentText = textColourField
                        ? textColourField.value.trim()
                        : "";
                    if (
                        currentText &&
                        isSimilarColour(
                            currentText,
                            colour,
                            100
                        )
                    ) {
                        showSimilarPopup(
                            currentText,
                            colour
                        );
                        return;
                    }

                    const strokeNone =
                        document.getElementById(
                            "strokeNone"
                        );


                    if (strokeNone) {
                        strokeNone.checked =
                            false;
                    }


                    row
                        .querySelectorAll(
                            ".swatch-choice"
                        )
                        .forEach((item) => {
                            item.classList.remove(
                                "selected-swatch"
                            );
                        });


                    swatch.classList.add(
                        "selected-swatch"
                    );


                    textStrokeColourField.value =
                        colour;

                    if (liveryColourField) {
                        liveryColourField.value =
                            colour;
                    }


                    applyTextStyling();
                    scheduleAutosave();
                }
            );


            row.appendChild(
                swatch
            );
        }
    );
}


const strokeNone =
    document.getElementById(
        "strokeNone"
    );


if (strokeNone) {
    strokeNone.addEventListener(
        "change",
        (event) => {
            if (event.target.checked) {
                textStrokeColourField.value =
                    "none";


                const row =
                    document.getElementById(
                        "strokeColourChoices"
                    );


                if (row) {
                    row
                        .querySelectorAll(
                            ".swatch-choice"
                        )
                        .forEach((swatch) => {
                            swatch.classList.remove(
                                "selected-swatch"
                            );
                        });
                }


                applyTextStyling();
                scheduleAutosave();
            } else {
                scheduleAutosave();
            }
        }
    );
}


/* ==========================================================================
   Blob colour
   ========================================================================== */

function buildBlobChoices() {
    const row =
        document.getElementById(
            "blobColourChoices"
        );


    if (!row) {
        return;
    }


    const palette =
        currentPalette();


    row.innerHTML = "";


    palette.forEach(
        (colour) => {
            const swatch =
                document.createElement(
                    "div"
                );

            swatch.className =
                "swatch-choice";

            swatch.style.background =
                colour;

            swatch.title =
                colour;


            if (
                colour ===
                liveryColourField.value
                    .toLowerCase()
            ) {
                swatch.classList.add(
                    "selected-swatch"
                );
            }


            swatch.addEventListener(
                "click",
                () => {
                    row
                        .querySelectorAll(
                            ".swatch-choice"
                        )
                        .forEach((item) => {
                            item.classList.remove(
                                "selected-swatch"
                            );
                        });


                    swatch.classList.add(
                        "selected-swatch"
                    );


                    liveryColourField.value =
                        colour;


                    applyTextStyling();
                    scheduleAutosave();
                }
            );


            row.appendChild(
                swatch
            );
        }
    );
}


/* ==========================================================================
   Form validation
   ========================================================================== */

const liveryCreatorForm =
    document.getElementById(
        "livery-creator-form"
    );


if (liveryCreatorForm) {
    liveryCreatorForm.addEventListener(
        "submit",
        function (event) {
            const text =
                textColourField.value.trim();

            const stroke =
                textStrokeColourField.value.trim();

            const blob =
                liveryColourField.value.trim();


            const errors = [];


            if (!text) {
                errors.push(
                    "Pick a text colour."
                );
            }


            if (!stroke) {
                errors.push(
                    "Pick a stroke colour, or choose 'No stroke'."
                );
            }


            if (!blob) {
                errors.push(
                    "Pick a blob colour from your livery."
                );
            }


            if (
                stroke !== "none" &&
                text &&
                stroke &&
                isSimilarColour(text, stroke, 100)
            ) {
                event.preventDefault();
                if (
                    typeof unlockCreateButton ===
                    "function"
                ) {
                    unlockCreateButton();
                }
                showSimilarPopup(text, stroke);
                const detailsTab =
                    document.querySelector(
                        '.livery-creator-tab[data-tab="details"]'
                    );
                if (detailsTab) {
                    detailsTab.classList.remove(
                        "disabled-tab"
                    );
                }
                activateTopTab("details");
                return false;
            }


            if (
                shapeBackgroundInput &&
                !shapeBackgroundInput.value.trim()
            ) {
                errors.push(
                    "Pick a background colour for shape mode."
                );
            } else if (
                shapeBackgroundInput &&
                !/^#([0-9A-Fa-f]{6})$/.test(
                    shapeBackgroundInput.value.trim()
                )
            ) {
                errors.push(
                    "Background colour must be a valid 6-digit hex."
                );
            }


            const palette =
                currentPalette();


            if (
                blob &&
                palette.length > 0 &&
                !palette.includes(
                    blob.toLowerCase()
                )
            ) {
                errors.push(
                    "Livery blob must match one of the colours from your livery."
                );
            }


            if (errors.length > 0) {
                event.preventDefault();

                if (
                    typeof unlockCreateButton ===
                    "function"
                ) {
                    unlockCreateButton();
                }

                alert(
                    errors.join("\n")
                );


                const detailsTab =
                    document.querySelector(
                        '.livery-creator-tab[data-tab="details"]'
                    );


                if (detailsTab) {
                    detailsTab.classList.remove(
                        "disabled-tab"
                    );
                }


                activateTopTab(
                    "details"
                );


                return false;
            }

            if (
                typeof lockCreateButton ===
                "function"
            ) {
                lockCreateButton();
            }

            return true;
        }
    );
}


/* ==========================================================================
   Clear livery
   ========================================================================== */

function openClearModal() {
    const modal =
        document.getElementById(
            "clear-livery-modal"
        );

    if (modal) {
        modal.classList.add("open");
    }
}

function closeClearModal() {
    const modal =
        document.getElementById(
            "clear-livery-modal"
        );

    if (modal) {
        modal.classList.remove("open");
    }
}

function doClearLivery() {
    mbtBaseLeftCss = "";
    mbtBaseRightCss = "";
    recolourColours = [];

    const recolourContainer =
        document.getElementById(
            "colorPickersBoth"
        );

    if (recolourContainer) {
        recolourContainer.innerHTML = "";
    }

    delete cssLeftField.dataset.base;
    delete cssRightField.dataset.base;

    // Clear select2 values if present
    if (typeof $ !== "undefined") {
        const bustimesSel = $("#bustimes-livery");
        const ownSel = $("#livery");

        if (bustimesSel.length) {
            bustimesSel.val(null).trigger("change");
        }

        if (ownSel.length) {
            ownSel.val(null).trigger("change");
        }
    } else {
        const bustimesSel =
            document.getElementById(
                "bustimes-livery"
            );
        const ownSel =
            document.getElementById("livery");

        if (bustimesSel) bustimesSel.value = "";
        if (ownSel) ownSel.value = "";
    }

    // Reset status messages
    const labStatus =
        document.getElementById("liverylab-status");
    if (labStatus) {
        labStatus.textContent = "";
        labStatus.className = "import-status";
    }

    const bustimesStatus =
        document.getElementById("bustimes-status");
    if (bustimesStatus) {
        bustimesStatus.textContent = "";
        bustimesStatus.className = "import-status";
    }

    // Reset CSS preview to default
    setCssFields("#111", "#111");

    // Clear livery name optionally? keep but reset block colours to default
    blockColours = ["#c8102e", "#ffffff"];
    renderBlockSwatches();
    updateSimpleBlocks();

    // Reset shape mode
    shapeLayers = [];
    renderShapeLayers();
    if (shapeBackgroundInput) {
        shapeBackgroundInput.value = "#ffffff";
        shapeBackgroundInput.style.background = "#ffffff";
    }

    closeClearModal();
}

document
    .querySelectorAll(".clear-livery-button")
    .forEach((btn) => {
        btn.addEventListener("click", openClearModal);
    });

const clearCancel =
    document.getElementById("clear-livery-cancel");

if (clearCancel) {
    clearCancel.addEventListener(
        "click",
        closeClearModal
    );
}

const clearConfirm =
    document.getElementById("clear-livery-confirm");

if (clearConfirm) {
    clearConfirm.addEventListener(
        "click",
        doClearLivery
    );
}

const clearModal =
    document.getElementById("clear-livery-modal");

if (clearModal) {
    clearModal.addEventListener(
        "click",
        (event) => {
            if (event.target === clearModal) {
                closeClearModal();
            }
        }
    );
}

const similarModal =
    document.getElementById(
        "similar-colour-modal"
    );
const similarClose =
    document.getElementById(
        "similar-colour-close"
    );

if (similarClose) {
    similarClose.addEventListener(
        "click",
        hideSimilarPopup
    );
}

if (similarModal) {
    similarModal.addEventListener(
        "click",
        (event) => {
            if (event.target === similarModal) {
                hideSimilarPopup();
            }
        }
    );
}


/* ==========================================================================
   Initial state + Autosave wiring
   ========================================================================== */

const _autosaveWrapped = new Set();
function _wrapWithAutosave(fnName) {
    if (_autosaveWrapped.has(fnName)) return;
    const orig = window[fnName];
    if (typeof orig === "function") {
        window[fnName] = function (...args) {
            const res = orig.apply(this, args);
            scheduleAutosave();
            return res;
        };
        _autosaveWrapped.add(fnName);
    } else if (typeof eval(fnName) === "function") {
        // fallback for function declarations not on window
        try {
            const origFn = eval(fnName);
            eval(
                `${fnName} = function(...args){ const r = origFn.apply(this,args); scheduleAutosave(); return r; }`
            );
            _autosaveWrapped.add(fnName);
        } catch (e) {}
    }
}

[
    "renderBlockSwatches",
    "updateSimpleBlocks",
    "renderShapeLayers",
    "updateShapeCss",
    "renderRecolourColours",
    "buildRecolourPalette",
    "updateCombinedRecolour",
    "applyCssToCells",
    "activateTopTab"
].forEach((n) => {
    try {
        const fn = eval(n);
        if (typeof fn === "function") {
            const orig = fn;
            eval(
                `${n} = function(...args){ const r = orig.apply(this,args); scheduleAutosave(); return r; }`
            );
        }
    } catch (e) {}
});

document.addEventListener("input", scheduleAutosave);
document.addEventListener("change", scheduleAutosave);
document
    .querySelectorAll(
        ".livery-creator-tab, .livery-sub-tab, .next-to-details, .clear-livery-button"
    )
    .forEach((el) =>
        el.addEventListener("click", () =>
            setTimeout(scheduleAutosave, 150)
        )
    );

// Try restore autosave, else default init
let _restored = false;
try {
    _restored = loadAutosave();
} catch (e) {}

if (!_restored) {
    activateTopTab("quick");
    renderBlockSwatches();
    updateSimpleBlocks();
    applyCssToCells();
}

// Clear autosave on successful save
if (typeof liveryCreatorForm !== "undefined" && liveryCreatorForm) {
    liveryCreatorForm.addEventListener("submit", (e) => {
        // Let validation handlers run first; clear only if not prevented
        setTimeout(() => {
            if (!e.defaultPrevented) {
                clearAutosave();
            }
        }, 50);
    });
}

// Also clear via explicit handler in validation (fallback)
const _origClearCheck = clearAutosave;
if (typeof Text !== "undefined") {
    // ensure clear is called after validation passes in the other submit handler
    document
        .getElementById("livery-creator-form")
        ?.addEventListener(
            "submit",
            function (ev) {
                // This runs after validation; if validation added errors and prevented, defaultPrevented true
                setTimeout(() => {
                    if (!ev.defaultPrevented) {
                        try {
                            localStorage.removeItem(
                                AUTOSAVE_KEY
                            );
                        } catch (e) {}
                    }
                }, 100);
            },
            true
        );
}

// Lock create button to prevent spam
const createBtn =
    document.getElementById(
        "create-livery-submit"
    );

function lockCreateButton() {
    if (!createBtn) return;
    createBtn.disabled = true;
    createBtn.style.opacity = "0.6";
    createBtn.style.pointerEvents = "none";
    if (!createBtn.dataset.originalText) {
        createBtn.dataset.originalText =
            createBtn.textContent;
    }
    createBtn.textContent = "Creating…";
}

function unlockCreateButton() {
    if (!createBtn) return;
    createBtn.disabled = false;
    createBtn.style.opacity = "";
    createBtn.style.pointerEvents = "";
    if (createBtn.dataset.originalText) {
        createBtn.textContent =
            createBtn.dataset.originalText;
    }
}

window.lockCreateButton = lockCreateButton;
window.unlockCreateButton = unlockCreateButton;

if (createBtn) {
    // Immediate click lock to stop double-click before async validation
    createBtn.addEventListener("click", () => {
        // Don't lock yet if already disabled
        if (createBtn.disabled) return;
        // Small delay to allow validation to decide, but prevent rapid double clicks
        setTimeout(() => {
            if (!createBtn.disabled) {
                // If still enabled after 50ms and form is submitting, it will be locked by submit handler
            }
        }, 50);
    });
}

const liveryFormForLock =
    document.getElementById(
        "livery-creator-form"
    );

if (liveryFormForLock && createBtn) {
    liveryFormForLock.addEventListener(
        "submit",
        () => {
            lockCreateButton();
        },
        true
    );
}

if (createBtn) {
    createBtn.addEventListener("click", () => {
        if (createBtn.disabled) return;
        // Immediate lock to stop spam, validation handlers will unlock if needed
        setTimeout(() => lockCreateButton(), 0);
    });
}