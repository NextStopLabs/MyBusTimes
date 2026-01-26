// main.go
package main

import (
	"log"
	"mybustimes/handlers"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/gofiber/template/html/v2"
)

func main() {
	// Initialize database
	handlers.InitDatabase()

	// Initialize template engine with reload enabled
	engine := html.New("./templates", ".html")
	engine.Reload(true)  // Force reload templates on every request
	engine.Debug(true)   // Enable debug mode

	// Create Fiber app
	app := fiber.New(fiber.Config{
		Views: engine,
	})

	// Middleware
	app.Use(logger.New())
	app.Use(recover.New())

	// Static files
	app.Static("/static", "./static")

	// Setup routes
	handlers.SetupRoutes(app)

	// Start server
	log.Println("Server starting on http://localhost:8080")
	log.Fatal(app.Listen(":8080"))
}