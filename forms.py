from flask_wtf import FlaskForm
from wtforms import Form, StringField, PasswordField, SubmitField, BooleanField, SelectMultipleField, IntegerField, TextAreaField, FieldList, FormField
from wtforms_sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Optional
from flask_wtf.file import FileField, FileRequired, FileAllowed
from models import User, Group
from wtforms.widgets import CheckboxInput, ListWidget, Input, TextInput
from markupsafe import Markup
from collections import OrderedDict
from xml_utils import merge_structured_data_for_form

# Custom widget to render only the input tag for text-like fields
class CustomTextInputWidget(TextInput):
    def __call__(self, field, **kwargs):
        return Markup(super().__call__(field, **kwargs))

# Custom widget to render only the input tag for boolean fields
class CustomCheckboxInputWidget(CheckboxInput):
    def __call__(self, field, **kwargs):
        return Markup(super().__call__(field, **kwargs))

class RegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('S\'inscrire')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ce nom d\'utilisateur est déjà pris.')

class LoginForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember = BooleanField('Se souvenir de moi')
    submit = SubmitField('Connexion')

class UploadForm(FlaskForm):
    file = FileField('Fichier XML APAFIS', validators=[FileRequired(), FileAllowed(['xml'], 'Seuls les fichiers XML sont autorisés !')])
    numero_court = StringField('Numéro Court (optionnel)', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Uploader')

# Base form for dynamic XML fields
class BaseXmlFieldForm(FlaskForm):
    # This form will be dynamically populated
    pass

def create_dynamic_form_class(structured_data, form_label_map, parent_path=''):
    """
    Recursively creates a WTForms FlaskForm class based on the structured XML data.
    """
    form_fields = OrderedDict()
    form_name = structured_data.get('tag', 'DynamicForm') + "Form"

    # Add a field for the current element's value if it exists and is not a parent
    if structured_data.get('value') is not None and not structured_data.get('children'):
        field_label = form_label_map.get(structured_data['tag'], structured_data['tag'].replace('_', ' '))
        field_name = structured_data['tag']

        # Determine field type based on value
        if isinstance(structured_data['value'], bool):
            form_fields[field_name] = BooleanField(field_label, default=structured_data['value'])
        elif isinstance(structured_data['value'], str) and (len(structured_data['value']) > 50 or '\n' in structured_data['value']):
            form_fields[field_name] = TextAreaField(field_label, default=structured_data['value'])
        else:
            form_fields[field_name] = StringField(field_label, default=structured_data['value'], widget=CustomTextInputWidget())

    if structured_data.get('children'):
        for child_tag, children_list in structured_data['children'].items():
            child_field_name = child_tag

            if len(children_list) > 1:
                # Merge all instances to get a superset structure for the form class
                merged_structure = merge_structured_data_for_form(children_list)
                nested_form_class = create_dynamic_form_class(merged_structure, form_label_map, parent_path=f"{parent_path}/{child_tag}")
                field_list_instance = FieldList(FormField(nested_form_class), min_entries=len(children_list))
                field_list_instance.type = 'FieldList'
                form_fields[child_field_name] = field_list_instance
            else:
                nested_form_class = create_dynamic_form_class(children_list[0], form_label_map, parent_path=f"{parent_path}/{child_tag}")
                form_field_instance = FormField(nested_form_class)
                form_field_instance.type = 'FormField'
                form_fields[child_field_name] = form_field_instance

    # Dynamically create the form class
    # Use Form instead of FlaskForm for dynamic forms to avoid CSRF issues in nested structures,
    # especially since we handle CSRF in the parent metadata form.
    DynamicForm = type(form_name, (Form,), form_fields)
    return DynamicForm

class DynamicDapForm(FlaskForm):
    # This will be replaced by the dynamically generated form
    pass

class UserForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Mot de passe', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[Optional(), EqualTo('password', message='Les mots de passe doivent correspond.')])
    is_admin = BooleanField('Administrateur')
    groups = SelectMultipleField('Groupes', coerce=int, option_widget=CheckboxInput(), widget=ListWidget())
    submit = SubmitField('Sauvegarder')

    def __init__(self, original_username=None, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.groups.choices = [(g.id, g.name) for g in Group.query.order_by('name').all()]

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Ce nom d\'utilisateur est déjà pris.')

class GroupForm(FlaskForm):
    name = StringField('Nom du Groupe', validators=[DataRequired(), Length(min=2, max=80)])
    users = SelectMultipleField('Membres', coerce=int, option_widget=CheckboxInput(), widget=ListWidget())
    submit = SubmitField('Sauvegarder')

    def __init__(self, original_name=None, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        self.original_name = original_name
        self.users.choices = [(u.id, u.username) for u in User.query.order_by('username').all()]

    def validate_name(self, name):
        if name.data != self.original_name:
            group = Group.query.filter_by(name=name.data).first()
            if group:
                raise ValidationError('Ce nom de groupe est déjà pris.')

class DapMetadataForm(FlaskForm):
    nom_projet = StringField('Titre du Projet', validators=[DataRequired(), Length(max=255)])
    numero_reference = StringField('Référence du Dossier', validators=[DataRequired(), Length(max=100)])
    numero_court = StringField('Numéro Court', validators=[Optional(), Length(max=50)])
    version = IntegerField('Version', validators=[DataRequired()])
    submit = SubmitField('Sauvegarder les modifications')

class AddPermissionForm(FlaskForm):
    user_id = QuerySelectField(
        'Utilisateur',
        query_factory=lambda: User.query.order_by('username').all(),
        get_label='username',
        allow_blank=True,
        blank_text='-- Sélectionner un utilisateur --'
    )
    group_id = QuerySelectField(
        'Groupe',
        query_factory=lambda: Group.query.order_by('name').all(),
        get_label='name',
        allow_blank=True,
        blank_text='-- Sélectionner un groupe --'
    )
    can_edit = BooleanField('Peut éditer', default=False)
    submit = SubmitField('Ajouter la permission')

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        
        if not self.user_id.data and not self.group_id.data:
            self.user_id.errors.append('Veuillez sélectionner un utilisateur OU un groupe.')
            self.group_id.errors.append('Veuillez sélectionner un utilisateur OU un groupe.')
            return False
        
        if self.user_id.data and self.group_id.data:
            self.user_id.errors.append('Veuillez sélectionner un utilisateur OU un groupe, pas les deux.')
            self.group_id.errors.append('Veuillez sélectionner un utilisateur OU un groupe, pas les deux.')
            return False
        
        return True
