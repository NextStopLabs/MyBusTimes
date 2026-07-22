from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from django.core.files.base import File


class NoChunkedBaseStorage(S3Boto3Storage):
    """
    Overrides _save to avoid all multipart / streaming uploads.
    Forces simple PUT with raw bytes, which Garage fully supports.
    """

    def _save(self, name, content):
        # Reset file pointer
        if isinstance(content, File):
            content.open()

        content.seek(0)

        obj = self.bucket.Object(self._normalize_name(name))

        obj.put(
            Body=content.read(),
            ContentType=getattr(content, "content_type", "application/octet-stream"),
        )

        if isinstance(content, File):
            content.close()

        return name


class StaticStorage(NoChunkedBaseStorage):
    location = "mybustimes/staticfiles"
    default_acl = None


class MediaStorage(NoChunkedBaseStorage):
    location = "mybustimes/media"
    file_overwrite = False
    default_acl = None
