import React, { useState } from 'react';
import { queryTexts } from '../Services/api';
import '../Styles/TextQuery.css';

const TextQuery = () => {
  const [queries, setQueries] = useState(['']);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const addQuery = () => {
    setQueries([...queries, '']);
  };

  const removeQuery = (index) => {
    setQueries(queries.filter((_, i) => i !== index));
  };

  const updateQuery = (index, value) => {
    const newQueries = [...queries];
    newQueries[index] = value;
    setQueries(newQueries);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResults(null);

    try {
      const filteredQueries = queries.filter(q => q.trim() !== '');
      const response = await queryTexts(filteredQueries);
      setResults(response);
    } catch (err) {
      setError(err.response?.data?.detail || 'Query failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="text-query-container">
      <h3>Text Query</h3>
      
      <form onSubmit={handleSubmit}>
        {queries.map((query, index) => (
          <div key={index} className="query-input-group">
            <textarea
              value={query}
              onChange={(e) => updateQuery(index, e.target.value)}
              placeholder={`Enter query ${index + 1}...`}
              rows="3"
            />
            {queries.length > 1 && (
              <button
                type="button"
                onClick={() => removeQuery(index)}
                className="remove-btn"
              >
                Remove
              </button>
            )}
          </div>
        ))}
        
        <div className="query-actions">
          <button type="button" onClick={addQuery} className="add-btn">
            Add Query
          </button>
          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? 'Processing...' : 'Submit Queries'}
          </button>
        </div>
      </form>

      {error && <div className="error-message">{error}</div>}
      
      {results && (
  <div className="results-container">
    <h4>Results:</h4>
    {results.results.map((result, index) => (
      <div key={index} className="result-item">
        <strong>Query {index + 1}:</strong> {results.text[index]}
        <br />
        <strong>Response:</strong> {result}
      </div>
    ))}
  </div>
)}

    </div>
  );
};

export default TextQuery;
