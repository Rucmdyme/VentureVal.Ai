class Collections:
    USERS = "users"
    ANALYSIS_DATA = "analysis"
    USER_ANALYSIS_MAPPING = "user_analysis_mapping"

class FirebaseAccessUrl:
    SIGN_IN_WITH_PASSWORD = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    ACCOUNT_LOOKUP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:lookup"
    SEND_MAIL = "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode"

class SendMailRequestTypes:
    PASSWORD_RESET = "PASSWORD_RESET"
    VERIFY_EMAIL = "VERIFY_EMAIL"

class RedirectUrl:
    LOGIN = "https://ventureval-ef705.web.app/login"