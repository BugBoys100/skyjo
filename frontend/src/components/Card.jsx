function Card({ value, isVisible, onClick, size = 'normal', highlight = false, isEmpty = false }) {
  const getCardColor = (val) => {
    if (val === null || val === undefined) return 'bg-gray-300'
    if (val < 0) return 'bg-blue-500'
    if (val <= 3) return 'bg-green-500'
    if (val <= 6) return 'bg-yellow-500'
    if (val <= 9) return 'bg-orange-500'
    return 'bg-red-500'
  }

  const sizeClasses = {
    small: 'w-12 h-16 text-xs',
    normal: 'w-16 h-20 text-sm',
    large: 'w-24 h-32 text-lg'
  }

  if (isEmpty) {
    return (
      <div
        className={`
          ${sizeClasses[size]}
          rounded-lg border-2 border-dashed border-gray-400 bg-gray-100
          flex items-center justify-center
        `}
      >
        <span className="text-gray-400 text-xs">∅</span>
      </div>
    )
  }

  return (
    <div
      className={`
        ${sizeClasses[size]}
        rounded-lg shadow-md flex items-center justify-center font-bold
        transition-all duration-200
        ${onClick ? 'cursor-pointer hover:scale-105 hover:shadow-xl active:scale-95' : ''}
        ${highlight ? 'ring-2 ring-yellow-400 ring-offset-1' : ''}
        ${isVisible ? getCardColor(value) + ' text-white' : 'bg-gradient-to-br from-gray-700 to-gray-900 border-2 border-gray-600'}
      `}
      onClick={onClick}
    >
      {isVisible ? (
        <span className="text-center">{value !== null && value !== undefined ? value : '?'}</span>
      ) : (
        <div className="w-full h-full flex items-center justify-center">
          <div className="w-3/4 h-3/4 bg-gray-600 rounded border-2 border-gray-500 flex items-center justify-center">
            <span className="text-gray-300 text-xs font-bold">?</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default Card

