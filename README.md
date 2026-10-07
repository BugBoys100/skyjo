# Skyjo Web Multijoueur

Un clone du jeu Skyjo jouable dans le navigateur avec support multijoueur en temps réel.

## 🎮 Fonctionnalités

- **Jeu complet Skyjo** : Respecte les règles officielles avec un deck de 150 cartes
- **Mode Solo** : Jouez contre des robots IA
- **Mode Multijoueur** : Créez ou rejoignez des parties avec un code (max 6 joueurs)
- **Temps réel** : Synchronisation via WebSockets pour voir les actions des autres joueurs
- **Interface moderne** : Design responsive avec Tailwind CSS

## 🚀 Installation

### Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Le serveur démarre sur `http://localhost:8000`

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

L'application démarre sur `http://localhost:3000`

## 📋 Règles du Jeu

- Chaque joueur a une grille de 3x4 cartes (12 cartes)
- Au début, 2 cartes sont révélées par joueur
- À votre tour :
  1. Piochez une carte (du deck ou de la défausse)
  2. Remplacez une carte cachée ou défaussez la carte piochée
  3. Si vous avez 3 cartes identiques dans une colonne, vous pouvez les défausser
- La manche se termine quand un joueur révèle toutes ses cartes
- Le score est la somme des valeurs visibles
- Si le joueur qui finit n'a pas le score le plus bas, son score est doublé

## 🎴 Composition du Deck

- **-2** : 5 cartes
- **0** : 15 cartes
- **-1 et 1 à 12** : 10 cartes chacun

Total : 150 cartes

## 📁 Structure du Projet

```
Skyjo/
├── backend/
│   ├── main.py              # Serveur FastAPI
│   ├── requirements.txt     # Dépendances Python
│   └── parties/             # Fichiers JSON des parties (créé automatiquement)
├── frontend/
│   ├── src/
│   │   ├── components/      # Composants React
│   │   ├── App.jsx          # Application principale
│   │   └── main.jsx         # Point d'entrée
│   └── package.json         # Dépendances Node
└── README.md
```

## 🛠️ Technologies

- **Backend** : Python, FastAPI, WebSockets
- **Frontend** : React, Vite, Tailwind CSS
- **Stockage** : Fichiers JSON (parties sauvegardées dans `/parties`)

## 📝 Notes

- Les parties sont sauvegardées dans le dossier `backend/parties/`
- Chaque partie a un code unique au format `XXXX-XXXX`
- Les robots jouent automatiquement avec une IA simple

