class Collections:
    USERS = "users"
    ANALYSIS = "analysis"
    USER_ANALYSIS_MAPPING = "user_analysis_mapping"
    RISK_ANALYSIS = "risk_analysis"
    BENCHMARK_ANALYSIS = "benchmark_analysis"
    DEAL_NOTE = "deal_note"
    WEIGHTED_SCORES = "weighted_scores"


class FirebaseAccessUrl:
    SIGN_IN_WITH_PASSWORD = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    ACCOUNT_LOOKUP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:lookup"
    SEND_MAIL = "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode"

class SendMailRequestTypes:
    PASSWORD_RESET = "PASSWORD_RESET"
    VERIFY_EMAIL = "VERIFY_EMAIL"

class RedirectUrl:
    LOGIN = "https://ventureval-ef705.web.app/login"