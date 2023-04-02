from datetime import datetime
import re
from dateutil.parser import parse


class NotEmtyOrWhitespased(str):

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not v or re.match(r'^\s*$', v):
            raise ValueError(
                'Строка не должна быть пустой или состоять только из пробелов')
        return v.strip()


class ISODateTime(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not v:
            raise ValueError('Значение не должно быть пустым')
        if isinstance(v, datetime):
            current_tz = datetime.now().astimezone().tzinfo
            local_time = v.astimezone(current_tz)
            return local_time.isoformat()
        try:
            return parse(v)
        except ValueError:
            raise ValueError('Значение не соответствует формату ISO 8601')

class ISO8601DatePattern(str):
    '''pattern "yyyy-MM-dd"'''
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not v:
            raise ValueError('Значение не должно быть пустым')
        if isinstance(v, datetime):
            current_tz = datetime.now().astimezone().tzinfo
            local_time = v.astimezone(current_tz)
            return local_time.isoformat()
        try:
            return datetime.strptime(v, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError('Значение не соответствует формату ISO 8601 (pattern "yyyy-MM-dd")')
