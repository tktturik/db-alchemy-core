
class DBConnectException(Exception):
    pass

class NotFoundError(DBConnectException):
    pass

class EmptyFilterError(DBConnectException):
    pass

class InvalidFieldError(DBConnectException):
    pass

class EmptyValueError(DBConnectException):
    pass

class UnknowAggregationFunc(DBConnectException):
    pass