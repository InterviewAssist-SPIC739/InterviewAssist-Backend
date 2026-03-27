from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, 
    jwt_required, get_jwt_identity
)
from flask_mail import Mail, Message
from config import Config
from database import db
import models 
import random
import threading
from datetime import datetime, timedelta
import requests
from sqlalchemy import text
from sqlalchemy.orm import joinedload

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Extensions
    db.init_app(app)
    CORS(app)
    jwt = JWTManager(app)
    mail = Mail(app)

    with app.app_context():
        try:
            # Check if pending_details column exists, if not add it
            db.session.execute(text("SELECT pending_details FROM users LIMIT 1"))
        except Exception:
            try:
                db.session.execute(text("ALTER TABLE users ADD COLUMN pending_details JSON"))
                db.session.commit()
            except Exception as e:
                app.logger.error(f"Failed to add pending_details column: {str(e)}")
                db.session.rollback()

    def send_email(subject, recipient, body):
        msg = Message(subject=subject, recipients=[recipient], body=body)
        thread = threading.Thread(target=send_async_email, args=(app, msg, mail))
        thread.start()

    def send_async_email(app, msg, mail):
        with app.app_context():
            try:
                mail.send(msg)
            except Exception as e:
                app.logger.error(f"Failed to send email: {str(e)}")

    def create_admin_notification(title, description, type, target_id=None):
        create_notification(title, description, type, user_id=None, target_id=target_id)

    def create_user_notification(user_id, title, description, type, target_id=None):
        create_notification(title, description, type, user_id=user_id, target_id=target_id)

    def create_notification(title, description, type, user_id=None, target_id=None):
        try:
            new_notif = models.Notification(
                title=title,
                description=description,
                type=type,
                user_id=user_id,
                target_id=target_id
            )
            db.session.add(new_notif)
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Failed to create notification: {str(e)}")

    def create_activity(user_name, action, target):
        try:
            new_activity = models.RecentActivity(
                user_name=user_name,
                action=action,
                target=target
            )
            db.session.add(new_activity)
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Failed to create activity: {str(e)}")

    # Health check
    @app.route('/health')
    def health_check():
        return {"status": "healthy", "database": "connected" if db.engine else "disconnected"}, 200

    @app.route('/register', methods=['POST'])
    def register():
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400
                
        email = data.get('email', '').strip().lower()
        if models.User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already registered"}), 400
            
        try:
            user_role = data.get('role', 'Student')
            user_status = 'pending' if user_role == 'Alumni' else 'active'
            
            new_user = models.User(
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=email,
                role=user_role,
                status=user_status
            )
            new_user.set_password(data['password'])
            
            db.session.add(new_user)
            db.session.commit()
            
            # Log activity for Alumni registration
            if user_role == 'Alumni':
                create_activity(f"{new_user.first_name} {new_user.last_name}", "requested alumni verification for", "the system")

            access_token = create_access_token(identity=str(new_user.id))
            
            # Send Welcome Email
            send_email(
                subject='Welcome to InterviewAssist!',
                recipient=new_user.email,
                body=f"Hi {new_user.first_name},\n\nYour account has been created successfully as a {new_user.role}. Welcome aboard!\n\nBest regards,\nInterviewAssist Team"
            )
            
            # Trigger Admin Notification
            role_badge = f"[{user_role}]"
            create_admin_notification(
                title=f"New {user_role} Joined",
                description=f"{role_badge} {new_user.first_name} {new_user.last_name} ({new_user.email}) has just registered. Approval may be required.",
                type="Registration",
                target_id=new_user.id
            )
            
            return jsonify({
                "message": "Account created successfully",
                "user": new_user.to_dict(),
                "access_token": access_token
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/login', methods=['POST'])
    def login():
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password')
        role = data.get('role')

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        # Decide which table to query based on role
        if role == 'Admin':
            user = models.Admin.query.filter_by(email=email).first()
        else:
            user = models.User.query.filter_by(email=email).first()

        if not user:
            return jsonify({"error": "no account found"}), 404

        if not user.check_password(password):
            return jsonify({"error": "Invalid password"}), 401
        
        # Double check role for non-admin users if role was provided
        if role and role != 'Admin' and user.role != role:
            return jsonify({"error": f"Account exists but not as a {role}"}), 403

        # Check status and suspension (only applies to non-admin users)
        if role != 'Admin':
            if getattr(user, 'status', None) == 'suspended' or getattr(user, 'is_suspended', False):
                return jsonify({"error": "Your account has been suspended. Please contact admin."}), 403
                
            if getattr(user, 'status', None) == 'pending' and user.role != 'Student':
                return jsonify({"error": "Your account activation is pending in admin side"}), 403

            if getattr(user, 'status', None) == 'rejected':
                return jsonify({"error": "Your access has been rejected by the admin."}), 403

        if getattr(user, 'two_factor_enabled', False):
            otp_code = str(random.randint(100000, 999999))
            expires_at = datetime.utcnow() + timedelta(minutes=5)
            models.OTP.query.filter_by(email=user.email, role=user.role).delete()
            new_otp = models.OTP(email=user.email, role=user.role, code=otp_code, expires_at=expires_at)
            db.session.add(new_otp)
            db.session.commit()
            
            # Send 2FA OTP via Email
            recipient_email = getattr(user, 'secondary_email', None) or user.email
            send_email(
                subject='Login OTP - InterviewAssist',
                recipient=recipient_email,
                body=f"Your One-Time Password (OTP) for login is: {otp_code}\n\nThis code will expire in 5 minutes."
            )
                    
            return jsonify({
                "message": "OTP required for login",
                "requires_otp": True,
                "user": user.to_dict()
            }), 200

        access_token = create_access_token(identity=str(user.id))

        # Send Login Notification
        send_email(
            subject='New Login Detected - InterviewAssist',
            recipient=user.email,
            body=f"Hi {user.email},\n\nA new login was detected for your account at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. If this wasn't you, please reset your password immediately."
        )

        return jsonify({
            "message": "Login successful",
            "user": user.to_dict(),
            "access_token": access_token
        }), 200

    @app.route('/verify-login-otp', methods=['POST'])
    def verify_login_otp():
        data = request.get_json()
        email = data.get('email', '').strip()
        role = data.get('role', 'Student')
        otp_code = data.get('otp')

        if not email or not otp_code:
            return jsonify({"error": "Email and OTP are required"}), 400

        otp_record = models.OTP.query.filter_by(email=email, role=role, code=otp_code).first()

        if not otp_record or otp_record.is_expired():
            return jsonify({"error": "Invalid or expired OTP"}), 401
            
        if role == 'Admin':
            user = models.Admin.query.filter_by(email=email).first()
        else:
            user = models.User.query.filter_by(email=email).first()

        if not user:
            return jsonify({"error": "Account not found"}), 404

        models.OTP.query.filter_by(email=email, role=role).delete()
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        
        send_email(
            subject='New Login Detected - InterviewAssist',
            recipient=user.email,
            body=f"Hi {user.email},\n\nA new login was detected for your account at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. If this wasn't you, please reset your password immediately."
        )

        return jsonify({
            "message": "OTP verified, login successful",
            "user": user.to_dict(),
            "access_token": access_token
        }), 200

    @app.route('/request-alumni-upgrade', methods=['POST'])
    @jwt_required()
    def request_alumni_upgrade():
        user_id = get_jwt_identity()
        data = request.get_json()
        
        user = models.User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        try:
            # Store proposed updates in pending_details JSON field instead of applying them
            pending_data = {
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'email': data.get('email'),
                'phone_number': data.get('phone_number'),
                'major': data.get('major'),
                'expected_grad_year': data.get('expected_grad_year'),
                'current_year': 'Alumni',
                'bio': data.get('bio'),
                'profile_pic': data.get('profile_pic'),
                'linkedin_url': data.get('linkedin_url'),
                'current_company': data.get('current_company'),
                'designation': data.get('designation'),
                'specialization': data.get('specialization')
            }
            user.pending_details = pending_data
            user.status = 'pending'
            db.session.commit()
            
            create_admin_notification(
                title="Alumni Upgrade Requested",
                description=f"Student {user.first_name} {user.last_name} has requested to upgrade their account to Alumni status.",
                type="Upgrade",
                target_id=user.id
            )
            
            return jsonify({"message": "Upgrade request submitted successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/admin/pending-upgrades', methods=['GET'])
    @jwt_required()
    def get_pending_upgrades():
        admin_id = get_jwt_identity()
        admin = models.Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        # Return students whose status is pending (meaning they requested upgrade)
        pending = models.User.query.filter_by(role='Student', status='pending').all()
        return jsonify([user.to_dict() for user in pending]), 200

    @app.route('/admin/notifications/', methods=['GET'])
    @jwt_required()
    def get_admin_notifications():
        # Check if user is admin
        user_id = get_jwt_identity()
        admin = models.Admin.query.get(user_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        notifications = models.Notification.query.filter_by(user_id=None).order_by(models.Notification.created_at.desc()).all()
        return jsonify([n.to_dict() for n in notifications]), 200

    @app.route('/notifications/', methods=['GET'])
    @jwt_required()
    def get_user_notifications():
        user_id = int(get_jwt_identity())
        notifications = models.Notification.query.filter_by(user_id=user_id).order_by(models.Notification.created_at.desc()).all()
        return jsonify([n.to_dict() for n in notifications]), 200

    @app.route('/notifications/mark-read/', methods=['POST'])
    @jwt_required()
    def mark_user_notifications_read():
        data = request.get_json()
        notification_ids = data.get('ids', [])
        user_id = int(get_jwt_identity())
        
        try:
            if notification_ids:
                # Direct SQL UPDATE for performance and persistence guarantee
                db.session.execute(
                    text("UPDATE notifications SET is_read = 1 WHERE id IN :ids AND user_id = :uid"),
                    {"ids": tuple(notification_ids), "uid": user_id}
                )
            else:
                # Mark all for this user
                db.session.execute(
                    text("UPDATE notifications SET is_read = 1 WHERE user_id = :uid AND is_read = 0"),
                    {"uid": user_id}
                )
            db.session.commit()
            return jsonify({"message": "Notifications marked as read"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/notifications/<int:notification_id>', methods=['DELETE'])
    @jwt_required()
    def delete_user_notification(notification_id):
        user_id = int(get_jwt_identity())
        notification = models.Notification.query.filter_by(id=notification_id, user_id=user_id).first_or_404()
        
        try:
            db.session.delete(notification)
            db.session.commit()
            return jsonify({"message": "Notification deleted"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/admin/notifications/mark-read/', methods=['POST'])
    @jwt_required()
    def mark_notifications_read():
        data = request.get_json()
        notification_ids = data.get('ids', [])
        
        # Check if user is admin
        user_identity = get_jwt_identity()
        try:
            admin_id = int(user_identity)
        except (ValueError, TypeError):
            admin_id = 0

        admin = models.Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        try:
            if notification_ids:
                db.session.execute(
                    text("UPDATE notifications SET is_read = 1 WHERE id IN :ids AND user_id IS NULL"),
                    {"ids": tuple(notification_ids)}
                )
            else:
                db.session.execute(
                    text("UPDATE notifications SET is_read = 1 WHERE user_id IS NULL AND is_read = 0")
                )
            db.session.commit()
            return jsonify({"message": "Notifications marked as read"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/admin/notifications/<int:notification_id>', methods=['DELETE'])
    @jwt_required()
    def delete_admin_notification(notification_id):
        user_id = get_jwt_identity()
        admin = models.Admin.query.get(user_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        notification = models.Notification.query.filter_by(id=notification_id, user_id=None).first_or_404()
        
        try:
            db.session.delete(notification)
            db.session.commit()
            return jsonify({"message": "Notification deleted"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500


    @app.route('/admin/dashboard-stats', methods=['GET'])
    @jwt_required()
    def get_dashboard_stats():
        # Check if user is admin
        user_id = get_jwt_identity()
        admin = models.Admin.query.get(user_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        # Total users excludes pending Alumni registrations to match the Users list visibility
        total_users = models.User.query.filter(
            ~((models.User.role == 'Alumni') & (models.User.status == 'pending'))
        ).count()
        pending_reviews = models.InterviewExperience.query.filter_by(status='pending').count()
        new_alumni = models.User.query.filter_by(status='pending').count()
        unread_notifications_count = models.Notification.query.filter_by(user_id=None, is_read=False).count()
        
        # Reports count - get from Report model
        reports_count = models.Report.query.count()

        # Recent activities
        recent_activities = models.RecentActivity.query.order_by(models.RecentActivity.created_at.desc()).limit(10).all()

        return jsonify({
            "total_users": total_users,
            "pending_reviews": pending_reviews,
            "new_alumni": new_alumni,
            "reports_count": reports_count,
            "unread_notifications_count": unread_notifications_count,
            "recent_activities": [a.to_dict() for a in recent_activities]
        }), 200

    @app.route('/admin/create-admin', methods=['POST'])
    @jwt_required()
    def create_admin():
        admin_id = get_jwt_identity()
        admin = models.Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403
            
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
            
        if models.Admin.query.filter_by(email=email).first():
            return jsonify({"error": "Admin already exists"}), 400
            
        try:
            new_admin = models.Admin(email=email)
            new_admin.set_password(password)
            db.session.add(new_admin)
            db.session.commit()
            return jsonify({"message": "Admin created successfully"}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/admin/update-admin-password', methods=['POST'])
    @jwt_required()
    def update_admin_password():
        admin_id = get_jwt_identity()
        admin = models.Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403
            
        data = request.get_json()
        email = data.get('email')
        new_password = data.get('new_password')
        
        if not email or not new_password:
            return jsonify({"error": "Email and new password are required"}), 400
            
        target_admin = models.Admin.query.filter_by(email=email).first()
        if not target_admin:
            return jsonify({"error": "Admin not found"}), 404
            
        try:
            target_admin.set_password(new_password)
            db.session.commit()
            return jsonify({"message": "Admin password updated successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500


    @app.route('/complete-profile', methods=['POST'])
    def complete_profile():
        data = request.get_json()
        user_id = data.get('user_id') or data.get('id') # Support both
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        user = models.User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        try:
            profile = models.UserProfile.query.filter_by(user_id=user_id).first()
            if not profile:
                profile = models.UserProfile(user_id=user_id)
                db.session.add(profile)
            
            # Partial Update logic: only update if field is provided and not None
            # This prevents overwriting existing data (like Student major) when Alumni completes profile
            if 'phone_number' in data and data['phone_number'] is not None:
                profile.phone_number = data['phone_number']
                user.phone_number = data['phone_number']
            if 'major' in data and data['major'] is not None:
                profile.major = data['major']
            if 'expected_grad_year' in data and data['expected_grad_year'] is not None:
                profile.expected_grad_year = data['expected_grad_year']
            if 'current_year' in data and data['current_year'] is not None:
                profile.current_year = data['current_year']
            if 'bio' in data and data['bio'] is not None:
                profile.bio = data['bio']
            if 'profile_pic' in data and data['profile_pic'] is not None:
                profile.profile_pic = data['profile_pic']
            if 'linkedin_url' in data and data['linkedin_url'] is not None:
                profile.linkedin_url = data['linkedin_url']
            if 'current_company' in data and data['current_company'] is not None:
                profile.current_company = data['current_company']
            if 'designation' in data and data['designation'] is not None:
                profile.designation = data['designation']
            if 'specialization' in data and data['specialization'] is not None:
                profile.specialization = data['specialization']
                
            # Update core user fields if provided
            if 'first_name' in data and data['first_name'] is not None:
                user.first_name = data['first_name']
            if 'last_name' in data and data['last_name'] is not None:
                user.last_name = data['last_name']
            if 'email' in data and data['email'] is not None:
                user.email = data['email'].strip().lower()
            
            user.has_completed_profile = True
            db.session.commit()
            return jsonify({"message": "Profile updated successfully"}), 200
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            db.session.rollback()
            print(f"Error in complete_profile: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/skip-profile', methods=['POST'])
    def skip_profile():
        data = request.get_json()
        user_id = data.get('user_id') or data.get('id')
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        user = models.User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        try:
            user.profile_skipped = True
            db.session.commit()
            return jsonify({"message": "Profile skip recorded"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/profile/<int:user_id>', methods=['GET'])
    def get_profile(user_id):
        user = models.User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        profile = models.UserProfile.query.filter_by(user_id=user_id).first()
        
        user_data = user.to_dict()
        if profile:
            user_data['profile'] = profile.to_dict()
        else:
            user_data['profile'] = None
            
        return jsonify(user_data), 200

    @app.route('/forgot-password', methods=['POST'])
    def forgot_password():
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        role = data.get('role', 'Student')

        if not email:
            return jsonify({"error": "Email is required"}), 400

        # Check if user exists
        if role == 'Admin':
            user = models.Admin.query.filter_by(email=email).first()
        else:
            user = models.User.query.filter_by(email=email).first()

        if not user:
            return jsonify({"error": "Account not found"}), 404
            
        if role != 'Admin' and user.role != role:
            return jsonify({"error": f"Account exists but not as a {role}"}), 403

        # Generate 6-digit OTP
        otp_code = str(random.randint(100000, 999999))
        expires_at = datetime.utcnow() + timedelta(minutes=10)

        # Clear existing OTPs for this email/role
        models.OTP.query.filter_by(email=email, role=role).delete()

        try:
            new_otp = models.OTP(
                email=email,
                role=role,
                code=otp_code,
                expires_at=expires_at
            )
            db.session.add(new_otp)
            db.session.commit()
            
            # Send OTP via Email
            send_email(
                subject='Password Reset OTP - InterviewAssist',
                recipient=email,
                body=f"Your One-Time Password (OTP) for resetting your password is: {otp_code}\n\nThis code will expire in 10 minutes."
            )
            
            return jsonify({
                "message": "OTP sent successfully to your email."
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/verify-otp', methods=['POST'])
    def verify_otp():
        data = request.get_json()
        email = data.get('email')
        role = data.get('role', 'Student')
        otp_code = data.get('otp')

        if not email or not otp_code:
            return jsonify({"error": "Email and OTP are required"}), 400

        otp_record = models.OTP.query.filter_by(email=email, role=role, code=otp_code).first()

        if not otp_record or otp_record.is_expired():
            return jsonify({"error": "Invalid or expired OTP"}), 401

        return jsonify({"message": "OTP verified successfully"}), 200

    @app.route('/reset-password', methods=['POST'])
    def reset_password():
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        role = data.get('role', 'Student')
        otp_code = data.get('otp')
        new_password = data.get('new_password')

        if not email or not otp_code or not new_password:
            return jsonify({"error": "Email, OTP and new password are required"}), 400

        # Verify OTP one last time
        otp_record = models.OTP.query.filter_by(email=email, role=role, code=otp_code).first()
        if not otp_record or otp_record.is_expired():
            return jsonify({"error": "Session expired, please request a new OTP"}), 401

        # Find user
        if role == 'Admin':
            user = models.Admin.query.filter_by(email=email).first()
        else:
            user = models.User.query.filter_by(email=email).first()

        if not user:
            return jsonify({"error": "Account not found"}), 404

        try:
            user.set_password(new_password)
            # Delete OTP after successful reset
            models.OTP.query.filter_by(email=email, role=role).delete()
            db.session.commit()
            
            # Send Reset Confirmation Email
            send_email(
                subject='Password Reset Successful - InterviewAssist',
                recipient=user.email,
                body=f"Hi,\n\nYour password has been reset successfully. If you did not perform this action, please contact support immediately."
            )
            
            return jsonify({"message": "Password reset successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/change-password', methods=['POST'])
    @jwt_required()
    def change_password():
        data = request.get_json()
        user_id = get_jwt_identity()
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not old_password or not new_password:
            return jsonify({"error": "Old and new password are required"}), 400

        user = models.User.query.get(user_id)
        if not user or not user.check_password(old_password):
            return jsonify({"error": "Invalid old password"}), 401

        try:
            user.set_password(new_password)
            db.session.commit()
            
            # Send Change Confirmation Email
            send_email(
                subject='Password Changed - InterviewAssist',
                recipient=user.email,
                body=f"Hi {user.first_name},\n\nYour password has been changed successfully. If you did not perform this action, please contact support immediately."
            )
            
            return jsonify({"message": "Password updated successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/toggle-2fa', methods=['POST'])
    @jwt_required()
    def toggle_2fa():
        data = request.get_json()
        user_id = get_jwt_identity()
        phone_number = data.get('phone_number')
        enable = data.get('enable', False)
        role = data.get('role', 'Student')

        if role == 'Admin':
            user = models.Admin.query.get(user_id)
        else:
            user = models.User.query.get(user_id)

        if not user:
            return jsonify({"error": "User not found"}), 404

        try:
            user.two_factor_enabled = enable
            if phone_number:
                user.phone_number = phone_number
            if data.get('secondary_email'):
                user.secondary_email = data.get('secondary_email')
            db.session.commit()
            return jsonify({"message": f"2FA updated successfully. Status: {'Enabled' if enable else 'Disabled'}"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    # --- Company and Experience Endpoints ---

    @app.route('/companies', methods=['GET'])
    def get_companies():
        # Optimize fetching with joinedload to avoid N+1 queries for experiences and questions
        companies = models.Company.query.options(
            joinedload(models.Company.experiences),
            joinedload(models.Company.questions)
        ).all()
        return jsonify([company.to_dict() for company in companies]), 200

    @app.route('/companies', methods=['POST'])
    @jwt_required()
    def add_company():
        # Check if user is admin
        user_id = get_jwt_identity()
        admin = models.Admin.query.get(user_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        data = request.get_json()
        name = data.get('name')
        if not name:
            return jsonify({"error": "Company name is required"}), 400

        # Check if company already exists
        if models.Company.query.filter_by(name=name).first():
            return jsonify({"error": "Company with this name already exists"}), 400

        try:
            new_company = models.Company(
                name=name,
                location=data.get('location'),
                sector=data.get('sector'),
                logo=data.get('logo'),
                difficulty=data.get('difficulty', 'Medium'),
                description=data.get('description'),
                website_url=data.get('website_url'),
                exam_pattern=data.get('exam_pattern'),
                hiring_process=data.get('hiring_process')
            )
            db.session.add(new_company)
            db.session.commit()
            return jsonify({"message": "Company added successfully", "company": new_company.to_dict()}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500
    @app.route('/companies/<int:company_id>', methods=['PUT'])
    @jwt_required()
    def update_company(company_id):
        # Check if user is admin
        user_id = get_jwt_identity()
        admin = models.Admin.query.get(user_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        company = models.Company.query.get_or_404(company_id)
        data = request.get_json()
        
        try:
            if 'name' in data:
                # Check if new name already exists elsewhere
                new_name = data['name']
                if new_name != company.name and models.Company.query.filter_by(name=new_name).first():
                    return jsonify({"error": "Company with this name already exists"}), 400
                company.name = new_name
            
            if 'location' in data:
                company.location = data['location']
            if 'sector' in data:
                company.sector = data['sector']
            if 'logo' in data:
                company.logo = data['logo']
            if 'difficulty' in data:
                company.difficulty = data['difficulty']
            if 'description' in data:
                company.description = data['description']
            if 'website_url' in data:
                company.website_url = data['website_url']
            if 'exam_pattern' in data:
                company.exam_pattern = data['exam_pattern']
            if 'hiring_process' in data:
                company.hiring_process = data['hiring_process']

            db.session.commit()
            return jsonify({"message": "Company updated successfully", "company": company.to_dict()}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/companies/<int:company_id>', methods=['DELETE'])
    @jwt_required()
    def delete_company(company_id):
        # Check if user is admin
        user_id = get_jwt_identity()
        admin = models.Admin.query.get(user_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        company = models.Company.query.get_or_404(company_id)
        try:
            db.session.delete(company)
            db.session.commit()
            return jsonify({"message": "Company deleted successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/companies/<int:company_id>', methods=['GET'])
    @jwt_required(optional=True)
    def get_company_detail(company_id):
        # Optimize fetching with joinedload
        company = models.Company.query.options(
            joinedload(models.Company.experiences),
            joinedload(models.Company.questions).joinedload(models.CompanyQuestion.user),
            joinedload(models.Company.questions).joinedload(models.CompanyQuestion.answers).joinedload(models.QuestionAnswer.user)
        ).get_or_404(company_id)
        
        current_user_id = None
        try:
            current_user_id = get_jwt_identity()
        except:
            pass
            
        # Return company dict with filtered experiences (only approved)
        result = company.to_dict(current_user_id=current_user_id)
        
        # If the user is an admin, they should see all experiences, otherwise only approved ones
        is_admin = False
        if current_user_id:
            is_admin = models.Admin.query.get(current_user_id) is not None
            
        if not is_admin:
            # Filter experiences to only show approved ones for students/alumni
            result['experiences'] = [
                exp.to_dict(current_user_id=current_user_id) 
                for exp in company.experiences 
                if exp.status == 'approved'
            ]
        else:
            # Admins see everything
            result['experiences'] = [
                exp.to_dict(current_user_id=current_user_id) 
                for exp in company.experiences
            ]
            
        return jsonify(result), 200

    @app.route('/companies/<int:company_id>/follow', methods=['POST'])
    @jwt_required()
    def toggle_follow_company(company_id):
        user_id = get_jwt_identity()
        company = models.Company.query.get_or_404(company_id)
        user = models.User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        if company in user.followed_companies:
            user.followed_companies.remove(company)
            message = "Unfollowed company"
            is_following = False
        else:
            user.followed_companies.append(company)
            message = "Following company"
            is_following = True
            
        db.session.commit()
        return jsonify({
            "message": message, 
            "is_following": is_following
        }), 200
    @app.route('/companies/<int:company_id>/questions', methods=['POST'])
    @jwt_required(optional=True)
    def ask_company_question(company_id):
        company = models.Company.query.get_or_404(company_id)
        data = request.get_json()
        question_text = data.get('question_text')
        
        if not question_text:
            return jsonify({"error": "Question text is required"}), 400
            
        user_id = get_jwt_identity()
        
        new_question = models.CompanyQuestion(
            company_id=company_id,
            user_id=user_id,
            question_text=question_text,
            asked_by_name=data.get('asked_by', 'Anonymous')
        )
        
        db.session.add(new_question)
        db.session.commit()
        
        # Log activity
        user = models.User.query.get(user_id) if user_id else None
        user_name = f"{user.first_name} {user.last_name}" if user else data.get('asked_by', 'Anonymous')
        create_activity(user_name, "asked a question for", company.name)

        return jsonify({"message": "Question posted successfully", "question": new_question.to_dict()}), 201

    @app.route('/my-questions', methods=['GET'])
    @jwt_required()
    def get_my_questions():
        user_id = get_jwt_identity()
        questions = models.CompanyQuestion.query.options(
            joinedload(models.CompanyQuestion.user),
            joinedload(models.CompanyQuestion.company),
            joinedload(models.CompanyQuestion.answers).joinedload(models.QuestionAnswer.user)
        ).filter_by(user_id=user_id).order_by(models.CompanyQuestion.created_at.desc()).all()

        return jsonify([q.to_dict() for q in questions]), 200

    @app.route('/alumni/assist-questions', methods=['GET'])
    @jwt_required()
    def get_alumni_assist_questions():
        """Returns questions from companies where this alumni has shared an experience."""
        user_id = get_jwt_identity()
        user = models.User.query.get(user_id)
        if not user or user.role != 'Alumni':
            return jsonify({"error": "Alumni access required"}), 403

        # Get all company IDs where this alumni has an approved experience
        alumni_company_ids = db.session.query(models.InterviewExperience.company_id).filter_by(
            user_id=user_id, status='approved'
        ).distinct().all()
        alumni_company_ids = [row[0] for row in alumni_company_ids]

        # Also include the company they currently work at from their profile
        profile = models.UserProfile.query.filter_by(user_id=user_id).first()
        if profile and profile.current_company:
            current_work_company = models.Company.query.filter(
                models.Company.name.ilike(profile.current_company.strip())
            ).first()
            if current_work_company and current_work_company.id not in alumni_company_ids:
                alumni_company_ids.append(current_work_company.id)

        if not alumni_company_ids:
            return jsonify([]), 200

        # Return all questions for those companies with optimized fetching
        questions = models.CompanyQuestion.query.options(
            joinedload(models.CompanyQuestion.user),
            joinedload(models.CompanyQuestion.company),
            joinedload(models.CompanyQuestion.answers).joinedload(models.QuestionAnswer.user)
        ).filter(
            models.CompanyQuestion.company_id.in_(alumni_company_ids)
        ).order_by(models.CompanyQuestion.created_at.desc()).limit(50).all()

        return jsonify([q.to_dict() for q in questions]), 200

    @app.route('/questions/<int:question_id>/answers', methods=['POST'])
    @jwt_required()
    def answer_question(question_id):
        question = models.CompanyQuestion.query.get_or_404(question_id)
        data = request.get_json()
        answer_text = data.get('answer_text')
        
        if not answer_text:
            return jsonify({"error": "Answer text is required"}), 400
            
        user_id = get_jwt_identity()
        user = models.User.query.get(user_id) or models.Admin.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Only alumni or admins should ideally answer, but we'll allow role-based check
        is_alumni = getattr(user, 'role', 'Student') == 'Alumni'
        is_admin = getattr(user, 'role', '') == 'Admin'
        
        if not (is_alumni or is_admin):
             return jsonify({"error": "Only alumni or admins can answer questions"}), 403

        if is_alumni:
            # Ensure this alumni has an approved experience at the company this question is for
            experience = models.InterviewExperience.query.filter_by(
                user_id=user_id,
                company_id=question.company_id,
                status='approved'
            ).first()
            
            works_there = False
            if not experience:
                # Check if they currently work there based on their profile
                profile = models.UserProfile.query.filter_by(user_id=user_id).first()
                if profile and profile.current_company and question.company:
                    if profile.current_company.lower().strip() == question.company.name.lower().strip():
                        works_there = True
            
            if not experience and not works_there:
                return jsonify({"error": "You can only answer questions for companies you have worked at"}), 403

        new_answer = models.QuestionAnswer(
            question_id=question_id,
            user_id=user_id if getattr(user, 'role', '') != 'Admin' else None, # Link to user if not admin
            answer_text=answer_text,
            answerer_name=f"{user.first_name} {user.last_name}" if not is_admin else "System Admin",
            answerer_role=data.get('answerer_role', 'Verified Alumni' if is_alumni else 'Admin'),
            is_verified_alumni=is_alumni
        )
        
        db.session.add(new_answer)
        db.session.commit()

        # Trigger User Notification to the person who asked
        if str(question.user_id) != str(user_id):  # Don't notify if answering own question
            answerer = f"{user.first_name} {user.last_name}" if not is_admin else "A System Admin"
            create_user_notification(
                user_id=question.user_id,
                title="New Answer Received",
                description=f"{answerer} has answered your question about {question.company.name}.",
                type="Question",
                target_id=question.id
            )
        
        return jsonify({"message": "Answer posted successfully", "answer": new_answer.to_dict()}), 201


    @app.route('/questions/<int:question_id>', methods=['DELETE'])
    @jwt_required()
    def delete_question(question_id):
        question = models.CompanyQuestion.query.get_or_404(question_id)
        current_user_id = get_jwt_identity()
        
        # Only the user who asked the question (or an admin) can delete it
        if str(question.user_id) != str(current_user_id):
            # Check if user is admin
            admin = models.Admin.query.get(current_user_id)
            if not admin:
                return jsonify({"error": "Unauthorized"}), 403
                
        db.session.delete(question)
        db.session.commit()
        return jsonify({"message": "Question deleted successfully"}), 200

    @app.route('/answers/<int:answer_id>', methods=['DELETE'])
    @jwt_required()
    def delete_answer(answer_id):
        answer = models.QuestionAnswer.query.get_or_404(answer_id)
        current_user_id = get_jwt_identity()
        
        # Only the user who posted the answer (or an admin) can delete it
        if str(answer.user_id) != str(current_user_id):
            # Check if user is admin
            admin = models.Admin.query.get(current_user_id)
            if not admin:
                return jsonify({"error": "Unauthorized"}), 403
                
        db.session.delete(answer)
        db.session.commit()
        
        return jsonify({"message": "Answer deleted successfully"}), 200

    @app.route('/experiences/<int:experience_id>', methods=['GET'])
    @jwt_required(optional=True)
    def get_experience(experience_id):
        experience = models.InterviewExperience.query.get_or_404(experience_id)
        
        current_user_id = None
        try:
            current_user_id = get_jwt_identity()
        except:
            pass
            
        exp_dict = experience.to_dict(current_user_id=current_user_id)
        # Add company name for convenience
        exp_dict['company_name'] = experience.company.name
        return jsonify(exp_dict), 200

    @app.route('/experiences/<int:experience_id>/helpful', methods=['POST'])
    @jwt_required()
    def toggle_helpful(experience_id):
        user_id = get_jwt_identity()
        experience = models.InterviewExperience.query.get_or_404(experience_id)
        user = models.User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        if user in experience.helpful_voters:
            experience.helpful_voters.remove(user)
            experience.helpful_count = max(0, experience.helpful_count - 1)
            message = "Removed from helpful"
            is_helpful = False
        else:
            experience.helpful_voters.append(user)
            experience.helpful_count += 1
            message = "Marked as helpful"
            is_helpful = True
            
        db.session.commit()
        return jsonify({
            "message": message, 
            "is_helpful": is_helpful, 
            "helpful_count": experience.helpful_count
        }), 200

    @app.route('/experiences/<int:experience_id>/save', methods=['POST'])
    @jwt_required()
    def toggle_save(experience_id):
        user_id = get_jwt_identity()
        experience = models.InterviewExperience.query.get_or_404(experience_id)
        user = models.User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        if user in experience.saved_by_users:
            experience.saved_by_users.remove(user)
            message = "Removed from saved"
            is_saved = False
        else:
            experience.saved_by_users.append(user)
            message = "Experience saved"
            is_saved = True
            
        db.session.commit()
        return jsonify({
            "message": message, 
            "is_saved": is_saved
        }), 200

    @app.route('/saved-experiences', methods=['GET'])
    @jwt_required()
    def get_saved_experiences():
        user_id = get_jwt_identity()
        user = models.User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Filter for approved/unsuspended items
        saved_items = user.saved_experiences.filter(
            models.InterviewExperience.status == 'approved'
        ).all()
        
        return jsonify([exp.to_dict(current_user_id=user_id) for exp in saved_items]), 200

    @app.route('/experiences', methods=['POST'])
    @jwt_required()
    def submit_experience():
        data = request.get_json()
        user_id = get_jwt_identity()
        
        # Required fields validation
        required_fields = ['company_id', 'user_role', 'difficulty']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        new_experience = models.InterviewExperience(
            user_id=user_id,
            company_id=data['company_id'],
            user_role=data['user_role'],
            difficulty=data['difficulty'],
            is_selected=data.get('is_selected', False),
            work_mode=data.get('work_mode'),
            candidate_type=data.get('candidate_type'),
            my_experience=data.get('my_experience'),
            brief=data.get('brief'),
            application_process=data.get('application_process'),
            interview_rounds=data.get('interview_rounds'),
            technical_questions=data.get('technical_questions'),
            behavioral_questions=data.get('behavioral_questions'),
            mistakes=data.get('mistakes'),
            preparation_strategy=data.get('preparation_strategy'),
            final_advice=data.get('final_advice'),
            status='pending' # Requires admin approval
        )
        
        db.session.add(new_experience)
        db.session.commit()
        
        # Log activity
        user = models.User.query.get(user_id)
        company = models.Company.query.get(data['company_id'])
        create_activity(f"{user.first_name} {user.last_name}", "submitted a new interview experience for", company.name)

        # Create notification for admin
        create_admin_notification(
            title="New Experience Submitted",
            description=f"{user.first_name} {user.last_name} submitted a new experience for {company.name}.",
            type="Experience",
            target_id=new_experience.id
        )
        
        return jsonify({"message": "Experience submitted successfully", "experience_id": new_experience.id}), 201

    @app.route('/admin/pending-experiences', methods=['GET'])
    @jwt_required()
    def get_pending_experiences():
        # Check if user is admin
        user_id = get_jwt_identity()
        admin = models.Admin.query.get(user_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        pending = models.InterviewExperience.query.filter_by(status='pending').all()
        return jsonify([exp.to_dict(current_user_id=user_id) for exp in pending]), 200

    @app.route('/admin/users', methods=['GET'])
    @jwt_required()
    def get_all_users():
        # Check if user is admin
        user_id = get_jwt_identity()
        admin = models.Admin.query.get(user_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        users = models.User.query.all()
        return jsonify([user.to_dict() for user in users]), 200

    @app.route('/admin/users/<int:user_id>/suspend', methods=['PUT'])
    @jwt_required()
    def suspend_user(user_id):
        admin_id = get_jwt_identity()
        admin = models.Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        user = models.User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        try:
            user.is_suspended = True
            user.status = 'suspended'
            db.session.commit()
            return jsonify({"message": f"{user.first_name} {user.last_name} has been suspended"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/admin/users/<int:user_id>/unsuspend', methods=['PUT'])
    @jwt_required()
    def unsuspend_user(user_id):
        admin_id = get_jwt_identity()
        admin = models.Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        user = models.User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        try:
            user.is_suspended = False
            user.status = 'active'
            db.session.commit()
            return jsonify({"message": f"{user.first_name} {user.last_name} has been reactivated"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/admin/users/<int:user_id>', methods=['DELETE'])
    @jwt_required()
    def admin_delete_user(user_id):
        admin_id = get_jwt_identity()
        admin = models.Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        user = models.User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        try:
            # OTPs are linked by email, not a formal foreign key, so we keep manual deletion
            models.OTP.query.filter_by(email=user.email).delete()

            # Profile, Experiences, Questions, Answers, Notifications, and Reports are now handled by cascading deletes
            db.session.delete(user)
            db.session.commit()
            return jsonify({"message": f"User {user.first_name} {user.last_name} and all associated data deleted successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/admin/pending-alumni', methods=['GET'])
    @jwt_required()
    def get_pending_alumni():
        admin_id = get_jwt_identity()
        admin = models.Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        pending = models.User.query.filter_by(role='Alumni', status='pending').all()
        return jsonify([user.to_dict() for user in pending]), 200

    @app.route('/admin/users/<int:user_id>/approve', methods=['PUT'])
    @jwt_required()
    def approve_user(user_id):
        admin_id = get_jwt_identity()
        admin = models.Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        user = models.User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        try:
            user.status = 'active'
            # If they were a student requesting upgrade, change their role to Alumni and apply pending changes
            if user.role == 'Student' and user.pending_details:
                pd = user.pending_details
                if pd.get('first_name'): user.first_name = pd['first_name']
                if pd.get('last_name'): user.last_name = pd['last_name']
                if pd.get('email'): user.email = pd['email']
                if pd.get('phone_number'): user.phone_number = pd['phone_number']
                
                profile = models.UserProfile.query.filter_by(user_id=user.id).first()
                if not profile:
                    profile = models.UserProfile(user_id=user.id)
                    db.session.add(profile)
                
                if pd.get('phone_number'): profile.phone_number = pd['phone_number']
                if pd.get('major'): profile.major = pd['major']
                if pd.get('expected_grad_year'): profile.expected_grad_year = pd['expected_grad_year']
                profile.current_year = "Alumni"
                if pd.get('bio'): profile.bio = pd['bio']
                if pd.get('profile_pic'): profile.profile_pic = pd['profile_pic']
                if pd.get('linkedin_url'): profile.linkedin_url = pd['linkedin_url']
                if pd.get('current_company'): profile.current_company = pd['current_company']
                if pd.get('designation'): profile.designation = pd['designation']
                if pd.get('specialization'): profile.specialization = pd['specialization']
                
                user.pending_details = None # Clear after applying
                user.role = 'Alumni'
            elif user.role == 'Student':
                user.role = 'Alumni'
                
            db.session.commit()

            # Trigger notification for successful upgrade logic
            if user.role == 'Alumni':
                create_user_notification(
                    user_id=user.id,
                    title="Account Upgraded",
                    description="Your request to become an Alumni has been approved!",
                    type="Upgrade"
                )

            return jsonify({"message": f"User {user.first_name} {user.last_name} approved successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/admin/users/<int:user_id>/reject', methods=['DELETE'])
    @jwt_required()
    def reject_user(user_id):
        admin_id = get_jwt_identity()
        admin = models.Admin.query.get(admin_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        user = models.User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        try:
            # If they were a student requesting upgrade, keep them as active student
            is_student_upgrade = user.role == 'Student' and user.status == 'pending'

            if user.role == 'Student':
                user.status = 'active'
                user.pending_details = None # Clear pending details on rejection
            else:
                user.status = 'rejected'
                
            db.session.commit()

            # Trigger notification for rejected upgrade
            if is_student_upgrade:
                create_user_notification(
                    user_id=user.id,
                    title="Upgrade Request Denied",
                    description="Your request to upgrade to an Alumni account was not approved by administrators.",
                    type="Upgrade"
                )

            return jsonify({"message": f"Request from {user.first_name} {user.last_name} has been rejected"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/experiences/<int:experience_id>/review', methods=['PUT'])
    @jwt_required()
    def review_experience(experience_id):
        # Check if user is admin
        user_id = get_jwt_identity()
        admin = models.Admin.query.get(user_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403

        experience = models.InterviewExperience.query.get_or_404(experience_id)
        data = request.get_json()
        status = data.get('status')

        if status not in ['approved', 'rejected']:
            return jsonify({"error": "Invalid status. Must be 'approved' or 'rejected'"}), 400

        try:
            experience.status = status
            db.session.commit()

            # Trigger User Notification
            action_word = "approved and is now visible" if status == 'approved' else "rejected"
            create_user_notification(
                user_id=experience.user_id,
                title=f"Experience {status.capitalize()}",
                description=f"Your interview experience for {experience.company.name} was {action_word} by an administrator.",
                type="Experience",
                target_id=experience.id
            )

            # Notify all company followers if approved
            if status == 'approved':
                company = experience.company
                followers = company.followers.all()
                for follower in followers:
                    if follower.id != experience.user_id: # Don't notify the author again
                        create_user_notification(
                            user_id=follower.id,
                            title="New Interview Experience",
                            description=f"A new interview experience for {company.name} has been shared and approved.",
                            type="Experience",
                            target_id=experience.id
                        )

            return jsonify({"message": f"Experience {status} successfully"}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/experiences/<int:experience_id>', methods=['DELETE'])
    @jwt_required()
    def delete_experience(experience_id):
        current_identity = get_jwt_identity()
        experience = models.InterviewExperience.query.get_or_404(experience_id)

        # Check if current user is an admin
        is_admin = models.Admin.query.get(current_identity) is not None

        # Only the owner or an admin can delete their experience
        if not is_admin and str(experience.user_id) != str(current_identity):
            return jsonify({"error": "You are not authorized to delete this experience"}), 403

        try:
            db.session.delete(experience)
            db.session.commit()
            return jsonify({"message": "Experience deleted successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/experiences/<int:experience_id>', methods=['PUT'])
    @jwt_required()
    def update_experience(experience_id):
        user_id = get_jwt_identity()
        experience = models.InterviewExperience.query.get_or_404(experience_id)

        # Only the owner can edit their experience
        if str(experience.user_id) != str(user_id):
            return jsonify({"error": "You are not authorized to edit this experience"}), 403

        data = request.get_json()
        
        try:
            # Update fields if present in request
            if 'user_role' in data: experience.user_role = data['user_role']
            if 'difficulty' in data: experience.difficulty = data['difficulty']
            if 'is_selected' in data: experience.is_selected = data['is_selected']
            if 'work_mode' in data: experience.work_mode = data['work_mode']
            if 'candidate_type' in data: experience.candidate_type = data['candidate_type']
            if 'my_experience' in data: experience.my_experience = data['my_experience']
            if 'brief' in data: experience.brief = data['brief']
            if 'application_process' in data: experience.application_process = data['application_process']
            if 'interview_rounds' in data: experience.interview_rounds = data['interview_rounds']
            if 'technical_questions' in data: experience.technical_questions = data['technical_questions']
            if 'behavioral_questions' in data: experience.behavioral_questions = data['behavioral_questions']
            if 'mistakes' in data: experience.mistakes = data['mistakes']
            if 'preparation_strategy' in data: experience.preparation_strategy = data['preparation_strategy']
            if 'final_advice' in data: experience.final_advice = data['final_advice']
            
            # Reset status to pending for re-review
            experience.status = 'pending'
            
            # Clear all existing reports so users can re-report if still incorrect
            models.Report.query.filter_by(experience_id=experience_id, content_type='experience').delete()
            
            db.session.commit()
            
            # Trigger Admin Notification for update
            user = models.User.query.get(user_id)
            user_name = f"{user.first_name} {user.last_name}" if user else 'An alumni'
            create_admin_notification(
                title="Interview Experience Updated",
                description=f"{user_name} updated their experience for {experience.company.name}. Requires re-review.",
                type="Experience",
                target_id=experience.id
            )
            
            return jsonify({"message": "Experience updated and sent for re-review", "id": experience.id}), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500


    @app.route('/my-experiences', methods=['GET'])
    @jwt_required()
    def get_my_experiences():
        user_id = get_jwt_identity()
        experiences = models.InterviewExperience.query.filter_by(user_id=user_id).all()
        # Add company name for each experience
        result = []
        for exp in experiences:
            exp_dict = exp.to_dict(current_user_id=user_id)
            exp_dict['company_name'] = exp.company.name
            result.append(exp_dict)
        return jsonify(result), 200

    @app.route('/experiences/<int:experience_id>/report', methods=['POST'])
    @jwt_required()
    def report_experience(experience_id):
        user_id = get_jwt_identity()
        data = request.get_json()
        reason = data.get('reason', 'General reporting')
        
        # Check if already reported by this user
        existing = models.Report.query.filter_by(experience_id=experience_id, user_id=user_id, content_type='experience').first()
        if existing:
            return jsonify({"message": "You have already reported this experience"}), 200

        new_report = models.Report(
            content_type='experience',
            experience_id=experience_id,
            user_id=user_id,
            reason=reason
        )
        db.session.add(new_report)
        
        # Add notification for admin
        notification = models.Notification(
            title="Experience Reported",
            description=f"An experience has been reported for: {reason}",
            type="Experience",
            target_id=experience_id
        )
        db.session.add(notification)
        
        db.session.commit()
        
        # Log activity
        user = models.User.query.get(user_id)
        create_activity(f"{user.first_name} {user.last_name}", "reported an experience at", "the platform")

        return jsonify({"message": "Report submitted successfully"}), 201

    @app.route('/questions/<int:question_id>/report', methods=['POST'])
    @jwt_required()
    def report_question(question_id):
        user_id = get_jwt_identity()
        data = request.get_json()
        reason = data.get('reason', 'General reporting')
        
        existing = models.Report.query.filter_by(question_id=question_id, user_id=user_id, content_type='question').first()
        if existing:
            return jsonify({"message": "You have already reported this question"}), 200

        new_report = models.Report(
            content_type='question',
            question_id=question_id,
            user_id=user_id,
            reason=reason
        )
        db.session.add(new_report)
        
        notification = models.Notification(
            title="Question Reported",
            description=f"A question has been reported for: {reason}",
            type="Question",
            target_id=question_id
        )
        db.session.add(notification)
        
        db.session.commit()
        
        # Log activity
        user = models.User.query.get(user_id)
        create_activity(f"{user.first_name} {user.last_name}", "reported a question at", "the platform")

        return jsonify({"message": "Report submitted successfully"}), 201

    @app.route('/answers/<int:answer_id>/report', methods=['POST'])
    @jwt_required()
    def report_answer(answer_id):
        user_id = get_jwt_identity()
        data = request.get_json()
        reason = data.get('reason', 'General reporting')
        
        existing = models.Report.query.filter_by(answer_id=answer_id, user_id=user_id, content_type='answer').first()
        if existing:
            return jsonify({"message": "You have already reported this answer"}), 200

        new_report = models.Report(
            content_type='answer',
            answer_id=answer_id,
            user_id=user_id,
            reason=reason
        )
        db.session.add(new_report)
        
        notification = models.Notification(
            title="Answer Reported",
            description=f"An answer has been reported for: {reason}",
            type="Answer",
            target_id=answer_id
        )
        db.session.add(notification)
        
        db.session.commit()
        
        # Log activity
        user = models.User.query.get(user_id)
        create_activity(f"{user.first_name} {user.last_name}", "reported an answer at", "the platform")

        return jsonify({"message": "Report submitted successfully"}), 201

    @app.route('/admin/reports', methods=['GET'])
    @jwt_required()
    def get_reports():
        # Check admin
        user_id = get_jwt_identity()
        admin = models.Admin.query.get(user_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403
            
        reports = models.Report.query.filter_by(status='pending').all()
        return jsonify([r.to_dict() for r in reports]), 200

    @app.route('/admin/reports/<int:report_id>/keep', methods=['POST'])
    @jwt_required()
    def keep_reported_content(report_id):
        # Check admin
        user_id = get_jwt_identity()
        admin = models.Admin.query.get(user_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403
            
        report = models.Report.query.get_or_404(report_id)
        report.status = 'kept'
        db.session.commit()
        return jsonify({"message": "Report dismissed, content kept"}), 200

    @app.route('/admin/reports/<int:report_id>/remove', methods=['POST'])
    @jwt_required()
    def remove_reported_content(report_id):
        # Check admin
        user_id = get_jwt_identity()
        admin = models.Admin.query.get(user_id)
        if not admin:
            return jsonify({"error": "Admin access required"}), 403
            
        report = models.Report.query.get_or_404(report_id)
        
        try:
            if report.content_type == 'experience' and report.experience:
                target = report.experience
                # Purge legacy stale table (MySQL FK requires this if it lacks CASCADE)
                db.session.execute(
                    text("DELETE FROM experience_reports WHERE experience_id = :eid"),
                    {"eid": target.id}
                )
                db.session.delete(target)
            elif report.content_type == 'question' and report.question:
                db.session.delete(report.question)
            elif report.content_type == 'answer' and report.answer:
                db.session.delete(report.answer)
            else:
                # Content already gone; just mark the report resolved
                report.status = 'removed'
            
            db.session.commit()
            return jsonify({"message": "Content removed permanently"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/delete-account', methods=['DELETE'])
    @jwt_required()
    def delete_account():
        user_id = get_jwt_identity()
        
        # Determine if it's an Admin or User based on some criteria 
        # (e.g., checking if the ID exists in users table first)
        user = models.User.query.get(user_id)
        if user:
            # OTPs are linked by email, not a formal foreign key
            models.OTP.query.filter_by(email=user.email).delete()
            
            # Profile, Experiences, Questions, Answers, Notifications, and Reports are now handled by cascading deletes
            db.session.delete(user)
            db.session.commit()
            return jsonify({"message": "Account deleted successfully"}), 200
        
        # Check if it's an Admin
        admin = models.Admin.query.get(user_id)
        if admin:
            db.session.delete(admin)
            db.session.commit()
            return jsonify({"message": "Admin account deleted successfully"}), 200
            
        return jsonify({"error": "User not found"}), 404

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
