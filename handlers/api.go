package handlers

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"net/http"
)

var MOD_CDN_URL string = "https://cdn.mybustimes.cc/mybustimes/media/JSON/mod.json?raw=1"
var THEMES_CDN_URL string = "http://localhost:8080/static/json/themes.json"
var maxInt int = 0

type BusTime struct {
	Route string `json:"route"`
	Time  string `json:"time"`
}

type Messages struct {
	Messages []string `json:"messages"`
}

type Theme struct {
	Name         string `json:"name"`
	LightCSSFile string `json:"light_css_file"`
	DarkCSSFile  string `json:"dark_css_file"`
	Active       bool   `json:"active"`
	Selected     bool   `json:"selected,omitempty"`
	Mode         string `json:"mode,omitempty"` // "light" or "dark"
}

type THEMES struct {
	Themes []Theme `json:"themes"`
}

func MessageOfTheDayAPIHandler(w http.ResponseWriter, r *http.Request) {
	resp, err := http.Get(MOD_CDN_URL)
	if err != nil {
		fmt.Println("Error fetching:", err) // Debug print
		return
	}
	defer resp.Body.Close()

	var messages Messages
	json.NewDecoder(resp.Body).Decode(&messages)
	maxInt = len(messages.Messages) - 1

	picked_message := map[string]string{
		"message": messages.Messages[rand.Intn(maxInt)],
	}
	json.NewEncoder(w).Encode(picked_message)
}

func ThemesAPIHandler(w http.ResponseWriter, r *http.Request) {
	resp, err := http.Get(THEMES_CDN_URL)
	if err != nil {
		fmt.Println("Error fetching:", err) // Debug print
		return
	}
	defer resp.Body.Close()

	var themes THEMES
	if err := json.NewDecoder(resp.Body).Decode(&themes); err != nil {
		http.Error(w, "failed to decode themes", http.StatusInternalServerError)
		return
	}

	// By default only return active themes. If ?show_all=true is present, include all themes.
	showAll := false
	if v := r.URL.Query().Get("show_all"); v == "true" || v == "1" {
		showAll = true
	}

	var out THEMES
	if showAll {
		out = themes
	} else {
		out = THEMES{Themes: []Theme{}}
		for _, t := range themes.Themes {
			if t.Active {
				out.Themes = append(out.Themes, t)
			}
		}
	}

	// Mark which theme is currently selected for this user (from profile or cookie)
	userTheme := GetThemeURL(r)
	if userTheme != "" {
		for i := range out.Themes {
			if out.Themes[i].DarkCSSFile == userTheme {
				out.Themes[i].Selected = true
				out.Themes[i].Mode = "dark"
			} else if out.Themes[i].LightCSSFile == userTheme {
				out.Themes[i].Selected = true
				out.Themes[i].Mode = "light"
			}
		}
	}

	json.NewEncoder(w).Encode(out)
}
