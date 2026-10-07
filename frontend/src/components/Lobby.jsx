import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'

const API_URL = 'http://localhost:8000'

function Lobby({ playerId, playerName, setGameCode }) {
  const { code } = useParams()
  const navigate = useNavigate()
  const [gameState, setGameState] = useState(null)
  const [numRobots, setNumRobots] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [ws, setWs] = useState(null)

  useEffect(() => {
    if (code) {
      setGameCode(code)
      loadGameState()
      connectWebSocket()
    }

    return () => {
      if (ws) {
        ws.close()
      }
    }
  }, [code])

  const loadGameState = async () => {
    try {
      const response = await axios.get(`${API_URL}/game-state/${code}`)
      setGameState(response.data)
    } catch (err) {
      // Si l'endpoint n'existe pas encore, on peut créer un état local
      console.error('Erreur lors du chargement de l\'état:', err)
    }
  }

  const connectWebSocket = () => {
    const websocket = new WebSocket(`ws://localhost:8000/ws/${code}`)
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'game_state') {
        setGameState(data.game_state)
      } else if (data.type === 'player_joined' || data.type === 'robot_added') {
        setGameState(prev => ({
          ...prev,
          players: data.players
        }))
      } else if (data.type === 'game_started') {
        setGameState(data.game_state)
        navigate(`/game/${code}`)
      }
    }

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    setWs(websocket)
  }

  const handleAddRobot = async () => {
    if (!playerId || gameState?.host_id !== playerId) {
      setError('Seul l\'hôte peut ajouter des robots')
      return
    }
    setLoading(true)
    setError('')
    try {
      await axios.post(`${API_URL}/add-robot`, {
        code: code,
        player_id: playerId
      })
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de l\'ajout du robot')
    } finally {
      setLoading(false)
    }
  }

  const handleStartGame = async () => {
    if (!playerId || gameState?.host_id !== playerId) {
      setError('Seul l\'hôte peut lancer la partie')
      return
    }
    if (!gameState || gameState.players.length < 1) {
      setError('Il faut au moins 1 joueur pour commencer')
      return
    }
    setLoading(true)
    setError('')
    try {
      await axios.post(`${API_URL}/start-game`, {
        code: code,
        player_id: playerId
      })
      // La navigation se fera via le WebSocket
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors du démarrage de la partie')
      setLoading(false)
    }
  }

  const isHost = gameState?.host_id === playerId
  const canStart = gameState && gameState.players.length >= 1 && !gameState.game_started

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-2xl">
        <h1 className="text-3xl font-bold text-center mb-6 text-gray-800">
          Configuration de la Partie
        </h1>

        {code && (
          <div className="mb-6 p-4 bg-purple-100 rounded-lg">
            <p className="text-sm text-gray-600 mb-1">Code de la partie</p>
            <p className="text-2xl font-mono font-bold text-purple-700">{code}</p>
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">
            Joueurs ({gameState?.players?.length || 0}/6)
          </h2>
          <div className="space-y-2">
            {gameState?.players?.map((player) => (
              <div
                key={player.id}
                className={`p-3 rounded-lg ${
                  player.id === playerId
                    ? 'bg-purple-100 border-2 border-purple-500'
                    : 'bg-gray-50 border border-gray-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">
                    {player.name}
                    {player.is_robot && ' 🤖'}
                    {player.id === playerId && ' (Vous)'}
                  </span>
                  {player.id === gameState?.host_id && (
                    <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                      Hôte
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {isHost && (
          <div className="mb-6 p-4 bg-blue-50 rounded-lg">
            <h3 className="font-semibold mb-3 text-gray-700">Options de l'hôte</h3>
            <div className="space-y-3">
              <button
                onClick={handleAddRobot}
                disabled={loading || (gameState?.players?.length || 0) >= 6}
                className="w-full bg-gray-500 hover:bg-gray-600 text-white font-semibold py-2 px-4 rounded-lg transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ➕ Ajouter un robot
              </button>
              {canStart && (
                <button
                  onClick={handleStartGame}
                  disabled={loading}
                  className="w-full bg-green-500 hover:bg-green-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Démarrage...' : '🚀 Lancer la partie'}
                </button>
              )}
            </div>
          </div>
        )}

        {!isHost && (
          <div className="p-4 bg-yellow-50 rounded-lg">
            <p className="text-sm text-gray-600">
              En attente que l'hôte lance la partie...
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default Lobby

