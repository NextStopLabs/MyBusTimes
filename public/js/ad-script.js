document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".ad-box").forEach(adContainer => {
        // 50% chance to show Google Ad or Custom Ad
        const showGoogleAd = Math.random() < 0.5;

        if (showGoogleAd) {
            // Google Ad
            adContainer.innerHTML = `
                <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2623095708353843" crossorigin="anonymous"><\/script>
                <ins class="adsbygoogle" style="display:block" data-adtest="on" data-ad-format="autorelaxed"
                    data-ad-client="ca-pub-2623095708353843" data-ad-slot="8420014093"></ins>
                <script>(adsbygoogle = window.adsbygoogle || []).push({});<\/script>
            `;
        } else {
            // Custom Ads with links
            const adImages = [
                { img: "ad1.png", link: "https://nova-spectra-games.itch.io/polly-bus" },
                { img: "ad2.png", link: "https://discord.gg/mybustimes" },
                { img: "ad3.png", link: "https://apply.mybustimes.cc" },
                { img: "ad9.png", link: "https://timesbus.org" },
                { img: "MBT-Banner.png", link: "https://turbonode.co/a/MyBusTimes" },
                { img: "SB.gif", link: "https://discord.gg/Ab9gddncxa" },
                { img: "SC.png", link: "https://www.roblox.com/games/127796616633703/Central-Scotland-Section-2" }
            ]; 

            function rotateAd() {
                const randomAd = adImages[Math.floor(Math.random() * adImages.length)];
                adContainer.innerHTML = `
                    <a href="${randomAd.link}" target="_blank">
                        <img src="/ads/${randomAd.img}" alt="Advertisement" style="width:100%;">
                    </a>
                `;
            }

            // Show first ad
            rotateAd();
            // Rotate every 15 seconds
            setInterval(rotateAd, 15000);
        }
    });
});
