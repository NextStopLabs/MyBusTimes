package handlers

import (
	"github.com/gofiber/fiber/v2"
)

func SetupRoutes(app *fiber.App) {
	// Public routes
	app.Get("/", HomeHandler)
	app.Get("/api/health", HealthHandler)

	// Admin routes
	admin := app.Group("/admin")
	admin.Get("/", AdminDashboardHandler)
	admin.Get("/users", AdminUsersHandler)
	admin.Get("/fleets", AdminFleetsHandler)
	admin.Get("/simulations", AdminSimulationsHandler)

	// API routes - Users
	api := app.Group("/api")

	users := api.Group("/users")
	users.Get("/", GetUsers)
	users.Get("/:id", GetUser)
	users.Post("/", CreateUser)
	users.Put("/:id", UpdateUser)
	users.Delete("/:id", DeleteUser)

	// API routes - Fleets
	fleets := api.Group("/fleets")
	fleets.Get("/", GetFleets)
	fleets.Get("/:id", GetFleet)
	fleets.Post("/", CreateFleet)
	fleets.Put("/:id", UpdateFleet)
	fleets.Delete("/:id", DeleteFleet)

	// API routes - Simulations
	simulations := api.Group("/simulations")
	simulations.Get("/", GetSimulations)
	simulations.Get("/:id", GetSimulation)
	simulations.Post("/", CreateSimulation)
	simulations.Put("/:id", UpdateSimulation)
	simulations.Delete("/:id", DeleteSimulation)
	simulations.Post("/:id/run", RunSimulation)
}

func HomeHandler(c *fiber.Ctx) error {
	return c.Render("home/home", fiber.Map{
		"Title":   "Welcome to My App",
		"Message": "Your fast, scalable Go app is running!",
	})
}

func HealthHandler(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"status":  "ok",
		"message": "Server is running",
	})
}