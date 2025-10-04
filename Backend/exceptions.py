class ServiceException(Exception):

    """
    To be inherited by service level exceptions and indicate exceptions that
    are to be handled at the service level itself.
    These exceptions shall not be counted as errors at the macroscopic level.
    eg: record not found, invalid parameter etc.
    """


class HandledException(ServiceException):
    status_code = 400
    message = "unable to process the request due to invalid syntax"

    def __init__(self, message, status_code=None, payload=None, show_payload=False, log_request_parameters=True, send_as_error_log=False):
        if message:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
        self.show_payload = show_payload
        self.log_request_parameters = log_request_parameters
        self.send_as_error_log = send_as_error_log

    def _type(self):
        return self.__class__.__name__

    def __str__(self):
        return self.message

    def to_dict(self):
        return_value = {"message": self.message}

        if self.show_payload and self.payload:
            return_value["data"] = {"error_payload": self.payload}

        return return_value


class InvalidParametersException(HandledException):
    def __init__(
        self,
        message="failed to validate data",
        status_code=400,
        payload=None,
        show_payload=True,
        log_request_parameters=True,
        send_as_error_log=False
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class InvalidValueException(HandledException):
    def __init__(
        self,
        message="Invalid value provided",
        status_code=400,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=False
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class ResourceNotFoundException(HandledException):
    def __init__(
        self,
        message="The requested data was not found",
        status_code=400,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=False
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class NotFoundException(HandledException):
    def __init__(
        self,
        message="requested resource not found",
        status_code=404,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=False
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class ConflictException(HandledException):
    def __init__(
        self,
        message="conflict with the current state of the target resource",
        status_code=409,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=True
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class UnprocessableContentException(HandledException):
    def __init__(
        self,
        message="unable to process the request due to semantic errors",
        status_code=422,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=True
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class DependencyException(HandledException):
    def __init__(
        self,
        message="request execution failed due to dependency failure",
        status_code=424,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=True
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class DatabaseException(HandledException):
    def __init__(
        self,
        message="database connection or query execution failure",
        status_code=500,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=True
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class ServerException(HandledException):
    def __init__(
        self,
        message="unable to process the current request",
        status_code=500,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=True
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class RequiredParameterException(HandledException):
    def __init__(
        self,
        message="Please provide complete details",
        status_code=400,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=False
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class PasswordException(HandledException):
    def __init__(
        self,
        message="Provided password is incorrect",
        status_code=400,
        payload=None,
        show_payload=False,
        log_request_parameters=False,
        send_as_error_log=False
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class UserBlockedException(HandledException):
    def __init__(
        self,
        message="User is Blocked. Please retry after 30 minutes",
        status_code=401,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=False
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class InvalidCredentialsException(HandledException):
    def __init__(
        self,
        message="Invalid username or password. Please try again",
        status_code=401,
        payload=None,
        show_payload=False,
        log_request_parameters=False,
        send_as_error_log=False
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class UnAuthorizedException(HandledException):
    def __init__(
        self,
        message="User not authorized",
        status_code=401,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=False
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class ForbiddenException(HandledException):
    def __init__(
        self,
        message="you have insufficient access rights",
        status_code=403,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=False
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class DuplicateUserException(HandledException):
    def __init__(
        self,
        message="User with provided details already exists",
        status_code=409,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=True
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class OTPException(HandledException):
    def __init__(
        self,
        message="Please provide correct OTP",
        status_code=400,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=False
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )


class MethodNotFoundException(HandledException):
    def __init__(
        self,
        message="Method not allowed",
        status_code=405,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
    ):
        super().__init__(
            message,
            status_code=status_code,
            payload=payload,
            show_payload=show_payload,
            log_request_parameters=log_request_parameters,
        )

class VariableTypeException(HandledException):
    def __init__(
        self,
        message="Variable type validation failed",
        status_code=400,
        payload=None,
        show_payload=False,
        log_request_parameters=True,
        send_as_error_log=False
    ):
        super().__init__(
            message, 
            status_code=status_code, 
            payload=payload, 
            show_payload=show_payload, 
            log_request_parameters=log_request_parameters,
            send_as_error_log=send_as_error_log
        )
