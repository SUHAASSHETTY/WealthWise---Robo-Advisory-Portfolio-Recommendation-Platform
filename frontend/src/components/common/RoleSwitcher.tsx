import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import type { PersonaId } from '../../types/auth';

export const RoleSwitcher: React.FC = () => {
  const { persona, setPersonaId, availablePersonas } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  const roleColors: Record<string, string> = {
    CUSTOMER: 'badge--indigo',
    ADVISOR: 'badge--emerald',
    ADMIN: 'badge--amber',
  };

  return (
    <div className="role-switcher">
      <button
        id="role-switcher-trigger"
        type="button"
        className="role-switcher__trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
        aria-label="Switch User Persona and Role"
      >
        <span className="role-switcher__avatar">{persona.avatar}</span>
        <div className="role-switcher__details">
          <span className="role-switcher__name">{persona.name}</span>
          <span className={`role-switcher__role-tag ${roleColors[persona.role] || ''}`}>
            {persona.role}
          </span>
        </div>
        <span className="role-switcher__arrow">{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && (
        <>
          <div className="dropdown-overlay" onClick={() => setIsOpen(false)} />
          <div className="role-switcher__dropdown" role="menu">
            <div className="role-switcher__dropdown-header">Select Persona (Stub Tokens)</div>
            {availablePersonas.map((p) => {
              const isSelected = p.id === persona.id;
              return (
                <button
                  id={`persona-option-${p.id}`}
                  key={p.id}
                  type="button"
                  className={`role-switcher__option ${isSelected ? 'role-switcher__option--selected' : ''}`}
                  onClick={() => {
                    setPersonaId(p.id as PersonaId);
                    setIsOpen(false);
                  }}
                  role="menuitem"
                >
                  <span className="role-switcher__avatar">{p.avatar}</span>
                  <div className="role-switcher__option-text">
                    <div className="role-switcher__option-row">
                      <span className="role-switcher__option-name">{p.name}</span>
                      <span className={`role-switcher__role-tag ${roleColors[p.role] || ''}`}>
                        {p.role}
                      </span>
                    </div>
                    <span className="role-switcher__option-desc">{p.description}</span>
                  </div>
                  {isSelected && <span className="role-switcher__check">✓</span>}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};
