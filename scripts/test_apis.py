import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import json
import random
import string

BASE_URL = "http://localhost:5000"

def generate_random_email():
    return f"test_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}@example.com"

def test_health():
    print("\n--- Testing Health Check ---")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_auth():
    print("\n--- Testing Registration and Login ---")
    email = generate_random_email()
    password = "password123"
    
    # Register
    reg_data = {
        "first_name": "Test",
        "last_name": "User",
        "email": email,
        "password": password,
        "role": "Student"
    }
    reg_response = requests.post(f"{BASE_URL}/register", json=reg_data)
    print(f"Register Status: {reg_response.status_code}")
    if reg_response.status_code != 201:
        print(f"Register Error: {reg_response.text}")
        return None

    # Login
    login_data = {
        "email": email,
        "password": password,
        "role": "Student"
    }
    login_response = requests.post(f"{BASE_URL}/login", json=login_data)
    print(f"Login Status: {login_response.status_code}")
    if login_response.status_code == 200:
        token = login_response.json().get("access_token")
        user_id = login_response.json().get("user", {}).get("id")
        return token, user_id
    else:
        print(f"Login Error: {login_response.text}")
        return None

def test_companies(token):
    print("\n--- Testing Companies API ---")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/companies", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        companies = response.json()
        print(f"Fetched {len(companies)} companies.")
        if companies:
            print(f"First company: {companies[0].get('name')}")
    return response.status_code == 200

def test_notifications(token):
    print("\n--- Testing Notifications API ---")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/notifications", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        notifications = response.json()
        print(f"Fetched {len(notifications)} notifications.")
    return response.status_code == 200

def test_profile(token, user_id):
    print("\n--- Testing Profile APIs ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get profile
    get_res = requests.get(f"{BASE_URL}/profile/{user_id}", headers=headers)
    print(f"Get Profile Status: {get_res.status_code}")
    
    # Complete profile
    profile_data = {
        "user_id": user_id,
        "phone_number": "1234567890",
        "major": "Computer Science",
        "expected_grad_year": "2025",
        "current_year": "Third Year",
        "bio": "Test biography",
        "linkedin_url": "https://linkedin.com/in/test"
    }
    comp_res = requests.post(f"{BASE_URL}/complete-profile", json=profile_data, headers=headers)
    print(f"Complete Profile Status: {comp_res.status_code}")
    return comp_res.status_code == 200

def test_experience_flow(token, admin_token):
    print("\n--- Testing Experience Flow (Submit -> Approve -> Helpful -> Save -> Report) ---")
    headers = {"Authorization": f"Bearer {token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Get a company ID
    comp_res = requests.get(f"{BASE_URL}/companies", headers=headers)
    if comp_res.status_code != 200 or not comp_res.json():
        print("Failed to get companies")
        return False
    company_id = comp_res.json()[0]['id']
    
    # 1. Submit Experience
    exp_data = {
        "company_id": company_id,
        "user_role": "Software Intern",
        "difficulty": "Medium",
        "is_selected": True,
        "work_mode": "Onsite",
        "candidate_type": "fresher",
        "my_experience": "Great interview process.",
        "brief": "Round 1 was coding, Round 2 was HR.",
        "interview_rounds": ["Coding", "Technical", "HR"]
    }
    sub_res = requests.post(f"{BASE_URL}/experiences", json=exp_data, headers=headers)
    print(f"Submit Experience Status: {sub_res.status_code}")
    if sub_res.status_code not in [200, 201]:
        return False
    experience_id = sub_res.json().get('id')
    
    # 2. Admin Approve Experience
    rev_res = requests.put(f"{BASE_URL}/experiences/{experience_id}/review", json={"status": "approved"}, headers=admin_headers)
    print(f"Admin Approve Status: {rev_res.status_code}")
    
    # 3. Toggle Helpful
    help_res = requests.post(f"{BASE_URL}/experiences/{experience_id}/helpful", headers=headers)
    print(f"Toggle Helpful Status: {help_res.status_code}")
    
    # 4. Toggle Save
    save_res = requests.post(f"{BASE_URL}/experiences/{experience_id}/save", headers=headers)
    print(f"Toggle Save Status: {save_res.status_code}")
    
    # 5. Report Experience
    rep_res = requests.post(f"{BASE_URL}/experiences/{experience_id}/report", json={"reason": "Incorrect info"}, headers=headers)
    print(f"Report Experience Status: {rep_res.status_code}")
    
    return True

def test_questions_flow(token, admin_token):
    print("\n--- Testing Questions Flow (Ask -> Answer -> Delete) ---")
    headers = {"Authorization": f"Bearer {token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    comp_res = requests.get(f"{BASE_URL}/companies", headers=headers)
    company_id = comp_res.json()[0]['id']
    
    # 1. Ask Question
    q_res = requests.post(f"{BASE_URL}/companies/{company_id}/questions", json={"question_text": "Tech stack?"}, headers=headers)
    print(f"Ask Question Status: {q_res.status_code}")
    if q_res.status_code not in [200, 201]: return False
    question_id = q_res.json().get('question', {}).get('id')
    
    # 2. Answer Question (Requires Alumni or Admin)
    # Using admin token to answer
    ans_res = requests.post(f"{BASE_URL}/questions/{question_id}/answers", json={"answer_text": "React and Python."}, headers=admin_headers)
    print(f"Answer Question Status: {ans_res.status_code}")
    
    return True

def get_admin_token():
    email = "admin_test@example.com"
    password = "adminpassword123"
    login_data = {"email": email, "password": password, "role": "Admin"}
    response = requests.post(f"{BASE_URL}/login", json=login_data)
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

if __name__ == "__main__":
    if test_health():
        admin_token = get_admin_token()
        if not admin_token:
            print("Failed to get Admin token. Run create_test_admin.py first.")
        
        auth_info = test_auth()
        if auth_info:
            token, user_id = auth_info
            
            # Run Comprehensive Tests
            test_companies(token)
            test_notifications(token)
            test_profile(token, user_id)
            
            if admin_token:
                test_experience_flow(token, admin_token)
                test_questions_flow(token, admin_token)
                
                # Test Admin Dashboard and Upgrades
                headers = {"Authorization": f"Bearer {admin_token}"}
                stats_res = requests.get(f"{BASE_URL}/admin/dashboard-stats", headers=headers)
                print(f"Admin Dashboard Status: {stats_res.status_code}")
                upgrades_res = requests.get(f"{BASE_URL}/admin/pending-upgrades", headers=headers)
                print(f"Pending Upgrades Status: {upgrades_res.status_code}")
                reports_res = requests.get(f"{BASE_URL}/admin/reports", headers=headers)
                print(f"Admin Reports Status: {reports_res.status_code}")
            
        else:
            print("Auth test failed, skipping subsequent tests.")
    else:
        print("Health check failed, skipping tests.")
