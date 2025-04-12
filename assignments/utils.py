from google.cloud import storage
from django.conf import settings
from datetime import timedelta

def generate_signed_url(blob_path: str, expiration_minutes=15):
    """Generate a signed URL for a file in Google Cloud Storage"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(settings.GS_BUCKET_NAME)
    blob = bucket.blob(blob_path)

    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expiration_minutes),
        method="GET",
    )
    return url
