const tabs = document.querySelectorAll(".livery-creator-tab");
const contents = document.querySelectorAll(".livery-creator-container > div");

tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => {
    // Remove active states
    tabs.forEach((t) => t.classList.remove("active-tab"));
    contents.forEach((c) => c.classList.remove("active-content"));

    const tabText = tab.textContent.trim().toLowerCase();

    if (tabText === "recolour existing livery" || tabText === "import bustimes") {
      document.getElementById("recolour-wrapper").style.display = "block";
    } else {
      document.getElementById("recolour-wrapper").style.display = "none";
    }

    // Add active to clicked tab and its corresponding content
    tab.classList.add("active-tab");
    if (contents[index]) {
      contents[index].classList.add("active-content");
    }
  });
});

contents[0].classList.add("active-content");

const input = document.getElementById("colour");
const textColour = document.getElementById("text-colour");
const textStrokeColour = document.getElementById("text-stroke-colour");
const liveryColour = document.getElementById("livery-colour");
const horizontal = document.getElementById("horizontal");

const leftCell = document.getElementById("left");
const rightCell = document.getElementById("right");
const simpleCell = document.getElementById("simpleCell");

const complexLeft = document.getElementById("livery-css-left");
const complexRight = document.getElementById("livery-css-right");

function updateCells() {
  const textColor = textColour.value.trim();
  const strokeColor = textStrokeColour.value.trim();
  const simpleColour = liveryColour.value.trim();
  const isHorizontal = horizontal.checked;

  const activeTab = document.querySelector(".livery-creator-tab.active-tab");
  const activeMode = activeTab
    ? activeTab.textContent.trim().toLowerCase()
    : "simple";

  if (activeMode.includes("complex") || activeMode.includes("recolour") || activeMode.includes("import")) {
    // COMPLEX MODE - RECOLOUR MODE - IMPORT MODE
    const leftGradient = complexLeft.value.trim();
    const rightGradient = complexRight.value.trim();

    leftCell.style.background = leftGradient || "#111";
    rightCell.style.background = rightGradient || "#111";
  } else {
    // SIMPLE MODE
    const raw = input.value;
    const colors = raw
      .split(",")
      .map((c) => c.trim())
      .filter((c) => /^#([0-9A-Fa-f]{6})$/.test(c));

    if (colors.length > 0) {
      const step = 100 / colors.length;
      const gradient = colors
        .map((color, i) => {
          const start = (i * step).toFixed(2);
          const end = ((i + 1) * step).toFixed(2);
          return `${color} ${start}%, ${color} ${end}%`;
        })
        .join(", ");

      const direction = isHorizontal ? "to bottom" : "to right";
      const directionFlipped = isHorizontal ? "to bottom" : "to left";

      leftCell.style.background = `linear-gradient(${direction}, ${gradient})`;
      rightCell.style.background = `linear-gradient(${directionFlipped}, ${gradient})`;

      complexLeft.value = `linear-gradient(${direction}, ${gradient})`;
      complexRight.value = `linear-gradient(${directionFlipped}, ${gradient})`;
    } else {
      leftCell.style.background = "#111";
      rightCell.style.background = "#111";

      complexLeft.value = `linear-gradient(${direction}, #111)`;
      complexRight.value = `linear-gradient(${directionFlipped}, #111)`;
    }
  }

  [leftCell, rightCell].forEach((cell) => {
    const span = cell.querySelector("span");
    if (textColor) {
      span.style.color = textColor;
    }
    if (strokeColor) {
      if (strokeColor !== "none" && strokeColor !== "") {
        span.style.webkitTextStroke = `1.5px ${strokeColor}`;
        span.style.textStroke = `1.5px ${strokeColor}`;
        span.style.fontWeight = "700";
      } else {
        span.style.webkitTextStroke = `0px transparent`;
        span.style.textStroke = `0px transparent`;
        span.style.fontWeight = "600";
      }
    }
  });

  if (simpleColour) {
    simpleCell.style.background = simpleColour;
  }
}

input.addEventListener("input", updateCells);
textColour.addEventListener("input", updateCells);
textStrokeColour.addEventListener("input", updateCells);
horizontal.addEventListener("change", updateCells);
complexLeft.addEventListener("input", updateCells);
complexRight.addEventListener("input", updateCells);
liveryColour.addEventListener("input", updateCells);

$(document).ready(function () {
  function formatLivery(livery) {
    if (!livery.id) return livery.text;

    // Get the original option element to access custom data attributes
    const $option = $("#livery").find('option[value="' + livery.id + '"]');
    const leftCss = livery.left_css || $option.data("left_css") || "#ccc";
    console.log($option.data("left_css"));

    const $container = $(`
            <div class="livery-cell" style="background: ${leftCss};"></div><span>${livery.text}</span>
        `);
    return $container;
  }
  $("#livery").select2({
    placeholder: "Select a livery",
    allowClear: true,
    width: "100%",
    templateResult: formatLivery,
    templateSelection: formatLivery,
    ajax: {
      url: "/api/liveries/",
      dataType: "json",
      delay: 250,
      data: function (params) {
        return {
          limit: 100,
          offset: params.page ? params.page * 100 : 0,
          name__icontains: params.term || "",
        };
      },
      processResults: function (data, params) {
        params.page = params.page || 0;

        return {
          results: data.results.map(function (livery) {
            return {
              id: livery.id,
              text: livery.name,
              left_css: livery.left_css,
              right_css: livery.right_css,
            };
          }),
          pagination: {
            more: data.next !== null,
          },
        };
      },
      cache: true,
    },
    minimumInputLength: 0,
  });
  $("#bustimes-livery").select2({
    placeholder: "Select a livery",
    allowClear: true,
    width: "100%",
    templateResult: formatLivery,
    templateSelection: formatLivery,
    ajax: {
      url: "https://bustimes.org/api/liveries/",
      dataType: "json",
      delay: 250,
      data: function (params) {
        return {
          limit: 100,
          offset: params.page ? params.page * 100 : 0,
          name__icontains: params.term || "",
        };
      },
      processResults: function (data, params) {
        params.page = params.page || 0;

        return {
          results: data.results.map(function (livery) {
            return {
              id: livery.id,
              text: livery.name,
              left_css: livery.left_css,
              right_css: livery.right_css,
            };
          }),
          pagination: {
            more: data.next !== null,
          },
        };
      },
      cache: true,
    },
    minimumInputLength: 0,
  });

  const recolourContainer = document.querySelector(".livery-creator-recolour");
  const liverySelect = document.getElementById("livery");
  const bustimesSelect = document.getElementById("bustimes-livery");

  function checkValidGradient(gradient) {
    try {
      const testElement = document.createElement("div");
      testElement.style.background = gradient;
      return testElement.style.background !== "";
    } catch (e) {
      return false;
    }
  }

  function extractHexColors(gradient) {
    const hexColorPattern = /#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b/g;

    const expandHex = (hex) => {
      if (hex.length === 4) {
        return `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`;
      }
      return hex;
    };

    const colors = (gradient.match(hexColorPattern) || []).map(expandHex);

    return colors;
  }

  function displayColorPickers(hexCodes, side) {
    if (side === "left") {
      const colorPickersContainer = document.getElementById("colorPickersLeft");
      colorPickersContainer.innerHTML = "<p>Left</p>";

      const colorPickerGroup = document.createElement("div");
      colorPickerGroup.classList.add("color-picker-group");

      hexCodes.forEach((hexColor, index) => {
        const colorPickerWrapper = document.createElement("div");
        colorPickerWrapper.classList.add("color-picker");

        const colorInput = document.createElement("input");
        colorInput.type = "color";
        colorInput.value = hexColor;
        colorInput.addEventListener("input", (event) =>
          updateGradientWithColor(event, index)
        );

        colorPickerWrapper.appendChild(colorInput);
        colorPickerGroup.appendChild(colorPickerWrapper);
      });

      colorPickersContainer.appendChild(colorPickerGroup);
    } else {
      const colorPickersContainer =
        document.getElementById("colorPickersRight");
      colorPickersContainer.innerHTML = "<p>Right</p>";

      const colorPickerGroup = document.createElement("div");
      colorPickerGroup.classList.add("color-picker-group");

      hexCodes.forEach((hexColor, index) => {
        const colorPickerWrapper = document.createElement("div");
        colorPickerWrapper.classList.add("color-picker");

        const colorInput = document.createElement("input");
        colorInput.type = "color";
        colorInput.value = hexColor;
        colorInput.addEventListener("input", (event) =>
          updateGradientWithColor(event, index)
        );

        colorPickerWrapper.appendChild(colorInput);
        colorPickerGroup.appendChild(colorPickerWrapper);
      });

      colorPickersContainer.appendChild(colorPickerGroup);
    }
  }

  function updateGradientWithColor(event, index) {
    const hexInputsLeft = document.querySelectorAll(
      "#colorPickersLeft input[type=color]"
    );
    const updatedColorsLeft = Array.from(hexInputsLeft).map(
      (input) => input.value
    );

    const hexInputsRight = document.querySelectorAll(
      "#colorPickersRight input[type=color]"
    );
    const updatedColorsRight = Array.from(hexInputsRight).map(
      (input) => input.value
    );

    const leftGradientBase = document.getElementById("livery-css-left").value;
    const rightGradientBase = document.getElementById("livery-css-right").value;

    const newGradientLeft = regenerateGradient(
      leftGradientBase,
      updatedColorsLeft
    );
    const newGradientRight = regenerateGradient(
      rightGradientBase,
      updatedColorsRight
    );

    document.getElementById("left").style.background = newGradientLeft;
    document.getElementById("right").style.background = newGradientRight;

    document.getElementById("livery-css-left").value = newGradientLeft;
    document.getElementById("livery-css-right").value = newGradientRight;

    complexLeft.value = newGradientLeft;
    complexRight.value = newGradientRight;

    updateCells();
  }

  function regenerateGradient(gradient, colors) {
    const hexColorPattern = /#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b/g;
    const colorsCopy = [...colors];
    return gradient.replace(hexColorPattern, () => {
      return colorsCopy.length > 0 ? colorsCopy.shift() : "#000000";
    });
  }

  $("#bustimes-livery").on("select2:select", function (e) {
    const selectedOption = bustimesSelect.options[bustimesSelect.selectedIndex];

    const selected = e.params.data;

    const leftCss = selected.left_css || "";
    const rightCss = selected.right_css || "";
    const textColour = selected.text_colour || "";
    const textStrokeColour = selected.stroke_colour || "";
    const liveryName = selected.text || "";
    const liveryColour = selected.livery_colour || "";


    document.getElementById("text-colour").value = textColour;
    document.getElementById("text-stroke-colour").value = textStrokeColour;
    document.getElementById("livery-name").value = liveryName;
    document.getElementById("livery-colour").value = liveryColour;

    const leftHexes = extractHexColors(leftCss);
    const rightHexes = extractHexColors(rightCss);

    const existingInputs = document.querySelectorAll(".color-picker");
    existingInputs.forEach((el) => el.remove());

    const leftInputs = displayColorPickers(leftHexes, "left");
    const rightInputs = displayColorPickers(rightHexes, "right");

    complexLeft.value = leftCss;
    complexRight.value = rightCss;

    updateCells();
  });


  $("#livery").on("select2:select", function (e) {
    const selectedOption = liverySelect.options[liverySelect.selectedIndex];
    const selected = e.params.data;

    const leftCss = selected.left_css || "";
    const rightCss = selected.right_css || "";
    const textColour = selectedOption.getAttribute("data-text-color") || "";
    const textStrokeColour =
      selectedOption.getAttribute("data-text-stroke-color") || "";
    const liveryName = selectedOption.getAttribute("data-livery-name") || "";
    const liveryColour =
      selectedOption.getAttribute("data-livery-colour") || "";

    document.getElementById("text-colour").value = textColour;
    document.getElementById("text-stroke-colour").value = textStrokeColour;
    document.getElementById("livery-name").value = liveryName;
    document.getElementById("livery-colour").value = liveryColour;

    const leftHexes = extractHexColors(leftCss);
    const rightHexes = extractHexColors(rightCss);

    const existingInputs = document.querySelectorAll(".color-picker");
    existingInputs.forEach((el) => el.remove());

    const leftInputs = displayColorPickers(leftHexes, "left");
    const rightInputs = displayColorPickers(rightHexes, "right");

    complexLeft.value = leftCss;
    complexRight.value = rightCss;

    updateCells();
  });

  document
    .getElementById("copy-left-to-right")
    .addEventListener("click", () => {
      const rightGradientBase =
        document.getElementById("livery-css-right").value;

      const leftColorInputs = document.querySelectorAll(
        "#colorPickersLeft input[type=color]"
      );
      const leftColors = Array.from(leftColorInputs).map(
        (input) => input.value
      );

      const newRightGradient = regenerateGradient(rightGradientBase, [
        ...leftColors,
      ]);

      document.getElementById("livery-css-right").value = newRightGradient;
      document.getElementById("right").style.background = newRightGradient;
      complexRight.value = newRightGradient;

      displayColorPickers(leftColors, "right");

      updateCells();
    });
});
