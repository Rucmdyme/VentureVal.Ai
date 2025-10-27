class Collections:
    USERS = "users"
    ANALYSIS = "analysis"
    USER_ANALYSIS_MAPPING = "user_analysis_mapping"
    RISK_ANALYSIS = "risk_analysis"
    BENCHMARK_ANALYSIS = "benchmark_analysis"
    DEAL_NOTE = "deal_note"
    WEIGHTED_SCORES = "weighted_scores"
    DOCUMENTS = "documents"


class FirebaseAccessUrl:
    SIGN_IN_WITH_PASSWORD = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    ACCOUNT_LOOKUP_URL = "https://identitytoolkit.googleapis.com/v1/accounts:lookup"
    SEND_MAIL = "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode"

class SendMailRequestTypes:
    PASSWORD_RESET = "PASSWORD_RESET"
    VERIFY_EMAIL = "VERIFY_EMAIL"

class RedirectUrl:
    LOGIN = "https://ventureval-ef705.web.app/login"

ALLOWED_MIME_TYPES = {
    'application/pdf',
    'text/plain',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/jpeg',
    'image/jpg',
    'image/png'
}

ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.jpg', '.jpeg', '.png'}

