# Plan for MBT V3

## Sites

### MyBusTimes

> www.mybustimes.cc<br>
> The main site for MBT that does all the user management and all the operator / fleet / route stuff

> This will be next.js / prisma

### MBT Forums

> forum.mybustimes.cc<br>
> The forum that syncs between discord and the site<br>
> On the discord the main section will have general when admin makes a new forum type it will make a new forum on discord. Then a new thread will make a new thread in that forum on the discord

> This will be next.js / prisma

### Tickets

> ticket.mybustimes.cc<br>
> This will be basicly the same system as the forum again syncing with discord

> This will be next.js / prisma

### Sim Tracking

> tracking.mybustiems.cc<br>
> This will be a simple django app that calls an API on the main site to get the data then uses that to generage simulated positions for all vehicles which the main site can call for the maps

> This will be django

## DB setup

### Main

```JSON
"Users": {
    "User": {
        "ID": "integer",
        "Username": "string",
        "Email": "string",
        "Password": "string",
        "JoinDate": "datetime",
        "UpdatedDate": "datetime",
        "Active": "boolean",
        "Banned": "boolean",
        "IsStaff": "boolean",
        "IsSuperuser": "boolean",
        "StaffTeam": "foreignkey (StaffTeams)"
    },
    "StaffTeams": {
        "ID": "integer",
        "Name": "string",
        "Perms": "many_to_many (StaffPerms)"
    },
    "StaffPerms": {
        "ID": "integer",
        "Name": "string",
        "Slug": "slug"
    },
    "UserProfile": {
        "ID": "integer",
        "User": "foreign_key",
        "PFP": "string",
        "Banner": "string",
        "Theme": "foreignkey (Themes)",
        "DarkMode": "bool",
        "OtherDetails": {
          "details": {
            "had_free_trial": "boolean"
          }
        },
        "Badges": "many_to_many (Badges)"
    },
    "Themes": {
        "ID": "integer",
        "Name": "string",
        "Public": "bool",
        "Dark_CSS": "string",
        "Light_CSS": "string",
        "Weight": "integer"
    },
    "Badges": {
        "ID": "integer",
        "Name": "string",
        "Foreground": "string",
        "Background": "string",
        "AdditionalCSS": "string",
        "SelfAssign": "boolean"
    },
    "Devices": {
        "ID": "integer",
        "Fingerprint": "string",
        "Details": "text",
        "User": "foreignkey (User)",
        "IP": "string",
        "TimesUsed": "integer",
        "LastUsed": "datetime"
    },
    "IPs": {
        "ID": "integer",
        "IP": "string",
        "User": "foreignkey (User)",
        "TimesUsed": "integer",
        "LastUsed": "datetime"
    },
    "Bans": {
        "ID": "integer",
        "User": "foreignkey (User)",
        "IPs": "many_to_many (IPs)",
        "Devices": "many_to_many (Devices)",
        "Reason": "text"
    },
    "ActiveSubscriptions": {
        "ID": "integer",
        "User": "foreignkey (User)",
        "SubID": "string",
        "CustomerID": "string",
        "InvoiceIDs": "JSON",
        "StartDate": "datetime",
        "EndDate": "datetime",
        "UpdatedAt": "datetime",
        "Plan": "string",
        "IsTrial": "bool"
    }
},
"Operators": {
    "Operator": {
        "ID": "integer",
        "Name": "string",
        "Code": "string",
        "Slug": "slug",
        "Details": "JSON",
        "Owner": "foreignkey (User)",
        "Group": "foreignkey (Group)",
        "Organisation": "foreignkey (Group)",
        "Regions": "many_to_many (Region)",
        "Verified": "bool",
        "PublicNotes": "text"
    },
    "Region": {
        "ID": "integer",
        "Name": "string",
        "Code": "string",
        "Parent": "foreignkey (self)"
    },
    "OperatorType": {
        "ID": "integer",
        "Name": "string",
        "Published": "bool"
    },
    "Group": {
        "ID": "integer",
        "Name": "string",
        "Parenet": "foreignkey (self)",
        "Public": "bool",
        "Type": "enum ('Group', 'Organisation')"
    },
    "Updates": {
        "ID": "integer",
        "Name": "string",
        "Details": "text",
        "Operator": "foreignkey (Operator)"
    },
    "Helpers": {
        "ID": "integer",
        "User": "foreignkey (User)",
        "Perms": "many_to_many (HelperPerms)",
    },
    "HelperPerms": {
        "ID": "integer",
        "Name": "string",
        "Slug": "slug",
        "PermLevel": "integer"
    }
},
"Vehicles": {
    "Vehicle": {
        "ID": "integer",
        "Operator": "foreignkey (Operator)",
        "FleetNumber": "string",
        "FleetNumberSorting": "string",
        "Reg": "string",
        "PrevReg": "string",
        "Livery": "foreignkey (Liveies)",
        "Details": "JSON",
        "Features": "JSON",
        "Notes": "text",
        "Type": "foreignkey (Type)",
        "IsInService": "bool",
        "IsForSale": "bool",
        "VehicleCategory": "foreignkey",
        "LastEditedBy": "foreignkey (User)"
    },
    "VehicleChanges": {
        "ID": "integer",
        "Vehicle": "foreignkey (Vehicle)",
        "Changes": "JSON",
        "ChangedAt": "datetime",
        "ApprovedAt": "datetime",
        "ChangedBy": "foreignkey (User)",
        "ApprovedBy": "foreignkey (User)"
    },
    "Liveies": {
        "ID": "integer",
        "Name": "string",
        "BLOB": "text",
        "TextColour": "text",
        "StrokeColour": "text",
        "LeftCSS": "text",
        "RightCSS": "text",
        "Status": "ENUM, ('Pending', 'Published', 'Declined')",
        "AddedBy": "foreignkey (User)",
        "UpdatedBy": "foreignkey (User)",
        "UpdatedAt": "datetime"
    },
    "Type": {
        "ID": "integer",
        "Name": "text",
        "FuelType": "text",
        "DoubleDecker": "bool",
        "Status": "ENUM, ('Pending', 'Published', 'Declined')",
        "AddedBy": "foreignkey (User)",
        "UpdatedBy": "foreignkey (User)",
        "UpdatedAt": "datetime"
    }
},
"Routes": {
    "Route": {
        "ID": "integer",
        "RouteNumber": "string",
        "RouteName": "string",
        "Destinations": "JSON",
        "Operators": "many_to_many (Operator)",
        "Details": "JSON",
        "Hidden": "bool",
        "LinkedRoutes": "foreignkey (self)",
        "RelatedRoutes": "foreignkey (self)",
        "RouteType": "foreignkey (RouteTypes)",
    },
    "RouteTypes": {
        "ID": "integer",
        "Name": "string",
        "Status": "ENUM, ('Pending', 'Published', 'Declined')",
        "AddedBy": "foreignkey (User)",
        "UpdatedBy": "foreignkey (User)",
        "UpdatedAt": "datetime"
    }
},
"Boards": {
    "Board": {
        "ID": "integer",
        "Name": "string",
        "Operator": "foreignkey (Operator)",
        "Type": "enum ('Running Board', 'Duty')"
    },
    "BoardTrips": {
        "ID": "integer",
        "RouteNumber": "string",
        "RouteLink": "fpreignkey (Route)",
        "Time": "time",
        "Direction": "enum ('inbound', 'outbound')",
        "StartAtStop": "string",
        "EndAtStop": "string",
        "StartAtDest": "string",
        "EndAtDest": "string"
    }
}
```