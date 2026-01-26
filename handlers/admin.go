package handlers

import (
	"github.com/gofiber/fiber/v2"
	"log"
)

func AdminDashboardHandler(c *fiber.Ctx) error {
	var userCount, fleetCount, simulationCount int64
	DB.Model(&User{}).Count(&userCount)
	DB.Model(&Fleet{}).Count(&fleetCount)
	DB.Model(&Simulation{}).Count(&simulationCount)

	log.Println("Rendering: admin/dashboard")
	return c.Render("admin/dashboard", fiber.Map{
		"Title":           "Admin Dashboard",
		"UserCount":       userCount,
		"FleetCount":      fleetCount,
		"SimulationCount": simulationCount,
	})
}

func AdminUsersHandler(c *fiber.Ctx) error {
	return c.Render("users_content", fiber.Map{
		"Title": "User Management",
	}, "layouts/admin_base")
}

func AdminFleetsHandler(c *fiber.Ctx) error {
	return c.Render("fleets_content", fiber.Map{
		"Title": "Fleet Management",
	}, "layouts/admin_base")
}

func AdminSimulationsHandler(c *fiber.Ctx) error {
	log.Println("Rendering: admin/simulations")
	return c.Render("admin/simulations", fiber.Map{
		"Title": "Simulation Management",
	})
}