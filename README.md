# APAFIX - Portail de gestion des saisines APAFIS

APAFIX est une application web permettant d'importer, d'editer et d'exporter les saisines APAFIS (demandes d'autorisation de projet utilisant des animaux a des fins scientifiques).

Les saisines sont des documents XML produits par l'outil Java officiel du ministere (MESR), base sur JaxFront. Cet outil genere un XML conforme au schema `APAFiS_formulaire_v1.16.xsd` et en produit un PDF. Cependant, l'outil est peu ergonomique : pas de correction orthographique, interface rigide, pas de travail collaboratif.

APAFIX propose une alternative en offrant :

- Un formulaire web dynamique genere directement depuis la structure XML, fidele au rendu PDF officiel
- Un export au format Word (.docx) pour relecture et impression
- Un systeme de permissions pour le travail collaboratif
- La conservation du XML original pour reimportation dans l'outil officiel

## Fonctionnalites

### Gestion des saisines

- **Import XML** : upload d'un fichier XML APAFIS. Le titre, la reference et la version sont extraits automatiquement. Verification des doublons sur le numero de reference.
- **Edition web** : formulaire dynamique genere recursivement depuis la structure XML. Les sections sont organisees selon la numerotation officielle (1. Informations Generales, 3. Informations Administratives, 4. Procedures Experimentales, 5. Resume europeen). Les champs texte s'auto-redimensionnent. Les booleens sont affiches en cases a cocher.
- **Export XML** : telechargement du XML modifie, reimportable dans l'outil officiel du ministere.
- **Export Word** : conversion en document .docx avec titres hierarchises, mise en page structuree et contenu fidele au PDF officiel.
- **Suppression** : par le proprietaire ou un administrateur.

### Procedures experimentales

Le formulaire gere la complexite des procedures experimentales (section 4 du formulaire APAFIS) :

- Numerotation dynamique des procedures (4.2.1, 4.2.2, ... 4.2.N)
- Chaque procedure peut avoir des champs differents (methode de suppression de la douleur, de la souffrance, prelevement et frequence, derogation d'hebergement...). Le formulaire fusionne les structures pour que tous les champs soient disponibles dans chaque procedure.
- Gestion du devenir des animaux (mise a mort, garde en vie, decision veterinaire, mise en liberte)

### Gestion des utilisateurs et permissions

- **Authentification** : inscription, connexion, sessions persistantes
- **Roles** : administrateur (acces complet) ou utilisateur standard
- **Groupes** : regroupement d'utilisateurs pour faciliter la gestion des droits
- **Permissions par saisine** :
  - Le proprietaire (celui qui a uploade) a un acces complet
  - Les administrateurs ont acces a tout
  - Des permissions individuelles (utilisateur) ou collectives (groupe) peuvent etre attribuees avec droit de lecture seule ou d'edition
  - Gestion des permissions via une interface dediee

### Administration

- Gestion des utilisateurs (creation, edition, suppression, attribution de groupes)
- Gestion des groupes (creation, edition des membres, suppression)
- Vue globale de toutes les saisines

## Architecture technique

```
apafix/
  app.py                # Application Flask, routes, controleurs
  wsgi.py               # Point d'entree WSGI (gunicorn)
  models.py             # Modeles SQLAlchemy (User, Dap, Group, Permission)
  forms.py              # Formulaires WTForms, generation dynamique
  xml_utils.py          # Parsing XML, FORM_LABEL_MAP, generation DOCX, fusion de structures
  extensions.py         # Initialisation des extensions Flask
  create_admin.py       # Commande CLI pour creer le compte admin
  requirements.txt      # Dependances Python
  gunicorn.conf.py      # Configuration gunicorn (production)
  templates/
    base.html           # Template de base (navbar, layout Bootstrap 5)
    index.html           # Page d'accueil
    upload.html          # Upload de saisine XML
    daps.html            # Liste des saisines
    edit_dap.html        # Edition d'une saisine (formulaire dynamique recursif)
    dap_permissions.html # Gestion des permissions d'une saisine
    _form_macros.html    # Macros Jinja2 pour le rendu des champs
    auth/                # Login, inscription
    admin/               # Gestion utilisateurs et groupes
  static/
    css/style.css        # Styles personnalises, hierarchie visuelle des sections
    js/main.js           # Initialisation Bootstrap (tooltips, popovers)
    js/textarea_autoresize.js  # Auto-redimensionnement des zones de texte
```

### Technologies

- **Backend** : Flask, SQLAlchemy (SQLite), Flask-Login, Flask-WTF, lxml
- **Frontend** : Bootstrap 5, Jinja2
- **Export** : python-docx pour la generation Word
- **Production** : gunicorn, nginx, systemd

## Installation

### Prerequis

- Python 3.10+
- pip

### Developpement (Windows/Linux)

```bash
git clone <url-du-depot> apafix
cd apafix

# Creer l'environnement virtuel
python -m venv .venv
# Linux/macOS :
source .venv/bin/activate
# Windows :
.venv\Scripts\activate

# Installer les dependances
pip install -r requirements.txt

# Configurer l'environnement
cp .env.production .env
# Editer .env : definir SECRET_KEY et ADMIN_PASSWORD

# Creer le compte administrateur
flask create-admin

# Lancer en mode developpement
flask run
# ou
python app.py
```

L'application est accessible sur `http://localhost:5000`.

### Production (Linux)

#### Installation automatique

```bash
# Sur le serveur, en root
git clone <url-du-depot> /tmp/apafix-src
sudo bash /tmp/apafix-src/install.sh
```

Le script `install.sh` effectue :

1. Installation des dependances systeme (python3, nginx)
2. Creation de l'utilisateur systeme `apafix`
3. Deploiement dans `/opt/apafix`
4. Creation du virtualenv et installation des paquets Python
5. Generation automatique d'une cle secrete
6. Configuration des permissions fichier
7. Installation du service systemd

#### Configuration post-installation

```bash
# Modifier le mot de passe admin
sudo nano /opt/apafix/.env

# Configurer nginx
sudo cp /opt/apafix/nginx.conf /etc/nginx/sites-available/apafix
sudo ln -s /etc/nginx/sites-available/apafix /etc/nginx/sites-enabled/
# Editer le server_name dans le fichier :
sudo nano /etc/nginx/sites-available/apafix
sudo nginx -t && sudo systemctl reload nginx
```

#### Gestion du service

```bash
# Demarrer
sudo systemctl start apafix

# Arreter
sudo systemctl stop apafix

# Redemarrer (rechargement des workers sans coupure)
sudo systemctl restart apafix

# Voir le statut
sudo systemctl status apafix

# Suivre les logs en temps reel
sudo journalctl -u apafix -f

# Logs gunicorn
tail -f /var/log/apafix/access.log
tail -f /var/log/apafix/error.log
```

Les scripts `start.sh`, `stop.sh` et `restart.sh` sont egalement disponibles pour une utilisation sans systemd.

#### Variables d'environnement

| Variable | Description | Defaut |
|---|---|---|
| `SECRET_KEY` | Cle secrete Flask (obligatoire) | - |
| `ADMIN_USERNAME` | Nom du compte admin | `admin` |
| `ADMIN_PASSWORD` | Mot de passe admin | - |
| `APAFIX_BIND` | Adresse:port d'ecoute | `0.0.0.0:8000` |
| `APAFIX_WORKERS` | Nombre de workers gunicorn | `CPU * 2 + 1` |
| `APAFIX_LOG_LEVEL` | Niveau de log | `info` |

#### HTTPS

Pour activer HTTPS avec Let's Encrypt :

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d apafix.example.com
```

Puis decommenter le bloc HTTPS dans `/etc/nginx/sites-available/apafix`.

## Utilisation

1. Se connecter avec le compte administrateur
2. **Uploader** une saisine via le menu "Uploader une saisine"
3. **Editer** la saisine : le formulaire affiche toutes les sections du document APAFIS avec les champs editables
4. **Sauvegarder** : le XML est reconstruit et stocke en base
5. **Exporter** : telecharger en XML (reimportable dans l'outil officiel) ou en Word (.docx)
6. **Partager** : attribuer des permissions de lecture ou d'edition a d'autres utilisateurs ou groupes

## Structure du formulaire APAFIS

Le formulaire suit la structure officielle :

- **Section 1** - Informations generales (titre, reference, duree, date de debut)
- **Section 3** - Informations administratives et reglementaires
  - 3.1 Etablissement utilisateur (agrement, responsables)
  - 3.2 Personnel (competences)
  - 3.3 Projet (objectifs, description, 3R)
  - 3.4 Animaux (especes, justification, origine, nombre)
- **Section 4** - Procedures experimentales
  - 4.1 Objets vises
  - 4.2 Procedures (description, lots, points limites, anesthesie, devenir)
  - 4.3 Reutilisation d'animaux
  - 4.4 Souffrance severe
- **Section 5** - Resume au format europeen (NTS)

> La section 2 (RNT) est inutilisee dans le formulaire officiel actuel.

## Licence

Usage interne.
