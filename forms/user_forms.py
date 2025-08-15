"""
WTForms for user authentication
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models.auth import User

class LoginForm(FlaskForm):
    """Login form"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class SignupForm(FlaskForm):
    """Signup form"""
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=3, max=80, message="Username must be between 3 and 80 characters")
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    relationship = SelectField('Relationship to Child', 
                              choices=[('Father', 'Father'), ('Mother', 'Mother'), 
                                     ('Guardian', 'Guardian'), ('Grandparent', 'Grandparent'),
                                     ('Babysitter', 'Babysitter'), ('Other', 'Other')],
                              default='Guardian')
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        """Check if username already exists"""
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        """Check if email already exists"""
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class ChangePasswordForm(FlaskForm):
    """Change password form for first-time login"""
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(), 
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(), 
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')

class UserManagementForm(FlaskForm):
    """User management form for admin"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    relationship = SelectField('Relationship to Child', 
                              choices=[('Father', 'Father'), ('Mother', 'Mother'), 
                                     ('Guardian', 'Guardian'), ('Grandparent', 'Grandparent'),
                                     ('Babysitter', 'Babysitter'), ('Other', 'Other')],
                              default='Guardian')
    active = SelectField('Status', choices=[('1', 'Active'), ('0', 'Inactive')], coerce=str)
    is_admin = BooleanField('Admin User')
    submit = SubmitField('Update User')

class CreateUserForm(FlaskForm):
    """Create new user form for admin"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    relationship = SelectField('Relationship to Child', 
                              choices=[('Father', 'Father'), ('Mother', 'Mother'), 
                                     ('Guardian', 'Guardian'), ('Grandparent', 'Grandparent'),
                                     ('Babysitter', 'Babysitter'), ('Other', 'Other')],
                              default='Guardian')
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    active = BooleanField('Active User', default=False)
    is_admin = BooleanField('Admin User', default=False)
    submit = SubmitField('Create User')
    
    def validate_username(self, username):
        """Check if username already exists"""
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        """Check if email already exists"""
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')
