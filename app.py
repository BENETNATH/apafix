from forms import LoginForm, RegistrationForm, UploadForm, DynamicDapForm, UserForm, GroupForm, AddPermissionForm, DapMetadataForm, CustomTextInputWidget, CustomCheckboxInputWidget
from io import BytesIO
import os
import re
from collections import OrderedDict
from dotenv import load_dotenv
from flask import Flask, request, send_file, abort, jsonify
from functools import wraps
from xml_utils import generate_docx_from_xml, flatten_xml_to_form_data, reconstruct_xml_from_form_data, parse_xml_to_structured_data, populate_nested_form_from_structured_data, reconstruct_xml_from_structured_form_data, FORM_LABEL_MAP
import xml.etree.ElementTree as ET
from wtforms import StringField, TextAreaField, IntegerField, BooleanField, FieldList, FormField
from forms import create_dynamic_form_class # Import the new function
from extensions import db, migrate, login_manager
from flask_login import current_user, login_user, logout_user, login_required
from flask import flash, redirect, url_for, render_template

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'une-cle-secrete-par-defaut')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///apafix.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    import models # Import here so create_all knows about the models
    with app.app_context():
        db.create_all()
    login_manager.login_view = 'login'
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_message_category = "info"
    from create_admin import register_commands
    register_commands(app)
    return app

app = create_app()
from models import Dap, User, Group, Permission, Snippet
import language_tool_python

try:
    grammar_tool = language_tool_python.LanguageTool('fr')
except Exception as e:
    grammar_tool = None
    app.logger.error(f"Failed to initialize LanguageTool: {e}")

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Accès non autorisé. Vous devez être administrateur.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
def check_permission(dap, user):
    if user.is_admin or dap.owner == user: return True
    user_permission = Permission.query.filter_by(dap_id=dap.id, user_id=user.id, can_edit=True).first()
    if user_permission: return True
    if user.groups:
        user_groups_ids = [g.id for g in user.groups]
        group_permission = Permission.query.filter(Permission.dap_id == dap.id, Permission.group_id.in_(user_groups_ids), Permission.can_edit == True).first()
        if group_permission: return True
    return False
@app.context_processor
def utility_processor():
    def get_heading_depth(label):
        """Return heading depth from numbered label prefix.
        '3.' → 1, '3.1.' → 2, '3.3.2.' → 3, '3.3.6.1.' → 4
        """
        if not label:
            return 0
        import re
        match = re.match(r'^(\d+\.)+', label)
        if match:
            return match.group().count('.')
        return 0
    return dict(check_permission=check_permission, get_heading_depth=get_heading_depth)

@app.route('/')
def index():
    if current_user.is_authenticated: return redirect(url_for('list_daps'))
    return render_template('index.html')
@app.route('/daps')
@login_required
def list_daps():
    all_daps = Dap.query.order_by(Dap.id.desc()).all()
    if current_user.is_admin:
        mes_saisines = [dap for dap in all_daps if dap.owner == current_user]
        saisines_partagees = [dap for dap in all_daps if dap.owner != current_user]
    else:
        owned_daps_ids = {dap.id for dap in all_daps if dap.owner == current_user}
        user_perms_ids = {p.dap_id for p in Permission.query.filter_by(user_id=current_user.id).all()}
        group_perms_ids = set()
        if current_user.groups:
            user_groups_ids = [g.id for g in current_user.groups]
            group_perms = Permission.query.filter(Permission.group_id.in_(user_groups_ids)).all()
            group_perms_ids = {p.dap_id for p in group_perms}
        
        allowed_dap_ids = user_perms_ids.union(group_perms_ids)
        
        mes_saisines = [dap for dap in all_daps if dap.id in owned_daps_ids]
        saisines_partagees = [dap for dap in all_daps if dap.id in allowed_dap_ids and dap.id not in owned_daps_ids]
        
    return render_template('daps.html', mes_saisines=mes_saisines, saisines_partagees=saisines_partagees)

@app.route('/api/check_grammar', methods=['POST'])
@login_required
def check_grammar():
    if not grammar_tool:
        return jsonify({'error': 'Le correcteur orthographique n\'est pas disponible sur ce serveur.'}), 503
    text = request.json.get('text', '')
    if not text:
        return jsonify({'matches': []})
    
    matches = grammar_tool.check(text)
    
    matches_dict = []
    for match in matches:
        matches_dict.append({
            'message': match.message,
            'replacements': match.replacements
        })
    return jsonify({'matches': matches_dict})

@app.route('/api/snippets', methods=['GET', 'POST'])
@login_required
def api_snippets():
    if request.method == 'POST':
        data = request.json
        titre = data.get('titre')
        contenu = data.get('contenu')
        if not titre or not contenu:
            return jsonify({'error': 'Titre et contenu obligatoires'}), 400
            
        snippet = Snippet(titre=titre, contenu=contenu, user_id=current_user.id)
        db.session.add(snippet)
        db.session.commit()
        return jsonify({'id': snippet.id, 'titre': snippet.titre, 'contenu': snippet.contenu}), 201
        
    else:
        search = request.args.get('q', '')
        accessible_user_ids = {current_user.id}
        if current_user.groups:
            for g in current_user.groups:
                for u in g.users:
                    accessible_user_ids.add(u.id)
                    
        query = Snippet.query.filter(Snippet.user_id.in_(accessible_user_ids))
        if search:
            query = query.filter(Snippet.titre.ilike(f'%{search}%') | Snippet.contenu.ilike(f'%{search}%'))
            
        snippets = query.order_by(Snippet.id.desc()).all()
        result = []
        for s in snippets:
            result.append({
                'id': s.id,
                'titre': s.titre,
                'contenu': s.contenu,
                'auteur': User.query.get(s.user_id).username,
                'can_delete': (s.user_id == current_user.id or current_user.is_admin)
            })
        return jsonify(result)

@app.route('/api/snippets/<int:snippet_id>', methods=['DELETE'])
@login_required
def delete_snippet(snippet_id):
    snippet = Snippet.query.get_or_404(snippet_id)
    if snippet.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Non autorisé'}), 403
    db.session.delete(snippet)
    db.session.commit()
    return jsonify({'success': True}), 200
@app.route('/upload_dap', methods=['GET', 'POST'])
@login_required
def upload_dap():
    form = UploadForm()
    if form.validate_on_submit():
        file = form.file.data
        if file:
            try:
                file_content_bytes = file.read()
                file.seek(0)
                file_content = file_content_bytes.decode('utf-8')
                root = ET.fromstring(file_content_bytes)
                nom_projet = root.findtext('.//TitreProjet', default='N/A')
                numero_reference = root.findtext('.//ReferenceDossier', default='N/A')
                version = int(root.findtext('.//NumVersion', default='1'))
                numero_court = form.numero_court.data
                existing_dap = Dap.query.filter_by(numero_reference=numero_reference).first()
                if existing_dap:
                    flash(f'Une saisine avec la référence {numero_reference} existe déjà.', 'warning')
                    return render_template('upload.html', form=form)
                new_dap = Dap(nom_projet=nom_projet, numero_reference=numero_reference, numero_court=numero_court, version=version, contenu_xml=file_content, user_id=current_user.id)
                db.session.add(new_dap)
                db.session.commit()
                flash('Fichier XML de saisine uploadé et enregistré avec succès !', 'success')
                return redirect(url_for('list_daps'))
            except ET.ParseError:
                flash('Le fichier XML est invalide.', 'danger')
            except Exception as e:
                app.logger.error(f"Erreur lors de l'upload : {e}")
                flash('Une erreur est survenue lors du traitement du fichier.', 'danger')
    return render_template('upload.html', form=form)
@app.route('/edit_dap/<int:dap_id>', methods=['GET', 'POST'])
@login_required
def edit_dap(dap_id):
    dap = Dap.query.get_or_404(dap_id)
    if not check_permission(dap, current_user):
        flash('Vous n\'êtes pas autorisé à éditer cette saisine.', 'danger')
        return redirect(url_for('list_daps'))
    dap_metadata_form = DapMetadataForm(obj=dap)
    structured_xml_data = parse_xml_to_structured_data(dap.contenu_xml)

    # Dynamically create the form class for the XML content
    # The root element of structured_xml_data is 'Formulaire_Apafis'
    # We need to create a form for its children, as the root itself is just a container
    DynamicXmlFormClass = create_dynamic_form_class(structured_xml_data, FORM_LABEL_MAP)
    dynamic_xml_form = DynamicXmlFormClass(request.form)

    if request.method == 'POST':
        # Validate both forms to ensure we capture all errors
        meta_is_valid = dap_metadata_form.validate_on_submit()
        xml_is_valid = dynamic_xml_form.validate()
        
        if meta_is_valid and xml_is_valid:
            dap_metadata_form.populate_obj(dap)
            
            # Reconstruct XML from the nested form data
            updated_xml_content = reconstruct_xml_from_structured_form_data(structured_xml_data, dynamic_xml_form)
            dap.contenu_xml = updated_xml_content
            
            try:
                root = ET.fromstring(dap.contenu_xml.encode('utf-8'))
                dap.nom_projet = root.findtext('.//TitreProjet', default=dap.nom_projet)
                dap.version = int(root.findtext('.//NumVersion', default=dap.version))
            except ET.ParseError:
                flash('Le XML est devenu invalide après modification. Vérifiez les données.', 'danger')
            db.session.commit()
            flash('Saisine mise à jour avec succès !', 'success')
            return redirect(url_for('list_daps'))
        else:
            flash('Veuillez corriger les erreurs dans le formulaire.', 'danger')
            # Detailed logging for debugging
            app.logger.error(f"Erreur de validation pour le DAP {dap_id}")
            app.logger.error(f"Métadonnées erreurs: {dap_metadata_form.errors}")
            app.logger.error(f"Contenu dynamique erreurs: {dynamic_xml_form.errors}")
            
            for field, errors in dap_metadata_form.errors.items():
                for error in errors:
                    flash(f"Métadonnées - {dap_metadata_form[field].label.text} : {error}", 'warning')
            
            # Simple recursive error flashing for dynamic form
            def flash_recursive_errors(form_errors, prefix=''):
                for field_name, errors in form_errors.items():
                    if isinstance(errors, dict):
                        flash_recursive_errors(errors, prefix=f"{prefix}{field_name} > ")
                    elif isinstance(errors, list):
                        for err in errors:
                            if isinstance(err, dict):
                                flash_recursive_errors(err, prefix=f"{prefix}{field_name} > ")
                            else:
                                flash(f"Contenu - {prefix}{field_name} : {err}", 'warning')
            
            flash_recursive_errors(dynamic_xml_form.errors)
    
    if request.method == 'GET':
        # Populate the form with structured_xml_data
        populate_nested_form_from_structured_data(dynamic_xml_form, structured_xml_data)

    return render_template('edit_dap.html', 
                           dap=dap, 
                           dap_metadata_form=dap_metadata_form, 
                           dynamic_xml_form=dynamic_xml_form,
                           structured_xml_data=structured_xml_data) # Keep structured_xml_data for display logic if needed
@app.route('/download_xml/<int:dap_id>')
@login_required
def download_xml(dap_id):
    dap = Dap.query.get_or_404(dap_id)
    if not (check_permission(dap, current_user) or dap.owner == current_user or current_user.is_admin):
        flash('Vous n\'êtes pas autorisé à télécharger ce fichier.', 'danger')
        return redirect(url_for('list_daps'))
    xml_content = dap.contenu_xml
    buffer = BytesIO(xml_content.encode('utf-8'))
    buffer.seek(0)
    return send_file(buffer, mimetype='application/xml', as_attachment=True, download_name=f"EDITED_{dap.numero_reference}_v{dap.version}.xml")
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Votre compte a été créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/register.html', form=form)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Connexion réussie.', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('Échec de la connexion. Veuillez vérifier votre nom d\'utilisateur et votre mot de passe.', 'danger')
    return render_template('auth/login.html', form=form)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))
@app.route('/delete_dap/<int:dap_id>', methods=['POST'])
@login_required
def delete_dap(dap_id):
    dap = Dap.query.get_or_404(dap_id)
    if not (current_user.is_admin or dap.owner == current_user):
        flash('Vous n\'êtes pas autorisé à supprimer cette saisine.', 'danger')
        return redirect(url_for('list_daps'))
    db.session.delete(dap)
    db.session.commit()
    flash('Saisine supprimée avec succès.', 'success')
    return redirect(url_for('list_daps'))
@app.route('/download_docx/<int:dap_id>')
@login_required
def download_docx(dap_id):
    dap = Dap.query.get_or_404(dap_id)
    if not (check_permission(dap, current_user) or dap.owner == current_user or current_user.is_admin):
        flash('Vous n\'êtes pas autorisé à télécharger cette saisine.', 'danger')
        return redirect(url_for('list_daps'))
    try:
        doc_io = generate_docx_from_xml(dap.contenu_xml)
        download_name = f"APAFIS_{dap.numero_reference}_v{dap.version}.docx"
        return send_file(doc_io, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document', as_attachment=True, download_name=download_name)
    except (ValueError, IOError) as e:
        app.logger.error(f"Erreur de génération DOCX pour DAP {dap_id}: {e}")
        flash(str(e), 'danger')
    return redirect(url_for('list_daps'))
@app.route('/dap/<int:dap_id>/permissions', methods=['GET', 'POST'])
@login_required
def dap_permissions(dap_id):
    dap = Dap.query.get_or_404(dap_id)
    if dap.owner != current_user and not current_user.is_admin:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('list_daps'))
    add_permission_form = AddPermissionForm()
    if add_permission_form.validate_on_submit():
        user, group, can_edit = add_permission_form.user_id.data, add_permission_form.group_id.data, add_permission_form.can_edit.data
        if user:
            permission = Permission.query.filter_by(dap_id=dap.id, user_id=user.id).first()
            if permission: permission.can_edit = can_edit
            else: db.session.add(Permission(dap_id=dap.id, user_id=user.id, can_edit=can_edit))
            flash(f'Permission pour l\'utilisateur {user.username} mise à jour.', 'success')
        elif group:
            permission = Permission.query.filter_by(dap_id=dap.id, group_id=group.id).first()
            if permission: permission.can_edit = can_edit
            else: db.session.add(Permission(dap_id=dap.id, group_id=group.id, can_edit=can_edit))
            flash(f'Permission pour le groupe {group.name} mise à jour.', 'success')
        db.session.commit()
        return redirect(url_for('dap_permissions', dap_id=dap.id))
    if request.method == 'POST':
        if 'delete_permission_id' in request.form:
            permission = Permission.query.get_or_404(request.form['delete_permission_id'])
            if permission.dap_id == dap.id:
                db.session.delete(permission)
                db.session.commit()
                flash('Permission supprimée avec succès.', 'success')
            else: flash('Action non autorisée.', 'danger')
            return redirect(url_for('dap_permissions', dap_id=dap.id))
        if 'toggle_permission_id' in request.form:
            permission = Permission.query.get_or_404(request.form['toggle_permission_id'])
            if permission.dap_id == dap.id:
                permission.can_edit = request.form['can_edit_status'] == 'true'
                db.session.commit()
                flash('Statut de permission mis à jour.', 'success')
            else: flash('Action non autorisée.', 'danger')
            return redirect(url_for('dap_permissions', dap_id=dap.id))
    return render_template('dap_permissions.html', dap=dap, add_permission_form=add_permission_form)
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    return render_template('admin/users.html', users=User.query.all())
@app.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_user():
    form = UserForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, is_admin=form.is_admin.data)
        user.set_password(form.password.data)
        user.groups = Group.query.filter(Group.id.in_(form.groups.data)).all()
        db.session.add(user)
        db.session.commit()
        flash('Utilisateur créé avec succès.', 'success')
        return redirect(url_for('admin_users'))
    return render_template('admin/user_form.html', form=form, user=None)
@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(original_username=user.username)
    if form.validate_on_submit():
        user.username = form.username.data
        user.is_admin = form.is_admin.data
        if form.password.data: user.set_password(form.password.data)
        user.groups = Group.query.filter(Group.id.in_(form.groups.data)).all()
        db.session.commit()
        flash('Utilisateur mis à jour avec succès.', 'success')
        return redirect(url_for('admin_users'))
    elif request.method == 'GET':
        form.username.data = user.username
        form.is_admin.data = user.is_admin
        form.groups.data = [g.id for g in user.groups]
    return render_template('admin/user_form.html', form=form, user=user)
@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'danger')
        return redirect(url_for('admin_users'))
    db.session.delete(user)
    db.session.commit()
    flash('Utilisateur supprimé avec succès.', 'success')
    return redirect(url_for('admin_users'))
@app.route('/admin/groups')
@login_required
@admin_required
def admin_groups():
    return render_template('admin/groups.html', groups=Group.query.all())
@app.route('/admin/groups/create', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_group():
    form = GroupForm()
    if form.validate_on_submit():
        group = Group(name=form.name.data)
        group.users = User.query.filter(User.id.in_(form.users.data)).all()
        db.session.add(group)
        db.session.commit()
        flash('Groupe créé avec succès.', 'success')
        return redirect(url_for('admin_groups'))
    return render_template('admin/group_form.html', form=form, group=None)
@app.route('/admin/groups/edit/<int:group_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_group(group_id):
    group = Group.query.get_or_404(group_id)
    form = GroupForm(original_name=group.name)
    if form.validate_on_submit():
        group.name = form.name.data
        group.users = User.query.filter(User.id.in_(form.users.data)).all()
        db.session.commit()
        flash('Groupe mis à jour avec succès.', 'success')
        return redirect(url_for('admin_groups'))
    elif request.method == 'GET':
        form.name.data = group.name
        form.users.data = [u.id for u in group.users]
    return render_template('admin/group_form.html', form=form, group=group)
@app.route('/admin/groups/delete/<int:group_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_group(group_id):
    group = Group.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    flash('Groupe supprimé avec succès.', 'success')
    return redirect(url_for('admin_groups'))
if __name__ == '__main__':
    app.run(debug=True)
