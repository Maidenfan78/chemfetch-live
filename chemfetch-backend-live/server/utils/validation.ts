export function isValidCode(code: unknown): code is string {
  return typeof code === 'string' && /^[A-Za-z0-9_-]{1,64}$/.test(code);
}

export function isValidName(name: unknown): name is string {
  if (typeof name !== 'string') return false;
  const trimmed = name.trim();
  return trimmed.length > 0 && trimmed.length <= 100;
}

export function isValidSize(size: unknown): size is string {
  if (typeof size !== 'string') return false;
  const trimmed = size.trim();
  return trimmed.length > 0 && trimmed.length <= 50;
}
