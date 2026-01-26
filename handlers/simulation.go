package handlers

import (
	"fmt"
	"time"

	"github.com/gofiber/fiber/v2"
)

func GetSimulations(c *fiber.Ctx) error {
	var simulations []Simulation
	DB.Preload("Fleet").Find(&simulations)
	return c.JSON(simulations)
}

func GetSimulation(c *fiber.Ctx) error {
	id := c.Params("id")
	var simulation Simulation
	if err := DB.Preload("Fleet").First(&simulation, id).Error; err != nil {
		return c.Status(404).JSON(fiber.Map{"error": "Simulation not found"})
	}
	return c.JSON(simulation)
}

func CreateSimulation(c *fiber.Ctx) error {
	simulation := new(Simulation)
	if err := c.BodyParser(simulation); err != nil {
		return c.Status(400).JSON(fiber.Map{"error": "Invalid request"})
	}

	if err := DB.Create(simulation).Error; err != nil {
		return c.Status(500).JSON(fiber.Map{"error": "Failed to create simulation"})
	}

	return c.Status(201).JSON(simulation)
}

func UpdateSimulation(c *fiber.Ctx) error {
	id := c.Params("id")
	var simulation Simulation

	if err := DB.First(&simulation, id).Error; err != nil {
		return c.Status(404).JSON(fiber.Map{"error": "Simulation not found"})
	}

	if err := c.BodyParser(&simulation); err != nil {
		return c.Status(400).JSON(fiber.Map{"error": "Invalid request"})
	}

	DB.Save(&simulation)
	return c.JSON(simulation)
}

func DeleteSimulation(c *fiber.Ctx) error {
	id := c.Params("id")
	var simulation Simulation

	if err := DB.First(&simulation, id).Error; err != nil {
		return c.Status(404).JSON(fiber.Map{"error": "Simulation not found"})
	}

	DB.Delete(&simulation)
	return c.JSON(fiber.Map{"message": "Simulation deleted successfully"})
}

func RunSimulation(c *fiber.Ctx) error {
	id := c.Params("id")
	var simulation Simulation

	if err := DB.Preload("Fleet").First(&simulation, id).Error; err != nil {
		return c.Status(404).JSON(fiber.Map{"error": "Simulation not found"})
	}

	// Update status to running
	simulation.Status = "running"
	DB.Save(&simulation)

	// Run simulation logic (this is a placeholder - implement your actual logic)
	go runSimulationAsync(&simulation)

	return c.JSON(fiber.Map{
		"message": "Simulation started",
		"id":      simulation.ID,
	})
}

func runSimulationAsync(simulation *Simulation) {
	// Simulate some work
	time.Sleep(5 * time.Second)

	// Update results
	simulation.Status = "completed"
	simulation.Results = fmt.Sprintf("Simulation completed for fleet %s with %d vehicles", 
		simulation.Fleet.Name, simulation.Fleet.VehicleCount)
	DB.Save(simulation)
}