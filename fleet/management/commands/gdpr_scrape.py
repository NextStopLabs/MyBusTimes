import os
import json
import shutil
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.db.models import ForeignKey, ManyToManyField, OneToOneField, FileField, ImageField, TextField, CharField
from django.forms.models import model_to_dict
from django.contrib.auth import get_user_model


def instance_to_dict(instance, include_m2m=True):
	"""Convert a model instance into a serializable dict, including file paths and m2m ids."""
	data = {}
	opts = instance._meta
	for field in opts.concrete_fields:
		name = field.name
		try:
			val = getattr(instance, name)
		except Exception:
			val = None

		# For FileField/ImageField, store the relative path
		if isinstance(field, (FileField, ImageField)):
			if val:
				data[name] = {
					"path": getattr(val, 'name', None),
					"url": getattr(val, 'url', None) if hasattr(val, 'url') else None,
				}
			else:
				data[name] = None
		else:
			# For foreign keys store the related pk (or None)
			if field.is_relation and val is not None:
				try:
					data[name] = getattr(val, 'pk', str(val))
				except Exception:
					data[name] = str(val)
			else:
				data[name] = val

	# Many-to-many
	if include_m2m:
		for field in opts.many_to_many:
			try:
				data[field.name] = [obj.pk for obj in getattr(instance, field.name).all()]
			except Exception:
				data[field.name] = None

	# Add a string representation and model metadata
	data['_meta'] = {
		'model': f"{opts.app_label}.{opts.model_name}",
		'pk': getattr(instance, 'pk', None),
		'repr': str(instance)
	}
	return data


class Command(BaseCommand):
	help = 'Export GDPR-related data for a user (by email/username/name) into multiple JSON files.'

	def add_arguments(self, parser):
		parser.add_argument('--email', help='Email address to search for')
		parser.add_argument('--username', help='Username to search for')
		parser.add_argument('--name', help='Full name or display name to search for')
		parser.add_argument('--output-dir', help='Directory to write JSON files to', default=None)
		parser.add_argument('--deep', action='store_true', help='Also scan Char/Text fields for occurrences of the email/username')
		parser.add_argument('--include-files', action='store_true', help='Copy referenced media files into the export (if found and accessible)')

	def handle(self, *args, **options):
		email = options.get('email')
		username = options.get('username')
		name = options.get('name')
		deep = options.get('deep')
		include_files = options.get('include_files')

		if not (email or username or name):
			raise CommandError('Provide at least --email, --username, or --name to identify the data subject.')

		User = get_user_model()

		# Build queryset to find matching users
		qs = User.objects.none()
		if email:
			qs = qs | User.objects.filter(email__iexact=email)
		if username:
			# try username or username-like fields
			if hasattr(User, 'USERNAME_FIELD'):
				qs = qs | User.objects.filter(**{f"{User.USERNAME_FIELD}__iexact": username})
			else:
				qs = qs | User.objects.filter(username__iexact=username)
		if name:
			# attempt first_name/last_name or full_name fields
			if hasattr(User, 'first_name') and hasattr(User, 'last_name'):
				qs = qs | User.objects.filter(first_name__iexact=name) | User.objects.filter(last_name__iexact=name)
			qs = qs | User.objects.filter(username__iexact=name)

		qs = qs.distinct()

		if not qs.exists():
			self.stdout.write(self.style.ERROR('No matching users found.'))
			return

		# Prepare output directory
		identifier = email or username or name
		timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
		out_dir = options.get('output_dir') or os.path.join(settings.BASE_DIR, 'gdpr_exports', f"{identifier}_{timestamp}")
		os.makedirs(out_dir, exist_ok=True)

		manifest = {
			'requested_by': identifier,
			'timestamp': timestamp,
			'users': [],
			'exports': []
		}

		# Iterate found users
		for user in qs:
			user_id = getattr(user, 'pk')
			user_dir = os.path.join(out_dir, f'user_{user_id}')
			os.makedirs(user_dir, exist_ok=True)

			# Export user model
			user_data = instance_to_dict(user)
			user_file = os.path.join(user_dir, f'user_{user_id}.json')
			with open(user_file, 'w', encoding='utf-8') as f:
				json.dump({'user': user_data}, f, ensure_ascii=False, indent=2, default=str)

			manifest['users'].append({'pk': user_id, 'file': os.path.relpath(user_file, out_dir)})

			# Walk all models and collect related records
			for model in apps.get_models():
				app_label = model._meta.app_label
				model_name = model._meta.model_name
				exported = []

				# Find relation fields that point to the user model
				relation_fields = [f for f in model._meta.get_fields() if getattr(f, 'remote_field', None) and getattr(f.remote_field, 'model', None) in (User, User.__name__, )]

				# Also include ForeignKey fields where remote_field.model is a string to AUTH_USER_MODEL
				for f in model._meta.get_fields():
					try:
						remote = getattr(f, 'remote_field', None)
						if remote and getattr(remote, 'model', None) is not None:
							# remote.model can be a string like settings.AUTH_USER_MODEL
							if isinstance(remote.model, str) and (remote.model == settings.AUTH_USER_MODEL or remote.model.endswith('.' + User.__name__)):
								if f not in relation_fields:
									relation_fields.append(f)
					except Exception:
						pass

				# Query for instances referencing this user
				for f in relation_fields:
					# Build filter
					fname = f.name
					try:
						kwargs = {fname: user}
						qs_rel = model.objects.filter(**kwargs)
					except Exception:
						# For reverse relations or complex fields skip
						continue

					if qs_rel.exists():
						for inst in qs_rel:
							exported.append(instance_to_dict(inst))

				# Optionally deep-scan Char/Text fields for containing identifiers
				if deep:
					text_fields = [f for f in model._meta.get_fields() if isinstance(getattr(f, 'remote_field', None), type(None)) and isinstance(f, (CharField, TextField))]
					for tf in text_fields:
						tname = tf.name
						try:
							q = model.objects.filter(**{f"{tname}__icontains": identifier})
						except Exception:
							continue
						if q.exists():
							for inst in q:
								exported.append(instance_to_dict(inst))

				# Remove duplicates by pk
				unique = {}
				for item in exported:
					pk = item.get('_meta', {}).get('pk')
					key = (app_label, model_name, pk)
					unique[key] = item

				if unique:
					rel_file = os.path.join(user_dir, f"{app_label}__{model_name}.json")
					with open(rel_file, 'w', encoding='utf-8') as f:
						json.dump(list(unique.values()), f, ensure_ascii=False, indent=2, default=str)
					manifest['exports'].append({'app': app_label, 'model': model_name, 'file': os.path.relpath(rel_file, out_dir), 'count': len(unique)})

					# Copy referenced files if requested
					if include_files:
						files_dir = os.path.join(user_dir, 'files')
						os.makedirs(files_dir, exist_ok=True)
						for item in unique.values():
							for k, v in item.items():
								if isinstance(v, dict) and v.get('path'):
									rel_path = v.get('path')
									src_path = os.path.join(settings.MEDIA_ROOT, rel_path) if settings.MEDIA_ROOT and not os.path.isabs(rel_path) else rel_path
									if os.path.exists(src_path):
										dest_path = os.path.join(files_dir, os.path.basename(rel_path))
										try:
											shutil.copy2(src_path, dest_path)
										except Exception:
											# ignore copy errors but note them in manifest
											manifest.setdefault('file_copy_errors', []).append({'src': src_path, 'dst': dest_path})

		# Write manifest
		manifest_file = os.path.join(out_dir, 'manifest.json')
		with open(manifest_file, 'w', encoding='utf-8') as f:
			json.dump(manifest, f, ensure_ascii=False, indent=2, default=str)

		self.stdout.write(self.style.SUCCESS(f'GDPR export completed. Files written to: {out_dir}'))
