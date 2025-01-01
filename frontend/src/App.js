import React, { useState, useEffect } from 'react';

function App() {
  // Keep track of the puzzle and the puzzle size
  const [puzzle, setPuzzle] = useState([]);
  const [newBoardSize, setNewBoardSize] = useState(4);
  const [size, setSize] = useState(4);
  // const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
  const API_URL = 'http://127.0.0.1:5000';

  // Fetch current puzzle on mount
  useEffect(() => {
    fetchPuzzle();
  }, []);

  // Function to fetch the puzzle from backend
  const fetchPuzzle = () => {
    fetch(`${API_URL}/api/puzzle`)
      .then((res) => res.json())
      .then((data) => {
        setSize(data.size);
        setPuzzle(data.puzzle);
      })
      .catch((err) => console.error(err));
  };

  // Request a new puzzle of the given size
  const startNewPuzzle = () => {
    fetch(`${API_URL}/api/new`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ size: newBoardSize }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.puzzle) {
          setSize(data.size);
          setPuzzle(data.puzzle);
        } else if (data.error) {
          alert(data.error);
        }
      })
      .catch((err) => console.error(err));
  };

  // Attempt to move a tile
  const handleTileClick = (tile) => {
    fetch(`${API_URL}/api/move`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tile }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.puzzle) {
          setSize(data.size);
          setPuzzle(data.puzzle);
        }
      })
      .catch((err) => console.error(err));
  };

  // Build a 2D array from the 1D puzzle array
  const rows = [];
  for (let i = 0; i < size; i++) {
    rows.push(puzzle.slice(i * size, i * size + size));
  }

  return (
    <div style={styles.container}>
      <h1>{size}x{size} Sliding Puzzle</h1>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ marginRight: '8px' }}>
          Board Size:
          <input
            type="number"
            value={newBoardSize}
            onChange={(e) => setNewBoardSize(e.target.value)}
            style={{ marginLeft: '8px', width: '60px' }}
            min="2"
            max="50"
          />
        </label>
        <button onClick={startNewPuzzle} style={styles.newPuzzleButton}>
          New Puzzle
        </button>
      </div>

      <div style={styles.board}>
        {rows.map((row, rowIndex) => (
          <div key={`row-${rowIndex}`} style={styles.row}>
            {row.map((tile, colIndex) => {
              const isHole = tile === 0;
              return (
                <div
                  key={`tile-${rowIndex}-${colIndex}`}
                  style={{
                    ...styles.tile,
                    width: 40, // you can also scale by size if you want
                    height: 40,
                    backgroundColor: isHole ? '#ccc' : '#69c',
                    cursor: isHole ? 'default' : 'pointer',
                  }}
                  onClick={() => !isHole && handleTileClick(tile)}
                >
                  {isHole ? '' : tile}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  container: {
    textAlign: 'center',
    marginTop: '40px',
  },
  newPuzzleButton: {
    marginLeft: '16px',
    fontSize: '16px',
    padding: '8px 16px',
    cursor: 'pointer',
  },
  board: {
    display: 'inline-block',
    border: '2px solid #333',
  },
  row: {
    display: 'flex',
  },
  tile: {
    margin: '2px',
    lineHeight: '40px',
    textAlign: 'center',
    fontSize: '16px',
    color: '#fff',
    borderRadius: '4px',
    userSelect: 'none',
  },
};

export default App;
