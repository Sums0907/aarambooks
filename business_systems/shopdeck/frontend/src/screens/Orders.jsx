import React, { useState, useEffect } from 'react';
import { fetchWithAuth } from '../apiClient';

function Orders({ apiBaseUrl }) {
  const [data, setData] = useState([]);
  const [orderSearch, setOrderSearch] = useState('');
  
  useEffect(() => {
    const url = new URL(`${apiBaseUrl}/orders`);
    if (orderSearch) url.searchParams.append('order_id', orderSearch);
    
    fetchWithAuth(url)
      .then(res => res.json())
      .then(res => setData(res.data || []))
      .catch(console.error);
  }, [apiBaseUrl, orderSearch]);

  return (
    <div>
      <h1>Orders</h1>
      <input 
        type="text" 
        placeholder="Search Order ID..." 
        value={orderSearch} 
        onChange={e => setOrderSearch(e.target.value)} 
      />
      <table border="1" cellPadding="5" style={{ marginTop: '10px', width: '100%' }}>
        <thead>
          <tr>
            <th>Order ID</th>
            <th>Amount</th>
            <th>Payment Mode</th>
            <th>Payment Status</th>
            <th>Updated At</th>
          </tr>
        </thead>
        <tbody>
          {data.map(row => (
            <tr key={row.order_id}>
              <td>{row.display_id || row.order_id}</td>
              <td>{row.total_amount}</td>
              <td>{row.payment_mode}</td>
              <td>{row.payment_status ? 'Success' : 'Failed/Pending'}</td>
              <td>{row.updatedat}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Orders;
