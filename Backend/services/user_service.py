
from firebase_admin import auth
from models.database import firestore
import requests
import logging
import asyncio

from models import schemas
from models.database import get_firestore_client
from constants import Collections, FirebaseAccessUrl, SendMailRequestTypes, RedirectUrl
from settings import API_KEY
from exceptions import DuplicateUserException, InvalidCredentialsException, UnAuthorizedException, ServerException, NotFoundException, ResourceNotFoundException, InvalidValueException, ForbiddenException
logger = logging.getLogger(__name__)


class UserService:
	def __init__(self, db=None):
		self.db = db or get_firestore_client()
		self.api_key = API_KEY
	def _handle_firebase_auth_error(self, e: Exception, operation: str):
		"""Centralized error handling for Firebase operations"""
		if isinstance(e, auth.EmailAlreadyExistsError):
			raise DuplicateUserException
		elif isinstance(e, auth.InvalidIdTokenError):
			raise InvalidCredentialsException
		elif isinstance(e, auth.ExpiredIdTokenError):
			raise UnAuthorizedException
		elif isinstance(e, requests.RequestException):
			logger.error(f"Network error during {operation}: {str(e)}")
			raise ServerException(message="Service temporarily unavailable", status_code=503)
		else:
			logger.error(f"Unexpected error during {operation}: {str(e)}", exc_info=True)
			raise ServerException


	async def signup(self, payload: schemas.SignupRequest):
		try:
			user_record = await asyncio.to_thread(
				auth.create_user,
				email=payload.email,
				password=payload.password,
				email_verified=False,
			)
		except Exception as e:
			self._handle_firebase_auth_error(e, "user signup")
		try:
			user_id = user_record.uid
			insert_data = {
				"user_id": user_id,
                "email": payload.email,
				"full_name": payload.full_name,
                "location": payload.location,
                "created_at": firestore.SERVER_TIMESTAMP
            }
			if payload.role_details:
				insert_data["role_details"] = dict(payload.role_details)
			await asyncio.to_thread(
				self.db.collection(Collections.USERS).document(user_id).set,
				insert_data
			)
			logger.info(f"User created successfully: {user_record.uid}")
		except Exception as error:
			# Rollback: Delete the Firebase user if Firestore creation fails
			logger.error(f"Failed to create user profile: {str(error)}")
			await asyncio.to_thread(auth.delete_user, user_record.uid)
			logger.warning(f"Rolled back Firebase user creation for: {payload.email}")
			raise ServerException(status_code=500, message="Failed to create user profile")
		return {"message": "Signup successful.", "success": True}
	

	async def login(self, payload: schemas.LoginRequest):

		params = {"key": self.api_key}
		json_payload = {
			"email": payload.email, 
			"password": payload.password, 
			"returnSecureToken": True
		}
		try:
			resp = await asyncio.to_thread(
				requests.post, 
				FirebaseAccessUrl.SIGN_IN_WITH_PASSWORD, 
				params=params, 
				json=json_payload
			)
		except Exception as e:
			logger.error(f"Network error during login: {str(e)}")
			self._handle_firebase_auth_error(e, "login")
			
		if resp.status_code != 200:
			raise InvalidCredentialsException(message="User does not exist or wrong password")
		login_info = resp.json()
		user_auth_token = login_info["idToken"]
		
		try:
			decoded_token = await asyncio.to_thread(auth.verify_id_token, user_auth_token)
			email_verified = decoded_token.get('email_verified')
			user_id = decoded_token.get('user_id')
			# TODO: check for allowing user to login only when verified.
			# if not email_verified:
			# 	raise ForbiddenException(
            #         status_code=403,
            #         detail="Please verify your email before logging in"
            #     )
			user_doc = await asyncio.to_thread(
				self.db.collection(Collections.USERS).document(user_id).get
			)
			if not user_doc.exists:
				raise InvalidCredentialsException(message="User profile missing")
			user_data = user_doc.to_dict()
			return {"data": {"user_auth_token": user_auth_token, "user_info": user_data}, "message": "login successful", "success": True}
		except Exception as e:
			self._handle_firebase_auth_error(e, "user login")


	async def get_current_user(self, token: str):
		try:
			decoded_token = await asyncio.to_thread(auth.verify_id_token, token)
			uid = decoded_token.get("uid")
			if not uid:
				logger.error("Missing localId in Firebase user data")
				raise InvalidCredentialsException(status_code=401, message="Invalid token - no UID found")

			user_doc = await asyncio.to_thread(
				self.db.collection(Collections.USERS).document(uid).get
			)
			if not user_doc.exists:
				logger.warning(f"User profile not found in Firestore for user_id: {uid}")
				raise NotFoundException(status_code=404, message="User profile not found")
			user_data = user_doc.to_dict()
			logger.info(f"Successfully retrieved user data for localId: {uid}")
			return user_data
		except Exception as error:
			logger.error(f"Unexpected error in get_current_user: {str(error)}", exc_info=True)
			raise UnAuthorizedException


	async def reset_password(self, payload: schemas.ResetPasswordRequest):
		params = {
			"key": self.api_key
        }
		data = {
			"requestType": SendMailRequestTypes.PASSWORD_RESET,
			"email": payload.email,
			"continueUrl": RedirectUrl.LOGIN
		}
		try:
			resp = await asyncio.to_thread(
				requests.post, 
				FirebaseAccessUrl.SEND_MAIL, 
				json=data, 
				params=params
			)
			if resp.status_code != 200:
				logger.error(f"Firebase API error: {resp.status_code} - {resp.text}")
				raise ResourceNotFoundException(
                    status_code=400,
                    message="Failed to send reset email. Please check the email and try again."
                )
			return {"message": "If this email is registered, you will receive a password reset email shortly.", "success": True}
		except Exception as e:
			logger.error(f"Network error during password reset: {str(e)}")
			self._handle_firebase_auth_error(e, "reset password")


	async def resend_verification(self, payload: schemas.ResendVerificationLink):
		try:
			decoded_token = await asyncio.to_thread(auth.verify_id_token, payload.token)
			user_email = decoded_token.get('email')
			email_verified = decoded_token.get('email_verified')
			if not user_email:
				raise InvalidValueException(message="ID Token does not contain a verifiable email address.")
			if email_verified:
				raise InvalidValueException(message="Email is already verified. Please proceed.")
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
			resp = await asyncio.to_thread(
				requests.post, 
				FirebaseAccessUrl.SEND_MAIL, 
				json=data, 
				params=params
			)
			if resp.status_code != 200:
				raise InvalidValueException(
                    status_code=400,
                    message="Failed to send send verification email. Please try again."
                )
			return {"message": "Verification email resent. Please check your inbox.", "success": True}
		except Exception as e:
			logger.error(f"Network error during verification resend: {str(e)}")
			self._handle_firebase_auth_error(e, "token verification")
