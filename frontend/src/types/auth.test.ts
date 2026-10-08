import { describe, expect, it } from 'vitest';
import { PERSONAS } from './auth';

describe('Persona configuration', () => {
  it('defines all required personas with valid stub tokens and roles', () => {
    expect(PERSONAS.alice.role).toBe('CUSTOMER');
    expect(PERSONAS.alice.token).toBe('stub-token-alice');

    expect(PERSONAS.bob.role).toBe('CUSTOMER');
    expect(PERSONAS.bob.token).toBe('stub-token-bob');

    expect(PERSONAS.carol.role).toBe('CUSTOMER');
    expect(PERSONAS.carol.token).toBe('stub-token-carol');

    expect(PERSONAS.dan.role).toBe('ADVISOR');
    expect(PERSONAS.dan.token).toBe('stub-token-dan');

    expect(PERSONAS.erin.role).toBe('ADMIN');
    expect(PERSONAS.erin.token).toBe('stub-token-erin');
  });
});
