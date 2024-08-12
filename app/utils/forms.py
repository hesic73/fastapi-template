from wtforms import Form, StringField, validators, EmailField, PasswordField


class RegistrationForm(Form):
    username = StringField('Username', [validators.Length(
        min=4, max=25), validators.DataRequired()])
    email = EmailField('Email Address', [validators.Length(
        min=6, max=35), validators.Email(), validators.DataRequired()])
    password = PasswordField('New Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match'),
        validators.DataRequired()
    ])
    confirm = PasswordField('Repeat Password', [validators.DataRequired()])


class LoginForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=25)])
    password = PasswordField('Password', [validators.DataRequired()])
