import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # points to repo root
load_dotenv(BASE_DIR / ".env")

INSTALLED_APPS = [
  # Django...
  "rest_framework",
  "corsheaders",
  "django_filters",
  "drf_spectacular",

  "users",
  "auth",
  "doctors",
  "appointments",
  "records",
  "chat",
  "video",
  "dashboard",
]
