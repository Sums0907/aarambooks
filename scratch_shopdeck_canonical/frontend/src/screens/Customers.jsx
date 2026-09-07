import React, { useState, useEffect } from 'react';
import { fetchWithAuth } from '../apiClient';

function Customers({ apiBaseUrl }) {
  const [data, setData] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  useEffect(() => {
    const url = new URL(`${apiBaseUrl}/customers`);
    if (searchQuery) {
      if (searchQuery.match(/^\d+$/)) {
        url.searchParams.append('phone', searchQuery);
      } else {
        url.searchParams.append('customer_id', searchQuery);
      }
    }
    
    fetchWithAuth(url)
      .then(res => res.json())
      .then(res => setData(res.data || []))
      .catch(console.error);
  }, [apiBaseUrl, searchQuery]);

  return (
    <div>
      <h1>Customers</h1>
      <input 
        type="text" 
        placeholder="Search Phone or ID..." 
        value={searchQuery} 
        onChange={e => setSearchQuery(e.target.value)} 
      />
      <table border="1" cellPadding="5" style={{ marginTop: '10px', width: '100%' }}>
        <thead>
          <tr>
            <th>Customer Name / ID</th>
            <th>AWB</th>
            <th>Pickup City</th>
            <th>Drop City</th>
            <th>Updated At</th>
          </tr>
        </thead>
        <tbody>
          {data.map(row => (
            <tr key={`${row.customer_id}-${row.awb_no}`}>
              <td>{row.customer_name || row.customer_id}</td>
              <td>{row.awb_no}</td>
              <td>{row.pickup_city}, {row.pickup_state}</td>
              <td>{row.drop_city}, {row.drop_state}</td>
              <td>{row.updatedat}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Customers;
