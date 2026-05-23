# logging decorator
from functools import wraps

def log_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling: {func.__name__}") #pre execution log
        result = func(*args, **kwargs)
        print(f"Result: {result}")
        return result
    return wrapper

class Fintech:
    def __init__(self, name):
        self.name = name

    @log_call
    def __str__(self):
        return f"Fintech Company: {self.name}"
    


#validating decorator
from functools import wraps

def log_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling: {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Result: {result}")
        return result
    return wrapper

class Fintech:
    def __init__(self, name):
        self.name = name

    @log_call
    def __str__(self):
        return f"Fintech Company: {self.name}"