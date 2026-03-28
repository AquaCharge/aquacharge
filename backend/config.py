import os
from datetime import timedelta

# ---------------------------------------------------------------------------
# Environment & DynamoDB table names
#
# Resolution order:
#   1. Explicit env var  (e.g. DYNAMODB_USERS_TABLE=aquacharge-users-prod)
#   2. ENVIRONMENT-based fallback → aquacharge-{table}-{ENVIRONMENT}
#
# Locally (no env vars) → resolves to *-dev tables.
# On EC2 the deploy script sets ENVIRONMENT=prod so all tables resolve to
# *-prod automatically without any other changes.
# ---------------------------------------------------------------------------
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def _is_production_environment() -> bool:
    return ENVIRONMENT.strip().lower() in {"prod", "production"}


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _table(name: str) -> str:
    env_key = f"DYNAMODB_{name.upper()}_TABLE"
    return os.environ.get(env_key) or f"aquacharge-{name.lower()}-{ENVIRONMENT}"


USERS_TABLE = _table("users")
STATIONS_TABLE = _table("stations")
CHARGERS_TABLE = _table("chargers")
VESSELS_TABLE = _table("vessels")
BOOKINGS_TABLE = _table("bookings")
CONTRACTS_TABLE = _table("contracts")
PORTS_TABLE = _table("ports")
DREVENTS_TABLE = _table("drevents")
ORGS_TABLE = _table("orgs")
MEASUREMENTS_TABLE = _table("measurements")
DR_START_ASYNC = _env_bool("DR_START_ASYNC", default=not _is_production_environment())
DR_DISPATCH_INTERVAL_SECONDS = _env_int(
    "DR_DISPATCH_INTERVAL_SECONDS",
    default=60 if _is_production_environment() else 10,
)


class Config:
    """Base configuration class"""

    # Flask settings
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"
    DEBUG = False
    TESTING = False

    # JWT settings
    JWT_SECRET_KEY = (
        os.environ.get("JWT_SECRET_KEY") or "jwt-secret-key-change-in-production"
    )
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Password reset settings
    PASSWORD_RESET_EXPIRY_HOURS = 2

    # Email settings (for password reset)
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ["true", "on", "1"]
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = (
        os.environ.get("MAIL_DEFAULT_SENDER") or "noreply@aquacharge.com"
    )

    # Database settings (for future use)
    DATABASE_URL = os.environ.get("DATABASE_URL")

    # API settings
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    JWT_SECRET_KEY = "dev-jwt-secret-key"


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    JWT_SECRET_KEY = "test-jwt-secret-key"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=1)  # Short expiry for testing


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    # Override to use only environment variables in production
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or Config.JWT_SECRET_KEY


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

# Export commonly used configuration values for direct import
# Read JWT_SECRET from the environment so production uses the injected secret
JWT_SECRET = os.environ.get("JWT_SECRET_KEY") or "dev-jwt-secret-key"
JWT_ALGORITHM = Config.JWT_ALGORITHM
