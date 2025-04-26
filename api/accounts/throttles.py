from rest_framework.throttling import AnonRateThrottle

class PasswordResetRateThrottle(AnonRateThrottle):
    scope = 'reset'

class VerificationResendRateThrottle(AnonRateThrottle):
    scope = 'verify'