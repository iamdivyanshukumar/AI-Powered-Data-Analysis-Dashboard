from werkzeug.security import generate_password_hash, check_password_hash
import hashlib
import os

def safe_generate_password_hash(password):
    """
    Generate password hash with scrypt fallback for compatibility.
    """
    try:
        # Force use of pbkdf2 method to avoid scrypt issues
        return generate_password_hash(password, method='pbkdf2:sha256')
    except Exception as e:
        print(f"Password hash fallback activated: {e}")
        # Ultimate fallback - create our own pbkdf2 implementation
        salt = os.urandom(16).hex()
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 150000)
        return f"pbkdf2:sha256:150000${salt}${pwd_hash.hex()}"

def safe_check_password_hash(pwhash, password):
    """
    Check password hash with compatibility handling.
    """
    try:
        return check_password_hash(pwhash, password)
    except Exception as e:
        print(f"Password check fallback activated: {e}")
        # Handle fallback hash format
        if pwhash.startswith('pbkdf2:sha256:150000$'):
            try:
                parts = pwhash.split('$')
                if len(parts) == 3:
                    salt = parts[1]
                    stored_hash = parts[2]
                    new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 150000).hex()
                    return stored_hash == new_hash
            except Exception as e:
                print(f"Fallback password check failed: {e}")
                return False
        return False