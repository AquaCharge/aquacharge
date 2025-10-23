import os
from datetime import timedelta


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
    # In production, these should be set via environment variables
    if not os.environ.get("JWT_SECRET_KEY"):
        raise ValueError("JWT_SECRET_KEY must be set in production")


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
