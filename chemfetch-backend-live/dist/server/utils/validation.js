export function isValidCode(code) {
    return typeof code === 'string' && /^[A-Za-z0-9_-]{1,64}$/.test(code);
}
export function isValidName(name) {
    if (typeof name !== 'string')
        return false;
    return name.trim().length > 0 && name.length <= 100;
}
export function isValidSize(size) {
    if (typeof size !== 'string')
        return false;
    return size.trim().length > 0 && size.length <= 50;
}
