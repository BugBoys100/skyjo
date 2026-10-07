import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

const API_URL = 'http://localhost:8000'

function HomeScreen({ playerName, setPlayerName, setPlayerId, setGameCode }) {
  const [joinCode, setJoinCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleCreateGame = async () => {
    if (!playerName.trim()) {
      setError('Veuillez entrer un pseudo')
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await axios.post(`${API_URL}/create-game`, {
        name: playerName
      })
      setPlayerId(response.data.player_id)
      setGameCode(response.data.code)
      navigate(`/lobby/${response.data.code}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la création de la partie')
    } finally {
      setLoading(false)
    }
  }

  const handleJoinGame = async () => {
    if (!playerName.trim()) {
      setError('Veuillez entrer un pseudo')
      return
    }
    if (!joinCode.trim()) {
      setError('Veuillez entrer un code de partie')
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await axios.post(`${API_URL}/join-game`, {
        code: joinCode.toUpperCase(),
        name: playerName
      })
      setPlayerId(response.data.player_id)
      setGameCode(response.data.code)
      navigate(`/lobby/${response.data.code}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la connexion à la partie')
    } finally {
      setLoading(false)
    }
  }

  const handleSolo = async () => {
    if (!playerName.trim()) {
      setError('Veuillez entrer un pseudo')
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await axios.post(`${API_URL}/create-game`, {
        name: playerName
      })
      setPlayerId(response.data.player_id)
      setGameCode(response.data.code)
      navigate(`/lobby/${response.data.code}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la création de la partie')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <h1 className="text-4xl font-bold text-center mb-8 text-gray-800">
          🎴 Skyjo
        </h1>
        
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Pseudo
          </label>
          <input
            type="text"
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            placeholder="Entrez votre pseudo"
            maxLength={20}
          />
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        <div className="space-y-3">
          <button
            onClick={handleSolo}
            disabled={loading}
            className="w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Chargement...' : '🎮 Solo'}
          </button>

          <button
            onClick={handleCreateGame}
            disabled={loading}
            className="w-full bg-purple-500 hover:bg-purple-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Chargement...' : '➕ Créer une partie multijoueur'}
          </button>

          <div className="pt-4 border-t border-gray-200">
            <div className="mb-3">
              <input
                type="text"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="XXXX-XXXX"
                maxLength={9}
              />
            </div>
            <button
              onClick={handleJoinGame}
              disabled={loading}
              className="w-full bg-green-500 hover:bg-green-600 text-white font-semibold py-3 px-4 rounded-lg transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Chargement...' : '🔗 Rejoindre une partie'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HomeScreen

