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
   Preview
   ========================================================================== */

function applyCssToCells() {
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
                text.toLowerCase() ===
                stroke.toLowerCase()
            ) {
                errors.push(
                    "Text colour and stroke colour must not be the same."
                );
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