import React, { useState } from 'react';
import { uploadBatchFiles } from '../Services/api';
import '../Styles/BatchUpload.css';

const BatchUpload = () => {
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFilesSelect = (selectedFiles) => {
    setFiles(Array.from(selectedFiles));
    setResults(null);
    setError('');
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (files.length === 0) {
      setError('Please select at least one file');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await uploadBatchFiles(files);
      setResults(response);
    } catch (err) {
      setError(err.response?.data?.detail || 'Batch upload failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="batch-upload-container">
      <h3>Batch Image Upload & OCR</h3>
      
      <form onSubmit={handleSubmit}>
        <div className="file-input-container">
          <input
            type="file"
            onChange={(e) => handleFilesSelect(e.target.files)}
            accept="image/*"
            multiple
            id="batch-file-input"
          />
          <label htmlFor="batch-file-input" className="file-input-label">
            Select Multiple Images
          </label>
        </div>
        
        {files.length > 0 && (
          <div className="selected-files">
            <h4>Selected Files ({files.length}):</h4>
            {files.map((file, index) => (
              <div key={index} className="file-item">
                <span>{file.name}</span>
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  className="remove-file-btn"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
        
        <button
          type="submit"
          disabled={loading || files.length === 0}
          className="batch-upload-btn"
        >
          {loading ? 'Processing...' : `Upload & Process ${files.length} Files`}
        </button>
      </form>

      {error && <div className="error-message">{error}</div>}
      
      {results && (
        <div className="batch-results-container">
          <h4>Batch Processing Results:</h4>
          {results.results.map((result, index) => (
            <div key={index} className="batch-result-item">
              <strong>File:</strong> {result.filename}
              {result.error ? (
                <div className="result-error">Error: {result.error}</div>
              ) : (
                <div className="result-success">
                  <div><strong>Extracted Text:</strong> {result.text}</div>
                  <div><strong>AI Response:</strong> {result.response}</div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default BatchUpload;
