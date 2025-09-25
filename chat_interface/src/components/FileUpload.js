import React, { useState } from 'react';
import { uploadFile } from '../Services/api';
import '../Styles/FileUpload.css';

const FileUpload = () => {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);

  const handleFileSelect = (selectedFile) => {
    setFile(selectedFile);
    setResult(null);
    setError('');
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await uploadFile(file);
      setResult(response);
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="file-upload-container">
      <h3>Image Upload & OCR</h3>
      
      <form onSubmit={handleSubmit}>
        <div
          className={`file-drop-zone ${dragOver ? 'drag-over' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input
            type="file"
            onChange={(e) => handleFileSelect(e.target.files[0])}
            accept="image/*"
            id="file-input"
          />
          <label htmlFor="file-input">
            {file ? (
              <span>{file.name}</span>
            ) : (
              <span>Click to select or drag & drop an image</span>
            )}
          </label>
        </div>
        
        <button type="submit" disabled={loading || !file} className="upload-btn">
          {loading ? 'Processing...' : 'Upload & Process'}
        </button>
      </form>

      {error && <div className="error-message">{error}</div>}
      
      {result && (
        <div className="result-container">
          <h4>OCR Result:</h4>
          <div className="ocr-text">
            <strong>Extracted Text:</strong>
            <p>{result.Query}</p>
          </div>
          <div className="llm-response">
            <strong>AI Response:</strong>
            <p>{result.Response}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
