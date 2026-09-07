import React, { useState, useEffect } from 'react';
import { fetchWithAuth } from '../apiClient';

function NDR({ apiBaseUrl }) {
  const [data, setData] = useState([]);
  const [awbSearch, setAwbSearch] = useState('');
  
  useEffect(() => {
    const url = new URL(`${apiBaseUrl}/ndr`);
    if (awbSearch) url.searchParams.append('awb_no', awbSearch);
    
    fetchWithAuth(url)
      .then(res => res.json())
      .then(res => setData(res.data || []))
      .catch(console.error);
  }, [apiBaseUrl, awbSearch]);

  return (
    <div>
      <h1>NDR Shipments</h1>
      <input 
        type="text" 
        placeholder="Search AWB..." 
        value={awbSearch} 
        onChange={e => setAwbSearch(e.target.value)} 
      />
      <table border="1" cellPadding="5" style={{ marginTop: '10px', width: '100%' }}>
        <thead>
          <tr>
            <th>AWB</th>
            <th>Customer</th>
            <th>Courier</th>
            <th>Status</th>
            <th>Reason</th>
            <th>Count</th>
          </tr>
        </thead>
        <tbody>
          {data.map(row => (
            <tr key={row.awb_no}>
              <td>{row.awb_no}</td>
              <td>{row.customer_name}</td>
              <td>{row.courier_partner}</td>
              <td>{row.status}</td>
              <td>{row.latest_ndr_reason}</td>
              <td>{row.ndr_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default NDR;
