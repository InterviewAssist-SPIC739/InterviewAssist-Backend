import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from admin_manager import create_admin_user
import sys

if __name__ == "__main__":
    email = "admin_test@example.com"
    password = "adminpassword123"
    create_admin_user(email, password)
    print(f"Test admin created: {email}")
