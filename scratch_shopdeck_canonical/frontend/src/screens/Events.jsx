import React, { useState, useEffect } from 'react';
import { fetchWithAuth } from '../apiClient';

function Events({ apiBaseUrl }) {
  const tables = [
    "cancel_reason_events", "order_cancellation_events", "return_exchange_events",
    "post_order_survey_submit_events", "rating_review_feedback_submit_events",
    "payment_gateway_events", "checkout_external_events", "checkout_input_error_events"
  ];
  const [selectedTable, setSelectedTable] = useState(tables[0]);
  const [data, setData] = useState([]);

  useEffect(() => {
    fetchWithAuth(`${apiBaseUrl}/events/${selectedTable}`)
      .then(res => res.json())
      .then(res => setData(res.data || []))
      .catch(console.error);
  }, [apiBaseUrl, selectedTable]);

  return (
    <div>
      <h1>Events</h1>
      <select value={selectedTable} onChange={e => setSelectedTable(e.target.value)}>
        {TABLES.map(t => <option key={t} value={t}>{t}</option>)}
      </select>
      
      <table border="1" cellPadding="5" style={{ marginTop: '10px', width: '100%' }}>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Identifiers</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i}>
              <td>{row.created_at || row.updatedat || 'N/A'}</td>
              <td>{row.order_id || row.awb_no || row.session_id || 'N/A'}</td>
              <td>
                <pre style={{ margin: 0, fontSize: '0.8em', maxWidth: '400px', overflowX: 'auto' }}>
                  {JSON.stringify(row, null, 2)}
                </pre>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Events;
