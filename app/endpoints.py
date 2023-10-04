from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from .models import User, Post
from .schemas import UserCreateSchema, UserLoginSchema, PostCreateSchema
from .authentication import validate_token,get_password_hash,verify_password,create_access_token
from .cache import response_cache
from .database import get_db
router = APIRouter()


# Signup Endpoint
@router.post("/signup", response_model=dict)
def signup(user: UserCreateSchema, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User registered successfully"}


# Login Endpoint
@router.post("/login", response_model=dict)
def login(user: UserLoginSchema, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user is None or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# AddPost Endpoint
@router.post("/addPost", response_model=dict)
def add_post(
    post_data: PostCreateSchema,
    token: dict = Depends(validate_token),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    # Check payload size
    if file.content_length > 1_000_000:  # 1 MB limit
        raise HTTPException(status_code=400, detail="File size too large")

    user_email = token.get("sub")

    db_user = db.query(User).filter(User.email == user_email).first()
    if db_user:
        new_post = Post(text=post_data.text, user_id=db_user.id)
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        return {"postID": new_post.id}
    else:
        raise HTTPException(status_code=404, detail="User not found")


# GetPosts Endpoint with Response Caching
@router.get("/getPosts", response_model=list)
def get_posts(token: dict = Depends(validate_token), db: Session = Depends(get_db)):
    user_email = token.get("sub")

    # Check if cached data is available
    cached_posts = response_cache.get(user_email)
    if cached_posts:
        return cached_posts

    # Fetch posts from the database
    db_user = db.query(User).filter(User.email == user_email).first()
    if db_user:
        user_posts = db.query(Post).filter(Post.user_id == db_user.id).all()

        # Cache the posts for 5 minutes
        response_cache[user_email] = user_posts
        return user_posts
    else:
        raise HTTPException(status_code=404, detail="User not found")


# DeletePost Endpoint
@router.delete("/deletePost", response_model=dict)
def delete_post(
    post_id: int,
    token: dict = Depends(validate_token),
    db: Session = Depends(get_db),
):
    user_email = token.get("sub")

    # Check if the post belongs to the user
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    user = db.query(User).filter(User.email == user_email).first()
    if user and post.user_id == user.id:
        db.delete(post)
        db.commit()
        return {"message": "Post deleted successfully"}
    else:
        raise HTTPException(
            status_code=403, detail="Unauthorized to delete this post")
