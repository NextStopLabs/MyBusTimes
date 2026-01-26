package handlers

import (
	"encoding/json"
	"fmt"
	"html/template"
	"mybustimes/air/database"
	"mybustimes/air/models"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/gorilla/securecookie"
	"github.com/gorilla/sessions"
	"golang.org/x/crypto/bcrypt"
)

var Store *sessions.CookieStore
var sessionName = "mbt-session"

func init() {
	// Generate keys for cookie store; if you want persistent keys, replace these with config values.
	authKey := securecookie.GenerateRandomKey(32)
	encKey := securecookie.GenerateRandomKey(32)
	Store = sessions.NewCookieStore(authKey, encKey)
	Store.Options = &sessions.Options{
		Path:     "/",
		HttpOnly: true,
		MaxAge:   60 * 60 * 24 * 7, // 7 days
	}
}

// RegisterHandler handles GET (form) and POST (create user)
func (h *Handlers) RegisterHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		data := PageData{Breadcrumbs: []Breadcrumb{{Name: "Home", URL: "/"}, {Name: "Register", URL: "/account/register"}}}
		files := append(baseTemplates, "templates/account/register.html")
		tmpl := template.Must(template.ParseFiles(files...))
		if username := GetUsername(r); username != "" {
			data.Username = username
		}
		if err := tmpl.ExecuteTemplate(w, "base.html", data); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
		}
		return
	case http.MethodPost:
		if err := r.ParseForm(); err != nil {
			http.Error(w, "Invalid form", http.StatusBadRequest)
			return
		}
		email := r.FormValue("email")
		username := r.FormValue("username")
		password := r.FormValue("password")
		if email == "" || username == "" || password == "" {
			http.Error(w, "Missing fields", http.StatusBadRequest)
			return
		}

		// Hash password
		hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
		if err != nil {
			http.Error(w, "Server error", http.StatusInternalServerError)
			return
		}

		user := models.User{Username: username, Email: email, Password: string(hash)}
		if err := database.DB.Create(&user).Error; err != nil {
			http.Error(w, fmt.Sprintf("Failed to create user: %v", err), http.StatusInternalServerError)
			return
		}

		// Set session
		session, _ := Store.Get(r, sessionName)
		session.Values["user_id"] = user.ID
		session.Values["username"] = user.Username
		session.Save(r, w)

		http.Redirect(w, r, "/", http.StatusSeeOther)
		return
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

// LoginHandler handles login form and authentication
func (h *Handlers) LoginHandler(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		data := PageData{Breadcrumbs: []Breadcrumb{{Name: "Home", URL: "/"}, {Name: "Login", URL: "/account/login"}}}
		files := append(baseTemplates, "templates/account/login.html")
		tmpl := template.Must(template.ParseFiles(files...))
		if username := GetUsername(r); username != "" {
			data.Username = username
		}
		if err := tmpl.ExecuteTemplate(w, "base.html", data); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
		}
		return
	case http.MethodPost:
		if err := r.ParseForm(); err != nil {
			http.Error(w, "Invalid form", http.StatusBadRequest)
			return
		}
		email := r.FormValue("email")
		password := r.FormValue("password")
		if email == "" || password == "" {
			http.Error(w, "Missing fields", http.StatusBadRequest)
			return
		}

		var user models.User
		if err := database.DB.Where("email = ?", email).First(&user).Error; err != nil {
			http.Error(w, "Invalid credentials", http.StatusUnauthorized)
			return
		}

		if err := bcrypt.CompareHashAndPassword([]byte(user.Password), []byte(password)); err != nil {
			http.Error(w, "Invalid credentials", http.StatusUnauthorized)
			return
		}

		// Update last login info if available
		database.DB.Model(&models.UserActivity{}).Where("user_id = ?", user.ID).Updates(models.UserActivity{LastLogin: time.Now()})

		session, _ := Store.Get(r, sessionName)
		session.Values["user_id"] = user.ID
		session.Values["username"] = user.Username
		session.Save(r, w)

		http.Redirect(w, r, "/", http.StatusSeeOther)
		return
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
	}
}

// LogoutHandler clears the session
func (h *Handlers) LogoutHandler(w http.ResponseWriter, r *http.Request) {
	session, _ := Store.Get(r, sessionName)
	session.Options.MaxAge = -1
	session.Save(r, w)
	http.Redirect(w, r, "/", http.StatusSeeOther)
}

// GetUsername returns username from session or empty string
func GetUsername(r *http.Request) string {
	if Store == nil {
		return ""
	}
	session, err := Store.Get(r, sessionName)
	if err != nil {
		return ""
	}
	if v, ok := session.Values["username"].(string); ok {
		return v
	}
	return ""
}

// getSessionUserID safely extracts a numeric user id from session values and
// normalizes it to uint. Returns (0,false) when not present or invalid.
func getSessionUserID(r *http.Request) (uint, bool) {
	if Store == nil {
		return 0, false
	}
	session, err := Store.Get(r, sessionName)
	if err != nil {
		return 0, false
	}
	v, ok := session.Values["user_id"]
	if !ok {
		return 0, false
	}
	switch id := v.(type) {
	case uint:
		return id, true
	case uint64:
		return uint(id), true
	case int:
		return uint(id), true
	case int64:
		return uint(id), true
	case float64:
		return uint(id), true
	case string:
		if id == "" {
			return 0, false
		}
		if u64, err := strconv.ParseUint(id, 10, 64); err == nil {
			return uint(u64), true
		}
	default:
		s := fmt.Sprintf("%v", v)
		if s == "" {
			return 0, false
		}
		if u64, err := strconv.ParseUint(s, 10, 64); err == nil {
			return uint(u64), true
		}
	}
	return 0, false
}

// GetThemeURL checks session for a logged-in user's saved theme, otherwise checks cookie, otherwise returns empty string
func GetThemeURL(r *http.Request) string {
	// If logged in, try to load from profile
	if Store != nil {
		if uid, ok := getSessionUserID(r); ok && uid != 0 {
			var profile models.UserProfile
			if err := database.DB.Where("user_id = ?", uid).First(&profile).Error; err == nil {
				if profile.StylePrefs != nil {
					// prefer explicit theme_url
					if v, ok := profile.StylePrefs["theme_url"].(string); ok && v != "" {
						return v
					}
					// fallback: if profile stores theme name + dark_mode, resolve to CSS
					if themeName, ok := profile.StylePrefs["theme"].(string); ok && themeName != "" {
						darkMode := false
						if dm, ok := profile.StylePrefs["dark_mode"].(bool); ok {
							darkMode = dm
						} else if dmStr, ok := profile.StylePrefs["dark_mode"].(string); ok {
							// attempt to parse string
							if dmStr == "true" {
								darkMode = true
							}
						}
						// fetch available themes and map
						type themeResp struct {
							Themes []struct {
								Name  string `json:"name"`
								Light string `json:"light_css_file"`
								Dark  string `json:"dark_css_file"`
							} `json:"themes"`
						}
						resp, err := http.Get(THEMES_CDN_URL)
						if err == nil {
							defer resp.Body.Close()
							var tr themeResp
							if err := json.NewDecoder(resp.Body).Decode(&tr); err == nil {
								for _, t := range tr.Themes {
									if t.Name == themeName {
										if darkMode {
											return t.Dark
										}
										return t.Light
									}
								}
							}
						}
					}
				}
			}
		}
	}

	// Check cookie for logged-out users or fallback
	if c, err := r.Cookie("mbt_theme"); err == nil {
		// cookie might be URL-encoded; decode
		if decoded, err := url.QueryUnescape(c.Value); err == nil {
			v := decoded
			// strip accidental leading slash before scheme ("/https://...")
			if strings.HasPrefix(v, "/http") {
				v = strings.TrimPrefix(v, "/")
			}
			return v
		}
		// fallback to raw value
		v := c.Value
		if strings.HasPrefix(v, "/http") {
			v = strings.TrimPrefix(v, "/")
		}
		return v
	}

	return ""
}

// SaveThemeHandler saves the selected theme for logged-in users; returns 401 if not logged in
func (h *Handlers) SaveThemeHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	uid, ok := getSessionUserID(r)
	if !ok || uid == 0 {
		http.Error(w, "unauthorized", http.StatusUnauthorized)
		return
	}

	var payload struct {
		ThemeURL string `json:"theme_url"`
		Theme    string `json:"theme"`
		Mode     string `json:"mode"`
		DarkMode *bool  `json:"dark_mode"`
	}

	if r.Header.Get("Content-Type") == "application/json" {
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			http.Error(w, "bad request", http.StatusBadRequest)
			return
		}
	} else {
		if err := r.ParseForm(); err != nil {
			http.Error(w, "bad request", http.StatusBadRequest)
			return
		}
		payload.ThemeURL = r.FormValue("theme_url")
		payload.Theme = r.FormValue("theme")
		payload.Mode = r.FormValue("mode")
		if v := r.FormValue("dark_mode"); v != "" {
			if v == "true" || v == "1" {
				b := true
				payload.DarkMode = &b
			} else {
				b := false
				payload.DarkMode = &b
			}
		}
	}

	if payload.ThemeURL == "" && payload.Theme == "" {
		http.Error(w, "missing theme info", http.StatusBadRequest)
		return
	}

	// determine theme name and dark_mode when only URL provided
	themeName := payload.Theme
	darkMode := false
	if payload.DarkMode != nil {
		darkMode = *payload.DarkMode
	} else if payload.Mode != "" {
		darkMode = (payload.Mode == "dark")
	}

	if themeName == "" && payload.ThemeURL != "" {
		// map url to theme name and mode by fetching remote list
		type themeResp struct {
			Themes []struct {
				Name  string `json:"name"`
				Light string `json:"light_css_file"`
				Dark  string `json:"dark_css_file"`
			} `json:"themes"`
		}
		resp, err := http.Get(THEMES_CDN_URL)
		if err == nil {
			defer resp.Body.Close()
			var tr themeResp
			if err := json.NewDecoder(resp.Body).Decode(&tr); err == nil {
				for _, t := range tr.Themes {
					if t.Light == payload.ThemeURL {
						themeName = t.Name
						darkMode = false
						break
					} else if t.Dark == payload.ThemeURL {
						themeName = t.Name
						darkMode = true
						break
					}
				}
			}
		}
	}

	var profile models.UserProfile
	if err := database.DB.Where("user_id = ?", uid).First(&profile).Error; err != nil {
		// create
		profile = models.UserProfile{UserID: uid, StylePrefs: map[string]interface{}{}}
	}
	if profile.StylePrefs == nil {
		profile.StylePrefs = map[string]interface{}{}
	}
	if payload.ThemeURL != "" {
		profile.StylePrefs["theme_url"] = payload.ThemeURL
	}
	if themeName != "" {
		profile.StylePrefs["theme"] = themeName
	}
	profile.StylePrefs["dark_mode"] = darkMode

	if profile.ID == 0 {
		if err := database.DB.Create(&profile).Error; err != nil {
			http.Error(w, "failed to save", http.StatusInternalServerError)
			return
		}
	} else {
		if err := database.DB.Save(&profile).Error; err != nil {
			http.Error(w, "failed to save", http.StatusInternalServerError)
			return
		}
	}

	w.WriteHeader(http.StatusNoContent)
}
