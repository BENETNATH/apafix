import os
import click
from flask.cli import with_appcontext
from extensions import db
from models import User
from dotenv import load_dotenv

@click.command(name='create-admin')
@with_appcontext
def create_admin_command():
    """Crée l'utilisateur admin à partir des variables d'environnement."""
    load_dotenv()
    admin_username = os.environ.get('ADMIN_USERNAME')
    admin_password = os.environ.get('ADMIN_PASSWORD')

    if not admin_username or not admin_password:
        click.echo("Erreur : ADMIN_USERNAME et ADMIN_PASSWORD doivent être définis dans le fichier .env")
        return

    if User.query.filter_by(username=admin_username).first():
        click.echo(f"L'utilisateur '{admin_username}' existe déjà.")
        return

    admin_user = User(username=admin_username, is_admin=True)
    admin_user.set_password(admin_password)
    db.session.add(admin_user)
    db.session.commit()
    click.echo(f"Utilisateur admin '{admin_username}' créé avec succès.")

def register_commands(app):
    app.cli.add_command(create_admin_command)