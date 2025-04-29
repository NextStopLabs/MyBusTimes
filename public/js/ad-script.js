/**
 * @description      : Handles the display and rotation of advertisements on the website
 * @author           : Kai
 * @group            : 
 * @created          : 20/04/2025 - 21:14:58
 * 
 * MODIFICATION LOG
 * - Version         : 1.1.0
 * - Date            : 20/04/2025
 * - Author          : Kai
 * - Modification    : 
**/

document.addEventListener("DOMContentLoaded", function () {

    if (!featureToggles['Enable Ads'].enabled) {
        document.querySelectorAll('.ad-box').forEach(el => {
            el.style.display = 'none';
        });
        return;
    }

    let adImages = [];

    async function fetchAds() {
        try {
            const response = await fetch('/api/ads/');
            adImages = await response.json();
        } catch (err) {
            console.error("Failed to load custom ads:", err);
        }
    }

    function renderGoogleAd(adContainer) {
        adContainer.innerHTML = `
            <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8764676296426896"
                crossorigin="anonymous"></script>
            <ins class="adsbygoogle"
                style="display:block"
                data-ad-client="ca-pub-8764676296426896"
                data-ad-slot="6402055533"
                data-ad-format="auto"
                data-full-width-responsive="true"></ins>
            <script>
                (adsbygoogle = window.adsbygoogle || []).push({});
            </script>
        `;
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
        document.querySelectorAll(".ad-box").forEach(adContainer => {
            const showGoogleAd = featureToggles['Google Ads'].enabled
                ? Math.random() < 0.5
                : false;

            if (showGoogleAd) {
                renderGoogleAd(adContainer);
            } else {
                renderImageAd(adContainer);
            }
        });
    });
});
