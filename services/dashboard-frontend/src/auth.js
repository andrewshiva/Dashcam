export const AUTH_USERS = {
  administrator: {
    username: 'administrator',
    aliases: ['administrator', 'admin'],
    password: 'Admin@123',
    role: 'administrator',
    displayName: 'Administrator',
  },
  ro: {
    username: 'ro',
    aliases: ['ro', 'ro user', 'regional officer'],
    password: 'Ro@123',
    role: 'ro',
    displayName: 'RO User',
  },
};

export const normalizeUsername = (username) => (
  String(username || '').trim().toLowerCase().replace(/\s+/g, ' ')
);

const normalizePassword = (password) => String(password || '').trim();

const AUTH_USER_LOOKUP = Object.values(AUTH_USERS).reduce((lookup, user) => {
  user.aliases.forEach((alias) => {
    lookup[normalizeUsername(alias)] = user;
  });
  return lookup;
}, {});

export const findAuthUser = (username) => AUTH_USER_LOOKUP[normalizeUsername(username)] || null;

export const createUserSession = (user) => ({
  username: user.username,
  role: user.role,
  displayName: user.displayName,
});

export const authenticateUser = ({ username, password }) => {
  const knownUser = findAuthUser(username);

  if (!knownUser || knownUser.password !== normalizePassword(password)) {
    return null;
  }

  return createUserSession(knownUser);
};
