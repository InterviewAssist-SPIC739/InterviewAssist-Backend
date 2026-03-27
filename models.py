from database import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Association table for helpful votes
experience_helpful_votes = db.Table('experience_helpful_votes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('experience_id', db.Integer, db.ForeignKey('interview_experiences.id'), primary_key=True)
)

# Association table for saved experiences
user_saved_experiences = db.Table('user_saved_experiences',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('experience_id', db.Integer, db.ForeignKey('interview_experiences.id'), primary_key=True)
)

# Association table for following companies
company_followers = db.Table('company_followers',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('company_id', db.Integer, db.ForeignKey('companies.id'), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Student') # Student, Alumni, Admin
    has_completed_profile = db.Column(db.Boolean, default=False)
    profile_skipped = db.Column(db.Boolean, default=False)
    phone_number = db.Column(db.String(20)) # Kept for direct access if profile not created
    secondary_email = db.Column(db.String(120))
    two_factor_enabled = db.Column(db.Boolean, default=False)
    is_suspended = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='active') # active, suspended
    pending_details = db.Column(db.JSON) # Store proposed alumni profile updates here
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user_profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    followed_companies = db.relationship('Company', secondary=company_followers,
                                       backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    experiences = db.relationship('InterviewExperience', backref='user', lazy=True, cascade='all, delete-orphan')
    questions = db.relationship('CompanyQuestion', backref='user', lazy=True, cascade='all, delete-orphan')
    question_answers = db.relationship('QuestionAnswer', backref='user', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    reports_made = db.relationship('Report', backref='user', lazy=True, cascade='all, delete-orphan')
    
    # Many-to-many relationships are cleaned up automatically from the association table when the user is deleted
    # but the other side (Experience/Company) remains.
    # The second User model had 'companies_following' which is the same as 'followed_companies'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        profile_data = self.user_profile.to_dict() if self.user_profile else {}
            
        # These counts were from the first User model's to_dict
        experiences_count = InterviewExperience.query.filter_by(user_id=self.id, status='approved').count()
        total_helpful_votes = db.session.query(db.func.sum(InterviewExperience.helpful_count)).filter(InterviewExperience.user_id == self.id, InterviewExperience.status == 'approved').scalar() or 0
        assisted_count = QuestionAnswer.query.filter_by(user_id=self.id).count()
        saved_count = self.saved_experiences.count()
        questions_count = CompanyQuestion.query.filter_by(user_id=self.id).count()
            
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'role': self.role,
            'has_completed_profile': self.has_completed_profile,
            'profile_skipped': self.profile_skipped,
            'phone_number': profile_data.get('phone_number') if profile_data else self.phone_number, # Prioritize profile data
            'secondary_email': self.secondary_email,
            'two_factor_enabled': self.two_factor_enabled,
            'is_suspended': self.is_suspended,
            'status': self.status,
            'pending_details': self.pending_details,
            'created_at': self.created_at.isoformat(),
            'profile_pic': profile_data.get('profile_pic') if profile_data else None,
            'profile': profile_data, # Full profile data
            'experiences_count': experiences_count,
            'total_helpful_votes': total_helpful_votes,
            'assisted_count': assisted_count,
            'saved_count': saved_count,
            'questions_count': questions_count,
            **profile_data # Merge profile data directly into the top level as well, as per second User model
        }

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    phone_number = db.Column(db.String(20))
    major = db.Column(db.String(100))
    expected_grad_year = db.Column(db.String(10))
    current_year = db.Column(db.String(20))
    bio = db.Column(db.Text)
    profile_pic = db.Column(db.Text(16777215)) # MediumText for larger Base64 images
    linkedin_url = db.Column(db.String(255))
    current_company = db.Column(db.String(100))
    designation = db.Column(db.String(100))
    specialization = db.Column(db.String(100))

    def to_dict(self):
        return {
            'phone_number': self.phone_number,
            'major': self.major,
            'expected_grad_year': self.expected_grad_year,
            'current_year': self.current_year,
            'bio': self.bio,
            'profile_pic': self.profile_pic,
            'linkedin_url': self.linkedin_url,
            'current_company': self.current_company,
            'designation': self.designation,
            'specialization': self.specialization
        }

class Admin(db.Model):
    __tablename__ = 'admin'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Admin')
    phone_number = db.Column(db.String(20))
    secondary_email = db.Column(db.String(120))
    two_factor_enabled = db.Column(db.Boolean, default=False)

    def set_password(self, password_text):
        self.password_hash = generate_password_hash(password_text)

    def check_password(self, password_text):
        return check_password_hash(self.password_hash, password_text)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'first_name': 'System',
            'last_name': 'Admin',
            'phone_number': self.phone_number,
            'secondary_email': self.secondary_email,
            'two_factor_enabled': self.two_factor_enabled
        }

class OTP(db.Model):
    __tablename__ = 'otps'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

class Company(db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(100))
    sector = db.Column(db.String(100))
    logo = db.Column(db.Text(16777215)) # MediumText for Base64 logo
    logo_url = db.Column(db.String(255))
    difficulty = db.Column(db.String(20)) # Easy, Medium, Hard
    description = db.Column(db.Text)
    website_url = db.Column(db.String(255))
    
    # JSON fields for complex data
    exam_pattern = db.Column(db.JSON) # List of sections
    hiring_process = db.Column(db.JSON) # List of steps
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    experiences = db.relationship('InterviewExperience', backref='company', lazy=True, cascade='all, delete-orphan')
    questions = db.relationship('CompanyQuestion', backref='company', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, current_user_id=None):
        is_following = False
        if current_user_id:
            try:
                user_id_int = int(current_user_id)
                is_following = self.followers.filter(User.id == user_id_int).count() > 0
            except:
                pass

        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'sector': self.sector,
            'logo': self.logo,
            'logo_url': self.logo_url,
            'difficulty': self.difficulty,
            'description': self.description,
            'website_url': self.website_url,
            'exam_pattern': self.exam_pattern,
            'hiring_process': self.hiring_process,
            'experiences_count': len([exp for exp in self.experiences if exp.status == 'approved']),
            'selected_count': len([exp for exp in self.experiences if exp.status == 'approved' and exp.is_selected]),
            'is_following': is_following,
            'questions': [q.to_dict() for q in self.questions]
        }


class CompanyQuestion(db.Model):
    __tablename__ = 'company_questions'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True) # Allow anonymous or system questions
    
    question_text = db.Column(db.Text, nullable=False)
    asked_by_name = db.Column(db.String(100), default="Anonymous")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationship is now explicitly defined in User with cascade
    # user = db.relationship('User', backref='questions', lazy=True)
    answers = db.relationship('QuestionAnswer', backref='question', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        asked_by = self.asked_by_name
        if self.user:
            asked_by = f"{self.user.first_name} {self.user.last_name}"
            
        return {
            'id': self.id,
            'user_id': self.user_id,
            'company_id': self.company_id,
            'company_name': self.company.name if self.company else '',
            'question_text': self.question_text,
            'asked_by': asked_by,
            'date': self.created_at.strftime('%Y-%m-%d'),
            'answers': [answer.to_dict() for answer in self.answers]
        }

class QuestionAnswer(db.Model):
    __tablename__ = 'question_answers'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('company_questions.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    
    answer_text = db.Column(db.Text, nullable=False)
    answerer_name = db.Column(db.String(100), default="Alumni")
    answerer_role = db.Column(db.String(100), default="Verified Alumni")
    is_verified_alumni = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationship is now explicitly defined in User with cascade
    # user = db.relationship('User', backref='question_answers', lazy=True)

    def to_dict(self):
        name = self.answerer_name
        role = self.answerer_role
        verified = self.is_verified_alumni
        
        if self.user:
            name = f"{self.user.first_name} {self.user.last_name}"
            verified = self.user.role == 'Alumni'
            if not role or role == "Verified Alumni":
                role = "Alumni" if verified else self.user.role

        profile_pic = None
        if self.user and self.user.user_profile:
            profile_pic = self.user.user_profile.profile_pic

        return {
            'id': self.id,
            'answerer_name': name,
            'answerer_role': role,
            'is_verified_alumni': verified,
            'answer_text': self.answer_text,
            'profile_pic': profile_pic,
            'date': self.created_at.strftime('%Y-%m-%d')
        }

class InterviewExperience(db.Model):
    __tablename__ = 'interview_experiences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    user_role = db.Column(db.String(100))
    difficulty = db.Column(db.String(20))
    is_selected = db.Column(db.Boolean, default=False)
    work_mode = db.Column(db.String(50)) # Onsite, Remote, Hybrid
    candidate_type = db.Column(db.String(50)) # fresher, experienced
    my_experience = db.Column(db.Text)
    brief = db.Column(db.String(255))
    application_process = db.Column(db.Text)
    
    # JSON fields for structured content
    interview_rounds = db.Column(db.JSON)
    technical_questions = db.Column(db.JSON)
    behavioral_questions = db.Column(db.JSON)
    mistakes = db.Column(db.JSON)
    preparation_strategy = db.Column(db.JSON) # Map of category to list
    final_advice = db.Column(db.JSON)
    
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected
    helpful_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship is now explicitly defined in User with cascade
    # user = db.relationship('User', backref='experiences', lazy=True)
    helpful_voters = db.relationship('User', secondary=experience_helpful_votes, 
                                   backref=db.backref('helpful_experiences', lazy='dynamic'), lazy='dynamic')
    saved_by_users = db.relationship('User', secondary=user_saved_experiences,
                                   backref=db.backref('saved_experiences', lazy='dynamic'), lazy='dynamic')

    def to_dict(self, current_user_id=None):
        is_helpful = False
        is_saved = False
        if current_user_id:
            try:
                user_id_int = int(current_user_id)
                is_helpful = self.helpful_voters.filter(User.id == user_id_int).count() > 0
                is_saved = self.saved_by_users.filter(User.id == user_id_int).count() > 0
            except:
                pass

        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': f"{self.user.first_name} {self.user.last_name}",
            'user_role': self.user_role,
            'is_user_verified': self.user.role == 'Alumni',
            'difficulty': self.difficulty,
            'date': self.created_at.strftime('%Y-%m-%d'),
            'is_selected': self.is_selected,
            'work_mode': self.work_mode,
            'candidate_type': self.candidate_type,
            'my_experience': self.my_experience,
            'brief': self.brief,
            'application_process': self.application_process,
            'interview_rounds': self.interview_rounds,
            'technical_questions': self.technical_questions,
            'behavioral_questions': self.behavioral_questions,
            'mistakes': self.mistakes,
            'preparation_strategy': self.preparation_strategy,
            'final_advice': self.final_advice,
            'status': self.status,
            'helpful_count': self.helpful_count,
            'is_helpful': is_helpful,
            'is_saved': is_saved,
            'company_name': self.company.name,
            'user_profile_company': self.user.user_profile.current_company if self.user.user_profile else None,
            'user_profile_role': self.user.user_profile.designation if self.user.user_profile else None,
            'user_profile_pic': self.user.user_profile.profile_pic if self.user.user_profile else None,
            'is_user_suspended': self.user.is_suspended if self.user else False
        }

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False) # Registration, Upgrade, Experience
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # If null, it's for admin
    target_id = db.Column(db.Integer) # ID of the user or experience
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.type,
            'user_id': self.user_id,
            'target_id': self.target_id,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'date': self.created_at.strftime('%Y-%m-%d %H:%M')
        }
class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    content_type = db.Column(db.String(50), nullable=False) # experience, question, answer
    experience_id = db.Column(db.Integer, db.ForeignKey('interview_experiences.id'), nullable=True)
    question_id = db.Column(db.Integer, db.ForeignKey('company_questions.id'), nullable=True)
    answer_id = db.Column(db.Integer, db.ForeignKey('question_answers.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # User who reported
    reason = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='pending') # pending, kept, removed

    experience = db.relationship('InterviewExperience', backref=db.backref('experience_reports', cascade='all, delete-orphan'))
    question = db.relationship('CompanyQuestion', backref=db.backref('question_reports', cascade='all, delete-orphan'))
    answer = db.relationship('QuestionAnswer', backref=db.backref('answer_reports', cascade='all, delete-orphan'))
    # Relationship is now explicitly defined in User with cascade
    # user = db.relationship('User', backref='reports_made_v2')

    def to_dict(self):
        title = "Reported Content"
        snippet = ""
        creator = "Unknown"
        
        if self.content_type == 'experience' and self.experience:
            title = f"Interview at {self.experience.company.name}"
            snippet = self.experience.my_experience[:100] + "..." if self.experience.my_experience else ""
            creator = f"{self.experience.user.first_name} {self.experience.user.last_name}" if self.experience.user else "Unknown"
        elif self.content_type == 'question' and self.question:
            title = f"Question for {self.question.company.name if self.question.company else 'Unknown'}"
            snippet = self.question.question_text[:100] + "..."
            creator = self.question.asked_by_name
        elif self.content_type == 'answer' and self.answer:
            title = f"Answer by {self.answer.answerer_name}"
            snippet = self.answer.answer_text[:100] + "..."
            creator = self.answer.answerer_name

        return {
            'id': self.id,
            'content_type': self.content_type,
            'experience_id': self.experience_id or 0,
            'question_id': self.question_id,
            'answer_id': self.answer_id,
            'user_id': self.user_id,
            'reason': self.reason,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
            'reported_by': f"{self.user.first_name} {self.user.last_name}",
            'experience_title': title,
            'experience_snippet': snippet,
            'content_creator': creator,
            'time_ago': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

class RecentActivity(db.Model):
    __tablename__ = 'recent_activities'

    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    target = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_name': self.user_name,
            'action': self.action,
            'target': self.target,
            'created_at': self.created_at.isoformat(),
            'time': self.created_at.strftime('%Y-%m-%d %H:%M')
        }
