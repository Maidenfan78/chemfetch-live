export function isValidCode(code: any): code is string {
  return typeof code === 'string' && /^[A-Za-z0-9_-]{1,64}$/.test(code);
}

export function isValidName(name: any): name is string {
  if (typeof name !== 'string') return false;
  return name.trim().length > 0 && name.length <= 100;
}

export function isValidSize(size: any): size is string {
  if (typeof size !== 'string') return false;
  return size.trim().length > 0 && size.length <= 50;
}
