"""ORM models. Importing here ensures Alembic autogenerate sees every table."""
from app.models.api_key import ApiKey
from app.models.face import Face
from app.models.person import Person
from app.models.recognition_log import RecognitionLog
from app.models.user import User

__all__ = ["Person", "Face", "RecognitionLog", "User", "ApiKey"]
