# router.py
from fastapi import APIRouter
from groq import Groq
import os
from dotenv import load_dotenv


load_dotenv()
groq_key = os.getenv("GROQ_KEY")
client = Groq(api_key=groq_key)
