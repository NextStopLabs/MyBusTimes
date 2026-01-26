package handlers

import (
	"html/template"
	"net/http"
)

type Handlers struct {
	Tmpl *template.Template
}

var baseTemplates = []string{
	"templates/layouts/base.html",
	"templates/partials/breadcrumb.html",
}

func (h *Handlers) HomeHandler(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		w.WriteHeader(http.StatusNotFound)
		data := PageData{
			Message: "The page you are looking for does not exist.",
			Breadcrumbs: []Breadcrumb{
				{Name: "Home", URL: "/"},
			},
		}

		// Combine base templates with 404 page template
		files := append(baseTemplates, "templates/errors/404.html")
		tmpl := template.Must(template.ParseFiles(files...))

		err := tmpl.ExecuteTemplate(w, "base.html", data)
		if err != nil {
			http.Error(w, err.Error(), 500)
		}
		return
	}
	data := PageData{
		Breadcrumbs: []Breadcrumb{
			{Name: "Home", URL: "/"},
		},
	}
	// attach username and theme if session/cookie exists
	if username := GetUsername(r); username != "" {
		data.Username = username
	}
	if theme := GetThemeURL(r); theme != "" {
		data.ThemeURL = theme
	}

	// Combine base templates with page template
	files := append(baseTemplates, "templates/home/index.html")
	tmpl := template.Must(template.ParseFiles(files...))

	err := tmpl.ExecuteTemplate(w, "base.html", data)
	if err != nil {
		http.Error(w, err.Error(), 500)
	}
}

func (h *Handlers) AboutHandler(w http.ResponseWriter, r *http.Request) {
	data := PageData{
		Breadcrumbs: []Breadcrumb{
			{Name: "Home", URL: "/"},
			{Name: "About", URL: "/about"},
		},
	}
	if username := GetUsername(r); username != "" {
		data.Username = username
	}
	if theme := GetThemeURL(r); theme != "" {
		data.ThemeURL = theme
	}

	// Combine base templates with page template
	files := append(baseTemplates, "templates/home/about.html")
	tmpl := template.Must(template.ParseFiles(files...))

	err := tmpl.ExecuteTemplate(w, "base.html", data)
	if err != nil {
		http.Error(w, err.Error(), 500)
	}
}
