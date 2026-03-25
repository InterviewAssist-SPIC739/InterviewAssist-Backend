import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import models
from app import create_app
from database import db
from datetime import datetime
import json

app = create_app()

print("NOTE: Use seed_all.py for the full dataset (9 companies).")
print("This script (seed_db.py) only contains a minimal subset.")

def seed_data():
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()

        print("Creating users...")
        # Create Admin
        admin = models.Admin(
            email="admin@example.com",
            role="Admin"
        )
        admin.set_password("admin123")
        db.session.add(admin)

        # Create Student
        student = models.User(
            first_name="Sathvik",
            last_name="User",
            email="student@example.com",
            role="Student",
            has_completed_profile=True
        )
        student.set_password("student123")
        db.session.add(student)

        # Create Alumni
        alumni = models.User(
            first_name="Rahul",
            last_name="Sharma",
            email="alumni@example.com",
            role="Alumni",
            has_completed_profile=True
        )
        alumni.set_password("alumni123")
        db.session.add(alumni)

        db.session.commit()

        print("Creating companies and experiences...")
        
        companies_data = [
            {
                "name": "Cognizant",
                "location": "Teaneck, NJ",
                "sector": "IT Services",
                "difficulty": "Medium",
                "description": "American multinational information technology services and consulting company.",
                "website_url": "https://cognizant.com",
                "exam_pattern": [
                    {"name": "Aptitude", "questions": 25, "time": "35 mins", "level": "Easy"},
                    {"name": "Verbal", "questions": 20, "time": "20 mins", "level": "Easy"},
                    {"name": "Logical", "questions": 35, "time": "45 mins", "level": "Medium"},
                    {"name": "Automata Fix", "questions": 7, "time": "20 mins", "level": "Medium"}
                ],
                "hiring_process": [
                    {"title": "GenC Assessment", "duration": "1 week"},
                    {"title": "Technical Interview", "duration": "1 week"},
                    {"title": "HR Discussion", "duration": "3 days"}
                ],
                "experiences": [
                    {
                        "user_id": alumni.id,
                        "user_role": "Programmer Analyst",
                        "difficulty": "Medium",
                        "is_selected": True,
                        "work_mode": "Onsite",
                        "candidate_type": "fresher",
                        "my_experience": "My journey with Cognizant started with the on-campus drive for the GenC profile...",
                        "brief": "CSE Grad, 2024 Batch.",
                        "application_process": "On-campus drive.",
                        "interview_rounds": [
                            {"title": "Round 1: Aptitude", "duration": "Quantitative & Logical"},
                            {"title": "Round 2: Technical", "duration": "Java Basics & Project"}
                        ],
                        "technical_questions": ["Explain Polymorphism.", "ArrayList vs LinkedList."],
                        "behavioral_questions": ["Relocation?"],
                        "mistakes": ["Got stuck in logic."],
                        "preparation_strategy": {"Resources": ["IndiaBix"], "Focus": ["Aptitude speed"]},
                        "final_advice": ["Focus on speed."],
                        "is_approved": True
                    }
                ],
                "questions": [
                    {
                        "question_text": "What is the difference between GenC and GenC Next?",
                        "asked_by": "Suresh K",
                        "answers": [
                            {
                                "answer_text": "GenC is standard (4LPA), GenC Next is higher (6.75LPA).",
                                "answerer_name": "Rahul Sharma",
                                "answerer_role": "PAT at Cognizant"
                            }
                        ]
                    }
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
                    {"name": "Numerical", "questions": 26, "time": "40 mins", "level": "Medium"},
                    {"name": "Verbal", "questions": 24, "time": "30 mins", "level": "Easy"},
                    {"name": "Reasoning", "questions": 30, "time": "50 mins", "level": "Medium"}
                ],
                "hiring_process": [
                    {"title": "NQT Exam", "duration": "2 weeks"},
                    {"title": "Technical Round", "duration": "1 week"}
                ],
                "experiences": [
                    {
                        "user_id": student.id,
                        "user_role": "System Engineer",
                        "difficulty": "Easy",
                        "is_selected": True,
                        "work_mode": "Onsite",
                        "candidate_type": "fresher",
                        "my_experience": "TCS conducts NQT...",
                        "is_approved": True
                    }
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
                    {"name": "C Programming", "questions": 15, "time": "30 mins", "level": "Hard"}
                ],
                "hiring_process": [
                    {"title": "Written Test", "duration": "1 day"},
                    {"title": "Machine Coding", "duration": "1 day"}
                ],
                "experiences": [],
                "questions": []
            }
        ]

        for c_data in companies_data:
            company = models.Company(
                name=c_data["name"],
                location=c_data["location"],
                sector=c_data["sector"],
                difficulty=c_data.get("difficulty", "Medium"),
                description=c_data.get("description"),
                website_url=c_data.get("website_url"),
                exam_pattern=c_data.get("exam_pattern"),
                hiring_process=c_data.get("hiring_process")
            )
            db.session.add(company)
            db.session.flush() # To get company.id

            for exp_data in c_data.get("experiences", []):
                experience = models.InterviewExperience(
                    user_id=exp_data["user_id"],
                    company_id=company.id,
                    user_role=exp_data["user_role"],
                    difficulty=exp_data["difficulty"],
                    is_selected=exp_data["is_selected"],
                    work_mode=exp_data["work_mode"],
                    candidate_type=exp_data["candidate_type"],
                    my_experience=exp_data["my_experience"],
                    brief=exp_data.get("brief"),
                    application_process=exp_data.get("application_process"),
                    interview_rounds=exp_data.get("interview_rounds"),
                    technical_questions=exp_data.get("technical_questions"),
                    behavioral_questions=exp_data.get("behavioral_questions"),
                    mistakes=exp_data.get("mistakes"),
                    preparation_strategy=exp_data.get("preparation_strategy"),
                    final_advice=exp_data.get("final_advice"),
                    is_approved=exp_data.get("is_approved", False)
                )
                db.session.add(experience)

            for q_data in c_data.get("questions", []):
                question = models.CompanyQuestion(
                    company_id=company.id,
                    question_text=q_data["question_text"],
                    asked_by_name=q_data["asked_by"]
                )
                db.session.add(question)
                db.session.flush()

                for a_data in q_data.get("answers", []):
                    answer = models.QuestionAnswer(
                        question_id=question.id,
                        answer_text=a_data["answer_text"],
                        answerer_name=a_data["answerer_name"],
                        answerer_role=a_data["answerer_role"],
                        is_verified_alumni=True
                    )
                    db.session.add(answer)

        db.session.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    seed_data()
