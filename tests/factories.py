from datetime import datetime, timezone

import factory

from extensions import db
from models.memory import Memory
from models.prompt import Prompt
from models.reflection import Reflection
from models.token import Token
from models.user import User


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"

    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    email_verified = True
    is_admin = False

    @factory.post_generation
    def set_password(self, create, extracted, **kwargs):
        if create:
            self.set_password("Testpassword123!")
            self.set_passphrase("testpassphrase123")


class MemoryFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Memory
        sqlalchemy_session_persistence = "commit"

    user_id = factory.SubFactory(UserFactory).id
    chat_id = factory.Faker("uuid4")
    mood = factory.Iterator(["happy", "sad", "neutral", "excited"])
    mood_emoji = factory.Iterator(["😊", "😢", "😐", "🎉"])
    tags = factory.Faker("words", nb=3)
    is_bookmarked = False

    @factory.post_generation
    def set_content(self, create, extracted, **kwargs):
        if create:
            user = db.session.get(User, self.user_id)
            if user:
                content = factory.Faker("paragraph").generate()
                self.set_content(content, user.encryption_key.encode())
                self.set_model_response(f"AI response to: {content}", user.encryption_key.encode())


class ReflectionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Reflection
        sqlalchemy_session_persistence = "commit"

    user_id = factory.SubFactory(UserFactory).id
    content = factory.Faker("paragraph")
    reflection_type = factory.Iterator(["daily", "weekly", "monthly"])
    period_start = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    period_end = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class PromptFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Prompt
        sqlalchemy_session_persistence = "commit"

    text = factory.Faker("sentence")
    is_active = True
    user_id = factory.SubFactory(UserFactory).id


class TokenFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Token
        sqlalchemy_session_persistence = "commit"

    user_id = factory.SubFactory(UserFactory).id
    token = factory.Faker("uuid4")


# Request payload factories
class MemoryRequestFactory(factory.Factory):
    class Meta:
        model = dict

    content = factory.Faker("paragraph")
    model_response = factory.Faker("sentence")
    chat_id = factory.Faker("uuid4")
    mood = factory.Iterator(["happy", "sad", "neutral", "excited"])
    mood_emoji = factory.Iterator(["😊", "😢", "😐", "🎉"])
    tags = factory.LazyFunction(lambda: ["tag1", "tag2", "tag3"])


class MemoryUpdateRequestFactory(factory.Factory):
    class Meta:
        model = dict

    content = factory.Faker("paragraph")
    chat_id = factory.Faker("uuid4")
    mood = factory.Iterator(["happy", "sad", "neutral", "excited"])
    mood_emoji = factory.Iterator(["😊", "😢", "😐", "🎉"])
    tags = factory.LazyFunction(lambda: ["updated_tag1", "updated_tag2"])


class ReflectionRequestFactory(factory.Factory):
    class Meta:
        model = dict

    content = factory.Faker("paragraph")
    reflection_type = factory.Iterator(["daily", "weekly", "monthly"])
    period_start = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())
    period_end = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())


class PromptRequestFactory(factory.Factory):
    class Meta:
        model = dict

    text = factory.Faker("sentence")
    is_active = True


class UserRegistrationRequestFactory(factory.Factory):
    class Meta:
        model = dict

    email = factory.Faker("email")
    password = "Testpassword123!"
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    passphrase = "testpassphrase123"


class UserLoginRequestFactory(factory.Factory):
    class Meta:
        model = dict

    email = factory.Faker("email")
    password = "Testpassword123!"


# Query parameter factories
class MemoryQueryFactory(factory.Factory):
    class Meta:
        model = dict

    search = factory.Faker("word")
    mood = factory.Iterator(["happy", "sad", "neutral", "excited"])
    mood_emoji = factory.Iterator(["😊", "😢", "😐", "🎉"])
    tag = factory.Faker("word")
    chat_id = factory.Faker("uuid4")
    bookmarked = factory.Iterator(["true", "false"])
    group_by_chat_id = factory.Iterator(["true", "false"])
    page = factory.Iterator([1, 2, 3])
    per_page = factory.Iterator([5, 10, 20])
