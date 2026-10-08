import React, { createContext, useContext, useEffect, useState } from 'react';
import { PERSONAS, type Persona, type PersonaId, type UserRole } from '../types/auth';

interface AuthContextType {
  persona: Persona;
  token: string;
  role: UserRole;
  setPersonaId: (id: PersonaId) => void;
  availablePersonas: Persona[];
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const STORAGE_KEY = 'wealthwise_active_persona';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [personaId, setPersonaIdState] = useState<PersonaId>(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as PersonaId | null;
    return saved && PERSONAS[saved] ? saved : 'alice';
  });

  const persona = PERSONAS[personaId];

  const setPersonaId = (id: PersonaId) => {
    if (PERSONAS[id]) {
      setPersonaIdState(id);
      localStorage.setItem(STORAGE_KEY, id);
    }
  };

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, personaId);
  }, [personaId]);

  return (
    <AuthContext.Provider
      value={{
        persona,
        token: persona.token,
        role: persona.role,
        setPersonaId,
        availablePersonas: Object.values(PERSONAS),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
