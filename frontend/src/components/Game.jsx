import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import Card from './Card'
import PlayerGrid from './PlayerGrid'

const API_URL = 'http://localhost:8000'

function Game({ playerId, playerName }) {
  const { code } = useParams()
  const [gameState, setGameState] = useState(null)
  const [ws, setWs] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    connectWebSocket()
    return () => {
      if (ws) {
        ws.close()
      }
    }
  }, [code])

  const connectWebSocket = () => {
    const websocket = new WebSocket(`ws://localhost:8000/ws/${code}`)
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'game_state' || data.type === 'game_update') {
        setGameState(data.game_state)
      }
    }

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    setWs(websocket)
  }

  const handleAction = async (action, row = null, col = null) => {
    setLoading(true)
    setError('')
    try {
      await axios.post(`${API_URL}/play-action`, {
        code: code,
        player_id: playerId,
        action: action,
        row: row,
        col: col
      })
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de l\'action')
    } finally {
      setLoading(false)
    }
  }

  const getCurrentPlayer = () => {
    if (!gameState) return null
    return gameState.players[gameState.current_player_index]
  }

  const isMyTurn = () => {
    if (!gameState || gameState.preparation_phase) return false
    const current = getCurrentPlayer()
    return current && current.id === playerId && !current.is_robot
  }

  const getMyPlayer = () => {
    if (!gameState) return null
    return gameState.players.find(p => p.id === playerId)
  }

  const getRevealedCount = (player) => {
    if (!player) return 0
    return player.grid_visible.reduce((count, row) => 
      count + row.filter(visible => visible).length, 0
    )
  }

  if (!gameState) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-900 to-blue-900">
        <div className="text-white text-xl">Chargement de la partie...</div>
      </div>
    )
  }

  const myPlayer = getMyPlayer()
  const currentPlayer = getCurrentPlayer()
  const otherPlayers = gameState.players.filter(p => p.id !== playerId)
  const myRevealedCount = getRevealedCount(myPlayer)

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900 p-4">
      {/* En-tête */}
      <div className="max-w-7xl mx-auto mb-4">
        <div className="bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-3">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-800">🎴 Skyjo</h1>
            <div className="text-sm">
              {gameState.preparation_phase ? (
                <span className="text-orange-600 font-semibold">
                  Phase de préparation - Révélez 2 cartes ({myRevealedCount}/2)
                </span>
              ) : (
                <>
                  <span className="font-semibold">Tour de : </span>
                  <span className={`font-bold ${currentPlayer?.id === playerId ? 'text-green-600' : 'text-gray-600'}`}>
                    {currentPlayer?.name || '...'}
                  </span>
                  {gameState.finisher_index !== null && gameState.finisher_index !== undefined && !gameState.round_ended && (
                    <span className="ml-3 text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded">
                      ⚠️ {gameState.players[gameState.finisher_index]?.name} a fini - Dernier tour !
                    </span>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Layout principal */}
      <div className="max-w-7xl mx-auto relative" style={{ height: 'calc(100vh - 120px)' }}>
        
        {/* Grilles des adversaires - Positionnées autour */}
        <div className="absolute top-4 left-0 right-0 flex justify-around flex-wrap gap-4 z-0">
          {otherPlayers.map((player, index) => (
            <div 
              key={player.id} 
              className={`bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-3 ${
                player.id === currentPlayer?.id ? 'ring-2 ring-green-500' : ''
              }`}
              style={{ width: '220px' }}
            >
              <h3 className="font-semibold mb-2 text-sm text-gray-700 text-center">
                {player.name}
                {player.is_robot && ' 🤖'}
              </h3>
              <PlayerGrid
                player={player}
                isCurrentPlayer={player.id === currentPlayer?.id}
                isMyGrid={false}
              />
            </div>
          ))}
        </div>

        {/* Zone Pioche et Défausse - En haut à droite */}
        <div className="absolute top-4 right-4 z-10">
          <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-2xl p-4">
            {error && (
              <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm">
                {error}
              </div>
            )}
            
            {gameState.preparation_phase && (
              <div className="mb-4 p-3 bg-yellow-50 border-2 border-yellow-400 rounded-lg">
                <p className="text-sm font-semibold text-gray-700 mb-1">
                  Phase de préparation
                </p>
                <p className="text-xs text-gray-600">
                  Cliquez sur 2 cartes de votre grille pour les révéler
                </p>
              </div>
            )}
            
            {!gameState.preparation_phase && gameState.action_phase === 'replace' && gameState.drawn_card !== null && (
              <div className="mb-4 p-3 bg-yellow-50 border-2 border-yellow-400 rounded-lg">
                <p className="text-sm font-semibold text-gray-700 mb-1">
                  Carte piochée : {gameState.drawn_card}
                </p>
                <p className="text-xs text-gray-600 mb-2">
                  Choisissez une carte à remplacer ou défaussez
                </p>
                <button
                  onClick={() => handleAction('discard_drawn')}
                  disabled={loading}
                  className="w-full px-3 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg disabled:opacity-50 text-sm"
                >
                  Défausser
                </button>
              </div>
            )}
            
            {!gameState.preparation_phase && gameState.action_phase === 'must_reveal' && (
              <div className="mb-4 p-3 bg-red-50 border-2 border-red-400 rounded-lg">
                <p className="text-sm font-semibold text-red-700 mb-1">
                  ⚠️ Action obligatoire
                </p>
                <p className="text-xs text-red-600">
                  Vous devez retourner une carte cachée de votre grille
                </p>
              </div>
            )}

            <div className="flex flex-col gap-4">
              <div className="text-center">
                <h3 className="font-semibold mb-2 text-sm text-gray-700">Pioche</h3>
                {isMyTurn() && gameState.action_phase === 'draw' && !gameState.preparation_phase && (
                  <div
                    onClick={() => handleAction('draw_from_deck')}
                    className="w-20 h-28 bg-gradient-to-br from-gray-700 to-gray-900 rounded-lg flex items-center justify-center cursor-pointer hover:scale-105 transition-transform border-2 border-gray-600 mx-auto shadow-lg"
                    title="Piocher une carte"
                  >
                    <span className="text-gray-300 text-base font-bold">?</span>
                  </div>
                )}
                {(!isMyTurn() || gameState.action_phase !== 'draw' || gameState.preparation_phase) && (
                  <div className="w-20 h-28 bg-gradient-to-br from-gray-700 to-gray-900 rounded-lg flex items-center justify-center mx-auto border-2 border-gray-600 shadow-lg">
                    <span className="text-gray-300 text-base font-bold">?</span>
                  </div>
                )}
                <p className="text-xs text-gray-500 mt-2">
                  {gameState.deck?.length || 0} cartes
                </p>
              </div>

              <div className="text-center">
                <h3 className="font-semibold mb-2 text-sm text-gray-700">Défausse</h3>
                {gameState.discard_pile && gameState.discard_pile.length > 0 && (
                  <>
                    {isMyTurn() && gameState.action_phase === 'draw' && !gameState.preparation_phase ? (
                      <div onClick={() => handleAction('take_discard')} className="cursor-pointer" title="Prendre cette carte (remplacer)">
                        <Card
                          value={gameState.discard_pile[gameState.discard_pile.length - 1]}
                          isVisible={true}
                          onClick={() => {}}
                          size="normal"
                        />
                      </div>
                    ) : (
                      <Card
                        value={gameState.discard_pile[gameState.discard_pile.length - 1]}
                        isVisible={true}
                        onClick={() => {}}
                        size="normal"
                      />
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Ma grille - En bas au centre */}
        <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 w-full max-w-2xl z-0">
          <div className="bg-white/95 backdrop-blur-sm rounded-xl shadow-2xl p-5">
            <h2 className="text-lg font-bold mb-3 text-gray-800 text-center">
              Ma Grille
              {gameState.preparation_phase && (
                <span className="ml-2 text-sm font-normal text-orange-600">
                  ({myRevealedCount}/2 révélées)
                </span>
              )}
            </h2>
            
            {gameState.round_ended && (
              <div className="mb-3 p-3 bg-green-50 border-2 border-green-400 rounded-lg">
                <p className="font-semibold text-green-800 mb-2 text-sm">Manche terminée !</p>
                <div className="space-y-1">
                  {gameState.players.map((p) => (
                    <p key={p.id} className="text-xs">
                      {p.name}: {p.score} points
                    </p>
                  ))}
                </div>
              </div>
            )}
            
            {myPlayer && (
              <PlayerGrid
                player={myPlayer}
                isCurrentPlayer={isMyTurn()}
                isMyGrid={true}
                onCardClick={(row, col) => {
                  if (gameState.preparation_phase) {
                    // Phase de préparation : révéler une carte (cachée uniquement)
                    if (myRevealedCount < 2 && !myPlayer.grid_visible[row][col] && myPlayer.grid[row][col] !== null) {
                      handleAction('reveal_card', row, col)
                    }
                  } else if (isMyTurn() && gameState.action_phase === 'replace' && gameState.drawn_card !== null) {
                    // Phase de jeu : remplacer une carte (cachée ou révélée, mais pas vide)
                    if (myPlayer.grid[row][col] !== null) {
                      handleAction('replace_card', row, col)
                    }
                  } else if (isMyTurn() && gameState.action_phase === 'must_reveal') {
                    // Phase obligatoire : retourner une carte cachée
                    if (!myPlayer.grid_visible[row][col] && myPlayer.grid[row][col] !== null) {
                      handleAction('reveal_card', row, col)
                    }
                  } else if (isMyTurn() && gameState.action_phase === 'draw') {
                    // Révéler une carte pendant son tour (action optionnelle, cachée uniquement)
                    if (!myPlayer.grid_visible[row][col] && myPlayer.grid[row][col] !== null) {
                      handleAction('reveal_card', row, col)
                    }
                  }
                }}
                canClick={isMyTurn() && (gameState.action_phase === 'replace' || gameState.action_phase === 'must_reveal' || gameState.action_phase === 'draw')}
                preparationMode={gameState.preparation_phase}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Game
