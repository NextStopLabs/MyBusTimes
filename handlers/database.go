package handlers

import (
	"log"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

var DB *gorm.DB

func InitDatabase() {
	var err error
	DB, err = gorm.Open(sqlite.Open("app.db"), &gorm.Config{})
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}

	// Auto-migrate all models
	DB.AutoMigrate(&User{}, &Fleet{}, &Simulation{})

	// Create sample data if database is empty
	var count int64
	DB.Model(&User{}).Count(&count)
	if count == 0 {
		sampleUsers := []User{
			{Email: "admin@example.com", Name: "Admin User", Password: "hashed_password", IsAdmin: true},
			{Email: "john@example.com", Name: "John Doe", Password: "hashed_password", IsAdmin: false},
		}
		DB.Create(&sampleUsers)

		sampleFleets := []Fleet{
			{Name: "Fleet A", VehicleCount: 10, Status: "active"},
			{Name: "Fleet B", VehicleCount: 5, Status: "active"},
		}
		DB.Create(&sampleFleets)

		log.Println("Created sample data")
	}
}