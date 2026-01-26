package database

import (
	"mybustimes/air/models"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

var DB *gorm.DB

func Connect() error {
	var err error
	DB, err = gorm.Open(sqlite.Open("mybustimes.db"), &gorm.Config{})
	if err != nil {
		return err
	}

	// Auto-migrate all models
	DB.AutoMigrate(
		&models.User{},
		&models.UserProfile{},
		&models.UserActivity{},
		&models.ActiveSubscription{},
		&models.Ban{},
	)

	return nil
}
