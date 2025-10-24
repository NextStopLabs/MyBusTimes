const timeout = new Promise(
  (_, reject) => setTimeout(() => reject(new Error("Request timed out")), 2000) // 1-second timeout
);

let fetchData = fetch("/api/service-updates/?live=true");

const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
};

const setCookie = (name, value, days) => {
  const expires = new Date();
  expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
  document.cookie = `${name}=${value}; expires=${expires.toUTCString()}; path=/`;
};

Promise.race([fetchData, timeout])
  .then((response) => response.json())
  .then((data) => data.results)
  .then((data) => {
    const latestUpdate = data[0];
    const banner = document.getElementById("service-updates-banner");
    const buttom = document.getElementById("dismiss-btn");
    const bannerText = document.getElementById("banner-text");
    const main = document.querySelector("main");
    const warning = data[0].warning;

    const dismissed = getCookie("banner-dismissed");
    const latestUpdateID = getCookie("latest-update-id");

    // Check if the banner has been dismissed and the latest update is not the same as the last one shown
    if (dismissed === "true" && String(data[0].id) !== String(latestUpdateID) && warning !== true) {
      banner.style.display = "none";
      main.style.margin = "55px auto";
    }

    if (Array.isArray(data) && data.length > 0) {
      let additionalUpdates = 0;

      // Check how many updates are between the latest update and the stored latest update ID
      if (latestUpdateID) {
        const filteredData = data.filter((item) => item.id >= latestUpdateID);
        additionalUpdates = filteredData.length - 2;
      }

      // If the update is different from the last one, display the banner
      if (String(latestUpdate.id) !== String(latestUpdateID)) {
        if (additionalUpdates > 0) {
          bannerText.textContent = `Update: ${latestUpdate.title} + ${additionalUpdates} more`;
        } else {
          bannerText.textContent = `Update: ${latestUpdate.title}`;
        }
        banner.style.display = "block";
        buttom.style.display = "block";
        main.style.margin = "6em auto";
      }
    } else {
      banner.textContent = "";
      banner.style.display = "none";
      buttom.style.display = "none";
      main.style.margin = "55px auto";
    }

    // Dismiss button functionality
    const dismissBtn = document.getElementById("dismiss-btn");
    dismissBtn.addEventListener("click", () => {
      setCookie("banner-dismissed", "true", 7); // expire in 7 days
      setCookie("latest-update-id", latestUpdate.id, 7); // expires in 7 days
      banner.style.display = "none";
      buttom.style.display = "none";
      main.style.margin = "55px auto";
    });

    banner.addEventListener("click", () => {
      setCookie("banner-dismissed", "true", 7); // expire in 7 days
      setCookie("latest-update-id", latestUpdate.id, 7); // expires in 7 days
      banner.style.display = "none";
      buttom.style.display = "none";
      main.style.margin = "55px auto";

      window.location.href = "/site-updates";
    });

    if (warning === true) {
      banner.style.display = "block";
      bannerText.style.display = "block";
      bannerText.textContent = `Important: ${latestUpdate.title}`;
      banner.style.backgroundColor = "rgba(205, 42, 42, 1)";
      banner.style.color = "#fff";
      buttom.style.display = "none";
    }
  })
  .catch((error) => {
    console.error("Error fetching service updates:", error);
    const banner = document.getElementById("service-updates-banner");
    const main = document.querySelector("main");
    const buttom = document.getElementById("dismiss-btn");

    banner.textContent = "";
    banner.style.display = "none";
    buttom.style.display = "none";
    main.style.margin = "55px auto";
  });
setTimeout(function () {
  const el = document.querySelector(".messages");
  if (el) {
    el.classList.add("fade-out");
    setTimeout(() => {
      el.style.display = "none";
    }, 1000); // match the fade duration
  }
}, 2000);
