#!/usr/bin/env bash
# Install APAFIX on a Linux production server
# Run as root or with sudo
set -euo pipefail

APP_USER="apafix"
APP_DIR="/opt/apafix"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installation d'APAFIX ==="

# 1. System dependencies
echo "[1/6] Installation des dépendances système..."
if command -v apt-get &>/dev/null; then
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv python3-pip nginx
elif command -v dnf &>/dev/null; then
    dnf install -y python3 python3-pip nginx
elif command -v yum &>/dev/null; then
    yum install -y python3 python3-pip nginx
else
    echo "Gestionnaire de paquets non reconnu. Installez manuellement: python3, python3-venv, nginx"
fi

# 2. Create app user
echo "[2/6] Création de l'utilisateur $APP_USER..."
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --shell /usr/sbin/nologin --home-dir "$APP_DIR" "$APP_USER"
fi

# 3. Deploy application files
echo "[3/6] Déploiement des fichiers..."
mkdir -p "$APP_DIR"
cp -r "$REPO_DIR"/{app.py,wsgi.py,gunicorn.conf.py,extensions.py,forms.py,models.py,xml_utils.py,create_admin.py} "$APP_DIR/"
cp -r "$REPO_DIR"/requirements.txt "$APP_DIR/"
cp -r "$REPO_DIR"/templates "$APP_DIR/"
cp -r "$REPO_DIR"/static "$APP_DIR/"
cp -r "$REPO_DIR"/start.sh "$REPO_DIR"/stop.sh "$REPO_DIR"/restart.sh "$APP_DIR/"
chmod +x "$APP_DIR"/{start,stop,restart}.sh

# Deploy .env
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$REPO_DIR/.env.production" "$APP_DIR/.env"
    # Generate a random secret key
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/CHANGE_ME_TO_A_RANDOM_STRING/$SECRET/" "$APP_DIR/.env"
    echo "  -> .env créé avec une clé secrète aléatoire"
    echo "  -> IMPORTANT: Modifiez ADMIN_PASSWORD dans $APP_DIR/.env"
else
    echo "  -> .env existant conservé"
fi

# 4. Virtual environment
echo "[4/6] Création de l'environnement virtuel..."
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip -q
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" -q

# 5. Permissions
echo "[5/6] Configuration des permissions..."
mkdir -p "$APP_DIR/instance"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
mkdir -p /var/log/apafix /var/run/apafix
chown "$APP_USER:$APP_USER" /var/log/apafix /var/run/apafix

# 6. Systemd service
echo "[6/6] Installation du service systemd..."
cp "$REPO_DIR/apafix.service" /etc/systemd/system/apafix.service
systemctl daemon-reload
systemctl enable apafix

# Initialize database and admin
echo ""
echo "Initialisation de la base de données..."
cd "$APP_DIR"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" -c "from app import app; print('Base de données initialisée')"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/flask" create-admin 2>/dev/null || true

echo ""
echo "=== Installation terminée ==="
echo ""
echo "Commandes utiles:"
echo "  Démarrer:    sudo systemctl start apafix"
echo "  Arrêter:     sudo systemctl stop apafix"
echo "  Redémarrer:  sudo systemctl restart apafix"
echo "  Status:      sudo systemctl status apafix"
echo "  Logs:        sudo journalctl -u apafix -f"
echo ""
echo "L'application écoute sur le port 8000."
echo "Configurez nginx comme reverse proxy (voir nginx.conf ci-dessous)."
echo ""
echo "IMPORTANT: Modifiez le mot de passe admin dans $APP_DIR/.env puis redémarrez."
