from extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

user_group = db.Table('user_group',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'), primary_key=True)
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    daps = db.relationship('Dap', backref='owner', lazy=True)
    groups = db.relationship('Group', secondary=user_group, lazy='subquery',
                             backref=db.backref('users', lazy=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Dap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom_projet = db.Column(db.String(255), nullable=False)
    numero_reference = db.Column(db.String(100), unique=True, nullable=False)
    numero_court = db.Column(db.String(50), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    contenu_xml = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    permissions = db.relationship('Permission', backref='dap', lazy=True, cascade="all, delete-orphan")

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    permissions = db.relationship('Permission', backref='group', lazy=True, cascade="all, delete-orphan")
    
class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    can_edit = db.Column(db.Boolean, default=False)
    dap_id = db.Column(db.Integer, db.ForeignKey('dap.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)