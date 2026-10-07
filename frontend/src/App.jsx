import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import HomeScreen from './components/HomeScreen'
import Lobby from './components/Lobby'
import Game from './components/Game'
import './App.css'

function App() {
  const [playerName, setPlayerName] = useState(() => {
    return localStorage.getItem('playerName') || 'Joueur'
  })
  const [playerId, setPlayerId] = useState(() => {
    return localStorage.getItem('playerId') || null
  })
  const [gameCode, setGameCode] = useState(() => {
    return localStorage.getItem('gameCode') || null
  })

  useEffect(() => {
    if (playerName) {
      localStorage.setItem('playerName', playerName)
    }
    if (playerId) {
      localStorage.setItem('playerId', playerId)
    }
    if (gameCode) {
      localStorage.setItem('gameCode', gameCode)
    }
  }, [playerName, playerId, gameCode])

  return (
    <Router>
      <div className="min-h-screen">
        <Routes>
          <Route 
            path="/" 
            element={
              <HomeScreen 
                playerName={playerName}
                setPlayerName={setPlayerName}
                setPlayerId={setPlayerId}
                setGameCode={setGameCode}
              />
            } 
          />
          <Route 
            path="/lobby/:code" 
            element={
              <Lobby 
                playerId={playerId}
                playerName={playerName}
                setGameCode={setGameCode}
              />
            } 
          />
          <Route 
            path="/game/:code" 
            element={
              <Game 
                playerId={playerId}
                playerName={playerName}
              />
            } 
          />
        </Routes>
      </div>
    </Router>
  )
}

export default App

