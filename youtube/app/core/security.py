from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['argon2'], deprecated="auto")

def hash(password: str):
    return pwd_context.hash(password)

def verify_pass(given_pass, hashed_pass):
    return pwd_context.verify(given_pass, hashed_pass)