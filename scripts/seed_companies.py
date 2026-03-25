import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from database import db
from models import Company

app = create_app()

def seed_companies():
    with app.app_context():
        companies = [
            {
                "name": "Cognizant",
                "location": "Teaneck, NJ",
                "sector": "IT Services",
                "difficulty": "Medium",
                "description": "American multinational information technology services and consulting company.",
                "website_url": "https://cognizant.com",
                "exam_pattern": [
                    {"section": "Aptitude", "questions": 25, "duration": "35 mins", "difficulty": "Easy"},
                    {"section": "Verbal", "questions": 20, "duration": "20 mins", "difficulty": "Easy"},
                    {"section": "Logical", "questions": 35, "duration": "45 mins", "difficulty": "Medium"},
                    {"section": "Automata Fix", "questions": 7, "duration": "20 mins", "difficulty": "Medium"}
                ],
                "hiring_process": [
                    {"step": "GenC Assessment", "duration": "1 week"},
                    {"step": "Technical Interview", "duration": "1 week"},
                    {"step": "HR Discussion", "duration": "3 days"}
                ]
            },
            {
                "name": "TCS",
                "location": "Mumbai, India",
                "sector": "IT Services",
                "difficulty": "Easy",
                "description": "Part of the Tata group, India's largest multinational business group.",
                "website_url": "https://tcs.com",
                "exam_pattern": [
                    {"section": "Numerical Ability", "questions": 26, "duration": "40 mins", "difficulty": "Medium"},
                    {"section": "Verbal Ability", "questions": 24, "duration": "30 mins", "difficulty": "Easy"},
                    {"section": "Reasoning Ability", "questions": 30, "duration": "50 mins", "difficulty": "Medium"},
                    {"section": "Coding", "questions": 2, "duration": "45 mins", "difficulty": "Medium"}
                ],
                "hiring_process": [
                    {"step": "NQT Exam", "duration": "2 weeks"},
                    {"step": "Technical Round", "duration": "1 week"},
                    {"step": "MR Round", "duration": "3 days"},
                    {"step": "HR Round", "duration": "3 days"}
                ]
            },
            {
                "name": "Zoho",
                "location": "Chennai, India",
                "sector": "Software",
                "difficulty": "Hard",
                "description": "Indian multinational technology company that makes web-based business tools.",
                "website_url": "https://zoho.com",
                "exam_pattern": [
                    {"section": "C Programming", "questions": 15, "duration": "30 mins", "difficulty": "Hard"},
                    {"section": "Aptitude", "questions": 10, "duration": "20 mins", "difficulty": "Medium"},
                    {"section": "Coding", "questions": 5, "duration": "90 mins", "difficulty": "Hard"}
                ],
                "hiring_process": [
                    {"step": "Written Test", "duration": "1 day"},
                    {"step": "Machine Coding", "duration": "1 day"},
                    {"step": "Advanced Coding", "duration": "1 day"},
                    {"step": "Tech HR", "duration": "1 day"}
                ]
            }
        ]

        for comp_data in companies:
            if not Company.query.filter_by(name=comp_data['name']).first():
                company = Company(**comp_data)
                db.session.add(company)
                print(f"Adding company: {comp_data['name']}")
        
        db.session.commit()
        print("Seeding complete!")

if __name__ == '__main__':
    seed_companies()
