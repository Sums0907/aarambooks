import React, { useState, useEffect } from 'react';

function Dashboard({ apiBaseUrl }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${apiBaseUrl}/system/status`)
      .then(res => res.json())
      .then(setData)
      .catch(console.error);
  }, [apiBaseUrl]);

  return (
    <div>
      <h1>Dashboard</h1>
      {data ? (
        <ul>
          <li><strong>API Status:</strong> {data.status}</li>
          <li><strong>Database Connected:</strong> {data.database_connected ? 'Yes' : 'No'}</li>
          <li><strong>Version:</strong> {data.version}</li>
        </ul>
      ) : (
        <p>Loading...</p>
      )}
    </div>
  );
}

export default Dashboard;
