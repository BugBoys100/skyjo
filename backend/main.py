from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Dict, List, Optional
import json
import os
import uuid
import random
from datetime import datetime
from pydantic import BaseModel

app = FastAPI()

# CORS pour permettre les connexions depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dossier pour stocker les parties
PARTIES_DIR = "parties"
os.makedirs(PARTIES_DIR, exist_ok=True)

# Gestionnaires de connexions WebSocket par partie
active_connections: Dict[str, List[WebSocket]] = {}


class Player(BaseModel):
    id: str
    name: str
    is_robot: bool = False
    grid: List[List[Optional[int]]] = [[None] * 4 for _ in range(3)]
    grid_visible: List[List[bool]] = [[False] * 4 for _ in range(3)]
    hand: List[int] = []
    score: int = 0
    has_finished: bool = False


class GameState(BaseModel):
    code: str
    host_id: str
    players: List[Player]
    deck: List[int]
    discard_pile: List[int]
    current_player_index: int
    game_started: bool = False
    game_ended: bool = False
    round_ended: bool = False
    preparation_phase: bool = False  # Phase où les joueurs révèlent 2 cartes
    drawn_card: Optional[int] = None  # Carte piochée en attente de décision
    action_phase: str = "draw"  # "draw", "replace", "must_reveal" (obligé de retourner après défausse), "reveal"
    finisher_index: Optional[int] = None  # Index du joueur qui a révélé toutes ses cartes


def create_deck() -> List[int]:
    """Crée un deck de 150 cartes selon les règles officielles de Skyjo"""
    deck = []
    # -2 : 5 cartes
    deck.extend([-2] * 5)
    # 0 : 15 cartes
    deck.extend([0] * 15)
    # -1 et 1 à 12 : 10 cartes chacun
    for value in [-1] + list(range(1, 13)):
        deck.extend([value] * 10)
    random.shuffle(deck)
    return deck


def generate_game_code() -> str:
    """Génère un code de partie au format XXXX-XXXX"""
    part1 = str(random.randint(1000, 9999))
    part2 = str(random.randint(1000, 9999))
    return f"{part1}-{part2}"


def save_game_state(game_state: GameState):
    """Sauvegarde l'état de la partie dans un fichier JSON"""
    file_path = os.path.join(PARTIES_DIR, f"{game_state.code}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(game_state.model_dump(), f, indent=2, ensure_ascii=False)


def load_game_state(code: str) -> Optional[GameState]:
    """Charge l'état d'une partie depuis un fichier JSON"""
    file_path = os.path.join(PARTIES_DIR, f"{code}.json")
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return GameState(**data)


async def broadcast_to_game(code: str, message: dict):
    """Envoie un message à tous les clients connectés à une partie"""
    if code in active_connections:
        disconnected = []
        for connection in active_connections[code]:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        for conn in disconnected:
            active_connections[code].remove(conn)


def deal_cards(deck: List[int], num_players: int) -> tuple:
    """Distribue les cartes : 12 cartes par joueur (3x4)"""
    hands = []
    for _ in range(num_players):
        hand = []
        for _ in range(12):
            if deck:
                hand.append(deck.pop())
        hands.append(hand)
    return hands, deck


def calculate_score(player: Player) -> int:
    """Calcule le score d'un joueur (somme des valeurs visibles + cartes défaussées = 0)"""
    score = 0
    for row in range(3):
        for col in range(4):
            if player.grid_visible[row][col]:
                # Carte révélée : ajouter sa valeur (ou 0 si None/défaussée)
                value = player.grid[row][col]
                if value is not None:
                    score += value
                # Si value is None, c'est une case défaussée qui compte pour 0 (on n'ajoute rien)
            elif player.grid[row][col] is None:
                # Case défaussée (vide) : compte pour 0
                score += 0
            # Les cartes cachées non défaussées ne comptent pas
    return score


def check_three_same_in_column(grid: List[List[Optional[int]]], grid_visible: List[List[bool]], col: int) -> bool:
    """Vérifie si une colonne contient 3 cartes identiques visibles"""
    values = []
    for row in range(3):
        if grid_visible[row][col] and grid[row][col] is not None:
            values.append(grid[row][col])
    return len(values) == 3 and len(set(values)) == 1


@app.get("/")
async def root():
    return {"message": "Skyjo API"}


@app.get("/game-state/{code}")
async def get_game_state(code: str):
    """Récupère l'état actuel d'une partie"""
    game_state = load_game_state(code.upper())
    if not game_state:
        raise HTTPException(status_code=404, detail="Partie non trouvée")
    return game_state.model_dump()


@app.post("/create-game")
async def create_game(data: dict):
    """Crée une nouvelle partie"""
    player_name = data.get("name", "Joueur")
    code = generate_game_code()
    
    # Vérifier que le code n'existe pas déjà
    while load_game_state(code) is not None:
        code = generate_game_code()
    
    player_id = str(uuid.uuid4())
    host = Player(
        id=player_id,
        name=player_name,
        grid=[[None] * 4 for _ in range(3)],
        grid_visible=[[False] * 4 for _ in range(3)]
    )
    
    game_state = GameState(
        code=code,
        host_id=player_id,
        players=[host],
        deck=[],
        discard_pile=[],
        current_player_index=0
    )
    
    save_game_state(game_state)
    active_connections[code] = []
    
    return {"code": code, "player_id": player_id}


@app.post("/join-game")
async def join_game(data: dict):
    """Rejoint une partie existante"""
    code = data.get("code", "").upper()
    player_name = data.get("name", "Joueur")
    
    game_state = load_game_state(code)
    if not game_state:
        raise HTTPException(status_code=404, detail="Partie non trouvée")
    
    if game_state.game_started:
        raise HTTPException(status_code=400, detail="La partie a déjà commencé")
    
    if len(game_state.players) >= 6:
        raise HTTPException(status_code=400, detail="La partie est pleine (max 6 joueurs)")
    
    player_id = str(uuid.uuid4())
    new_player = Player(
        id=player_id,
        name=player_name,
        grid=[[None] * 4 for _ in range(3)],
        grid_visible=[[False] * 4 for _ in range(3)]
    )
    
    game_state.players.append(new_player)
    save_game_state(game_state)
    
    await broadcast_to_game(code, {
        "type": "player_joined",
        "player": new_player.model_dump(),
        "players": [p.model_dump() for p in game_state.players]
    })
    
    return {"player_id": player_id, "code": code}


@app.post("/add-robot")
async def add_robot(data: dict):
    """Ajoute un robot à la partie"""
    code = data.get("code", "").upper()
    player_id = data.get("player_id")
    
    game_state = load_game_state(code)
    if not game_state:
        raise HTTPException(status_code=404, detail="Partie non trouvée")
    
    if game_state.host_id != player_id:
        raise HTTPException(status_code=403, detail="Seul l'hôte peut ajouter des robots")
    
    if game_state.game_started:
        raise HTTPException(status_code=400, detail="La partie a déjà commencé")
    
    if len(game_state.players) >= 6:
        raise HTTPException(status_code=400, detail="La partie est pleine (max 6 joueurs)")
    
    robot_id = str(uuid.uuid4())
    robot = Player(
        id=robot_id,
        name=f"Robot {len([p for p in game_state.players if p.is_robot]) + 1}",
        is_robot=True,
        grid=[[None] * 4 for _ in range(3)],
        grid_visible=[[False] * 4 for _ in range(3)]
    )
    
    game_state.players.append(robot)
    save_game_state(game_state)
    
    await broadcast_to_game(code, {
        "type": "robot_added",
        "player": robot.model_dump(),
        "players": [p.model_dump() for p in game_state.players]
    })
    
    return {"success": True}


@app.post("/start-game")
async def start_game(data: dict):
    """Démarre la partie"""
    code = data.get("code", "").upper()
    player_id = data.get("player_id")
    
    game_state = load_game_state(code)
    if not game_state:
        raise HTTPException(status_code=404, detail="Partie non trouvée")
    
    if game_state.host_id != player_id:
        raise HTTPException(status_code=403, detail="Seul l'hôte peut lancer la partie")
    
    if game_state.game_started:
        raise HTTPException(status_code=400, detail="La partie a déjà commencé")
    
    if len(game_state.players) < 1:
        raise HTTPException(status_code=400, detail="Il faut au moins 1 joueur")
    
    # Créer et mélanger le deck
    deck = create_deck()
    
    # Distribuer les cartes
    hands, remaining_deck = deal_cards(deck, len(game_state.players))
    
    # Placer les cartes dans les grilles (toutes face cachée)
    for i, player in enumerate(game_state.players):
        player.hand = hands[i]
        # Placer les 12 cartes dans la grille 3x4, toutes révélées = False
        card_index = 0
        for row in range(3):
            for col in range(4):
                if card_index < len(hands[i]):
                    player.grid[row][col] = hands[i][card_index]
                    player.grid_visible[row][col] = False  # Toutes cachées au départ
                    card_index += 1
    
    # Pour les robots, révéler automatiquement 2 cartes aléatoires
    for player in game_state.players:
        if player.is_robot:
            revealed = 0
            while revealed < 2:
                row = random.randint(0, 2)
                col = random.randint(0, 3)
                if not player.grid_visible[row][col]:
                    player.grid_visible[row][col] = True
                    revealed += 1
    
    # Première carte de la défausse
    if remaining_deck:
        game_state.discard_pile = [remaining_deck.pop()]
    
    game_state.deck = remaining_deck
    game_state.current_player_index = 0
    game_state.game_started = True
    game_state.preparation_phase = True  # Phase de préparation active
    
    save_game_state(game_state)
    
    save_game_state(game_state)
    await broadcast_to_game(code, {
        "type": "game_started",
        "game_state": game_state.model_dump()
    })
    
    # Vérifier si tous les robots ont déjà révélé leurs cartes
    # Si tous les joueurs humains ont révélé 2 cartes, la phase de préparation se terminera automatiquement
    if check_preparation_complete(game_state):
        game_state.preparation_phase = False
        # Déterminer qui commence (joueur avec la PLUS GRANDE somme des 2 cartes révélées)
        scores = []
        for p in game_state.players:
            score = calculate_score(p)  # Somme des cartes révélées
            scores.append((score, p))
        scores.sort(key=lambda x: x[0], reverse=True)  # Tri décroissant (plus grand d'abord)
        # Trouver l'index du joueur avec le score le plus haut
        highest_player = scores[0][1]
        game_state.current_player_index = next(
            i for i, p in enumerate(game_state.players) if p.id == highest_player.id
        )
        save_game_state(game_state)
        
        # Si le premier joueur est un robot, le faire jouer automatiquement
        current_player = game_state.players[game_state.current_player_index]
        if current_player.is_robot:
            import asyncio
            await asyncio.sleep(0.5)  # Petit délai
            await robot_play(game_state, current_player, code)
        
        await broadcast_to_game(code, {
            "type": "game_update",
            "game_state": game_state.model_dump()
        })
    
    return {"success": True}


def next_turn(game_state: GameState):
    """Passe au tour suivant"""
    # Si un joueur a fini, vérifier si on doit arrêter
    if game_state.finisher_index is not None:
        # Si on revient au joueur qui a fini, la partie est terminée
        next_index = (game_state.current_player_index + 1) % len(game_state.players)
        if next_index == game_state.finisher_index:
            # Fin de la partie - calculer les scores finaux
            for p in game_state.players:
                p.score = calculate_score(p)
            
            # Trouver le score le plus bas
            min_score = min(p.score for p in game_state.players)
            finisher = game_state.players[game_state.finisher_index]
            finisher_score = finisher.score
            
            # Doublement des points si le finisseur n'a pas le score le plus bas
            if finisher_score != min_score:
                finisher.score *= 2
            
            game_state.round_ended = True
            return
    
    game_state.current_player_index = (game_state.current_player_index + 1) % len(game_state.players)
    game_state.action_phase = "draw"
    game_state.drawn_card = None


def check_game_end(game_state: GameState) -> bool:
    """Vérifie si un joueur a révélé toutes ses cartes (déclenche la fin de partie)"""
    for i, player in enumerate(game_state.players):
        # Vérifier que toutes les cartes non-vides sont révélées
        all_revealed = all(
            player.grid[row][col] is None or player.grid_visible[row][col]
            for row in range(3)
            for col in range(4)
        )
        if all_revealed and game_state.finisher_index is None:
            # Un joueur a révélé toutes ses cartes - marquer comme finisseur
            player.has_finished = True
            game_state.finisher_index = i
            return True
    return False


async def robot_play(game_state: GameState, robot: Player, code: str):
    """Logique de jeu pour un robot"""
    import asyncio
    
    # Le robot pioche de la défausse si la carte est bonne, sinon du deck
    should_draw_from_discard = False
    if game_state.discard_pile:
        discard_value = game_state.discard_pile[-1]
        # Le robot prend la défausse si c'est une carte négative ou faible
        if discard_value <= 2:
            should_draw_from_discard = True
    
    if should_draw_from_discard and game_state.discard_pile:
        drawn_card = game_state.discard_pile.pop()
    elif game_state.deck:
        drawn_card = game_state.deck.pop()
    else:
        # Plus de cartes, fin de partie
        return
    
    game_state.drawn_card = drawn_card
    game_state.action_phase = "replace"
    
    # Trouver la meilleure position pour remplacer (peut remplacer n'importe quelle carte)
    best_row, best_col = None, None
    best_improvement = float('-inf')
    
    for row in range(3):
        for col in range(4):
            current_value = robot.grid[row][col]
            if current_value is not None:
                # Calculer l'amélioration potentielle (valeur actuelle - nouvelle valeur)
                # Plus la différence est grande, mieux c'est
                improvement = current_value - drawn_card
                if improvement > best_improvement:
                    best_improvement = improvement
                    best_row, best_col = row, col
    
    # Si on peut améliorer, remplacer
    if best_row is not None and best_improvement > 0:
        # Remplacer la carte
        old_card = robot.grid[best_row][best_col]
        robot.grid[best_row][best_col] = drawn_card
        robot.grid_visible[best_row][best_col] = True
        game_state.discard_pile.append(old_card)
        
        game_state.drawn_card = None
        game_state.action_phase = "draw"
        
        # Vérifier si on peut défausser une colonne
        for col in range(4):
            if check_three_same_in_column(robot.grid, robot.grid_visible, col):
                # Récupérer les 3 cartes avant de les défausser
                discarded_cards = []
                for row in range(3):
                    if robot.grid[row][col] is not None:
                        discarded_cards.append(robot.grid[row][col])
                    robot.grid[row][col] = None
                    robot.grid_visible[row][col] = False
                # Remettre les 3 cartes dans le deck et mélanger
                if discarded_cards:
                    game_state.deck.extend(discarded_cards)
                    random.shuffle(game_state.deck)
        
        # Vérifier fin de partie
        check_game_end(game_state)
        
        # Passer au tour suivant
        if not game_state.round_ended:
            next_turn(game_state)
    else:
        # Défausser la carte piochée - le robot doit alors retourner une carte
        game_state.discard_pile.append(drawn_card)
        game_state.drawn_card = None
        game_state.action_phase = "must_reveal"
        
        # Le robot retourne automatiquement une carte cachée
        # Trouver une carte cachée à retourner
        revealed = False
        for row in range(3):
            for col in range(4):
                if robot.grid[row][col] is not None and not robot.grid_visible[row][col]:
                    robot.grid_visible[row][col] = True
                    revealed = True
                    break
            if revealed:
                break
        
        # Vérifier si on peut défausser une colonne
        for col in range(4):
            if check_three_same_in_column(robot.grid, robot.grid_visible, col):
                # Récupérer les 3 cartes avant de les défausser
                discarded_cards = []
                for row in range(3):
                    if robot.grid[row][col] is not None:
                        discarded_cards.append(robot.grid[row][col])
                    robot.grid[row][col] = None
                    robot.grid_visible[row][col] = False
                # Remettre les 3 cartes dans le deck et mélanger
                if discarded_cards:
                    game_state.deck.extend(discarded_cards)
                    random.shuffle(game_state.deck)
        
        # Vérifier fin de partie
        check_game_end(game_state)
        
        game_state.action_phase = "draw"
        # Passer au tour suivant
        if not game_state.round_ended:
            next_turn(game_state)
    
    save_game_state(game_state)
    await broadcast_to_game(code, {
        "type": "game_update",
        "game_state": game_state.model_dump()
    })


def check_preparation_complete(game_state: GameState) -> bool:
    """Vérifie si tous les joueurs ont révélé 2 cartes"""
    for player in game_state.players:
        if not player.is_robot:
            revealed_count = sum(
                1 for row in player.grid_visible
                for visible in row
                if visible
            )
            if revealed_count < 2:
                return False
    return True


@app.post("/play-action")
async def play_action(data: dict):
    """Traite une action de jeu"""
    code = data.get("code", "").upper()
    player_id = data.get("player_id")
    action = data.get("action")
    row = data.get("row")
    col = data.get("col")
    
    game_state = load_game_state(code)
    if not game_state:
        raise HTTPException(status_code=404, detail="Partie non trouvée")
    
    if not game_state.game_started:
        raise HTTPException(status_code=400, detail="La partie n'a pas commencé")
    
    if game_state.round_ended:
        raise HTTPException(status_code=400, detail="La manche est terminée")
    
    # Si un joueur a fini, on continue jusqu'à ce que le tour revienne au finisseur
    # Les joueurs peuvent encore jouer normalement
    
    # Phase de préparation : révéler 2 cartes
    if game_state.preparation_phase:
        if action == "reveal_card":
            player = next((p for p in game_state.players if p.id == player_id), None)
            if not player:
                raise HTTPException(status_code=404, detail="Joueur non trouvé")
            
            if row is None or col is None:
                raise HTTPException(status_code=400, detail="Position de carte requise")
            if row < 0 or row >= 3 or col < 0 or col >= 4:
                raise HTTPException(status_code=400, detail="Position invalide")
            
            # Vérifier que la carte n'est pas déjà révélée
            if player.grid_visible[row][col]:
                raise HTTPException(status_code=400, detail="Cette carte est déjà révélée")
            
            # Compter les cartes déjà révélées
            revealed_count = sum(
                1 for r in player.grid_visible
                for visible in r
                if visible
            )
            if revealed_count >= 2:
                raise HTTPException(status_code=400, detail="Vous avez déjà révélé 2 cartes")
            
            # Révéler la carte
            player.grid_visible[row][col] = True
            
            save_game_state(game_state)
            
            # Vérifier si tous les joueurs ont fini
            if check_preparation_complete(game_state):
                game_state.preparation_phase = False
                # Déterminer qui commence (joueur avec la PLUS GRANDE somme des 2 cartes révélées)
                scores = []
                for p in game_state.players:
                    score = calculate_score(p)  # Somme des cartes révélées
                    scores.append((score, p))
                scores.sort(key=lambda x: x[0], reverse=True)  # Tri décroissant (plus grand d'abord)
                # Trouver l'index du joueur avec le score le plus haut
                highest_player = scores[0][1]
                game_state.current_player_index = next(
                    i for i, p in enumerate(game_state.players) if p.id == highest_player.id
                )
                save_game_state(game_state)
                
                # Si le premier joueur est un robot, le faire jouer automatiquement
                current_player = game_state.players[game_state.current_player_index]
                if current_player.is_robot:
                    import asyncio
                    await asyncio.sleep(0.5)  # Petit délai
                    await robot_play(game_state, current_player, code)
            
            await broadcast_to_game(code, {
                "type": "game_update",
                "game_state": game_state.model_dump()
            })
            return {"success": True}
    
    current_player = game_state.players[game_state.current_player_index]
    if current_player.id != player_id and not current_player.is_robot:
        raise HTTPException(status_code=403, detail="Ce n'est pas votre tour")
    
    # Phase 1 : Piocher ou prendre la défausse
    if game_state.action_phase == "draw":
        if action == "draw_from_deck":
            # Piocher du deck
            if not game_state.deck:
                raise HTTPException(status_code=400, detail="Le deck est vide")
            game_state.drawn_card = game_state.deck.pop()
            game_state.action_phase = "replace"
        elif action == "take_discard":
            # Prendre la carte de la défausse (remplacer directement)
            if not game_state.discard_pile:
                raise HTTPException(status_code=400, detail="La défausse est vide")
            game_state.drawn_card = game_state.discard_pile.pop()
            game_state.action_phase = "replace"
    
    # Phase 2 : Remplacer ou défausser
    elif game_state.action_phase == "replace":
        if action == "replace_card":
            if row is None or col is None:
                raise HTTPException(status_code=400, detail="Position de carte requise")
            if row < 0 or row >= 3 or col < 0 or col >= 4:
                raise HTTPException(status_code=400, detail="Position invalide")
            
            # On peut remplacer n'importe quelle carte (cachée ou révélée) selon les règles de Skyjo
            # Remplacer la carte
            old_card = current_player.grid[row][col]
            current_player.grid[row][col] = game_state.drawn_card
            current_player.grid_visible[row][col] = True  # La nouvelle carte est toujours révélée
            
            # Mettre l'ancienne carte dans la défausse
            if old_card is not None:
                game_state.discard_pile.append(old_card)
            
            game_state.drawn_card = None
            game_state.action_phase = "draw"
            
            # Vérifier si on peut défausser une colonne
            for c in range(4):
                if check_three_same_in_column(current_player.grid, current_player.grid_visible, c):
                    # Récupérer les 3 cartes avant de les défausser
                    discarded_cards = []
                    for r in range(3):
                        if current_player.grid[r][c] is not None:
                            discarded_cards.append(current_player.grid[r][c])
                        current_player.grid[r][c] = None
                        current_player.grid_visible[r][c] = False
                    # Remettre les 3 cartes dans le deck et mélanger
                    if discarded_cards:
                        game_state.deck.extend(discarded_cards)
                        random.shuffle(game_state.deck)
                        # La prochaine carte piochée sera l'une de ces cartes (déjà mélangée)
            
            # Vérifier fin de partie
            check_game_end(game_state)
            
            # Passer au tour suivant
            if not game_state.round_ended:
                next_turn(game_state)
        
        elif action == "discard_drawn":
            # Défausser la carte piochée
            game_state.discard_pile.append(game_state.drawn_card)
            game_state.drawn_card = None
            # Après défausse, on est OBLIGÉ de retourner une carte
            game_state.action_phase = "must_reveal"
    
    # Action pour révéler une carte (pendant le jeu normal)
    if action == "reveal_card" and not game_state.preparation_phase:
        player = next((p for p in game_state.players if p.id == player_id), None)
        if not player:
            raise HTTPException(status_code=404, detail="Joueur non trouvé")
        
        if row is None or col is None:
            raise HTTPException(status_code=400, detail="Position de carte requise")
        if row < 0 or row >= 3 or col < 0 or col >= 4:
            raise HTTPException(status_code=400, detail="Position invalide")
        
        # Vérifier que c'est bien notre carte
        if player.id != player_id:
            raise HTTPException(status_code=403, detail="Ce n'est pas votre carte")
        
        # Vérifier que la carte n'est pas déjà révélée
        if player.grid_visible[row][col]:
            raise HTTPException(status_code=400, detail="Cette carte est déjà révélée")
        
        # Vérifier que la case n'est pas vide (colonne défaussée)
        if player.grid[row][col] is None:
            raise HTTPException(status_code=400, detail="Cette case est vide (colonne défaussée)")
        
        # Révéler la carte
        player.grid_visible[row][col] = True
        
        # Vérifier si on peut défausser une colonne
        for c in range(4):
            if check_three_same_in_column(player.grid, player.grid_visible, c):
                # Récupérer les 3 cartes avant de les défausser
                discarded_cards = []
                for r in range(3):
                    if player.grid[r][c] is not None:
                        discarded_cards.append(player.grid[r][c])
                    player.grid[r][c] = None
                    player.grid_visible[r][c] = False
                # Remettre les 3 cartes dans le deck et mélanger
                if discarded_cards:
                    game_state.deck.extend(discarded_cards)
                    random.shuffle(game_state.deck)
        
        # Vérifier fin de partie
        check_game_end(game_state)
        
        # Si on était en phase "must_reveal", on passe au tour suivant après avoir retourné
        if game_state.action_phase == "must_reveal":
            game_state.action_phase = "draw"
            if not game_state.round_ended:
                next_turn(game_state)
        
        save_game_state(game_state)
        await broadcast_to_game(code, {
            "type": "game_update",
            "game_state": game_state.model_dump()
        })
        return {"success": True}
    
    save_game_state(game_state)
    await broadcast_to_game(code, {
        "type": "game_update",
        "game_state": game_state.model_dump()
    })
    
    # Si c'est le tour d'un robot, jouer automatiquement
    if not game_state.round_ended:
        current_player = game_state.players[game_state.current_player_index]
        if current_player.is_robot:
            import asyncio
            await asyncio.sleep(1)  # Délai pour voir l'action
            if game_state.action_phase == "must_reveal":
                # Le robot doit retourner une carte
                revealed = False
                for row in range(3):
                    for col in range(4):
                        if current_player.grid[row][col] is not None and not current_player.grid_visible[row][col]:
                            current_player.grid_visible[row][col] = True
                            revealed = True
                            break
                    if revealed:
                        break
                # Vérifier colonnes identiques
                for c in range(4):
                    if check_three_same_in_column(current_player.grid, current_player.grid_visible, c):
                        # Récupérer les 3 cartes avant de les défausser
                        discarded_cards = []
                        for r in range(3):
                            if current_player.grid[r][c] is not None:
                                discarded_cards.append(current_player.grid[r][c])
                            current_player.grid[r][c] = None
                            current_player.grid_visible[r][c] = False
                        # Remettre les 3 cartes dans le deck et mélanger
                        if discarded_cards:
                            game_state.deck.extend(discarded_cards)
                            random.shuffle(game_state.deck)
                check_game_end(game_state)
                game_state.action_phase = "draw"
                if not game_state.round_ended:
                    next_turn(game_state)
                save_game_state(game_state)
                await broadcast_to_game(code, {
                    "type": "game_update",
                    "game_state": game_state.model_dump()
                })
            else:
                await robot_play(game_state, current_player, code)
                # Continuer à jouer tant que c'est un robot
                while not game_state.round_ended:
                    current_player = game_state.players[game_state.current_player_index]
                    if current_player.is_robot:
                        await asyncio.sleep(1)
                        if game_state.action_phase == "must_reveal":
                            # Le robot doit retourner une carte
                            revealed = False
                            for row in range(3):
                                for col in range(4):
                                    if current_player.grid[row][col] is not None and not current_player.grid_visible[row][col]:
                                        current_player.grid_visible[row][col] = True
                                        revealed = True
                                        break
                                if revealed:
                                    break
                            # Vérifier colonnes identiques
                            for c in range(4):
                                if check_three_same_in_column(current_player.grid, current_player.grid_visible, c):
                                    for r in range(3):
                                        current_player.grid[r][c] = None
                                        current_player.grid_visible[r][c] = False
                            check_game_end(game_state)
                            game_state.action_phase = "draw"
                            if not game_state.round_ended:
                                next_turn(game_state)
                            save_game_state(game_state)
                            await broadcast_to_game(code, {
                                "type": "game_update",
                                "game_state": game_state.model_dump()
                            })
                        else:
                            await robot_play(game_state, current_player, code)
                    else:
                        break
    
    return {"success": True}


@app.websocket("/ws/{code}")
async def websocket_endpoint(websocket: WebSocket, code: str):
    """Endpoint WebSocket pour les mises à jour en temps réel"""
    await websocket.accept()
    
    code = code.upper()
    if code not in active_connections:
        active_connections[code] = []
    active_connections[code].append(websocket)
    
    # Envoyer l'état actuel de la partie
    game_state = load_game_state(code)
    if game_state:
        await websocket.send_json({
            "type": "game_state",
            "game_state": game_state.model_dump()
        })
    
    try:
        while True:
            data = await websocket.receive_text()
            # Traiter les messages du client si nécessaire
    except WebSocketDisconnect:
        active_connections[code].remove(websocket)
        if not active_connections[code]:
            del active_connections[code]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

