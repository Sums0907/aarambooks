import React, { useState, useEffect } from 'react';
import { fetchWithAuth } from '../apiClient';

function SyncHealth({ apiBaseUrl }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchWithAuth(`${apiBaseUrl}/sync/health`)
      .then(async res => {
        if (!res.ok) throw new Error(await res.text());
        return res.json();
      })
      .then(res => setData(res.checkpoints || []))
      .catch(err => {
        console.error(err);
        setError(err.message);
      });
  }, [apiBaseUrl]);

  return (
    <div>
      <h1>Sync Health</h1>
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      <table border="1" cellPadding="5" style={{ marginTop: '10px', width: '100%' }}>
        <thead>
          <tr>
            <th>Table / Sync Unit</th>
            <th>Last Watermark Checkpoint</th>
            <th>Cadence (mins)</th>
          </tr>
        </thead>
        <tbody>
          {data ? data.map(row => (
            <tr key={row.table_name}>
              <td>{row.table_name}</td>
              <td>{row.last_watermark || 'Never'}</td>
              <td>{row.cadence_minutes || 'External'}</td>
            </tr>
          )) : <tr><td colSpan="3">Loading...</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

export default SyncHealth;
