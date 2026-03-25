import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from database import db
from models import Admin
import sys

def create_admin_user(email, password):
    app = create_app()
    with app.app_context():
        # Check if admin already exists
        existing = Admin.query.filter_by(email=email).first()
        if existing:
            print(f"\n[!] Error: Admin with email {email} already exists.")
            return

        new_admin = Admin(email=email)
        new_admin.set_password(password)
        
        try:
            db.session.add(new_admin)
            db.session.commit()
            print(f"\n[+] Success: Admin user {email} created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"\n[!] Error creating admin: {e}")

def update_admin_password(email, new_password):
    app = create_app()
    with app.app_context():
        admin = Admin.query.filter_by(email=email).first()
        
        if not admin:
            print(f"\n[!] Error: Admin with email {email} not found.")
            return

        admin.set_password(new_password)
        
        try:
            db.session.commit()
            print(f"\n[+] Success: Password for admin {email} has been updated!")
        except Exception as e:
            db.session.rollback()
            print(f"\n[!] Error updating password: {e}")

def main_menu():
    while True:
        print("\n" + "="*30)
        print("   ADMIN MANAGEMENT TOOL")
        print("="*30)
        print("1. Create New Admin")
        print("2. Update Existing Admin Password")
        print("3. Exit")
        
        choice = input("\nSelect an option (1-3): ").strip()
        
        if choice == '1':
            print("\n--- Create New Admin ---")
            email = input("Enter Email: ").strip()
            password = input("Enter Password: ").strip()
            if email and password:
                create_admin_user(email, password)
            else:
                print("\n[!] Error: Email and Password cannot be empty.")
                
        elif choice == '2':
            print("\n--- Update Admin Password ---")
            email = input("Enter Admin Email: ").strip()
            password = input("Enter New Password: ").strip()
            if email and password:
                update_admin_password(email, password)
            else:
                print("\n[!] Error: Email and Password cannot be empty.")
                
        elif choice == '3':
            print("\nExiting Admin Management Tool. Goodbye!")
            break
        else:
            print("\n[!] Invalid choice. Please try again.")

if __name__ == '__main__':
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. Exiting...")
        sys.exit(0)
