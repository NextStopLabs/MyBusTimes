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

// Wait for the DOM to be fully loaded before executing the ad script
document.addEventListener("DOMContentLoaded", function () {
    // Check if ads are enabled through feature toggles
    if (!featureToggles['Enable Ads'].enabled) {
        // Hide all ad containers if ads are disabled
        document.querySelectorAll(".ad-box").forEach(adContainer => {
            adContainer.style.display = 'none';
        });
        return;
    }

    // Array to store fetched ad images
    let adImages = [];

    /**
     * Fetches custom ads from the server API
     * @async
     */
    async function fetchAds() {
        try {
            const response = await fetch('/api/ads/');
            adImages = await response.json();
        } catch (err) {
            console.error("Failed to load custom ads:", err);
        }
    }

    /**
     * Renders a Google AdSense advertisement in the specified container
     * @param {HTMLElement} adContainer - The container element where the ad will be displayed
     */
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

    /**
     * Renders and rotates custom image advertisements
     * @param {HTMLElement} adContainer - The container element where the ad will be displayed
     */
    function renderImageAd(adContainer) {
        /**
         * Rotates through available ads by randomly selecting one
         */
        function rotateAd() {
            if (adImages.length === 0) {
                // Display a message if no ads are available
                adContainer.innerHTML = `<p style="text-align:center;">No ads available.</p>`;
                return;
            }
            // Select a random ad from the available ads
            const randomAd = adImages[Math.floor(Math.random() * adImages.length)];
            adContainer.innerHTML = `
                <a href="${randomAd.ad_link}" target="_blank">
                    <img src="${randomAd.ad_img}" alt="Advertisement" style="width:100%;">
                </a>
            `;
        }

        // Initial ad display
        rotateAd();
        // Set up rotation interval (every 15 seconds)
        setInterval(rotateAd, 15000);
    }

    // Fetch ads and then render them in all ad containers
    fetchAds().then(() => {
        document.querySelectorAll(".ad-box").forEach(adContainer => {
            // Randomly decide whether to show Google Ad or custom image ad
            // (only if Google Ads feature toggle is enabled)
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
