import React from 'react';
import { ApiError } from '../types/api';
import './ErrorDisplay.css';

interface ErrorDisplayProps {
  error: ApiError | null | undefined;
  onRetry?: () => void;
  onDismiss?: () => void;
}

const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ error, onRetry, onDismiss }) => {
  // Handle null/undefined error or missing error.error structure
  if (!error) {
    return null;
  }
  
  // Normalize error structure - handle both {error: {...}} and {message: "..."} formats
  let normalizedError: ApiError['error'];
  
  if (error.error && typeof error.error === 'object') {
    normalizedError = error.error;
  } else {
    // Handle cases where error is in a different format (e.g., {message: "..."})
    const anyError = error as any;
    normalizedError = {
      type: 'InternalError' as const,
      message: anyError.message || anyError.error || 'An unexpected error occurred',
      request_id: anyError.request_id || 'unknown',
      timestamp: anyError.timestamp || new Date().toISOString(),
      guidance: anyError.guidance
    };
  }
  
  // If we still don't have a valid error structure, show a generic error
  if (!normalizedError || !normalizedError.type) {
    return (
      <div className="error-display error-internalerror">
        <div className="error-content">
          <div className="error-header">
            <span className="error-icon" aria-hidden="true">❌</span>
            <h3 className="error-title">Error</h3>
          </div>
          <div className="error-body">
            <p className="error-message">{normalizedError?.message || 'An unexpected error occurred'}</p>
          </div>
          <div className="error-actions">
            {onRetry && (
              <button className="error-retry-button" onClick={onRetry}>
                Try Again
              </button>
            )}
            {onDismiss && (
              <button className="error-dismiss-button" onClick={onDismiss}>
                Dismiss
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }
  
  // Use normalizedError for the rest of the component
  const errorData = normalizedError;

  const getErrorIcon = (type: string) => {
    switch (type) {
      case 'ValidationError':
        return '⚠️';
      case 'TimeoutError':
        return '⏱️';
      case 'ServiceUnavailable':
        return '🔌';
      default:
        return '❌';
    }
  };

  const getErrorTitle = (type: string) => {
    switch (type) {
      case 'ValidationError':
        return 'Invalid Request';
      case 'TimeoutError':
        return 'Request Timeout';
      case 'ServiceUnavailable':
        return 'Service Unavailable';
      case 'InternalError':
        return 'Internal Error';
      default:
        return 'Error';
    }
  };

  const shouldShowRetry = (type: string) => {
    return ['TimeoutError', 'ServiceUnavailable', 'InternalError'].includes(type);
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  return (
    <div className={`error-display error-${errorData.type.toLowerCase()}`}>
      <div className="error-content">
        <div className="error-header">
          <span className="error-icon" aria-hidden="true">
            {getErrorIcon(errorData.type)}
          </span>
          <h3 className="error-title">
            {getErrorTitle(errorData.type)}
          </h3>
        </div>

        <div className="error-body">
          <p className="error-message">
            {errorData.message}
          </p>

          {errorData.guidance && (
            <div className="error-guidance">
              <h4>What you can do:</h4>
              <p>{errorData.guidance}</p>
            </div>
          )}

          {errorData.details && (
            <details className="error-details">
              <summary>Technical Details</summary>
              <p>{errorData.details}</p>
            </details>
          )}
        </div>

        <div className="error-actions">
          {shouldShowRetry(errorData.type) && onRetry && (
            <button
              className="retry-button"
              onClick={onRetry}
              type="button"
            >
              Try Again
              {errorData.retry_after && (
                <span className="retry-hint">
                  (wait {errorData.retry_after}s)
                </span>
              )}
            </button>
          )}

          {onDismiss && (
            <button
              className="dismiss-button"
              onClick={onDismiss}
              type="button"
            >
              Dismiss
            </button>
          )}
        </div>

        <div className="error-footer">
          <div className="error-meta">
            <span className="error-id">
              Request ID: {errorData.request_id}
            </span>
            <span className="error-timestamp">
              {formatTimestamp(errorData.timestamp)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ErrorDisplay;