import json
import os
from django.core.management.base import BaseCommand, CommandError
from words.models import bannedWord, whitelistedWord


class Command(BaseCommand):
    help = "Import banned and whitelisted words from JSON files in /media/JSON/"

    def handle(self, *args, **options):
        base_path = "media/JSON"
        banned_path = os.path.join(base_path, "bannedWords.json")
        white_path = os.path.join(base_path, "whiteListedWords.json")

        # --- Verify file existence ---
        if not os.path.exists(banned_path):
            raise CommandError(f"File not found: {banned_path}")
        if not os.path.exists(white_path):
            raise CommandError(f"File not found: {white_path}")

        # --- Load and validate JSON data ---
        try:
            with open(banned_path, "r", encoding="utf-8") as f:
                banned_data = json.load(f)
            with open(white_path, "r", encoding="utf-8") as f:
                white_data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON format: {e}")

        # --- Extract arrays from keys ---
        banned_words = banned_data.get("bannedWords", [])
        white_words = white_data.get("whiteListedWords", [])

        if not isinstance(banned_words, list) or not isinstance(white_words, list):
            raise CommandError("Expected JSON keys 'bannedWords' and 'whiteListedWords' to contain lists.")

        # --- Normalize and clean ---
        banned_words = [w.strip().lower() for w in banned_words if isinstance(w, str) and w.strip()]
        white_words = [w.strip().lower() for w in white_words if isinstance(w, str) and w.strip()]

        # --- Import banned words ---
        self.stdout.write(self.style.WARNING(f"Importing {len(banned_words)} banned words..."))
        banned_created = 0
        for word in banned_words:
            _, created = bannedWord.objects.get_or_create(word=word)
            if created:
                banned_created += 1
        self.stdout.write(self.style.SUCCESS(f"✅ Imported {banned_created} new banned words."))

        # --- Import whitelisted words ---
        self.stdout.write(self.style.WARNING(f"Importing {len(white_words)} whitelisted words..."))
        white_created = 0
        for word in white_words:
            _, created = whitelistedWord.objects.get_or_create(word=word)
            if created:
                white_created += 1
        self.stdout.write(self.style.SUCCESS(f"✅ Imported {white_created} new whitelisted words."))

        self.stdout.write(self.style.SUCCESS("🎉 Import complete!"))
