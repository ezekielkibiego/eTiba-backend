from django.contrib.auth.tokens import PasswordResetTokenGenerator
import six

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """
    Token generator for account activation. Inherits from PasswordResetTokenGenerator
    but modifies the hash to ensure one-time use.
    """
    def _make_hash_value(self, user, timestamp):
        """
        Create a hash of user state to invalidate the token upon activation.

        By including the `is_active` status, the token hash will change once
        the user is activated, rendering the original token invalid.
        """
        return (
            six.text_type(user.pk) + 
            six.text_type(timestamp) +
            six.text_type(user.is_active) 
        )

# Create a singleton instance for use throughout the application.
account_activation_token = AccountActivationTokenGenerator()
