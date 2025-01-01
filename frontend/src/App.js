import React, { useState, useEffect } from 'react';
import { Grid } from '@mui/material';

function App() {
  const [puzzle, setPuzzle] = useState([]); // store puzzle as 1D array of length 16
  // const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
  const API_URL = 'http://127.0.0.1:5000';

  // Fetch puzzle on mount
  useEffect(() => {
    fetch(`${API_URL}/api/puzzle`)
      .then((res) => res.json())
      .then((data) => {
        setPuzzle(data.puzzle);
      })
      .catch((err) => console.error(err));
  }, [API_URL]);

  const handleTileClick = (tile) => {
    // Attempt to move clicked tile
    fetch(`${API_URL}/api/move`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tile }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.puzzle) {
          setPuzzle(data.puzzle);
        }
      })
      .catch((err) => console.error(err));
  };

  const startNewPuzzle = () => {
    // Call the /api/new endpoint to get a fresh puzzle
    fetch(`${API_URL}/api/new`, { method: 'POST' })
      .then((res) => res.json())
      .then((data) => {
        setPuzzle(data.puzzle);
      })
      .catch((err) => console.error(err));
  };

  // Convert puzzle array to 4x4 for rendering
  const rows = [];
  for (let i = 0; i < 4; i++) {
    rows.push(puzzle.slice(i * 4, i * 4 + 4));
  }

  return (
    <div style={styles.container}>
      <h1>15/16 Sliding Puzzle</h1>
      
      {/* New Puzzle button */}
      <button onClick={startNewPuzzle} style={styles.newPuzzleButton}>
        New Puzzle
      </button>

      <Grid container direction="column" alignItems="center" justifyContent="center">
        <div style={styles.board}>
          {rows.map((row, rowIndex) => (
            <div key={rowIndex} style={styles.row}>
              {row.map((tile, colIndex) => {
                const isHole = tile === 0;
                return (
                  <div
                    key={`${rowIndex}-${colIndex}`}
                    style={{
                      ...styles.tile,
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
      </Grid>
    </div>
  );
}

const styles = {
  container: {
    textAlign: 'center',
    marginTop: '40px',
  },
  newPuzzleButton: {
    marginBottom: '20px',
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
    width: '60px',
    height: '60px',
    margin: '2px',
    lineHeight: '60px',
    textAlign: 'center',
    fontSize: '20px',
    color: '#fff',
    borderRadius: '4px',
    userSelect: 'none',
  },
};

export default App;
