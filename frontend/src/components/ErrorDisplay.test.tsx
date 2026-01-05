import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ErrorDisplay from './ErrorDisplay';
import { ApiError } from '../types/api';

describe('ErrorDisplay', () => {
  const mockOnRetry = jest.fn();
  const mockOnDismiss = jest.fn();

  beforeEach(() => {
    mockOnRetry.mockClear();
    mockOnDismiss.mockClear();
  });

  const validationError: ApiError = {
    error: {
      type: 'ValidationError',
      message: 'Query is too long. Please limit your request to 500 characters.',
      request_id: 'req-123',
      timestamp: '2024-12-27T10:30:00Z',
      guidance: 'Try to be more concise in your request.',
      details: 'Input length: 501 characters',
    },
  };

  const timeoutError: ApiError = {
    error: {
      type: 'TimeoutError',
      message: 'Request timed out after 30 seconds.',
      request_id: 'req-456',
      timestamp: '2024-12-27T10:30:00Z',
      guidance: 'Please try again. The service may be experiencing high load.',
      retry_after: 60,
    },
  };

  const serviceUnavailableError: ApiError = {
    error: {
      type: 'ServiceUnavailable',
      message: 'The service is temporarily unavailable.',
      request_id: 'req-789',
      timestamp: '2024-12-27T10:30:00Z',
      guidance: 'Please try again in a few minutes.',
    },
  };

  it('renders error message and title', () => {
    render(<ErrorDisplay error={validationError} />);
    
    expect(screen.getByText('Invalid Request')).toBeInTheDocument();
    expect(screen.getByText('Query is too long. Please limit your request to 500 characters.')).toBeInTheDocument();
  });

  it('displays appropriate icon for validation error', () => {
    render(<ErrorDisplay error={validationError} />);
    
    expect(screen.getByText('⚠️')).toBeInTheDocument();
  });

  it('displays appropriate icon for timeout error', () => {
    render(<ErrorDisplay error={timeoutError} />);
    
    expect(screen.getByText('⏱️')).toBeInTheDocument();
  });

  it('displays appropriate icon for service unavailable error', () => {
    render(<ErrorDisplay error={serviceUnavailableError} />);
    
    expect(screen.getByText('🔌')).toBeInTheDocument();
  });

  it('shows guidance when provided', () => {
    render(<ErrorDisplay error={validationError} />);
    
    expect(screen.getByText('What you can do:')).toBeInTheDocument();
    expect(screen.getByText('Try to be more concise in your request.')).toBeInTheDocument();
  });

  it('shows technical details when provided', () => {
    render(<ErrorDisplay error={validationError} />);
    
    const detailsElement = screen.getByText('Technical Details');
    expect(detailsElement).toBeInTheDocument();
  });

  it('expands technical details when clicked', async () => {
    render(<ErrorDisplay error={validationError} />);
    
    const detailsElement = screen.getByText('Technical Details');
    userEvent.click(detailsElement);
    
    expect(screen.getByText('Input length: 501 characters')).toBeInTheDocument();
  });

  it('shows retry button for retryable errors', () => {
    render(<ErrorDisplay error={timeoutError} onRetry={mockOnRetry} />);
    
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('does not show retry button for validation errors', () => {
    render(<ErrorDisplay error={validationError} onRetry={mockOnRetry} />);
    
    expect(screen.queryByText('Try Again')).not.toBeInTheDocument();
  });

  it('shows retry hint when retry_after is provided', () => {
    render(<ErrorDisplay error={timeoutError} onRetry={mockOnRetry} />);
    
    expect(screen.getByText('(wait 60s)')).toBeInTheDocument();
  });

  it('calls onRetry when retry button is clicked', async () => {
    render(<ErrorDisplay error={timeoutError} onRetry={mockOnRetry} />);
    
    const retryButton = screen.getByText('Try Again');
    userEvent.click(retryButton);
    
    expect(mockOnRetry).toHaveBeenCalledTimes(1);
  });

  it('shows dismiss button when onDismiss is provided', () => {
    render(<ErrorDisplay error={validationError} onDismiss={mockOnDismiss} />);
    
    expect(screen.getByText('Dismiss')).toBeInTheDocument();
  });

  it('calls onDismiss when dismiss button is clicked', async () => {
    render(<ErrorDisplay error={validationError} onDismiss={mockOnDismiss} />);
    
    const dismissButton = screen.getByText('Dismiss');
    userEvent.click(dismissButton);
    
    expect(mockOnDismiss).toHaveBeenCalledTimes(1);
  });

  it('displays request ID and timestamp', () => {
    render(<ErrorDisplay error={validationError} />);
    
    expect(screen.getByText('Request ID: req-123')).toBeInTheDocument();
    
    // Check that timestamp is formatted (should contain the date in some format)
    const timestampElement = screen.getByText(/12\/27\/2024|27\/12\/2024|2024-12-27/);
    expect(timestampElement).toBeInTheDocument();
  });

  it('applies correct CSS class for error type', () => {
    const { container } = render(<ErrorDisplay error={validationError} />);
    
    expect(container.firstChild).toHaveClass('error-validationerror');
  });

  it('handles errors without guidance gracefully', () => {
    const errorWithoutGuidance: ApiError = {
      error: {
        type: 'InternalError',
        message: 'An unexpected error occurred.',
        request_id: 'req-999',
        timestamp: '2024-12-27T10:30:00Z',
      },
    };
    
    render(<ErrorDisplay error={errorWithoutGuidance} />);
    
    expect(screen.getByText('An unexpected error occurred.')).toBeInTheDocument();
    expect(screen.queryByText('What you can do:')).not.toBeInTheDocument();
  });

  it('handles errors without details gracefully', () => {
    const errorWithoutDetails: ApiError = {
      error: {
        type: 'ServiceUnavailable',
        message: 'Service is down.',
        request_id: 'req-888',
        timestamp: '2024-12-27T10:30:00Z',
      },
    };
    
    render(<ErrorDisplay error={errorWithoutDetails} />);
    
    expect(screen.getByText('Service is down.')).toBeInTheDocument();
    expect(screen.queryByText('Technical Details')).not.toBeInTheDocument();
  });
});