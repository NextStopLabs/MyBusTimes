/**
 * @description      : Theme loader and user interface management script
 * @author           : Kai
 * @group            :
 * @created          : 20/04/2025 - 21:24:49
 *
 * MODIFICATION LOG
 * - Version         : 1.0.0
 * - Date            : 20/04/2025
 * - Author          : Kai
 * - Modification    :
 **/

// Main initialization when DOM content is loaded
document.addEventListener("DOMContentLoaded", () => {
  // Get username from cookies
  let username = document.cookie
    .split("; ")
    .find((row) => row.startsWith("username="))
    ?.split("=")[1];

  // Update navigation menu based on login status
  if (username) {
    // User is logged in - show profile and logout options
    document.getElementById("login-profile").textContent = "My Profile";
    document.getElementById("login-profile").href = "/u/" + username;
    document.getElementById("logout-profile").textContent = "Logout";
    document.getElementById("logout-profile").href = "/account/logout";
  } else {
    // User is not logged in - show login option
    document.getElementById("login-profile").textContent = "Login";
    document.getElementById("login-profile").href = "/account/login";
    document.getElementById("logout-profile").display = "none";
  }

  // Get theme preferences from cookies
  let themeCSS = document.cookie
    .split("; ")
    .find((row) => row.startsWith("theme="))
    ?.split("=")[1];
  let themeID = document.cookie
    .split("; ")
    .find((row) => row.startsWith("themeID="))
    ?.split("=")[1];
  let themeDark = document.cookie
    .split("; ")
    .find((row) => row.startsWith("themeDark="))
    ?.split("=")[1];

  // Set default theme if none is selected
  if (!themeID) {
    themeCSS = "Light.css";
    themeID = 1;
    themeDark = "false";
  }

  // Apply the selected theme
  applyTheme(themeID);

  // Function to apply theme-specific UI changes
  function applyTheme(themeID) {
    const currentMonth = new Date().getMonth();
    const isPrideMonth = currentMonth === 5; // June is month 6 (0-based index)

    if (themeDark === "false") {
      // Light theme - use black icons
      document.getElementById("logo").src = "/src/icons/MBT-Logo-Black.png";
      document.getElementById("menu").src = "/src/icons/Burger-Menu-Black.png";
    } else {
      // Dark theme - use white icons
      document.getElementById("logo").src = "/src/icons/MBT-Logo-White.png";
      document.getElementById("menu").src = "/src/icons/Burger-Menu-White.png";
    }

    if (isPrideMonth) {
      // Pride month logo
      document.getElementById("logo").src = "https://github.com/Kai-codin/MBT-Media-Kit/blob/main/MBT%20Logos/MBT-Logo-Pride-MMH-outline.png?raw=true";
    }
  }

  // Fetch available themes from the API
  fetch("/api/themes/")
    .then((response) => response.json())
    .then((data) => {
      const themeSelect = document.getElementById("theme-selector");

      data.results
        .sort((a, b) => a.weight - b.weight)
        .forEach((theme) => {
          const option = document.createElement("option");
          option.value = theme.id;
          option.textContent = theme.theme_name;
          themeSelect.appendChild(option);
        });

      // Set current theme as selected
      themeSelect.value = themeID;
    })
    .catch((error) => {
      console.error("Error fetching themes:", error);
    });

  // Helper function to get cookie value by name
  function getCookie(name) {
    let matches = document.cookie.match(
      new RegExp(
        "(?:^|; )" +
          name.replace(/([\.$?*|{}\(\)\[\]\\\/\+\-])/g, "\\$1") +
          "=([^;]*)"
      )
    );
    return matches ? decodeURIComponent(matches[1]) : undefined;
  }

  // Function to refresh access token when expired
  function refreshAccessToken() {
    const refreshToken = getCookie("refresh_token");

    if (!refreshToken) {
      window.location.reload();
      return;
    }

    fetch("/api/users/refresh/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        refresh: refreshToken,
      }),
      credentials: "same-origin",
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.access) {
          // Update cookies with new tokens
          document.cookie = `access_token=${data.access}; path=/; secure; sameSite=Strict`;
          document.cookie = `refresh_token=${data.refresh}; path=/; secure; sameSite=Strict`;
          sendPostRequest();
        } else {
          console.error("Failed to refresh token:", data);
        }
      })
      .catch((error) => console.error("Error refreshing token:", error));
  }

  // Function to send theme update request to server
  function sendPostRequest() {
    const selectedThemeID = document.getElementById("theme-selector").value;
    const accessToken = getCookie("access_token");

    if (!accessToken) {
      refreshAccessToken();
      return;
    }

    fetch("/api/users/profile/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        theme_id: selectedThemeID,
      }),
    })
      .then((response) => {
        if (response.status === 401) {
          refreshAccessToken();
        } else {
          return response.json();
        }
      })
      .then((data) => {
        window.location.reload();
      })
      .catch((error) => console.error("Error:", error));
  }

  // Event listener for theme selection changes
  document
    .getElementById("theme-selector")
    .addEventListener("change", function (event) {
      const selectedThemeID = event.target.value;

      // Fetch theme details and update cookies
      fetch(`/api/themes/${selectedThemeID}`, {
        method: "GET",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      })
        .then((response) => response.json())
        .then((data) => {
          // Update theme-related cookies
          document.cookie = `theme=${data.css}; path=/;`;
          document.cookie = `themeDark=${data.dark_theme}; path=/;`;
          document.cookie = `themeID=${data.id}; path=/;`;
          document.cookie = `brand-color=${data.main_colour}; path=/;`;
          document.getElementById("theme-selector").value = selectedThemeID;
          sendPostRequest();
        })
        .catch((error) => {
          console.error("Error fetching themes:", error);
        });
    });
});

// Second DOMContentLoaded event for menu and user stats
document.addEventListener("DOMContentLoaded", () => {
  // Initialize menu toggle functionality
  const menuButton = document.getElementById("menu-toggle");
  const navMenu = document.getElementById("nav-menu");
  let username = document.cookie
    .split("; ")
    .find((row) => row.startsWith("username="))
    ?.split("=")[1];

  // Toggle menu visibility on button click
  menuButton.addEventListener("click", () => {
    navMenu.classList.toggle("active");
  });

  // Initial fetch and periodic updates of user stats
  fetchUserStats();
  setInterval(fetchUserStats, 30000);

  const timeout = new Promise(
    (_, reject) =>
      setTimeout(() => reject(new Error("Request timed out")), 2000) // 1-second timeout
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

      const dismissed = getCookie("banner-dismissed");
      const latestUpdateID = getCookie("latest-update-id");

      // Check if the banner has been dismissed and the latest update is not the same as the last one shown
      if (
        dismissed === "true" &&
        String(data[0].id) !== String(latestUpdateID)
      ) {
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

        window.location.href = "/service-updates";
      });
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

  // Update user's last active timestamp
  fetch("/api/reset-last-active/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username: `${username}` }),
  })
    .then((response) => response.json())
    .catch((error) => console.error("Error:", error));

  // Function to fetch and display user statistics
  function fetchUserStats() {
    fetch("/api/user-stats/")
      .then((response) => response.json())
      .then((data) => {
        const statsElement = document.getElementById("users-stats");
        statsElement.textContent = `Online: ${data.online} | Total: ${data.total}`;
      })
      .catch((error) => {
        console.error("Error fetching user stats:", error);
      });
  }
});
