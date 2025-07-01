document.addEventListener("DOMContentLoaded", function () {
  if (featureToggles["Ads"].enabled) {
    let adImages = [];

    async function fetchAds() {
      try {
        const response = await fetch("/api/ads/?ad_live=true");
        const data = await response.json();
        adImages = data.results;
        console.log(adImages);
      } catch (err) {
        console.error("Failed to load custom ads:", err);
      }
    }

    function renderGoogleAd(adContainer) {
      const adId = adContainer.id;
      const type = adContainer.dataset.type;
      adContainer.classList.add("ad-box-google");
      adContainer.style.position = "relative";
      adContainer.innerHTML = "";

      const loading = document.createElement("div");
      loading.className = "ad-loading-overlay";
      loading.textContent = "Loading...";
      adContainer.appendChild(loading);

      const ins = document.createElement("ins");
      ins.className = "adsbygoogle";
      ins.style.display = "block";
      if (type === "article") {
        ins.style.textAlign = "center";
        ins.setAttribute("data-ad-layout", "in-article");
      }
      ins.setAttribute("data-ad-format", "fluid");
      ins.setAttribute("data-ad-layout-key", "-gh+4m+2n-c9+cd");
      ins.setAttribute("data-ad-client", "ca-pub-8764676296426896");
      ins.setAttribute("data-ad-slot", getSlotById(adId, type));
      adContainer.appendChild(ins);

      (adsbygoogle = window.adsbygoogle || []).push({});

      setTimeout(() => {
        loading.remove();
        adContainer.style.border = "0";
      }, 500);
    }

    function getSlotById(id, type = "default") {
      if (type === "article") {
        const slotMap = {
          "body-ad-1": "6635106786",
          "body-ad-2": "2452319191",
          "body-ad-3": "4063340805",
          "body-ad-4": "1139237525",
        };
        return slotMap[id] || "";
      } else {
        const slotMap = {
          "footer-ad-1": "3642870105",
          "footer-ad-2": "7070995135",
          "body-ad-1": "7070995135",
          "body-ad-2": "1515400214",
          "body-ad-3": "3331044763",
          "body-ad-4": "6959907396",
        };
        return slotMap[id] || "";
      }
    }

    function renderImageAd(adContainer) {
      if (adImages.length === 0) {
        adContainer.innerHTML = `<p style="text-align:center;">No ads available.</p>`;
        return;
      }
      const randomAd = adImages[Math.floor(Math.random() * adImages.length)];
      adContainer.innerHTML = `
        <a href="${randomAd.ad_link}" target="_blank">
          <img src="${randomAd.ad_img}" alt="Advertisement" style="width:100%;">
        </a>
      `;
    }

    function renderAllAds() {
      document.querySelectorAll(".ad-box").forEach((adContainer) => {
        let showGoogleAd = false;
        const currentHour = new Date().getHours();

        if (featureToggles["Google Ads"].enabled && featureToggles["MBT Ads"].enabled) {
          showGoogleAd = currentHour >= 13 && currentHour < 21 ? Math.random() < 0.9 : Math.random() < 0.5;
        } else if (featureToggles["Google Ads"].enabled) {
          showGoogleAd = true;
        } else if (featureToggles["MBT Ads"].enabled) {
          showGoogleAd = false;
        }

        if (showGoogleAd) {
          renderGoogleAd(adContainer);
        } else {
          renderImageAd(adContainer);
        }

        adContainer.style.display = "block";
      });
    }

    fetchAds().then(() => {
      renderAllAds();
      setInterval(renderAllAds, 15000); // Refresh ads every 15 seconds
    });
  }
});
