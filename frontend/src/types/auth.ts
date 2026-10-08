export type UserRole = 'CUSTOMER' | 'ADVISOR' | 'ADMIN';

export type PersonaId = 'alice' | 'bob' | 'carol' | 'frank' | 'grace' | 'dan' | 'erin';

export interface Persona {
  id: PersonaId;
  token: string;
  name: string;
  username: string;
  role: UserRole;
  description: string;
  avatar: string;
}

export const PERSONAS: Record<PersonaId, Persona> = {
  alice: {
    id: 'alice',
    token: 'stub-token-alice',
    name: 'Alice Fernandes',
    username: 'alice.customer',
    role: 'CUSTOMER',
    description: 'Moderate profile, $100k+ portfolio, drift breached',
    avatar: 'AF',
  },
  bob: {
    id: 'bob',
    token: 'stub-token-bob',
    name: 'Bob Mathew',
    username: 'bob.customer',
    role: 'CUSTOMER',
    description: 'Aggressive risk profile, advisor overridden',
    avatar: 'BM',
  },
  carol: {
    id: 'carol',
    token: 'stub-token-carol',
    name: 'Carol Dsouza',
    username: 'carol.customer',
    role: 'CUSTOMER',
    description: 'Unassessed profile, unverified KYC',
    avatar: 'CD',
  },
  frank: {
    id: 'frank',
    token: 'stub-token-frank',
    name: 'Frank Miller',
    username: 'frank.customer',
    role: 'CUSTOMER',
    description: 'Aggressive profile, 48m goal horizon',
    avatar: 'FM',
  },
  grace: {
    id: 'grace',
    token: 'stub-token-grace',
    name: 'Grace Hopper',
    username: 'grace.customer',
    role: 'CUSTOMER',
    description: 'Moderate profile, 29m goal horizon',
    avatar: 'GH',
  },
  dan: {
    id: 'dan',
    token: 'stub-token-dan',
    name: 'Dan Advisor',
    username: 'dan.advisor',
    role: 'ADVISOR',
    description: 'Senior Wealth Advisor (overrides & workbench)',
    avatar: 'DA',
  },
  erin: {
    id: 'erin',
    token: 'stub-token-erin',
    name: 'Erin Admin',
    username: 'erin.admin',
    role: 'ADMIN',
    description: 'Platform Admin (templates, policies, NAV)',
    avatar: 'EA',
  },
};
