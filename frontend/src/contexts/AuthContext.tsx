import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiClient } from '../services/apiClient';
import { AuthState } from '../types/api';

interface AuthContextType {
  authState: AuthState;
  login: (username: string, password: string) => Promise<boolean>;
  register: (username: string, password: string, email: string, school?: string, subjectSpecialization?: string) => Promise<boolean>;
  logout: () => void;
  isLoading: boolean;
  error: string | null;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>(apiClient.getAuthState());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Validate session on app start
    const validateSession = async () => {
      if (authState.isAuthenticated && authState.sessionToken) {
        setIsLoading(true);
        try {
          const isValid = await apiClient.validateSession();
          if (!isValid) {
            setAuthState(apiClient.getAuthState());
          }
        } catch (error) {
          console.error('Session validation error:', error);
          setAuthState(apiClient.getAuthState());
        } finally {
          setIsLoading(false);
        }
      }
    };

    validateSession();
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.login(username, password);
      
      if (response.success) {
        setAuthState(apiClient.getAuthState());
        return true;
      } else {
        setError(response.message);
        return false;
      }
    } catch (error: any) {
      const errorMessage = error.error?.message || 'Login failed. Please try again.';
      setError(errorMessage);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (
    username: string, 
    password: string, 
    email: string, 
    school?: string, 
    subjectSpecialization?: string
  ): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.register(username, password, email, school, subjectSpecialization);
      
      if (response.success) {
        setAuthState(apiClient.getAuthState());
        return true;
      } else {
        setError(response.message);
        return false;
      }
    } catch (error: any) {
      const errorMessage = error.error?.message || 'Registration failed. Please try again.';
      setError(errorMessage);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    apiClient.logout();
    setAuthState(apiClient.getAuthState());
    setError(null);
  };

  const clearError = () => {
    setError(null);
  };

  const value: AuthContextType = {
    authState,
    login,
    register,
    logout,
    isLoading,
    error,
    clearError
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;