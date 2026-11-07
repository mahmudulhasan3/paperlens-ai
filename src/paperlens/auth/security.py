from pwdlib import PasswordHash

# Auth step: pwdlib with its recommended hasher, which is argon2
password_hash = PasswordHash.recommended()


# Auth step: turn a plain password into a hash that is safe to store
def hash_password(password):
    return password_hash.hash(password)


# Auth step: check a plain password against a stored hash (password first, hash second)
def verify_password(password, hashed):
    return password_hash.verify(password, hashed)
