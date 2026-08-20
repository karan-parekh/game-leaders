export type AuthForm = { username: string; password: string };

const USERNAME_PATTERN = /^[A-Za-z0-9_]+$/;

export function usernameError(username: string, required = false) {
  if (required && username.length === 0) return "At least 3 characters";
  if (username.length > 0 && username.length < 3) return "At least 3 characters";
  if (username.length > 32) return "At most 32 characters";
  if (username.length > 0 && !USERNAME_PATTERN.test(username)) return "Letters, numbers, and underscores only";
  return "";
}

export function passwordError(password: string, required = false) {
  if (required && password.length === 0) return "At least 8 characters";
  if (password.length > 0 && password.length < 8) return "At least 8 characters";
  if (password.length > 128) return "At most 128 characters";
  return "";
}

export function validate(form: AuthForm) {
  const errors = {
    username: usernameError(form.username, true),
    password: passwordError(form.password, true),
  };
  return { errors, valid: errors.username === "" && errors.password === "" };
}
