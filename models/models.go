package models

import (
	"time"

	"gorm.io/gorm"
)

type User struct {
	gorm.Model
	Username      string `json:"username" gorm:"unique;not null"`
	Password      string `json:"-"`
	Email         string `json:"email" gorm:"unique;not null"`
	Profile       UserProfile
	Activity      UserActivity
	Subscriptions []ActiveSubscription
	Bans          []Ban
}

type UserProfile struct {
	gorm.Model
	UserID     uint                   `json:"user_id" gorm:"index"`
	StylePrefs map[string]interface{} `json:"style_prefs" gorm:"serializer:json"`
	Badges     []string               `json:"badges" gorm:"serializer:json"`
	OtherInfo  map[string]interface{} `json:"other_info" gorm:"serializer:json"`
	BannerURL  string                 `json:"banner_url"`
	AvatarURL  string                 `json:"avatar_url"`
}

type UserActivity struct {
	gorm.Model
	UserID                uint      `json:"user_id" gorm:"index"`
	LastLogin             time.Time `json:"last_login"`
	LastIP                string    `json:"last_ip"`
	LastDeviceFingerprint string    `json:"last_device_fingerprint"`
	AllIPAddresses        []string  `json:"all_ip_addresses" gorm:"serializer:json"`
	AllDeviceFingerprints []string  `json:"all_device_fingerprints" gorm:"serializer:json"`
}

type ActiveSubscription struct {
	gorm.Model
	UserID           uint       `json:"user_id" gorm:"index"`
	StripeSubID      string     `json:"stripe_sub_id" gorm:"unique"`
	StripeCustomerID string     `json:"stripe_customer_id"`
	PlanName         string     `json:"plan_name"`
	StartDate        time.Time  `json:"start_date"`
	EndDate          *time.Time `json:"end_date"`
	PlanType         string     `json:"plan_type"`
	IsATrial         bool       `json:"is_a_trial" gorm:"default:false"`
	OtherNotes       string     `json:"other_notes"`
}

type Ban struct {
	gorm.Model
	UserID        uint       `json:"user_id" gorm:"index"`
	BanReason     string     `json:"ban_reason" gorm:"not null"`
	BanDate       time.Time  `json:"ban_date"`
	UnbanDate     *time.Time `json:"unban_date"`
	BannedBy      uint       `json:"banned_by"`
	OtherNotes    string     `json:"other_notes"`
	IPsBanned     []string   `json:"ips_banned" gorm:"serializer:json"`
	DevicesBanned []string   `json:"devices_banned" gorm:"serializer:json"`
}
