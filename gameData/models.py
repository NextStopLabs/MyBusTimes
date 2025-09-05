from django.db import models

def game_details():
    return {
        "parent_game": "roblox"
    }

class game(models.Model):
    game_name = models.CharField(max_length=100)
    routes_json_file = models.FileField(upload_to='JSON/gameRoutes/', blank=True, null=True)
    dests_json_file = models.FileField(upload_to='JSON/gameRoutes/Dests', blank=True, null=True)
    details = models.JSONField(default=game_details)
    active = models.BooleanField(default=False)

    def __str__(self):
        return self.game_name
    
class game_tiles(models.Model):
    game = models.ForeignKey(game, on_delete=models.CASCADE)
    tiles_json_file = models.FileField(upload_to='JSON/gameTiles/', blank=True, null=True)

    def __str__(self):
        return self.game.game_name
