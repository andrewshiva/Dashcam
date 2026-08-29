const VALID_AUTH_ROLES = new Set(['administrator', 'ro']);

export const normalizeUsername = (username) => (
  String(username || '').trim().toLowerCase().replace(/\s+/g, ' ')
);

export const createUserSession = (user) => {
  const username = normalizeUsername(user?.username);
  const role = String(user?.role || '').trim().toLowerCase();
  const displayName = String(user?.displayName || user?.display_name || username).trim();

  if (!username || !VALID_AUTH_ROLES.has(role)) {
    return null;
  }

  return {
    username,
    role,
    displayName: displayName || username,
  };
};
