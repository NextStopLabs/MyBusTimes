from django.db import models

def game_details():
    return {
        "parent_game": "roblox"
    }

class game(models.Model):
    game_name = models.CharField(max_length=100)
    routes_json_file = models.FileField(upload_to='JSON/gameRoutes/')
    dests_json_file = models.FileField(upload_to='JSON/gameRoutes/Dests')
    details = models.JSONField(default=game_details)

    def __str__(self):
        return self.game_name