import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import QueryInput from './QueryInput';

describe('QueryInput', () => {
  const mockOnSubmit = jest.fn();

  beforeEach(() => {
    mockOnSubmit.mockClear();
  });

  it('renders query input form', () => {
    render(<QueryInput onSubmit={mockOnSubmit} loading={false} />);
    
    expect(screen.getByLabelText(/describe the questions/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate questions/i })).toBeInTheDocument();
    expect(screen.getByText('0/500')).toBeInTheDocument();
  });

  it('updates character count as user types', async () => {
    render(<QueryInput onSubmit={mockOnSubmit} loading={false} />);
    
    const textarea = screen.getByLabelText(/describe the questions/i);
    userEvent.type(textarea, 'Test query');
    
    expect(screen.getByText('10/500')).toBeInTheDocument();
  });

  it('prevents input beyond 500 characters', async () => {
    render(<QueryInput onSubmit={mockOnSubmit} loading={false} />);
    
    const textarea = screen.getByLabelText(/describe the questions/i);
    const longText = 'a'.repeat(501);
    
    userEvent.type(textarea, longText);
    
    expect(textarea).toHaveValue('a'.repeat(500));
    expect(screen.getByText('500/500')).toBeInTheDocument();
  });

  it('shows warning styles when near character limit', async () => {
    render(<QueryInput onSubmit={mockOnSubmit} loading={false} />);
    
    const textarea = screen.getByLabelText(/describe the questions/i);
    userEvent.type(textarea, 'a'.repeat(450));
    
    expect(screen.getByText('450/500')).toHaveClass('warning');
    expect(textarea).toHaveClass('near-limit');
  });

  it('shows error styles when at character limit', async () => {
    render(<QueryInput onSubmit={mockOnSubmit} loading={false} />);
    
    const textarea = screen.getByLabelText(/describe the questions/i);
    userEvent.type(textarea, 'a'.repeat(500));
    
    expect(screen.getByText('500/500')).toHaveClass('error');
    expect(textarea).toHaveClass('at-limit');
  });

  it('disables submit button when input is empty', () => {
    render(<QueryInput onSubmit={mockOnSubmit} loading={false} />);
    
    const submitButton = screen.getByRole('button', { name: /generate questions/i });
    expect(submitButton).toBeDisabled();
  });

  it('enables submit button when input has content', async () => {
    render(<QueryInput onSubmit={mockOnSubmit} loading={false} />);
    
    const textarea = screen.getByLabelText(/describe the questions/i);
    const submitButton = screen.getByRole('button', { name: /generate questions/i });
    
    userEvent.type(textarea, 'Test query');
    
    expect(submitButton).not.toBeDisabled();
  });

  it('calls onSubmit with trimmed query when form is submitted', async () => {
    render(<QueryInput onSubmit={mockOnSubmit} loading={false} />);
    
    const textarea = screen.getByLabelText(/describe the questions/i);
    const submitButton = screen.getByRole('button', { name: /generate questions/i });
    
    userEvent.type(textarea, '  Test query  ');
    userEvent.click(submitButton);
    
    expect(mockOnSubmit).toHaveBeenCalledWith('Test query');
  });

  it('shows loading state when loading prop is true', () => {
    render(<QueryInput onSubmit={mockOnSubmit} loading={true} />);
    
    const submitButton = screen.getByRole('button', { name: /generating questions/i });
    expect(submitButton).toBeDisabled();
    expect(screen.getByText(/generating questions/i)).toBeInTheDocument();
    expect(screen.getByRole('button')).toHaveClass('generate-button');
  });

  it('disables form when disabled prop is true', () => {
    render(<QueryInput onSubmit={mockOnSubmit} loading={false} disabled={true} />);
    
    const textarea = screen.getByLabelText(/describe the questions/i);
    const submitButton = screen.getByRole('button', { name: /generate questions/i });
    
    expect(textarea).toBeDisabled();
    expect(submitButton).toBeDisabled();
  });

  it('shows clear button when input has content', async () => {
    render(<QueryInput onSubmit={mockOnSubmit} loading={false} />);
    
    const textarea = screen.getByLabelText(/describe the questions/i);
    userEvent.type(textarea, 'Test query');
    
    expect(screen.getByRole('button', { name: /clear input/i })).toBeInTheDocument();
  });

  it('clears input when clear button is clicked', async () => {
    render(<QueryInput onSubmit={mockOnSubmit} loading={false} />);
    
    const textarea = screen.getByLabelText(/describe the questions/i);
    userEvent.type(textarea, 'Test query');
    
    const clearButton = screen.getByRole('button', { name: /clear input/i });
    userEvent.click(clearButton);
    
    expect(textarea).toHaveValue('');
    expect(screen.getByText('0/500')).toBeInTheDocument();
  });

  it('shows help text with examples', () => {
    render(<QueryInput onSubmit={mockOnSubmit} loading={false} />);
    
    expect(screen.getByText(/examples/i)).toBeInTheDocument();
    expect(screen.getByText(/5 foundation fractions questions/i)).toBeInTheDocument();
    expect(screen.getByText(/3 higher algebra questions/i)).toBeInTheDocument();
  });
});