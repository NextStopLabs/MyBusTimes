document.addEventListener("DOMContentLoaded", function () {
    if (featureToggles['Enable Ads'].enabled) {
        console.log(featureToggles['Enable Ads'].enabled)
        document.querySelectorAll(".ad-box").forEach(adContainer => {
            // 50% chance to show Google Ad or Custom Ad
            //const showGoogleAd = Math.random() < 0.5;

            //if (showGoogleAd) {
            //    // Google Ad
            //    adContainer.innerHTML = `
            //        <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2623095708353843" crossorigin="anonymous"><\/script>
            //        <ins class="adsbygoogle" style="display:block" data-adtest="on" data-ad-format="autorelaxed"
            //            data-ad-client="ca-pub-2623095708353843" data-ad-slot="8420014093"></ins>
            //        <script>(adsbygoogle = window.adsbygoogle || []).push({});<\/script>
            //    `;
            //} else {
            // Custom Ads with links
            let adImages = []; // Declare the adImages variable outside the function

            async function fetchAds() {
                // Fetch the ad data from the API once and save it
                const response = await fetch('/api/ads/');
                adImages = await response.json();  // Save the response data to adImages
            }

            function rotateAd() {
                if (adImages.length === 0) {
                    console.log("No ads available.");
                    return;
                }

                // Get a random ad
                const randomAd = adImages[Math.floor(Math.random() * adImages.length)];

                // Update the ad container with the ad image and link
                adContainer.innerHTML = `
                    <a href="${randomAd.ad_link}" target="_blank">
                        <img src="${randomAd.ad_img}" alt="Advertisement" style="width:100%;">
                    </a>
                `;
            }

            // Fetch the ad data once before starting the ad rotation
            fetchAds().then(() => {
                // Show first ad
                rotateAd();
                // Rotate every 15 seconds
                setInterval(rotateAd, 15000);
            });
            //}
        });
    } else {
        document.querySelectorAll(".ad-box").forEach(adContainer => {
            adContainer.style.display = 'none';
        });
    }
});
