package handlers

type Breadcrumb struct {
	Name string
	URL  string
}

type PageData struct {
	Message     string
	Username    string
	ThemeURL    string
	ThemeStyle  string
	Breadcrumbs []Breadcrumb
}
