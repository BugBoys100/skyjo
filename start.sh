#!/bin/bash

# Script de démarrage pour Skyjo

echo "🎴 Démarrage de Skyjo..."

# Suppression des anciennes parties
echo "🧹 Suppression des anciennes parties..."
rm -rf backend/parties/*

# Création d'un fichier de log pour le backend
echo "📝 Création du fichier de log pour le backend..."
touch backend/log.txt

# Création d'un fichier de log pour le frontend
echo "📝 Création du fichier de log pour le frontend..."
touch frontend/log.txt

echo "🎴 Démarrage de Skyjo..."

# Démarrer le backend
echo "📦 Démarrage du backend..."
cd backend
if [ ! -d "venv" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
fi
source venv/bin/activate

# Installer les dépendances si nécessaire
echo "Vérification des dépendances Python..."
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installation des dépendances Python..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Erreur lors de l'installation des dépendances Python"
        exit 1
    fi
fi

echo "Démarrage du serveur backend..."
python main.py &
BACKEND_PID=$!
cd ..

# Attendre que le backend démarre
sleep 2

# Démarrer le frontend
echo "⚛️  Démarrage du frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installation des dépendances..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Skyjo est démarré !"
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend: http://localhost:8000"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter les serveurs"

# Attendre l'interruption
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

