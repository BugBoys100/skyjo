import Card from './Card'

function PlayerGrid({ player, isCurrentPlayer, isMyGrid, onCardClick, canClick = false, preparationMode = false }) {
  if (!player) return null

  return (
    <div className={`${isCurrentPlayer ? 'ring-2 ring-green-500' : ''} rounded-lg`}>
      <div className={`grid grid-cols-4 ${isMyGrid ? 'gap-2' : 'gap-1.5'}`}>
        {player.grid.map((row, rowIndex) =>
          row.map((value, colIndex) => {
            const isVisible = player.grid_visible[rowIndex][colIndex]
            const isEmpty = value === null || value === undefined
            
            // En mode préparation, on peut cliquer sur les cartes cachées uniquement
            // En mode jeu normal, on peut cliquer sur toutes les cartes non vides si canClick est true
            const canClickCard = isMyGrid && onCardClick && !isEmpty && (
              (preparationMode && !isVisible) || 
              (!preparationMode && canClick)
            )
            return (
              <Card
                key={`${rowIndex}-${colIndex}`}
                value={value}
                isVisible={isVisible}
                onClick={canClickCard ? () => onCardClick(rowIndex, colIndex) : undefined}
                size={isMyGrid ? 'normal' : 'small'}
                highlight={canClickCard}
                isEmpty={isEmpty}
              />
            )
          })
        )}
      </div>
      {player.has_finished && (
        <div className="mt-2 text-center">
          <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded font-semibold">
            ✓ Terminé {player.score !== undefined && player.score !== 0 ? `- Score: ${player.score}` : ''}
          </span>
        </div>
      )}
    </div>
  )
}

export default PlayerGrid

