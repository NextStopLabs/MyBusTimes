/**
    * @description      : 
    * @author           : Kai
    * @group            : 
    * @created          : 29/04/2025 - 14:56:27
    * 
    * MODIFICATION LOG
    * - Version         : 1.0.0
    * - Date            : 29/04/2025
    * - Author          : Kai
    * - Modification    : 
**/
googleAdsArray = {
  'footer-ad': '<ins class="adsbygoogle"style="display:block" data-ad-client="ca-pub-8764676296426896" data-ad-slot="6402055533" data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({});</script>',
  'body-ad-1': '<ins class="adsbygoogle"style="display:block" data-ad-client="ca-pub-8764676296426896" data-ad-slot="8113638160" data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({});</script>',
  'body-ad-2': '<ins class="adsbygoogle"style="display:block" data-ad-client="ca-pub-8764676296426896" data-ad-slot="6469158662" data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({});</script>',
  'body-ad-3': '<ins class="adsbygoogle"style="display:block" data-ad-client="ca-pub-8764676296426896" data-ad-slot="3555446058" data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({});</script>',
};

document.addEventListener("DOMContentLoaded", function () {
  if (featureToggles["Enable Ads"].enabled) {
    let adImages = [];

    async function fetchAds() {
      try {
        const response = await fetch("/api/ads/");
        adImages = await response.json();
      } catch (err) {
        console.error("Failed to load custom ads:", err);
      }
    }

    function renderGoogleAd(adContainer) {
      const adId = adContainer.id; // Get the ID of the ad container
      adContainer.style.aspectRatio = "7 / 1"; // Corrected property name
      adContainer.innerHTML = `${googleAdsArray[adId]} <p style="text-align:center; margin:5.75% 0;">Loading...</p>` || `<p style="text-align:center;">Ad not found.</p>`;
    }

    function renderImageAd(adContainer) {
      function rotateAd() {
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

      rotateAd();
      setInterval(rotateAd, 15000);
    }
    fetchAds().then(() => {
      document.querySelectorAll(".ad-box").forEach((adContainer) => {
        let showGoogleAd = false;

        if (featureToggles["Google Ads"].enabled && featureToggles["MBT Ads"].enabled) {
          showGoogleAd = Math.random() < 0.5;
        } else if (featureToggles["Google Ads"].enabled && !featureToggles["MBT Ads"].enabled) {
          showGoogleAd = true;
        } else if (!featureToggles["Google Ads"].enabled && featureToggles["MBT Ads"].enabled) {
          showGoogleAd = false;
        }

        if (showGoogleAd) {
          renderGoogleAd(adContainer);
        } else {
          renderImageAd(adContainer);
        }

        document.querySelectorAll('.ad-box').forEach(el => {
            el.style.display = 'block';
        });
      });
    });
  }
});
