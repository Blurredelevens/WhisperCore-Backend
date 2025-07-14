import copy
import json
from functools import wraps

import pytest
from flask_jwt_extended import create_access_token


def response_to_json(response):
    """Decode json from response"""
    return json.loads(response.data.decode("utf8"))


def skip_if_method_not_allowed(method, method_type):
    def decorator(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            if method not in self.allowed_methods[method_type]:
                pytest.skip(f"{method} {method_type} not allowed")

            return fn(self, *args, **kwargs)

        return wrapper

    return decorator


def skip_if_no_query_schema_cls():
    def decorator(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            if not self.query_schema_test_cls:
                pytest.skip("no query_schema_test_cls")

            return fn(self, *args, **kwargs)

        return wrapper

    return decorator


class FlaskViewTestBase:
    """Base class for Flask API view tests with JWT authentication and encryption support."""

    @property
    def model(self):
        """The database model class to test."""
        raise NotImplementedError()

    @property
    def allowed_methods(self):
        """Define which HTTP methods are allowed for list and detail views."""
        return {
            "detail": ["get", "put", "delete"],
            "list": ["get", "post"],
        }

    @property
    def base_url(self):
        """The base URL for the API endpoint (e.g., '/api/memories')."""
        raise NotImplementedError()

    @property
    def factory_test_cls(self):
        """Factory class for creating test data."""
        return None

    @property
    def request_factory_test_cls(self):
        """Factory class for creating request payloads."""
        return None

    @property
    def query_schema_test_cls(self):
        """Factory class for creating query parameters."""
        return None

    @property
    def distinct_query_params(self):
        """List of query parameters that should return distinct results."""
        return []

    @property
    def query_mappings(self):
        """Mapping between query parameters and factory parameters."""
        return {}

    @property
    def relations(self):
        """List of related models that need to be created."""
        return []

    @property
    def requires_auth(self):
        """Whether the endpoint requires JWT authentication."""
        return True

    @property
    def user_fixture(self):
        """The user fixture to use for authentication."""
        return "user"

    def update_batch(self, batch):
        """Update a batch of test records before saving."""
        return batch

    def validate(self, payload, response):
        """Validate the response against the payload."""
        raise NotImplementedError()

    def validate_list(self, response, session):
        """Validate the list response."""
        raise NotImplementedError()

    def create_auth_headers(self, user):
        """Create authentication headers for the given user."""
        if not self.requires_auth:
            return {}

        token = create_access_token(identity=user.id)
        return {"Authorization": f"Bearer {token}"}

    def test_get_list(self, client, db_session, user):
        """Test GET request for list endpoint."""
        record_count = 2
        batch = self.factory_test_cls.create_batch(record_count) if self.factory_test_cls else []
        self.update_batch(batch)

        headers = self.create_auth_headers(user) if self.requires_auth else {}
        response = client.get(self.base_url, headers=headers)

        if "get" not in self.allowed_methods["list"]:
            assert response.status_code == 405
        else:
            if self.requires_auth:
                assert response.status_code != 401  # Should not be unauthorized
            assert response.status_code == 200
            self.validate_list(response, db_session)

    @skip_if_method_not_allowed("get", "list")
    def test_list_empty(self, client, user):
        """Test GET request for empty list."""
        headers = self.create_auth_headers(user) if self.requires_auth else {}
        response = client.get(self.base_url, headers=headers)

        assert response.status_code == 200
        if self.requires_auth:
            assert response.status_code != 401

    @skip_if_no_query_schema_cls()
    @skip_if_method_not_allowed("get", "list")
    def test_get_empty_list_by_query(self, client, user):
        """Test GET request with query parameters for empty list."""
        query_params = self.query_schema_test_cls.build()
        if self.factory_test_cls:
            self.factory_test_cls.create_batch(2)

        headers = self.create_auth_headers(user) if self.requires_auth else {}
        response = client.get(self.base_url, query_string=query_params, headers=headers)

        assert response.status_code == 200
        if self.requires_auth:
            assert response.status_code != 401

    @skip_if_no_query_schema_cls()
    @skip_if_method_not_allowed("get", "list")
    def test_get_list_by_query(self, client, db_session, user):
        """Test GET request with query parameters."""
        record_count = 2
        expected_count = record_count

        query_params = self.query_schema_test_cls.build()
        factory_params = copy.deepcopy(query_params)
        distinct_factory_params = copy.deepcopy(query_params)

        for key in query_params.keys():
            mapping_key = self.query_mappings[key] if key in self.query_mappings else key
            factory_params[mapping_key] = factory_params.pop(key)

            if key in self.distinct_query_params:
                expected_count = 1
                del factory_params[mapping_key]

            distinct_factory_params[mapping_key] = distinct_factory_params.pop(key)

        batch = []
        if expected_count == 1:
            batch.extend(
                self.factory_test_cls.create_batch(
                    expected_count,
                    **distinct_factory_params,
                ),
            )
            batch.extend(
                self.factory_test_cls.create_batch(
                    record_count - expected_count,
                    **factory_params,
                ),
            )
        else:
            batch.extend(self.factory_test_cls.create_batch(record_count, **factory_params))

        self.update_batch(batch)

        headers = self.create_auth_headers(user) if self.requires_auth else {}
        response = client.get(self.base_url, query_string=query_params, headers=headers)

        assert response.status_code == 200
        if self.requires_auth:
            assert response.status_code != 401
        self.validate_list(response, db_session)

    @skip_if_method_not_allowed("get", "detail")
    def test_get_detail_404(self, client, user):
        """Test GET request for non-existent detail."""
        headers = self.create_auth_headers(user) if self.requires_auth else {}
        response = client.get(f"{self.base_url}/99999", headers=headers)

        assert response.status_code == 404

    def test_get_detail(self, client, user):
        """Test GET request for detail endpoint."""
        if not self.factory_test_cls:
            pytest.skip("No factory class defined")

        db_record = self.factory_test_cls()
        self.update_batch([db_record])
        db_record.save()
        self.factory_test_cls.create_batch(3)

        headers = self.create_auth_headers(user) if self.requires_auth else {}
        response = client.get(f"{self.base_url}/{db_record.id}", headers=headers)

        if "get" not in self.allowed_methods["detail"]:
            assert response.status_code == 405
        else:
            assert response.status_code == 200
            if self.requires_auth:
                assert response.status_code != 401

    @skip_if_method_not_allowed("delete", "detail")
    def test_delete_404(self, client, user):
        """Test DELETE request for non-existent detail."""
        headers = self.create_auth_headers(user) if self.requires_auth else {}
        response = client.delete(f"{self.base_url}/99999", headers=headers)

        assert response.status_code == 404

    def test_delete(self, client, db_session, user):
        """Test DELETE request for detail endpoint."""
        if not self.factory_test_cls:
            pytest.skip("No factory class defined")

        record_count = 2
        db_record = self.factory_test_cls()
        self.update_batch([db_record])
        db_record.save()
        self.factory_test_cls.create_batch(record_count)
        record_id = db_record.id

        headers = self.create_auth_headers(user) if self.requires_auth else {}
        response = client.delete(f"{self.base_url}/{record_id}", headers=headers)

        if "delete" not in self.allowed_methods["detail"]:
            assert response.status_code == 405
        else:
            assert response.status_code in [200, 204]
            if self.requires_auth:
                assert response.status_code != 401

    def test_post(self, client, db_session, user):
        """Test POST request for list endpoint."""
        payload = self.request_factory_test_cls() if self.request_factory_test_cls else {}

        headers = self.create_auth_headers(user) if self.requires_auth else {}
        response = client.post(self.base_url, json=payload, headers=headers)

        if "post" not in self.allowed_methods["list"]:
            assert response.status_code == 405
        else:
            assert response.status_code == 201
            if self.requires_auth:
                assert response.status_code != 401
            self.validate(payload, response)

    def test_put(self, client, db_session, user):
        """Test PUT request for detail endpoint."""
        if not self.factory_test_cls:
            pytest.skip("No factory class defined")

        db_record = self.factory_test_cls()
        self.update_batch([db_record])
        db_record.save()
        payload = self.request_factory_test_cls() if self.request_factory_test_cls else {}

        headers = self.create_auth_headers(user) if self.requires_auth else {}
        response = client.put(f"{self.base_url}/{db_record.id}", json=payload, headers=headers)

        if "put" not in self.allowed_methods["detail"]:
            assert response.status_code == 405
        else:
            assert response.status_code == 200
            if self.requires_auth:
                assert response.status_code != 401
            self.validate(payload, response)

    @skip_if_method_not_allowed("put", "detail")
    def test_put_non_existent_relations(self, client, user):
        """Test PUT request with non-existent relations."""
        if not self.relations:
            pytest.skip("no relations")

        if not self.factory_test_cls:
            pytest.skip("No factory class defined")

        db_record = self.factory_test_cls()
        self.update_batch([db_record])
        db_record.save()

        relation_params = {}
        for relation in self.relations:
            relation_params[relation] = 99999  # Non-existent ID

        payload = {}
        if self.request_factory_test_cls:
            payload = self.request_factory_test_cls(**relation_params, create_relations__should_create=False)

        headers = self.create_auth_headers(user) if self.requires_auth else {}
        response = client.put(f"{self.base_url}/{db_record.id}", json=payload, headers=headers)

        assert response.status_code == 400

    def test_unauthorized_access(self, client):
        """Test access without authentication when auth is required."""
        if not self.requires_auth:
            pytest.skip("Endpoint does not require authentication")

        response = client.get(self.base_url)
        assert response.status_code == 401
