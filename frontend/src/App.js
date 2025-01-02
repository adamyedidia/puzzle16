// src/App.js
import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';

function App() {
  const [puzzle, setPuzzle] = useState([]);
  const [size, setSize] = useState(4);
  const [newBoardSize, setNewBoardSize] = useState(4);
  const [isSolving, setIsSolving] = useState(false);
  const [numMoves, setNumMoves] = useState(0);
  const [thinkingTime, setThinkingTime] = useState(0);

  const [maxExpansions, setMaxExpansions] = useState(50000);
  const [useHeuristicAdjustment, setUseHeuristicAdjustment] = useState(false);


  // const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
  const API_URL = 'http://127.0.0.1:5000';
  // Connect to socket.io
  const [socket, setSocket] = useState(null);

  // On component mount, fetch initial puzzle + setup socket
  useEffect(() => {
    // Fetch the puzzle
    fetch(`${API_URL}/api/stop_auto_solve`, { method: 'POST' })
    .then(res => res.json())
    .catch(err => console.error('Error stopping auto-solve:', err));

    fetchPuzzle();

    // Setup socket connection
    const newSocket = io(API_URL);
    setSocket(newSocket);

    // Listen for solver updates
    newSocket.on('solver_update', (data) => {
      console.log('got solver update')
      setPuzzle(data.puzzle);
      setSize(data.size);
      setNumMoves(data.num_moves);
      setThinkingTime(data.thinking_time);

      // if data.solved is true, the puzzle is done
      if (data.solved) {
        setIsSolving(false);
      }
    });

    // Listen for solver complete
    newSocket.on('solver_complete', (data) => {
      // data.message might be "Puzzle solved!"
      setIsSolving(false);
    });

    // Cleanup socket on unmount
    return () => {
      newSocket.close();
    };
  }, [API_URL]);

  const fetchPuzzle = () => {
    fetch(`${API_URL}/api/puzzle`)
      .then(res => res.json())
      .then(data => {
        setPuzzle(data.puzzle);
        setSize(data.size);
        setNumMoves(0);
        setThinkingTime(0);
      })
      .catch(err => console.error(err));
  };

  // Start auto-solve
  const startAutoSolve = () => {
    fetch(`${API_URL}/api/auto_solve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        max_expansions: maxExpansions,
        use_heuristic_adjustment: useHeuristicAdjustment
      })
    })
      .then(res => res.json())
      .then(_ => {
        setIsSolving(true);
      })
      .catch(err => console.error(err));
  };

  // Stop auto-solve
  const stopAutoSolve = () => {
    fetch(`${API_URL}/api/stop_auto_solve`, { method: 'POST' })
      .then(res => res.json())
      .then(_ => {
        setIsSolving(false);
      })
      .catch(err => console.error(err));
  };

  // Attempt to move a tile (disabled while isSolving = true)
  const handleTileClick = (tile) => {
    if (isSolving || tile === 0) return;
    fetch(`${API_URL}/api/move`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tile }),
    })
      .then(res => res.json())
      .then(data => {
        setPuzzle(data.puzzle);
        setSize(data.size);
        setNumMoves(data.num_moves);
      })
      .catch(err => console.error(err));
  };

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

  // Build 2D grid
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
            disabled={isSolving}
          />
        </label>
        <button 
          onClick={startNewPuzzle} 
          style={{
            ...styles.newPuzzleButton,
            opacity: isSolving ? 0.5 : 1,
            cursor: isSolving ? 'not-allowed' : 'pointer'
          }}
          disabled={isSolving}
        >
          New Puzzle
        </button>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ marginRight: '16px' }}>
          Max Expansions:
          <input
            type="number"
            value={maxExpansions}
            onChange={(e) => setMaxExpansions(parseInt(e.target.value))}
            style={{ marginLeft: '8px', width: '100px' }}
            min="1000"
            disabled={isSolving}
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={useHeuristicAdjustment}
            onChange={(e) => setUseHeuristicAdjustment(e.target.checked)}
            disabled={isSolving}
          />
          Use Heuristic Adjustment
        </label>
      </div>


      <div style={{ marginBottom: '20px' }}>
        {isSolving ? (
          <button onClick={stopAutoSolve} style={styles.button}>
            Stop Auto-Solve
          </button>
        ) : (
          <button 
            onClick={startAutoSolve} 
            style={{
              ...styles.button,
              opacity: puzzle.length === 0 ? 0.5 : 1,
              cursor: puzzle.length === 0 ? 'not-allowed' : 'pointer'
            }}
            disabled={puzzle.length === 0}
          >
            Auto-Solve
          </button>
        )}
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
                    backgroundColor: isHole ? '#ccc' : '#69c',
                    cursor: isSolving ? 'not-allowed'
                                      : (isHole ? 'default' : 'pointer'),
                  }}
                  onClick={() => handleTileClick(tile)}
                >
                  {isHole ? '' : tile}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      <br />
      <div style={styles.puzzleState}>
        Current State: 
        <input 
          type="text" 
          value={puzzle.join(',')}
          readOnly
          style={styles.stateInput}
          onClick={(e) => e.target.select()}
        />
      </div>
      <div style={styles.puzzleState}>
        Set New State: 
        <input 
          type="text" 
          placeholder="Enter comma-separated numbers..."
          style={styles.stateInput}
          disabled={isSolving}
        />
        <button
          onClick={() => {
            const input = document.querySelector('input[placeholder="Enter comma-separated numbers..."]');
            const newState = input.value.split(',').map(num => parseInt(num.trim()));
            
            fetch(`${API_URL}/api/set_state`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ puzzle: newState }),
            })
              .then(res => res.json())
              .then(data => {
                if (data.error) {
                  alert(data.error);
                } else {
                  setPuzzle(data.puzzle);
                  setSize(data.size);
                }
              })
              .catch(err => {
                console.error(err);
                alert('Error setting puzzle state');
              });
          }}
          style={{
            ...styles.button,
            opacity: isSolving ? 0.5 : 1,
            cursor: isSolving ? 'not-allowed' : 'pointer'
          }}
          disabled={isSolving}
        >
          Set State
        </button>
      </div>      
      <div style={styles.puzzleState}>
        Moves: {numMoves}
      </div>
      <div style={styles.puzzleState}>
        Thinking Time: {thinkingTime.toFixed(0)}s
      </div>
    </div>
  );
}

const styles = {
  container: {
    textAlign: 'center',
    marginTop: '40px',
  },
  button: {
    fontSize: '16px',
    padding: '8px 16px',
    cursor: 'pointer',
    marginLeft: '10px'
  },
  board: {
    display: 'inline-block',
    border: '2px solid #333',
  },
  row: {
    display: 'flex',
  },
  tile: {
    width: '40px',
    height: '40px',
    margin: '2px',
    lineHeight: '40px',
    textAlign: 'center',
    fontSize: '16px',
    color: '#fff',
    borderRadius: '4px',
    userSelect: 'none',
  },
  puzzleState: {
    marginTop: '20px',
    fontFamily: 'monospace',
    fontSize: '14px',
    color: '#666',
  },  
};

export default App;
