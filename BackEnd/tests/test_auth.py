# BackEnd/tests/test_auth.py

"""
test:

A. JWT
B. Secret
"""

import pytest
from datetime import timedelta
from app.users.auth.jwt import (
    create_access_token,
    get_subject,
    JWTAuthError,
)
from app.users.auth.password import get_password_hash, verify_password


class TestJWT:
    """
    JWT about:
    1. normal process: issue token, get back user id
    2. expired token processing
    3. how to deal with signature tampering
    """

    def test_token_subject_roundtrip(self):
        '''
        use get_subject to get back the correct user ID after issuing the token
        '''
 
        token, _ = create_access_token(subject="user_42")
        assert get_subject(token) == "user_42"
 
    def test_expired_token_raises(self):
        '''
        Expired tokens must be rejected; invalid credentials should not be allowed to continue accessing the system.
        Construct an expired token using timedelta(minutes=-1),
        '''
   
        token, _ = create_access_token(
            subject="user_42",
            expires_delta=timedelta(minutes=-1)
        )
        with pytest.raises(JWTAuthError):
            get_subject(token)
 
    def test_tampered_token_raises(self):
        """
        Tokens with tampered signatures must be rejected; otherwise, anyone can forge their identities.
        Add a character at the end of the token to simulate tampering.
        """
        token, _ = create_access_token(subject="user_42")
        tampered = token + "x"
        with pytest.raises(JWTAuthError):
            get_subject(tampered)
 

class TestPassword:
    """
    Password about.
    1. correct password pass
    2. wrong password blocking
    3. encrypted password storage
    """
    def test_correct_password_verifies(self):
        """
        The correct password must be able to be verified to ensure that the normal flow of logging in is not broken.
        """
        hashed = get_password_hash("mysecret")
        assert verify_password("mysecret", hashed) is True
 
    def test_wrong_password_fails(self):
        """
        Incorrect passwords must be rejected.
        This test verifies that verify password is really making comparisons and does not always return True.
        """
        hashed = get_password_hash("mysecret")
        assert verify_password("wrongpassword", hashed) is False
 
    def test_hash_is_not_plaintext(self):
        """
        What is stored in the database must be hash, not plaintext.
        """

        password = "mysecret"
        hashed = get_password_hash(password)
        assert hashed != password