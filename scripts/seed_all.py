import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import models
from app import create_app
from database import db
from datetime import datetime
import random

app = create_app()

def seed_all(reset=False):
    with app.app_context():
        if reset:
            print("Resetting database...")
            db.drop_all()
            db.create_all()
        
        print("Seeding Users...")
        # 1. Admin
        admin = models.Admin.query.filter_by(email="admin@example.com").first()
        if not admin:
            admin = models.Admin(email="admin@example.com", role="Admin")
            admin.set_password("admin123")
            db.session.add(admin)
            print("Added Admin: admin@example.com")

        # 2. Sathvik (Student)
        student = models.User.query.filter_by(email="student@example.com").first()
        if not student:
            student = models.User(
                first_name="Sathvik",
                last_name="User",
                email="student@example.com",
                role="Student",
                has_completed_profile=True
            )
            student.set_password("student123")
            db.session.add(student)
            print("Added Student: student@example.com")

        # 3. Rahul (Alumni)
        alumni = models.User.query.filter_by(email="alumni@example.com").first()
        if not alumni:
            alumni = models.User(
                first_name="Rahul",
                last_name="Sharma",
                email="alumni@example.com",
                role="Alumni",
                has_completed_profile=True
            )
            alumni.set_password("alumni123")
            db.session.add(alumni)
            print("Added Alumni: alumni@example.com")

        # 4. Mock Alumni for additional data
        mock_alumni = models.User.query.filter_by(email="alumni@mock.com").first()
        if not mock_alumni:
            mock_alumni = models.User(
                first_name="Verified",
                last_name="Alumni",
                email="alumni@mock.com",
                role="Alumni",
                has_completed_profile=True
            )
            mock_alumni.set_password("password123")
            db.session.add(mock_alumni)
            print("Added Mock Alumni: alumni@mock.com")

        db.session.commit()

        # Companies from seed_mock_data.py (The most complete set)
        mock_companies = [
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
                        "user_role": "Programmer Analyst",
                        "difficulty": "Medium",
                        "is_selected": True,
                        "work_mode": "Onsite",
                        "candidate_type": "fresher",
                        "brief": "CSE Grad, 2024 Batch.",
                        "application_process": "On-campus drive.",
                        "my_experience": "My journey with Cognizant started with the on-campus drive for the GenC profile...",
                        "interview_rounds": [
                            {"title": "Round 1: Aptitude", "duration": "Quantitative & Logical"},
                            {"title": "Round 2: Technical", "duration": "Java Basics & Project"}
                        ],
                        "technical_questions": [
                            "Explain Polymorphism with real-world example.",
                            "Difference between ArrayList and LinkedList."
                        ],
                        "behavioral_questions": ["Are you willing to relocate?"],
                        "mistakes": ["Got stuck in one logical reasoning question."],
                        "preparation_strategy": {
                            "Resources": ["IndiaBix", "FacePrep"],
                            "Focus": ["Aptitude speed"]
                        },
                        "final_advice": ["Focus on speed for aptitude."]
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
                    {"name": "Numerical Ability", "questions": 26, "time": "40 mins", "level": "Medium"},
                    {"name": "Verbal Ability", "questions": 24, "time": "30 mins", "level": "Easy"},
                    {"name": "Reasoning Ability", "questions": 30, "time": "50 mins", "level": "Medium"},
                    {"name": "Coding", "questions": 2, "time": "45 mins", "level": "Medium"}
                ],
                "hiring_process": [
                    {"title": "NQT Exam", "duration": "2 weeks"},
                    {"title": "Technical Round", "duration": "1 week"},
                    {"title": "MR Round", "duration": "3 days"},
                    {"title": "HR Round", "duration": "3 days"}
                ],
                "experiences": [
                    {
                        "user_role": "System Engineer",
                        "difficulty": "Easy",
                        "is_selected": True,
                        "work_mode": "Onsite",
                        "candidate_type": "fresher",
                        "brief": "IT Graduate.",
                        "application_process": "Applied via TCS NextStep.",
                        "my_experience": "TCS conducts its National Qualifier Test (NQT) which is the gateway for multiple roles like Ninja and Digital...",
                        "interview_rounds": [
                            {"title": "Round 1: NQT", "duration": "National Qualifier Test"},
                            {"title": "Round 2: TR+MR+HR", "duration": "Combined interview"}
                        ],
                        "technical_questions": [
                            "Write a query to find the second highest salary.",
                            "What are pointers in C?"
                        ],
                        "behavioral_questions": ["Why TCS?"],
                        "mistakes": [],
                        "preparation_strategy": {
                            "Resources": ["TCS NQT past papers"],
                            "Focus": ["NQT Score"]
                        },
                        "final_advice": ["Score high in NQT for Digital profile."]
                    }
                ]
            },
            {
                "name": "Blackstraw",
                "location": "Chennai, India",
                "sector": "AI Solutions",
                "difficulty": "Hard",
                "description": "AI and Analytics solutions provider. Focuses on Computer Vision and NLP.",
                "website_url": "https://blackstraw.ai",
                "exam_pattern": [
                    {"name": "Aptitude", "questions": 20, "time": "30 mins", "level": "Medium"},
                    {"name": "Python/C++", "questions": 20, "time": "30 mins", "level": "Hard"},
                    {"name": "Coding", "questions": 3, "time": "90 mins", "level": "Hard"}
                ],
                "hiring_process": [
                    {"title": "Coding Round", "duration": "1 week"},
                    {"title": "Technical Zoom", "duration": "1 week"},
                    {"title": "Project Task", "duration": "1 week"}
                ],
                "experiences": [
                    {
                        "user_role": "AI Engineer",
                        "difficulty": "Hard",
                        "is_selected": True,
                        "work_mode": "Hybrid",
                        "candidate_type": "experienced",
                        "brief": "Data Scientist with 2 years xp.",
                        "application_process": "LinkedIn Easy Apply.",
                        "my_experience": "Blackstraw is very particular about mathematical foundations...",
                        "interview_rounds": [
                            {"title": "Round 1: Coding", "duration": "Data Structures & AI Math"},
                            {"title": "Round 2: API Task", "duration": "Build a serving layer"}
                        ],
                        "technical_questions": [
                            "Explain Backpropagation calculus.",
                            "Optimize a Python script using Multiprocessing."
                        ],
                        "behavioral_questions": ["Describe a time you optimized a model."],
                        "mistakes": ["Forgot to handle exceptions in the API."],
                        "preparation_strategy": {
                            "Resources": ["Andrew Ng Coursera", "FastAI"],
                            "Focus": ["Deep Learning fundamentals"]
                        },
                        "final_advice": ["Don't rely just on libraries, know the math."]
                    }
                ]
            },
            {
                "name": "Hexaware",
                "location": "Navi Mumbai, India",
                "sector": "IT Services",
                "difficulty": "Medium",
                "description": "Fast-growing automation-led next-generation service provider.",
                "website_url": "https://hexaware.com",
                "exam_pattern": [
                    {"name": "Aptitude", "questions": 20, "time": "20 mins", "level": "Medium"},
                    {"name": "Domain Test", "questions": 20, "time": "20 mins", "level": "Medium"},
                    {"name": "Coding", "questions": 2, "time": "45 mins", "level": "Medium"}
                ],
                "hiring_process": [
                    {"title": "Online Test", "duration": "1 week"},
                    {"title": "Technical Interview", "duration": "1 week"},
                    {"title": "Communication Test", "duration": "3 days"},
                    {"title": "HR", "duration": "3 days"}
                ],
                "experiences": [
                    {
                        "user_role": "GET",
                        "difficulty": "Medium",
                        "is_selected": True,
                        "work_mode": "Onsite",
                        "candidate_type": "fresher",
                        "brief": "ECE Grad.",
                        "application_process": "Campus.",
                        "my_experience": "Hexaware's process is quite streamlined...",
                        "interview_rounds": [
                            {"title": "Round 1: Online", "duration": "Aptitude + Coding"},
                            {"title": "Round 2: Technical", "duration": "Basics of C/C++"},
                            {"title": "Round 3: Versant", "duration": "Speaking skills"}
                        ],
                        "technical_questions": ["Palindrome program.", "What is a Class?"],
                        "behavioral_questions": ["Tell me about yourself."],
                        "mistakes": ["Stuttered during Versant due to mic issue."],
                        "preparation_strategy": {
                            "Resources": ["PrepInsta"],
                            "Focus": ["Communication"]
                        },
                        "final_advice": ["Check your microphone before the test."]
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
                    {"name": "C Programming", "questions": 15, "time": "30 mins", "level": "Hard"},
                    {"name": "Aptitude", "questions": 10, "time": "20 mins", "level": "Medium"},
                    {"name": "Coding", "questions": 5, "time": "90 mins", "level": "Hard"}
                ],
                "hiring_process": [
                    {"title": "Written Test", "duration": "1 day"},
                    {"title": "Machine Coding", "duration": "1 day"},
                    {"title": "Advanced Coding", "duration": "1 day"},
                    {"title": "Tech HR", "duration": "1 day"}
                ],
                "experiences": [
                    {
                        "user_role": "Software Developer",
                        "difficulty": "Hard",
                        "is_selected": True,
                        "work_mode": "Onsite",
                        "candidate_type": "fresher",
                        "brief": "Mechanical Engineering student who loves coding.",
                        "application_process": "Walk-in drive.",
                        "my_experience": "Zoho is famous for its unconventional interview style...",
                        "interview_rounds": [
                            {"title": "Round 1: C output guessing", "duration": "Predict output and pointers"},
                            {"title": "Round 2: Basic Programming", "duration": "No library functions allowed"},
                            {"title": "Round 3: System Design", "duration": "Console application design"}
                        ],
                        "technical_questions": [
                            "Sorting an array with minimum swaps.",
                            "Print a specific pattern.",
                            "Design Call Taxi Booking application."
                        ],
                        "behavioral_questions": ["Why coding after Mechanical engineering?"],
                        "mistakes": ["Used a library function by mistake and was warned."],
                        "preparation_strategy": {
                            "Resources": ["GeeksForGeeks Zoho Archives"],
                            "Focus": ["Logic building", "System Design (LLD)"]
                        },
                        "final_advice": ["Practice standard LLD problems like Parking Lot, Railway Reservation."]
                    }
                ]
            },
            {
                "name": "Wipro",
                "location": "Bangalore, India",
                "sector": "IT Services",
                "difficulty": "Easy",
                "description": "Leading global information technology, consulting and business process services company.",
                "website_url": "https://wipro.com",
                "exam_pattern": [
                    {"name": "Aptitude", "questions": 20, "time": "20 mins", "level": "Medium"},
                    {"name": "Logical", "questions": 20, "time": "20 mins", "level": "Medium"},
                    {"name": "Verbal", "questions": 20, "time": "20 mins", "level": "Easy"},
                    {"name": "Coding", "questions": 2, "time": "60 mins", "level": "Medium"}
                ],
                "hiring_process": [
                    {"title": "NLTH Exam", "duration": "2 weeks"},
                    {"title": "Business Discussion", "duration": "1 week"}
                ],
                "experiences": [
                    {
                        "user_role": "Project Engineer",
                        "difficulty": "Medium",
                        "is_selected": True,
                        "work_mode": "Onsite",
                        "candidate_type": "fresher",
                        "brief": "MCA Graduate, 2024.",
                        "application_process": "National Level Talent Hunt (NLTH).",
                        "my_experience": "Wipro's National Level Talent Hunt (NLTH) is a massive drive...",
                        "interview_rounds": [
                            {"title": "Round 1: Online Assessment", "duration": "Aptitude + Coding + Essay Writing"},
                            {"title": "Round 2: Technical Interview", "duration": "Project & Java Basics"}
                        ],
                        "technical_questions": ["Explain OOPs concepts.", "What is a primary key?"],
                        "behavioral_questions": ["Why Wipro?", "Relocation preference?"],
                        "mistakes": ["Nervous during essay writing."],
                        "preparation_strategy": {
                            "Resources": ["PrepInsta", "FacePrep"],
                            "Focus": ["Essay Writing", "Coding patterns"]
                        },
                        "final_advice": ["Don't ignore the essay writing section."]
                    }
                ]
            },
            {
                "name": "Infosys",
                "location": "Bangalore, India",
                "sector": "IT Services",
                "difficulty": "Medium",
                "description": "Global leader in next-generation digital services and consulting.",
                "website_url": "https://infosys.com",
                "exam_pattern": [
                    {"name": "Reasoning Ability", "questions": 15, "time": "25 mins", "level": "Hard"},
                    {"name": "Mathematical Ability", "questions": 10, "time": "35 mins", "level": "Medium"},
                    {"name": "Verbal Ability", "questions": 20, "time": "20 mins", "level": "Medium"},
                    {"name": "Pseudocode", "questions": 5, "time": "10 mins", "level": "Medium"},
                    {"name": "Puzzle Solving", "questions": 4, "time": "10 mins", "level": "Hard"}
                ],
                "hiring_process": [
                    {"title": "InfyTQ / HackWithInfy", "duration": "Varies"},
                    {"title": "Technical Interview", "duration": "1 week"},
                    {"title": "HR Interview", "duration": "3 days"}
                ],
                "experiences": [
                    {
                        "user_role": "Systems Engineer Specialist",
                        "difficulty": "Hard",
                        "is_selected": True,
                        "work_mode": "Onsite",
                        "candidate_type": "fresher",
                        "brief": "CSE, Top Coder.",
                        "application_process": "HackWithInfy Contest.",
                        "my_experience": "I secured the 'Power Programmer' role via HackWithInfy...",
                        "interview_rounds": [
                            {"title": "Round 1: Coding Contest", "duration": "3 questions"},
                            {"title": "Round 2: Interview", "duration": "Code optimization"}
                        ],
                        "technical_questions": ["Dynamic Programming for Knapsack.", "Detect cycle in a graph."],
                        "behavioral_questions": ["Why Power Programmer?"],
                        "mistakes": ["Suboptimal solution for 3rd question."],
                        "preparation_strategy": {
                            "Resources": ["CodeChef", "LeetCode"],
                            "Focus": ["Competitive Programming"]
                        },
                        "final_advice": ["Participate in HackWithInfy for higher packages."]
                    }
                ]
            },
            {
                "name": "HCL",
                "location": "Noida, India",
                "sector": "IT Services",
                "difficulty": "Medium",
                "description": "Next-generation global technology company helps enterprises reimagine business.",
                "website_url": "https://hcltech.com",
                "exam_pattern": [
                    {"name": "Aptitude", "questions": 15, "time": "20 mins", "level": "Medium"},
                    {"name": "Logical", "questions": 15, "time": "20 mins", "level": "Medium"},
                    {"name": "Technical", "questions": 20, "time": "30 mins", "level": "Medium"}
                ],
                "hiring_process": [
                    {"title": "Online Test", "duration": "1 week"},
                    {"title": "Technical Interview", "duration": "1 week"}
                ],
                "experiences": [
                    {
                        "user_role": "Software Engineer",
                        "difficulty": "Medium",
                        "is_selected": True,
                        "work_mode": "Onsite",
                        "candidate_type": "fresher",
                        "brief": "B.Tech IT.",
                        "application_process": "On-campus placement.",
                        "my_experience": "I secured a pre-placement offer (PPO) through HCL First Career...",
                        "interview_rounds": [
                            {"title": "Round 1: Online Test", "duration": "Aptitude + CS Fundamentals"},
                            {"title": "Round 2: Technical Interview", "duration": "Project deep dive"}
                        ],
                        "technical_questions": ["Explain React lifecycle.", "What is middleware in Node.js?"],
                        "behavioral_questions": ["Teamwork situation?"],
                        "mistakes": ["Couldn't explain database schema clearly."],
                        "preparation_strategy": {
                            "Resources": ["React Documentation", "GeeksForGeeks"],
                            "Focus": ["Project details"]
                        },
                        "final_advice": ["Know every line of code in your project."]
                    }
                ]
            },
            {
                "name": "Capgemini",
                "location": "Paris, France",
                "sector": "Consulting",
                "difficulty": "Medium",
                "description": "Global leader in partnering with companies to transform and manage business.",
                "website_url": "https://capgemini.com",
                "exam_pattern": [
                    {"name": "Pseudocode", "questions": 25, "time": "25 mins", "level": "Medium"},
                    {"name": "English", "questions": 25, "time": "25 mins", "level": "Easy"},
                    {"name": "Game-based Aptitude", "questions": 4, "time": "20 mins", "level": "Medium"},
                    {"name": "Behavioral", "questions": 100, "time": "20 mins", "level": "Easy"}
                ],
                "hiring_process": [
                    {"title": "Online Assessment", "duration": "1 week"},
                    {"title": "Technical Interview", "duration": "1 week"},
                    {"title": "HR Interview", "duration": "2 days"}
                ],
                "experiences": [
                    {
                        "user_role": "Analyst",
                        "difficulty": "Medium",
                        "is_selected": True,
                        "work_mode": "Onsite",
                        "candidate_type": "fresher",
                        "brief": "B.Tech ECE.",
                        "application_process": "Off-campus.",
                        "my_experience": "Capgemini introduced a 'Game-based Aptitude' round which is fun but tricky...",
                        "interview_rounds": [
                            {"title": "Round 1: Introduction", "duration": "Resume screening"},
                            {"title": "Round 2: Game-based Aptitude", "duration": "Memory & Logic games"}
                        ],
                        "technical_questions": ["What is a Join?", "Explain Inheritance."],
                        "behavioral_questions": ["Why IT from ECE?"],
                        "mistakes": [],
                        "preparation_strategy": {
                            "Resources": ["YouTube channels for game aptitude"],
                            "Focus": ["Speed and Accuracy"]
                        },
                        "final_advice": ["Practice game-based aptitude tests online."]
                    }
                ]
            }
        ]

        print("Seeding Companies and Experiences...")
        for comp_data in mock_companies:
            company = models.Company.query.filter_by(name=comp_data['name']).first()
            if not company:
                company = models.Company(
                    name=comp_data['name'],
                    location=comp_data['location'],
                    sector=comp_data['sector'],
                    difficulty=comp_data['difficulty'],
                    description=comp_data['description'],
                    website_url=comp_data['website_url'],
                    exam_pattern=comp_data['exam_pattern'],
                    hiring_process=comp_data['hiring_process']
                )
                db.session.add(company)
                db.session.flush() # Get ID
                print(f"Added Company: {company.name}")
            else:
                # Update existing company with details if missing
                company.location = comp_data['location']
                company.sector = comp_data['sector']
                company.description = comp_data['description']
                company.exam_pattern = comp_data['exam_pattern']
                company.hiring_process = comp_data['hiring_process']
                print(f"Updated Company: {company.name}")
            
            for exp_data in comp_data.get('experiences', []):
                # Search for existing experience to avoid duplicates
                # We'll use mock_alumni as the author for these mock experiences
                existing_exp = models.InterviewExperience.query.filter_by(
                    user_id=mock_alumni.id,
                    company_id=company.id,
                    user_role=exp_data['user_role']
                ).first()
                
                if not existing_exp:
                    experience = models.InterviewExperience(
                        user_id=mock_alumni.id,
                        company_id=company.id,
                        user_role=exp_data['user_role'],
                        difficulty=exp_data['difficulty'],
                        is_selected=exp_data['is_selected'],
                        work_mode=exp_data['work_mode'],
                        candidate_type=exp_data['candidate_type'],
                        brief=exp_data.get('brief'),
                        application_process=exp_data.get('application_process'),
                        my_experience=exp_data.get('my_experience'),
                        interview_rounds=exp_data.get('interview_rounds'),
                        technical_questions=exp_data.get('technical_questions'),
                        behavioral_questions=exp_data.get('behavioral_questions'),
                        mistakes=exp_data.get('mistakes'),
                        preparation_strategy=exp_data.get('preparation_strategy'),
                        final_advice=exp_data.get('final_advice'),
                        is_approved=True 
                    )
                    db.session.add(experience)
                    print(f"  Added Experience for {company.name}")

        db.session.commit()
        print("\n[+] Seeding completed successfully!")
        print(f"Total Companies: {models.Company.query.count()}")
        print(f"Total Users: {models.User.query.count()}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset database before seeding")
    args = parser.parse_args()
    
    seed_all(reset=args.reset)
