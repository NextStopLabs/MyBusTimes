package handlers

import (
	"github.com/gofiber/fiber/v2"
)

func GetFleets(c *fiber.Ctx) error {
	var fleets []Fleet
	DB.Find(&fleets)
	return c.JSON(fleets)
}

func GetFleet(c *fiber.Ctx) error {
	id := c.Params("id")
	var fleet Fleet
	if err := DB.First(&fleet, id).Error; err != nil {
		return c.Status(404).JSON(fiber.Map{"error": "Fleet not found"})
	}
	return c.JSON(fleet)
}

func CreateFleet(c *fiber.Ctx) error {
	fleet := new(Fleet)
	if err := c.BodyParser(fleet); err != nil {
		return c.Status(400).JSON(fiber.Map{"error": "Invalid request"})
	}

	if err := DB.Create(fleet).Error; err != nil {
		return c.Status(500).JSON(fiber.Map{"error": "Failed to create fleet"})
	}

	return c.Status(201).JSON(fleet)
}

func UpdateFleet(c *fiber.Ctx) error {
	id := c.Params("id")
	var fleet Fleet

	if err := DB.First(&fleet, id).Error; err != nil {
		return c.Status(404).JSON(fiber.Map{"error": "Fleet not found"})
	}

	if err := c.BodyParser(&fleet); err != nil {
		return c.Status(400).JSON(fiber.Map{"error": "Invalid request"})
	}

	DB.Save(&fleet)
	return c.JSON(fleet)
}

func DeleteFleet(c *fiber.Ctx) error {
	id := c.Params("id")
	var fleet Fleet

	if err := DB.First(&fleet, id).Error; err != nil {
		return c.Status(404).JSON(fiber.Map{"error": "Fleet not found"})
	}

	DB.Delete(&fleet)
	return c.JSON(fiber.Map{"message": "Fleet deleted successfully"})
}