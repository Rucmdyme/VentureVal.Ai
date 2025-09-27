
from firebase_admin import auth
from fastapi import HTTPException
from models.database import firestore
import requests
import logging

from models import schemas
from models.database import get_firestore_client
from constants import Collections, FirebaseAccessUrl, SendMailRequestTypes, RedirectUrl
from settings import API_KEY
logger = logging.getLogger(__name__)


class UserService:
	def __init__(self, db=None):
		self.db = db or get_firestore_client()
		self.api_key = API_KEY
	def _handle_firebase_auth_error(self, e: Exception, operation: str):
		"""Centralized error handling for Firebase operations"""
		if isinstance(e, auth.EmailAlreadyExistsError):
			raise HTTPException(status_code=409, detail="Email already exists")
		elif isinstance(e, auth.InvalidIdTokenError):
			raise HTTPException(status_code=401, detail="Invalid or expired token")
		elif isinstance(e, auth.ExpiredIdTokenError):
			raise HTTPException(status_code=401, detail="Token expired")
		elif isinstance(e, requests.RequestException):
			logger.error(f"Network error during {operation}: {str(e)}")
			raise HTTPException(status_code=503, detail="Service temporarily unavailable")
		else:
			logger.error(f"Unexpected error during {operation}: {str(e)}", exc_info=True)
			raise HTTPException(status_code=500, detail="Internal server error")


	def signup(self, payload: schemas.SignupRequest):
		try:
			user_record = auth.create_user(
				email=payload.email,
				password=payload.password,
				email_verified=False,
			)
		except Exception as e:
			self._handle_firebase_auth_error(e, "user signup")
		try:
			user_id = user_record.uid
			self.db.collection(Collections.USERS).document(user_id).set({
				"user_id": user_id,
                "email": payload.email,
                "role": payload.role,
                "location": payload.location,
                "created_at": firestore.SERVER_TIMESTAMP
            })
			logger.info(f"User created successfully: {user_record.uid}")
		except Exception as error:
			# Rollback: Delete the Firebase user if Firestore creation fails
			logger.error(f"Failed to create user profile: {str(error)}")
			auth.delete_user(user_record.uid)
			logger.warning(f"Rolled back Firebase user creation for: {payload.email}")
			raise HTTPException(status_code=500, detail="Failed to create user profile")
		return {"msg": "Signup successful, Please verify your email"}
	

	def login(self, payload: schemas.LoginRequest):

		params = {"key": self.api_key}
		json_payload = {
			"email": payload.email, 
			"password": payload.password, 
			"returnSecureToken": True
		}
		try:
			resp = requests.post(FirebaseAccessUrl.SIGN_IN_WITH_PASSWORD, params=params, json=json_payload)
		except requests.RequestException as e:
			logger.error(f"Network error during login: {str(e)}")
			raise HTTPException(status_code=503, detail="Service temporarily unavailable")
			
		if resp.status_code != 200:
			raise HTTPException(status_code=401, detail="User does not exist or wrong password")
		login_info = resp.json()
		user_auth_token = login_info["idToken"]
		
		try:
			decoded_token = auth.verify_id_token(user_auth_token)
			email_verified = decoded_token.get('email_verified')
			user_id = decoded_token.get('user_id')
			# TODO: check for allowing user to login only when verified.
			# if not email_verified:
			# 	raise HTTPException(
            #         status_code=403,
            #         detail="Please verify your email before logging in"
            #     )
			user_doc = self.db.collection(Collections.USERS).document(user_id).get()
			if not user_doc.exists:
				raise HTTPException(status_code=401, detail="User profile missing")
			user_data = user_doc.to_dict()
			return {"user_auth_token": user_auth_token, "user_info": user_data}
		except HTTPException:
			raise
		except Exception as e:
			self._handle_firebase_auth_error(e, "user login")


	def get_current_user(self, token: str):
		try:
			decoded_token = auth.verify_id_token(token)
			uid = decoded_token.get("uid")
			if not uid:
				logger.error("Missing localId in Firebase user data")
				raise HTTPException(status_code=401, detail="Invalid token - no UID found")

			user_doc = self.db.collection(Collections.USERS).document(uid).get()
			if not user_doc.exists:
				logger.warning(f"User profile not found in Firestore for user_id: {uid}")
				raise HTTPException(status_code=404, detail="User profile not found")
			user_data = user_doc.to_dict()
			logger.info(f"Successfully retrieved user data for localId: {uid}")
			return user_data
		except HTTPException:
			raise
		except Exception as error:
			logger.error(f"Unexpected error in get_current_user: {str(error)}", exc_info=True)
			raise HTTPException(status_code=401, detail="Invalid or expired token")


	def reset_password(self, payload: schemas.ResetPasswordRequest):
		params = {
			"key": self.api_key
        }
		data = {
			"requestType": SendMailRequestTypes.PASSWORD_RESET,
			"email": payload.email,
			"continueUrl": RedirectUrl.LOGIN
		}
		try:
			resp = requests.post(FirebaseAccessUrl.SEND_MAIL, json=data, params=params)
			if resp.status_code != 200:
				logger.error(f"Firebase API error: {resp.status_code} - {resp.text}")
				raise HTTPException(
                    status_code=400,
                    detail="Failed to send reset email. Please check the address and try again."
                )
			return {"msg": "If this email is registered, you will receive a password reset email shortly."}
		except requests.RequestException as e:
			logger.error(f"Network error during password reset: {str(e)}")
			raise HTTPException(status_code=503, detail="Service temporarily unavailable")


	def resend_verification(self, payload: schemas.ResendVerificationLink):
		try:
			decoded_token = auth.verify_id_token(payload.token)
			user_email = decoded_token.get('email')
			email_verified = decoded_token.get('email_verified')
			if not user_email:
				raise ValueError("ID Token does not contain a verifiable email address.")
			if email_verified:
				return {"message": "Email is already verified. Please proceed."}
		except Exception as e:
			self._handle_firebase_auth_error(e, "token verification")

		params = {
			"key": self.api_key
        }
		data = {
			"requestType": SendMailRequestTypes.VERIFY_EMAIL,
			"idToken": payload.token,
			"continueUrl": RedirectUrl.LOGIN
		}
		try:
			resp = requests.post(FirebaseAccessUrl.SEND_MAIL, json=data, params=params)
			if resp.status_code != 200:
				raise HTTPException(
                    status_code=400,
                    detail="Failed to send send verification email. Please try again."
                )
			return {"msg": "Verification email resent. Please check your inbox."}
		except requests.RequestException as e:
			logger.error(f"Network error during verification resend: {str(e)}")
			raise HTTPException(status_code=503, detail="Service temporarily unavailable")
