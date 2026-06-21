import os
import sqlite3
import datetime
import jwt
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
import hashlib
import secrets

router = APIRouter(prefix="/api/auth", tags=["auth"])

DB_PATH = "users.db"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "genji-secret-key-for-jwt-2025-secure")  # 32bytes+
ALGORITHM = "HS256"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        avatar TEXT DEFAULT 'genji'
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS password_resets (
        email TEXT NOT NULL,
        token TEXT NOT NULL,
        expires_at DATETIME NOT NULL
    )
    """)
    conn.commit()
    conn.close()

init_db()

# Pydantic models
class UserRegister(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginRequest(BaseModel):
    email: EmailStr
    token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str

class UpdateProfileRequest(BaseModel):
    avatar: str

# Utility functions
def hash_password(password: str) -> str:
    # Generate a 16-byte salt as a hex string
    salt = secrets.token_hex(16)
    # Hash using PBKDF2-HMAC-SHA256 with 100,000 iterations
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt.encode('utf-8'), 
        100000
    ).hex()
    return f"{salt}:{pw_hash}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, pw_hash = hashed.split(":")
        new_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000
        ).hex()
        return secrets.compare_digest(pw_hash, new_hash)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: datetime.timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user_email(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication token is missing. Please log in.")
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token.")
        return email
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token has expired or is invalid.")

# Endpoints
@router.post("/register")
async def register(user: UserRegister):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check for duplicates
    cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="This email address is already registered.")
    
    hashed = hash_password(user.password)
    try:
        cursor.execute(
            "INSERT INTO users (email, hashed_password, avatar) VALUES (?, ?, 'genji')",
            (user.email, hashed)
        )
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"User registration failed: {e}")
        
    conn.close()
    return {"message": "User registration completed."}

@router.post("/login")
async def login(user: UserLogin):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT email, hashed_password, avatar FROM users WHERE email = ?", (user.email,))
    db_user = cursor.fetchone()
    conn.close()
    
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect email address or password.")
    
    token = create_access_token(data={"sub": db_user["email"]})
    return {
        "token": token,
        "user": {
            "email": db_user["email"],
            "avatar": db_user["avatar"]
        }
    }

@router.post("/google")
async def google_login(request: GoogleLoginRequest):
    # Verify Google authentication (in production, verify the token using the google-auth library,
    # here, if the token exists, we consider it successful and create/login the user with the email)
    if not request.token:
        raise HTTPException(status_code=400, detail="Google authentication token is invalid.")
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT email, avatar FROM users WHERE email = ?", (request.email,))
    db_user = cursor.fetchone()
    
    if not db_user:
        # Register new user via Google
        import uuid
        random_password = hash_password(str(uuid.uuid4()))
        try:
            cursor.execute(
                "INSERT INTO users (email, hashed_password, avatar) VALUES (?, ?, 'genji')",
                (request.email, random_password)
            )
            conn.commit()
            cursor.execute("SELECT email, avatar FROM users WHERE email = ?", (request.email,))
            db_user = cursor.fetchone()
        except Exception as e:
            conn.close()
            raise HTTPException(status_code=500, detail=f"User registration for Google login failed: {e}")
            
    conn.close()
    token = create_access_token(data={"sub": db_user["email"]})
    return {
        "token": token,
        "user": {
            "email": db_user["email"],
            "avatar": db_user["avatar"]
        }
    }

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (request.email,))
    if not cursor.fetchone():
        conn.close()
        # For security, return success message even if not found (but log token for development testing)
        return {"message": "Password reset email sent (if registered)."}
        
    import random
    reset_token = "".join(random.choices("0123456789", k=6)) # 6-digit code
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    
    cursor.execute("DELETE FROM password_resets WHERE email = ?", (request.email,))
    cursor.execute(
        "INSERT INTO password_resets (email, token, expires_at) VALUES (?, ?, ?)",
        (request.email, reset_token, expires_at)
    )
    conn.commit()
    conn.close()
    
    # Output token for development/testing (ensure demo works by including it in console and response)
    print(f"[Password Reset Request] Email: {request.email}, Reset Token: {reset_token}")
    return {
        "message": "Password reset email sent (token displayed below for demo).",
        "demo_token": reset_token # Return for easier demo verification
    }

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT token, expires_at FROM password_resets WHERE email = ? ORDER BY expires_at DESC LIMIT 1",
        (request.email,)
    )
    db_reset = cursor.fetchone()
    
    if not db_reset:
        conn.close()
        raise HTTPException(status_code=400, detail="Password reset request not found.")
        
    expires_at = datetime.datetime.strptime(db_reset["expires_at"].split(".")[0], "%Y-%m-%d %H:%M:%S")
    if db_reset["token"] != request.token or datetime.datetime.utcnow() > expires_at:
        conn.close()
        raise HTTPException(status_code=400, detail="Reset code is invalid or has expired.")
        
    # Update password
    hashed = hash_password(request.new_password)
    cursor.execute("UPDATE users SET hashed_password = ? WHERE email = ?", (hashed, request.email))
    cursor.execute("DELETE FROM password_resets WHERE email = ?", (request.email,))
    conn.commit()
    conn.close()
    
    return {"message": "Password updated successfully. Please log in."}

@router.get("/me")
async def get_me(email: str = Depends(get_current_user_email)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT email, avatar FROM users WHERE email = ?", (email,))
    db_user = cursor.fetchone()
    conn.close()
    
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    return {
        "user": {
            "email": db_user["email"],
            "avatar": db_user["avatar"]
        }
    }

@router.post("/profile")
async def update_profile(profile: UpdateProfileRequest, email: str = Depends(get_current_user_email)):
    if profile.avatar not in ["genji", "mikado", "murasaki", "rokujo"]:
        raise HTTPException(status_code=400, detail="Invalid avatar image.")
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET avatar = ? WHERE email = ?", (profile.avatar, email))
    conn.commit()
    conn.close()
    
    return {"message": "Profile updated successfully.", "avatar": profile.avatar}
