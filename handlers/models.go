package handlers

import (
	"time"
	"gorm.io/gorm"
)

type User struct {
	ID        uint           `gorm:"primarykey" json:"id"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"-"`
	Email     string         `gorm:"unique;not null" json:"email"`
	Name      string         `gorm:"not null" json:"name"`
	Password  string         `gorm:"not null" json:"-"`
	IsAdmin   bool           `gorm:"default:false" json:"is_admin"`
}

type Fleet struct {
	ID           uint           `gorm:"primarykey" json:"id"`
	CreatedAt    time.Time      `json:"created_at"`
	UpdatedAt    time.Time      `json:"updated_at"`
	DeletedAt    gorm.DeletedAt `gorm:"index" json:"-"`
	Name         string         `gorm:"not null" json:"name"`
	VehicleCount int            `json:"vehicle_count"`
	Status       string         `gorm:"default:active" json:"status"`
}

type Simulation struct {
	ID        uint           `gorm:"primarykey" json:"id"`
	CreatedAt time.Time      `json:"created_at"`
	UpdatedAt time.Time      `json:"updated_at"`
	DeletedAt gorm.DeletedAt `gorm:"index" json:"-"`
	Name      string         `gorm:"not null" json:"name"`
	FleetID   uint           `json:"fleet_id"`
	Fleet     Fleet          `gorm:"foreignKey:FleetID" json:"fleet"`
	Status    string         `gorm:"default:pending" json:"status"`
	Results   string         `gorm:"type:text" json:"results"`
}