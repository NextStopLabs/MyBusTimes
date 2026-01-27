package main

import (
	"fmt"
	"html/template"
	"mybustimes/air/database"
	"mybustimes/air/handlers"
	"net/http"
)

var port = "8080"

func main() {
	fs := http.FileServer(http.Dir("./static"))
	http.Handle("/static/", http.StripPrefix("/static/", fs))
	tmpl := template.Must(template.ParseGlob("templates/**/*.html"))

	h := &handlers.Handlers{Tmpl: tmpl}

	err := database.Connect()
	if err != nil {
		panic("Failed to connect to database: " + err.Error())
	}

	http.HandleFunc("/", h.HomeHandler)
	http.HandleFunc("/about", h.AboutHandler)

	// API Endpoints
	http.HandleFunc("/api/motd", handlers.MessageOfTheDayAPIHandler)
	http.HandleFunc("/api/themes", handlers.ThemesAPIHandler)
	http.HandleFunc("/api/regions", handlers.RegionsAPIHandler)

	// Account routes
	http.HandleFunc("/account/register", h.RegisterHandler)
	http.HandleFunc("/account/login", h.LoginHandler)
	http.HandleFunc("/account/logout", h.LogoutHandler)
	http.HandleFunc("/account/theme", h.SaveThemeHandler)

	fmt.Printf("Server is running, http://localhost:%s\n", port)
	http.ListenAndServe(":"+port, nil)
}
