import React, { useState } from 'react';
import './UploadContentPage.css';

const UploadContentPage: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setSuccess(false);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      // Read file as base64
      const reader = new FileReader();
      const fileContent = await new Promise<string>((resolve, reject) => {
        reader.onload = () => {
          const base64 = (reader.result as string).split(',')[1];
          resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      // Upload directly through Lambda
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/upload/presigned`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.REACT_APP_API_KEY || ''
        },
        body: JSON.stringify({
          filename: file.name,
          file_content: fileContent,
          content_type: file.type
        })
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const result = await response.json();
      
      if (result.success) {
        setSuccess(true);
        setFile(null);
        console.log('Upload successful:', result.key);
      } else {
        throw new Error(result.error || 'Upload failed');
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-content-page">
      <div className="upload-container">
        <h1>Upload Training Content</h1>
        <p className="upload-description">
          Upload Edexcel past papers, mark schemes, or specification documents to improve question quality.
        </p>

        <div className="upload-box">
          <input
            type="file"
            accept=".pdf,.json"
            onChange={handleFileChange}
            id="file-input"
            className="file-input"
          />
          <label htmlFor="file-input" className="file-label">
            {file ? (
              <>
                <span className="file-icon">📄</span>
                <span className="file-name">{file.name}</span>
                <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
              </>
            ) : (
              <>
                <span className="upload-icon">📤</span>
                <span>Click to select a PDF or JSON file</span>
              </>
            )}
          </label>

          {file && (
            <button
              className="upload-button"
              onClick={handleUpload}
              disabled={uploading}
            >
              {uploading ? 'Uploading...' : 'Upload to AI'}
            </button>
          )}
        </div>

        {success && (
          <div className="success-message">
            ✅ File uploaded successfully! The AI will use this content for future questions.
          </div>
        )}

        {error && (
          <div className="error-message">
            ❌ {error}
          </div>
        )}

        <div className="upload-info">
          <h3>What to Upload:</h3>
          <ul>
            <li><strong>Past Papers (PDF)</strong> - Real Edexcel exam questions</li>
            <li><strong>Mark Schemes (PDF)</strong> - Official marking criteria</li>
            <li><strong>Specification (PDF)</strong> - Topic requirements</li>
            <li><strong>Example Questions (JSON)</strong> - Custom question templates</li>
          </ul>

          <h3>How It Works:</h3>
          <ol>
            <li>Select a file from your computer</li>
            <li>Click "Upload to AI"</li>
            <li>The AI extracts content and learns from it</li>
            <li>Future questions will be more authentic</li>
          </ol>
        </div>
      </div>
    </div>
  );
};

export default UploadContentPage;