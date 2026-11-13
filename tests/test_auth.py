import time
import unittest
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from neosignis.auth import Authenticator, Settings


class AuthTests(unittest.TestCase):
    def test_cloud_cannot_use_development_token(self):
        with self.assertRaises(ValueError):
            Authenticator(Settings("cloud", "dev_token", "x" * 40, "", "", "http://engine.internal:8001"))

    def test_weak_local_token_rejected(self):
        with self.assertRaises(ValueError):
            Authenticator(Settings("local", "dev_token", "weak", "", "", "http://127.0.0.1:8001"))

    def test_worker_origin_rejects_embedded_credentials(self):
        with self.assertRaises(ValueError):
            Authenticator(Settings("local", "dev_token", "x" * 40, "", "", "http://user:password@127.0.0.1:8001"))

    def setUp(self):
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.issuer = "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_fixture"
        self.auth = Authenticator(Settings("cloud", "cognito", "", self.issuer, "fixture-client", "http://engine.internal:8001"))
        self.auth.jwks = SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=self.key.public_key()))
        self.claims = {"iss": self.issuer, "sub": "fixture-subject", "iat": int(time.time()), "exp": int(time.time()) + 60, "token_use": "access", "client_id": "fixture-client"}

    def token(self, changes=None):
        return jwt.encode(self.claims | (changes or {}), self.key, algorithm="RS256", headers={"kid": "fixture-key"})

    def test_valid_access_token(self):
        self.assertEqual(self.auth.verify(self.token()), "fixture-subject")

    def test_invalid_claims_rejected(self):
        for changes in ({"token_use": "id"}, {"client_id": "other"}, {"iss": "https://evil.example"}, {"exp": 0}, {"sub": ""}):
            with self.subTest(changes=changes), self.assertRaises((ValueError, jwt.PyJWTError)):
                self.auth.verify(self.token(changes))

    def test_wrong_signature_rejected(self):
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with self.assertRaises(jwt.InvalidSignatureError):
            self.auth.verify(jwt.encode(self.claims, other_key, algorithm="RS256"))

    def test_unsigned_token_rejected(self):
        with self.assertRaises(jwt.InvalidAlgorithmError):
            self.auth.verify(jwt.encode(self.claims, key="", algorithm="none"))
